#!/usr/bin/env python3
"""Probe MVT tiles around point-cluster representations found in positive z8 parents.

This is a diagnostic only. It tests the point's own tile and its eight immediate
neighbours at z9-z12 to distinguish tile-edge/zoom representation effects from
a consistently unavailable target tile. It never changes the monitoring plan.
"""
from __future__ import annotations
import argparse, hashlib, json, math, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import mapbox_vector_tile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORLD = 20037508.342789244
LOCAL = threading.local()


def world_to_tile(x: float, y: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    tx = math.floor((x + WORLD) / (2 * WORLD) * n)
    ty = math.floor((WORLD - y) / (2 * WORLD) * n)
    return min(max(tx, 0), n - 1), min(max(ty, 0), n - 1)


def tile_neighbourhood(z: int, x: int, y: int) -> list[tuple[int, int, int]]:
    n = 2 ** z
    return [(z, xx, yy)
            for yy in range(max(0, y - 1), min(n, y + 2))
            for xx in range(max(0, x - 1), min(n, x + 2))]


def session() -> requests.Session:
    if getattr(LOCAL, "session", None) is None:
        retry = Retry(total=3, connect=3, read=2, status=2, backoff_factor=0.8,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET"], respect_retry_after_header=True)
        s = requests.Session()
        s.headers.update({"User-Agent": "Skog-SCA-cluster-point-probe/1.0",
                          "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf, */*"})
        s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4))
        LOCAL.session = s
    return LOCAL.session


def point_candidates(overlap_report: dict) -> list[dict]:
    points = []
    seen = set()
    for row in overlap_report.get("rows", []):
        child = row.get("child_z9", {})
        for hit in row.get("intersections", []):
            if hit.get("parent_geometry_type") != "Point":
                continue
            bounds = hit.get("bounds_epsg3857")
            if not bounds or len(bounds) != 4:
                continue
            x, y = float(bounds[0]), float(bounds[1])
            key = (round(x, 3), round(y, 3), hit.get("layer"), hit.get("feature_index"))
            if key in seen:
                continue
            seen.add(key)
            points.append({
                "point_id": hashlib.sha256(repr(key).encode()).hexdigest()[:16],
                "x_epsg3857": x, "y_epsg3857": y,
                "source_child_z9": child,
                "source_layer": hit.get("layer"),
                "source_feature_index": hit.get("feature_index"),
                "source_mvt_id": hit.get("mvt_id"),
                "source_properties": hit.get("properties", {}),
                "source_parent_geometry_type": hit.get("parent_geometry_type"),
            })
    return points


def fetch_tile(key: tuple[int, int, int]) -> dict:
    z, x, y = key
    url = URL.format(z=z, x=x, y=y)
    try:
        response = session().get(url, timeout=(20, 60))
        body = response.content
        base = {"z": z, "x": x, "y": y, "url": url,
                "http_status": response.status_code, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if body else None,
                "content_type": response.headers.get("Content-Type")}
        if response.status_code == 404:
            return {**base, "state": "not_found_404"}
        if response.status_code != 200:
            return {**base, "state": "http_error"}
        try:
            decoded = mapbox_vector_tile.decode(body)
            counts = {name: len(layer.get("features", [])) for name, layer in decoded.items()}
            total = sum(counts.values())
            return {**base, "state": "valid_mvt_with_features" if total else "valid_mvt_empty",
                    "feature_count": total, "layer_feature_counts": counts}
        except Exception as exc:
            return {**base, "state": "decode_error", "error": str(exc)[:240]}
    except Exception as exc:
        return {"z": z, "x": x, "y": y, "url": url,
                "state": "request_error", "error": str(exc)[:240]}


def run(overlap_path: Path, out_path: Path, workers: int = 4):
    overlap = json.loads(overlap_path.read_text(encoding="utf-8"))
    points = point_candidates(overlap)
    plan = {}
    for point in points:
        point["target_tiles"] = {}
        for z in range(9, 13):
            x, y = world_to_tile(point["x_epsg3857"], point["y_epsg3857"], z)
            point["target_tiles"][str(z)] = {"x": x, "y": y}
            for key in tile_neighbourhood(z, x, y):
                plan[key] = True
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(fetch_tile, key): key for key in sorted(plan)}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                results[key] = {"z": key[0], "x": key[1], "y": key[2],
                                "state": "worker_error", "error": str(exc)[:240]}
    for point in points:
        point["zoom_results"] = {}
        for z in range(9, 13):
            target = point["target_tiles"][str(z)]
            center = results[(z, target["x"], target["y"])]
            nearby = [results[k] for k in tile_neighbourhood(z, target["x"], target["y"])
                      if k != (z, target["x"], target["y"])]
            point["zoom_results"][str(z)] = {
                "target_state": center["state"],
                "target_http_status": center.get("http_status"),
                "neighbour_state_counts": {
                    state: sum(1 for item in nearby if item["state"] == state)
                    for state in sorted({item["state"] for item in nearby})
                },
                "positive_neighbour_tiles": [
                    {k: item.get(k) for k in ("z", "x", "y", "state", "feature_count", "layer_feature_counts")}
                    for item in nearby if item["state"] == "valid_mvt_with_features"
                ],
            }
    state_counts = {}
    for item in results.values():
        state_counts[item["state"]] = state_counts.get(item["state"], 0) + 1
    out = {
        "schema_version": 1,
        "purpose": "Point-directed MVT probes around parent features that overlap z9 404 children.",
        "source_overlap_report": str(overlap_path),
        "source_point_count": len(points),
        "unique_tiles_probed": len(results),
        "state_counts": state_counts,
        "points": points,
        "tile_results": [results[k] for k in sorted(results)],
        "interpretation_limits": [
            "MVT point clusters are generalized representations, not necessarily exact source-object coordinates.",
            "A positive neighbouring tile does not prove the target tile should contain the same feature.",
            "A 404 is unavailable/unknown, not proof of geographic absence.",
            "This diagnostic does not alter monitoring plans or merge geometries."
        ]
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("source_point_count", "unique_tiles_probed", "state_counts")}, indent=2))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlap", type=Path, default=Path("output/sca-parent-child-geometry-overlap.json"))
    parser.add_argument("--out", type=Path, default=Path("output/sca-cluster-point-targeted-probes.json"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    run(args.overlap, args.out, args.workers)


if __name__ == "__main__":
    main()
