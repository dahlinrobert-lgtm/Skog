#!/usr/bin/env python3
"""Harvest deterministic, globally deduplicated SCA voluntary z12 XYZ tiles.

The national target set is the union of all z12 descendants of every
voluntary-positive z9 census tile plus a configurable neighbor ring. The
global union is partitioned into non-overlapping batches, so no z12 tile is
requested by more than one batch. Raw MVT geometries and tile provenance are
preserved; no feature deduplication or area aggregation is performed.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mapbox_vector_tile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

Z0, Z = 9, 12
URL = "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORKERS = 3
TIMEOUT = (20, 60)
OUT = Path("sca-national-voluntary-tile-expansion-z12.json")
SESSION_LOCAL = threading.local()


def load_positive_seeds():
    candidates = sorted(Path("seed").glob("*.json"))
    if len(candidates) != 1:
        raise SystemExit(
            f"Expected exactly one census JSON in seed/, found {len(candidates)}: "
            + ", ".join(str(p) for p in candidates)
        )
    source = candidates[0]
    census = json.loads(source.read_text(encoding="utf-8"))
    rows = census.get("tile_results", [])
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"Census JSON has no tile_results: {source}")
    positive_rows = [
        row for row in rows
        if row.get("voluntary", {}).get("state") == "valid_mvt_with_features"
    ]
    positive_rows.sort(key=lambda row: (
        -sum(int(layer.get("feature_count", 0))
             for layer in row.get("voluntary", {}).get("layers", [])),
        int(row["x"]), int(row["y"])
    ))
    seeds = [(int(row["x"]), int(row["y"])) for row in positive_rows]
    if not seeds:
        raise SystemExit("No voluntary-positive z9 seeds found in census artifact")
    return seeds, census.get("summary", {}), source.name


def build_global_tile_plan(seeds, radius):
    """Return sorted unique z12 tiles and their parent z9 seed provenance."""
    descendants = 2 ** (Z - Z0)
    owners = {}
    for sx, sy in seeds:
        for dx in range(descendants):
            for dy in range(descendants):
                x, y = sx * descendants + dx, sy * descendants + dy
                for ox in range(-radius, radius + 1):
                    for oy in range(-radius, radius + 1):
                        xx, yy = x + ox, y + oy
                        if 0 <= xx < 2 ** Z and 0 <= yy < 2 ** Z:
                            owners.setdefault((xx, yy), set()).add((sx, sy))
    return owners


def get_session():
    session = getattr(SESSION_LOCAL, "session", None)
    if session is None:
        retry = Retry(
            total=4, connect=4, read=3, status=3, backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"], respect_retry_after_header=True
        )
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Skog-SCA-national-voluntary-z12/2.0",
            "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf, */*"
        })
        session.mount("https://", HTTPAdapter(
            max_retries=retry, pool_connections=4, pool_maxsize=4
        ))
        SESSION_LOCAL.session = session
    return session


def decode_tile(x, y, parents):
    url = URL.format(z=Z, x=x, y=y)
    try:
        response = get_session().get(url, timeout=TIMEOUT)
        raw = response.content
        base = {
            "http_status": response.status_code,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
            "url": url,
            "covering_z9_seeds": [
                {"z": Z0, "x": sx, "y": sy}
                for sx, sy in sorted(parents)
            ],
        }
        if response.status_code == 404:
            return {**base, "state": "not_found_404", "layers": []}
        if response.status_code != 200:
            return {**base, "state": "http_error", "layers": []}
        try:
            decoded = mapbox_vector_tile.decode(raw)
            layers = []
            for name, obj in decoded.items():
                feats = obj.get("features", [])
                layers.append({
                    "name": name,
                    "extent": obj.get("extent"),
                    "feature_count": len(feats),
                    "features": [{
                        "id": feature.get("id"),
                        "type": (feature.get("geometry") or {}).get("type"),
                        "geometry": feature.get("geometry"),
                        "properties": feature.get("properties") or {},
                    } for feature in feats],
                })
            count = sum(layer["feature_count"] for layer in layers)
            return {
                **base,
                "state": "valid_mvt_with_features" if count else "valid_mvt_empty",
                "layers": layers,
            }
        except Exception as exc:
            return {**base, "state": "decode_error",
                    "error": str(exc)[:240], "layers": []}
    except Exception as exc:
        return {"state": "request_error", "error": str(exc)[:240],
                "url": url, "covering_z9_seeds": [
                    {"z": Z0, "x": sx, "y": sy}
                    for sx, sy in sorted(parents)
                ], "layers": []}


def main():
    batch = max(0, int(os.getenv("BATCH", "0")))
    batch_size = max(1, min(1000, int(os.getenv("BATCH_SIZE", "500"))))
    radius = max(0, min(2, int(os.getenv("RADIUS", "1"))))
    seeds, seed_summary, census_file = load_positive_seeds()
    owners = build_global_tile_plan(seeds, radius)
    all_tiles = sorted(owners)
    total_batches = (len(all_tiles) + batch_size - 1) // batch_size
    start = batch * batch_size
    selected = all_tiles[start:start + batch_size]
    if not selected:
        raise SystemExit(
            f"Batch {batch} has no tiles; unique targets={len(all_tiles)}, "
            f"batch_size={batch_size}, total_batches={total_batches}"
        )
    targets = [(x, y, owners[(x, y)]) for x, y in selected]
    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {
            pool.submit(decode_tile, x, y, parents): (x, y, parents)
            for x, y, parents in targets
        }
        for index, future in enumerate(as_completed(futures), 1):
            x, y, parents = futures[future]
            result = future.result()
            rows.append({"z": Z, "x": x, "y": y, **result})
            if index % 25 == 0 or index == len(futures):
                rows.sort(key=lambda item: (item["x"], item["y"]))
                payload = {
                    "purpose": "National SCA voluntary-set-aside z12 MVT harvest, partitioned into globally unique tile batches.",
                    "source": URL,
                    "zoom": Z,
                    "batch": batch,
                    "batch_size": batch_size,
                    "batch_count": total_batches,
                    "batch_tile_start_index": start,
                    "batch_tile_end_index_exclusive": start + len(selected),
                    "neighbor_radius": radius,
                    "census_artifact_file": census_file,
                    "z9_positive_seed_count": len(seeds),
                    "seed_census_summary": seed_summary,
                    "global_unique_z12_target_tiles": len(all_tiles),
                    "selected_z12_tiles": len(selected),
                    "tile_results": rows,
                    "interpretation": [
                        "The global z12 tile plan is a union across all positive z9 seeds; a z12 tile appears in exactly one batch.",
                        "Each tile records every z9 seed whose descendant neighborhood includes that tile.",
                        "Tile feature records are not counts of unique voluntary set-asides.",
                        "Raw MVT geometry is retained in decoder tile-local coordinates with source tile and hash provenance.",
                        "HTTP 404 is not proof that the geographic area lacks a set-aside.",
                        "No deduplication, dissolve, or area totals are asserted."
                    ]
                }
                OUT.write_text(
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8"
                )
                print(json.dumps({
                    "batch": batch, "completed": index, "total": len(selected),
                    "state_counts": dict(Counter(row["state"] for row in rows)),
                }, ensure_ascii=False), flush=True)
    rows.sort(key=lambda item: (item["x"], item["y"]))
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print(json.dumps({
        "batch": batch,
        "batch_count": total_batches,
        "positive_z9_seeds": len(seeds),
        "global_unique_z12_target_tiles": len(all_tiles),
        "selected_z12_tiles": len(selected),
        "state_counts": dict(Counter(row["state"] for row in rows)),
        "feature_records": sum(
            sum(layer["feature_count"] for layer in row.get("layers", []))
            for row in rows
        ),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
