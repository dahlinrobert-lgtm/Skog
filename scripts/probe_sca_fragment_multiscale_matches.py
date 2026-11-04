#!/usr/bin/env python3
"""Compare the 20 same-class SCA fragment-signal pairs across bounded MVT zooms.

For each pair, query a small neighborhood around both source-feature
representative points at z9/z11/z13/z15. Compare same-class MVT features
against both traced z12 source geometries. This is a cross-scale diagnostic,
not object identity resolution.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mapbox_vector_tile
import requests
from pyproj import Transformer
from requests.adapters import HTTPAdapter
from shapely.geometry import shape
from shapely.ops import transform
from urllib3.util.retry import Retry

INPUT = Path("input")
OUT = Path("output")
BASE_URL = "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORLD = 20037508.342789244
ZOOMS = (9, 11, 13, 15)
MAX_TILES = int(os.environ.get("MAX_TILES", "900"))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "4"))
TO_3006 = Transformer.from_crs("EPSG:3857", "EPSG:3006", always_xy=True).transform


def tile_xy_from_3857(x: float, y: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    span = (2 * WORLD) / n
    tx = int(math.floor((x + WORLD) / span))
    ty = int(math.floor((WORLD - y) / span))
    return max(0, min(n - 1, tx)), max(0, min(n - 1, ty))


def tile_to_3857(geom, tx: int, ty: int, z: int, extent: int):
    span = (2 * WORLD) / (2 ** z)
    def convert(x, y, z_value=None):
        xx = -WORLD + (tx + x / extent) * span
        yy = WORLD - (ty + y / extent) * span
        return (xx, yy) if z_value is None else (xx, yy, z_value)
    return transform(convert, geom)


def get_property(properties: dict, token: str):
    token = token.casefold()
    preferred = {
        "skotsel_kl": ("SKOTSEL_KL_resolved", "SKOTSEL_KL"),
        "motiv": ("MOTIV_resolved", "MOTIV"),
    }.get(token, ())
    for key in preferred:
        if key in properties and properties[key] not in (None, ""):
            return str(properties[key])
    for key, value in properties.items():
        if token in str(key).casefold() and value not in (None, ""):
            return str(value)
    return ""


def normalize(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def build_tile_plan(points_by_pair: dict, zooms=ZOOMS):
    plan = set()
    for pair_id, sides in points_by_pair.items():
        for side in ("a", "b"):
            geom = sides[side]
            p = geom.representative_point()
            for z in zooms:
                tx, ty = tile_xy_from_3857(p.x, p.y, z)
                radius = 0 if z in (9, 11) else 1
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        x, y = tx + dx, ty + dy
                        if 0 <= x < 2 ** z and 0 <= y < 2 ** z:
                            plan.add((z, x, y))
    return sorted(plan)


def session():
    retry = Retry(
        total=2, connect=2, read=1, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
    )
    s = requests.Session()
    s.headers.update({"User-Agent": "Skog-SCA-bounded-multiscale-review/1.0"})
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def fetch_tile(tile_key):
    z, x, y = tile_key
    url = BASE_URL.format(z=z, x=x, y=y)
    try:
        response = session().get(url, timeout=(10, 25))
        row = {
            "z": z, "x": x, "y": y, "url": url,
            "http_status": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "bytes": len(response.content),
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "error": "",
        }
        if response.status_code != 200:
            return row, []
        decoded = mapbox_vector_tile.decode(
            response.content, default_options={"y_coord_down": True}
        )
        features = []
        for layer_name, layer in decoded.items():
            if "frivillig" not in layer_name.casefold() and "avsatt" not in layer_name.casefold():
                continue
            extent = int(layer.get("extent") or 4096)
            for feature_index, feature in enumerate(layer.get("features", [])):
                geometry = feature.get("geometry")
                if not geometry:
                    continue
                try:
                    geom = tile_to_3857(
                        shape(geometry), x, y, z, extent
                    )
                    if geom.is_empty or not geom.is_valid:
                        continue
                    props = feature.get("properties") or {}
                    features.append({
                        "z": z, "x": x, "y": y,
                        "layer": layer_name,
                        "feature_index": feature_index,
                        "feature_id": feature.get("id"),
                        "class_value": get_property(props, "skotsel_kl"),
                        "motive_value": get_property(props, "motiv"),
                        "properties": props,
                        "geometry": geom,
                        "tile_sha256": row["sha256"],
                    })
                except Exception:
                    continue
        row["decoded_feature_count"] = len(features)
        return row, features
    except Exception as exc:
        return {
            "z": z, "x": x, "y": y, "url": url,
            "http_status": None, "content_type": "",
            "bytes": 0, "sha256": "", "error": f"{type(exc).__name__}: {exc}"[:250],
        }, []


def load_inputs():
    csvs = sorted(INPUT.rglob("sca-overlap-source-trace.csv"))
    geojsons = sorted(INPUT.rglob("sca-overlap-source-trace.geojson"))
    if len(csvs) != 1 or len(geojsons) != 1:
        raise SystemExit("Expected exactly one source trace CSV and GeoJSON")
    with csvs[0].open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    geojson = json.loads(geojsons[0].read_text(encoding="utf-8"))
    geometries = {
        str(feature["id"]): shape(feature["geometry"])
        for feature in geojson.get("features", [])
    }
    pairs = defaultdict(dict)
    for row in rows:
        if row.get("review_bucket") != "partial_same_class_fragment_signal":
            continue
        pair_id = str(row["relation_sample_id"])
        side = str(row["side"])
        geom = geometries.get(f"sample-{pair_id}-{side}")
        if geom is None or geom.is_empty or not geom.is_valid:
            raise SystemExit(f"Missing or invalid source geometry for pair {pair_id} side {side}")
        props = json.loads(row.get("raw_properties_json") or "{}")
        row["_class_value"] = get_property(props, "skotsel_kl")
        row["_motive_value"] = get_property(props, "motiv")
        row["_geometry"] = geom
        pairs[pair_id][side] = row
    pairs = {k: v for k, v in pairs.items() if set(v) == {"a", "b"}}
    if len(pairs) != 20:
        raise SystemExit(f"Expected 20 same-class fragment-signal pairs, found {len(pairs)}")
    return pairs


def similarity(source_geom, candidate_geom):
    source_m = transform(TO_3006, source_geom)
    candidate_m = transform(TO_3006, candidate_geom)
    inter = source_m.intersection(candidate_m).area
    source_area = source_m.area
    candidate_area = candidate_m.area
    union = source_area + candidate_area - inter
    return {
        "source_coverage": inter / source_area if source_area else 0.0,
        "candidate_coverage": inter / candidate_area if candidate_area else 0.0,
        "overlap_smaller_fraction": inter / min(source_area, candidate_area) if min(source_area, candidate_area) else 0.0,
        "iou": inter / union if union else 0.0,
        "intersection_m2_epsg3006": inter,
        "distance_m_epsg3006": source_m.distance(candidate_m),
    }


def select_best_candidates(candidates):
    candidates_a = [c for c in candidates if c["sim_a"]["intersection_m2_epsg3006"] > 0]
    candidates_b = [c for c in candidates if c["sim_b"]["intersection_m2_epsg3006"] > 0]
    candidates_common = [
        c for c in candidates
        if c["sim_a"]["intersection_m2_epsg3006"] > 0
        and c["sim_b"]["intersection_m2_epsg3006"] > 0
    ]
    best_a = max(candidates_a, key=lambda c: (c["sim_a"]["source_coverage"], -c["sim_a"]["distance_m_epsg3006"]), default=None)
    best_b = max(candidates_b, key=lambda c: (c["sim_b"]["source_coverage"], -c["sim_b"]["distance_m_epsg3006"]), default=None)
    # A common candidate must geometrically intersect BOTH original source
    # fragments. Never label a one-sided match as common.
    best_common = max(
        candidates_common,
        key=lambda c: (
            min(c["sim_a"]["source_coverage"], c["sim_b"]["source_coverage"]),
            c["sim_a"]["source_coverage"] + c["sim_b"]["source_coverage"],
            -c["sim_a"]["distance_m_epsg3006"] - c["sim_b"]["distance_m_epsg3006"],
        ),
        default=None,
    )
    return best_a, best_b, best_common


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = load_inputs()
    points = {
        pair_id: {"a": sides["a"]["_geometry"], "b": sides["b"]["_geometry"]}
        for pair_id, sides in pairs.items()
    }
    tile_plan = build_tile_plan(points)
    if len(tile_plan) > MAX_TILES:
        raise SystemExit(
            f"Planned {len(tile_plan)} tile requests, exceeding MAX_TILES={MAX_TILES}; "
            "reduce the neighborhood or raise the explicit limit."
        )
    tile_rows, tile_features = [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_tile, key): key for key in tile_plan}
        for future in as_completed(futures):
            row, features = future.result()
            tile_rows.append(row)
            tile_features.extend(features)
    tile_rows.sort(key=lambda r: (r["z"], r["x"], r["y"]))
    features_by_zoom = defaultdict(list)
    for feature in tile_features:
        features_by_zoom[feature["z"]].append(feature)

    pair_output = []
    for pair_id, sides in sorted(pairs.items(), key=lambda x: int(x[0])):
        source_a, source_b = sides["a"], sides["b"]
        class_a, class_b = source_a["_class_value"], source_b["_class_value"]
        if normalize(class_a) != normalize(class_b):
            raise SystemExit(f"Pair {pair_id} is not same-class despite fragment bucket")
        source_a_geom, source_b_geom = source_a["_geometry"], source_b["_geometry"]
        for z in ZOOMS:
            candidates = []
            for candidate in features_by_zoom[z]:
                if normalize(candidate["class_value"]) != normalize(class_a):
                    continue
                sim_a = similarity(source_a_geom, candidate["geometry"])
                sim_b = similarity(source_b_geom, candidate["geometry"])
                if sim_a["intersection_m2_epsg3006"] <= 0 and sim_b["intersection_m2_epsg3006"] <= 0:
                    continue
                candidate = {**candidate, "sim_a": sim_a, "sim_b": sim_b}
                candidates.append(candidate)
            best_a, best_b, best_common = select_best_candidates(candidates)
            pair_output.append({
                "relation_sample_id": pair_id,
                "review_bucket": "partial_same_class_fragment_signal",
                "source_class": class_a,
                "source_motive_a": source_a["_motive_value"],
                "source_motive_b": source_b["_motive_value"],
                "zoom": z,
                "tile_requests_at_zoom": sum(1 for t in tile_rows if t["z"] == z),
                "successful_tiles_at_zoom": sum(1 for t in tile_rows if t["z"] == z and t["http_status"] == 200),
                "same_class_candidate_features_in_neighborhood": len(candidates),
                "best_candidate_locator": (
                    f'{best_common["z"]}/{best_common["x"]}/{best_common["y"]}/'
                    f'{best_common["layer"]}/{best_common["feature_index"]}' if best_common else ""
                ),
                "best_candidate_feature_id": best_common["feature_id"] if best_common else "",
                "best_candidate_motive": best_common["motive_value"] if best_common else "",
                "best_candidate_motive_matches_a": (
                    normalize(best_common["motive_value"]) == normalize(source_a["_motive_value"])
                    if best_common and source_a["_motive_value"] else None
                ),
                "best_candidate_motive_matches_b": (
                    normalize(best_common["motive_value"]) == normalize(source_b["_motive_value"])
                    if best_common and source_b["_motive_value"] else None
                ),
                "best_single_candidate_source_a_coverage": best_common["sim_a"]["source_coverage"] if best_common else 0.0,
                "best_single_candidate_source_b_coverage": best_common["sim_b"]["source_coverage"] if best_common else 0.0,
                "best_single_candidate_min_source_coverage": min(
                    best_common["sim_a"]["source_coverage"], best_common["sim_b"]["source_coverage"]
                ) if best_common else 0.0,
                "best_single_candidate_iou_a": best_common["sim_a"]["iou"] if best_common else 0.0,
                "best_single_candidate_iou_b": best_common["sim_b"]["iou"] if best_common else 0.0,
                "best_single_candidate_distance_a_m": best_common["sim_a"]["distance_m_epsg3006"] if best_common else None,
                "best_single_candidate_distance_b_m": best_common["sim_b"]["distance_m_epsg3006"] if best_common else None,
                "best_a_locator": (
                    f'{best_a["z"]}/{best_a["x"]}/{best_a["y"]}/{best_a["layer"]}/{best_a["feature_index"]}'
                    if best_a else ""
                ),
                "best_a_source_coverage": best_a["sim_a"]["source_coverage"] if best_a else 0.0,
                "best_b_locator": (
                    f'{best_b["z"]}/{best_b["x"]}/{best_b["y"]}/{best_b["layer"]}/{best_b["feature_index"]}'
                    if best_b else ""
                ),
                "best_b_source_coverage": best_b["sim_b"]["source_coverage"] if best_b else 0.0,
                "identity_resolved": False,
                "interpretation": "cross_zoom_mvt_candidate_match_only_not_source_object_identity",
            })

    with (OUT / "sca-fragment-multiscale-pair-matches.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(pair_output[0].keys()))
        writer.writeheader()
        writer.writerows(pair_output)
    with (OUT / "sca-fragment-multiscale-tile-requests.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(tile_rows[0].keys()) if tile_rows else [])
        writer.writeheader()
        writer.writerows(tile_rows)

    summary = {
        "input_same_class_fragment_pairs": len(pairs),
        "zooms_tested": list(ZOOMS),
        "unique_tile_requests_planned": len(tile_plan),
        "tile_http_200": sum(r["http_status"] == 200 for r in tile_rows),
        "tile_http_404": sum(r["http_status"] == 404 for r in tile_rows),
        "tile_other_or_error": sum(r["http_status"] not in (200, 404) for r in tile_rows),
        "decoded_candidate_features": len(tile_features),
        "pair_zoom_comparisons": len(pair_output),
        "pairs_with_common_candidate_min_coverage_ge_50pct_by_zoom": {
            str(z): sum(
                r["zoom"] == z and r["best_single_candidate_min_source_coverage"] >= 0.5
                for r in pair_output
            ) for z in ZOOMS
        },
        "pairs_with_common_candidate_min_coverage_ge_90pct_by_zoom": {
            str(z): sum(
                r["zoom"] == z and r["best_single_candidate_min_source_coverage"] >= 0.9
                for r in pair_output
            ) for z in ZOOMS
        },
        "identity_resolved_relations": 0,
        "limitations": [
            "This probes a bounded 3x3 neighborhood at z13/z15 and the containing tile at z9/z11 around each source-feature representative point.",
            "MVT feature IDs are treated as tile-local metadata and are not presumed globally stable or unique.",
            "A same-class candidate that overlaps both source geometries is evidence of cross-scale cartographic concordance, not proof of common source-object identity.",
            "Missing candidates may reflect zoom-dependent generalization, tile coverage, clipping, filtering or source changes.",
            "Only the 20 same-class fragment-signal pairs are examined; this is not a national coverage survey.",
            "No source geometry is merged, dissolved, deleted or modified."
        ]
    }
    (OUT / "sca-fragment-multiscale-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(pair_output) != len(pairs) * len(ZOOMS):
        raise SystemExit("Unexpected pair/zoom comparison count")
    if any(r["identity_resolved"] for r in pair_output):
        raise SystemExit("Identity resolution is prohibited in this diagnostic")


if __name__ == "__main__":
    main()
