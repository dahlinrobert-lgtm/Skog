#!/usr/bin/env python3
"""Stratified multi-zoom audit of SCA voluntary MVT tile availability.

The audit is diagnostic, not a national census. It samples positive and 404
z9 tiles, checks their z8 parent and z10-z12 descendants, and records response
signatures and decoded feature counts without merging geometries.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading
import requests
import mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
TIMEOUT = (20, 60)
LOCAL = threading.local()


def session():
    """Reuse one HTTP session per worker thread for connection pooling."""
    existing = getattr(LOCAL, "session", None)
    if existing is not None:
        return existing
    retry = Retry(total=3, connect=3, read=2, status=2, backoff_factor=1,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    s = requests.Session()
    s.headers.update({"User-Agent": "Skog-SCA-multizoom-coverage-audit/1.0",
                      "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf, */*"})
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=2))
    LOCAL.session = s
    return s


def classify_response(sess, z, x, y, seed, relation):
    url = URL.format(z=z, x=x, y=y)
    try:
        r = sess.get(url, timeout=TIMEOUT)
        raw = r.content
        result = {"z": z, "x": x, "y": y, "url": url,
                  "seed_z9": {"x": seed["x"], "y": seed["y"], "class": seed["class"]},
                  "relation": relation, "status": r.status_code, "bytes": len(raw),
                  "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                  "content_type": r.headers.get("Content-Type"),
                  "server": r.headers.get("Server")}
        if r.status_code == 404:
            return {**result, "state": "not_found_404",
                    "body_preview": raw[:240].decode("utf-8", errors="replace")}
        if r.status_code != 200:
            return {**result, "state": "http_error",
                    "body_preview": raw[:240].decode("utf-8", errors="replace")}
        try:
            decoded = mapbox_vector_tile.decode(raw)
            layers = []
            total = 0
            for name, layer in decoded.items():
                n = len(layer.get("features", []))
                total += n
                layers.append({"name": name, "feature_count": n})
            return {**result,
                    "state": "valid_mvt_with_features" if total else "valid_mvt_empty",
                    "feature_records": total, "layers": layers}
        except Exception as exc:
            return {**result, "state": "decode_error", "error": str(exc)[:240]}
    except Exception as exc:
        return {"z": z, "x": x, "y": y, "url": url,
                "seed_z9": {"x": seed["x"], "y": seed["y"], "class": seed["class"]},
                "relation": relation, "state": "request_error", "error": str(exc)[:240]}


def spread_select(rows, count, feature_first=False):
    """Deterministic farthest-point sample in tile space."""
    if not rows or count <= 0:
        return []
    remaining = list(rows)
    if feature_first:
        first = max(remaining, key=lambda r: (sum(x.get("feature_count", 0) for x in r.get("voluntary", {}).get("layers", [])), -r["x"], -r["y"]))
    else:
        first = min(remaining, key=lambda r: (r["x"], r["y"]))
    selected = [first]
    remaining.remove(first)
    while remaining and len(selected) < count:
        nxt = max(remaining, key=lambda r: (min((r["x"]-s["x"])**2 + (r["y"]-s["y"])**2 for s in selected), -r["x"], -r["y"]))
        selected.append(nxt)
        remaining.remove(nxt)
    return selected


def _grid_cell(x, y, bounds, columns=4, rows=4):
    min_x, max_x, min_y, max_y = bounds
    width = max(1, max_x - min_x + 1)
    height = max(1, max_y - min_y + 1)
    col = min(columns - 1, (int(x) - min_x) * columns // width)
    row = min(rows - 1, (int(y) - min_y) * rows // height)
    return row, col


def choose_seeds(census, per_class):
    """Sample positive, valid-empty and 404 tiles, including 404-only grid cells."""
    rows = census.get("tile_results", [])
    positives = [r for r in rows if r.get("voluntary", {}).get("state") == "valid_mvt_with_features"]
    empty = [r for r in rows if r.get("voluntary", {}).get("state") == "valid_mvt_empty"]
    missing = [r for r in rows if r.get("voluntary", {}).get("state") == "not_found_404"]

    positive = spread_select(positives, per_class, feature_first=True)
    empty_sample = spread_select(empty, per_class)

    if rows:
        bounds = (min(int(t["x"]) for t in rows), max(int(t["x"]) for t in rows),
                  min(int(t["y"]) for t in rows), max(int(t["y"]) for t in rows))
    else:
        bounds = (0, 0, 0, 0)
    positive_cells = {_grid_cell(r["x"], r["y"], bounds) for r in positives}

    # Reserve half the 404 sample for grid cells with no positive z9 response.
    # This deliberately probes areas the positive-only discovery path does not seed.
    no_positive_cell_404 = [
        r for r in missing if _grid_cell(r["x"], r["y"], bounds) not in positive_cells
    ]
    no_positive_sample = spread_select(no_positive_cell_404, per_class // 2)

    used = {(r["x"], r["y"]) for r in no_positive_sample}
    remaining_404 = [r for r in missing if (r["x"], r["y"]) not in used]
    adjacent = [r for r in remaining_404 if any(
        max(abs(r["x"] - p["x"]), abs(r["y"] - p["y"])) == 1 for p in positive
    )]
    adjacent_sample = spread_select(adjacent, per_class - len(no_positive_sample))
    used.update((r["x"], r["y"]) for r in adjacent_sample)
    rest = [r for r in remaining_404 if (r["x"], r["y"]) not in used]
    fill = spread_select(rest, per_class - len(no_positive_sample) - len(adjacent_sample))
    missing_sample = no_positive_sample + adjacent_sample + fill

    selected = []
    for rows_for_class, label in (
        (positive, "positive_z9"),
        (empty_sample, "valid_empty_z9"),
        (no_positive_sample, "not_found_404_z9_no_positive_cell"),
        (adjacent_sample + fill, "not_found_404_z9"),
    ):
        for row in rows_for_class:
            selected.append({"z": 9, "x": int(row["x"]), "y": int(row["y"]), "class": label})
    return selected


def spatial_state_summary(census, columns=4, rows=4):
    """Summarize z9 response states in a deterministic coarse spatial grid."""
    tiles = census.get("tile_results", [])
    if not tiles:
        return {"columns": columns, "rows": rows, "cells": []}
    min_x = min(int(t["x"]) for t in tiles)
    max_x = max(int(t["x"]) for t in tiles)
    min_y = min(int(t["y"]) for t in tiles)
    max_y = max(int(t["y"]) for t in tiles)
    width = max(1, max_x - min_x + 1)
    height = max(1, max_y - min_y + 1)
    cells = {}
    for tile in tiles:
        x, y = int(tile["x"]), int(tile["y"])
        col = min(columns - 1, (x - min_x) * columns // width)
        row = min(rows - 1, (y - min_y) * rows // height)
        cell = cells.setdefault((row, col), Counter())
        cell[tile.get("voluntary", {}).get("state", "pending")] += 1
    output = []
    for (row, col), counts in sorted(cells.items()):
        total = sum(counts.values())
        output.append({
            "row": row, "column": col, "tile_count": total,
            "positive_tiles": counts.get("valid_mvt_with_features", 0),
            "valid_empty_tiles": counts.get("valid_mvt_empty", 0),
            "not_found_404_tiles": counts.get("not_found_404", 0),
            "technical_or_unknown_tiles": sum(
                count for state, count in counts.items()
                if state not in {"valid_mvt_with_features", "valid_mvt_empty", "not_found_404"}
            ),
        })
    return {"columns": columns, "rows": rows, "cells": output}


def probes_for_seed(seed):
    x, y = seed["x"], seed["y"]
    coords = {(8, x // 2, y // 2, "parent_z8")}
    for z in (10, 11, 12):
        factor = 2 ** (z - 9)
        for dx in range(factor):
            for dy in range(factor):
                coords.add((z, x * factor + dx, y * factor + dy, "descendant"))
    return coords


def build_probe_jobs(seeds):
    """Return one request per unique tile while retaining every seed relationship."""
    jobs = defaultdict(list)
    for seed in seeds:
        for z, x, y, relation in probes_for_seed(seed):
            ref = {"seed_z9": {"x": seed["x"], "y": seed["y"], "class": seed["class"]},
                   "relation": relation}
            if ref not in jobs[(z, x, y)]:
                jobs[(z, x, y)].append(ref)
    return [(z, x, y, refs) for (z, x, y), refs in sorted(jobs.items())]


def run(census_path, out_path, per_class=8, workers=2):
    census = json.loads(Path(census_path).read_text(encoding="utf-8"))
    summary = census.get("summary", {})
    rows = census.get("tile_results", [])
    if not rows or int(summary.get("tiles_completed", 0)) != int(summary.get("tiles_in_bbox", -1)):
        raise ValueError("Cannot run multi-zoom audit from incomplete z9 census")
    seeds = choose_seeds(census, per_class)
    jobs = build_probe_jobs(seeds)

    def task(item):
        z, x, y, refs = item
        primary = refs[0]
        result = classify_response(session(), z, x, y, primary["seed_z9"], primary["relation"])
        result["seed_z9_refs"] = refs
        return result

    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(4, workers))) as pool:
        futures = [pool.submit(task, item) for item in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if i % 100 == 0 or i == len(futures):
                print(json.dumps({"progress": i, "total": len(futures)}), flush=True)
    results.sort(key=lambda r: (r["z"], r["x"], r["y"]))
    states_by_zoom = {}
    features_by_zoom = {}
    for z in (8, 10, 11, 12):
        subset = [r for r in results if r["z"] == z]
        states_by_zoom[str(z)] = dict(Counter(r["state"] for r in subset))
        features_by_zoom[str(z)] = sum(r.get("feature_records", 0) for r in subset)
    payload = {
        "schema_version": 1,
        "purpose": "Stratified diagnostic sample only; not a national inventory or completeness claim.",
        "source_layer": URL,
        "z9_census_tiles_completed": summary["tiles_completed"],
        "samples_per_class_requested": per_class,
        "sampled_classes": dict(Counter(seed["class"] for seed in seeds)),
        "sampled_z9_seed_spatial_cells": {
            f"{row}:{column}": sum(
                _grid_cell(seed["x"], seed["y"], (
                    min(int(t["x"]) for t in rows), max(int(t["x"]) for t in rows),
                    min(int(t["y"]) for t in rows), max(int(t["y"]) for t in rows)
                )) == (row, column)
                for seed in seeds
            )
            for row in range(4) for column in range(4)
        },
        "z9_spatial_state_summary": spatial_state_summary(census),
        "sampled_z9_seeds": seeds,
        "unique_probe_tiles": len(jobs),
        "probe_requests": len(results),
        "duplicate_probe_requests_avoided": sum(len(refs) - 1 for _, _, _, refs in jobs),
        "states_by_zoom": states_by_zoom,
        "feature_records_by_zoom": features_by_zoom,
        "positive_probe_tiles": [
            {k: r[k] for k in ("z", "x", "y", "state", "feature_records", "seed_z9_refs")}
            for r in results if r["state"] == "valid_mvt_with_features"
        ],
        "probe_results": results,
        "interpretation": [
            "A z9 404 is not interpreted as empty coverage.",
            "A unique probe tile is requested once even when it belongs to multiple sampled seeds.",
            "Positive z10-z12 descendants are valid discovery signals and can extend z12 monitoring.",
            "The sample is diagnostic and cannot prove national completeness.",
            "No geometries are merged, dissolved or assigned a stable global identity."
        ]
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("samples_per_class_requested", "unique_probe_tiles",
          "probe_requests", "duplicate_probe_requests_avoided", "states_by_zoom",
          "feature_records_by_zoom")}, ensure_ascii=False, indent=2))
    return payload


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--census", type=Path, default=Path("sca-national-independent-layer-census-z9.json"))
    p.add_argument("--out", type=Path, default=Path("output/sca-multizoom-coverage-audit.json"))
    p.add_argument("--samples-per-class", type=int, default=8)
    p.add_argument("--workers", type=int, default=2)
    a = p.parse_args()
    run(a.census, a.out, max(1, a.samples_per_class), a.workers)


if __name__ == "__main__":
    main()
