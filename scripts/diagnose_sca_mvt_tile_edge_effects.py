#!/usr/bin/env python3
"""Diagnose MVT tile-edge effects in a traced SCA overlap sample.

Calculates pair geometry metrics and each decoded feature's relation to its
nominal XYZ tile rectangle. It is diagnostic only: tile-buffer presence is
not proof of source-object identity.
"""
from __future__ import annotations
import csv, json, math
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, box, shape
from shapely.ops import transform

INPUT = Path("input")
OUT = Path("output")
WORLD = 20037508.342789244
ZOOM = 12
SPAN = (2 * WORLD) / (2 ** ZOOM)
TO_3006 = Transformer.from_crs("EPSG:3857", "EPSG:3006", always_xy=True).transform
EDGE_TOLERANCE_M = 10.0


def tile_bounds(tx: int, ty: int):
    xmin = -WORLD + tx * SPAN
    xmax = xmin + SPAN
    ymax = WORLD - ty * SPAN
    ymin = ymax - SPAN
    return xmin, ymin, xmax, ymax


def edge_metrics(geom, tx: int, ty: int, tolerance: float = EDGE_TOLERANCE_M):
    xmin, ymin, xmax, ymax = tile_bounds(tx, ty)
    tile = box(xmin, ymin, xmax, ymax)
    edges = [
        LineString([(xmin, ymin), (xmax, ymin)]),
        LineString([(xmax, ymin), (xmax, ymax)]),
        LineString([(xmax, ymax), (xmin, ymax)]),
        LineString([(xmin, ymax), (xmin, ymin)]),
    ]
    boundary_length = geom.boundary.length
    near_length = sum(geom.boundary.intersection(edge.buffer(tolerance)).length for edge in edges)
    near_length = min(near_length, boundary_length)
    area = geom.area
    outside_area = geom.difference(tile).area
    inside_area = geom.intersection(tile).area
    return {
        "nominal_tile_min_x": xmin,
        "nominal_tile_min_y": ymin,
        "nominal_tile_max_x": xmax,
        "nominal_tile_max_y": ymax,
        "min_distance_to_tile_edge_m": min(geom.boundary.distance(edge) for edge in edges),
        "boundary_length_within_edge_tolerance_m": near_length,
        "boundary_edge_share": near_length / boundary_length if boundary_length else 0.0,
        "outside_tile_area_m2_epsg3857": outside_area,
        "outside_tile_area_fraction": outside_area / area if area else 0.0,
        "inside_tile_area_fraction": inside_area / area if area else 0.0,
        "tile_edge_tolerance_m": tolerance,
    }


def pair_metrics(a, b):
    inter = a.intersection(b).area
    aa, ab = a.area, b.area
    smaller = min(aa, ab)
    union = aa + ab - inter
    return {
        "area_a_m2_epsg3006": aa,
        "area_b_m2_epsg3006": ab,
        "intersection_m2_epsg3006": inter,
        "overlap_smaller_fraction": inter / smaller if smaller else 0.0,
        "area_ratio": smaller / max(aa, ab) if max(aa, ab) else 0.0,
        "iou": inter / union if union else 0.0,
        "distance_m_epsg3006": a.distance(b),
        "hausdorff_m_epsg3006": a.hausdorff_distance(b),
    }


def classify_edge_pattern(a, b):
    adjacent = max(abs(int(a["source_tile_x"]) - int(b["source_tile_x"])),
                   abs(int(a["source_tile_y"]) - int(b["source_tile_y"]))) == 1
    near_a = float(a["min_distance_to_tile_edge_m"]) <= EDGE_TOLERANCE_M
    near_b = float(b["min_distance_to_tile_edge_m"]) <= EDGE_TOLERANCE_M
    outside_a = float(a["outside_tile_area_fraction"]) >= 0.05
    outside_b = float(b["outside_tile_area_fraction"]) >= 0.05
    if adjacent and near_a and near_b:
        return "both_features_near_nominal_tile_edge"
    if adjacent and ((near_a and outside_b) or (near_b and outside_a)):
        return "one_edge_contact_other_tile_buffer_candidate"
    if adjacent and (outside_a or outside_b):
        return "adjacent_pair_with_geometry_outside_nominal_tile"
    return "no_strong_nominal_tile_edge_signal"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    csv_paths = list(INPUT.rglob("sca-overlap-source-trace.csv"))
    geojson_paths = list(INPUT.rglob("sca-overlap-source-trace.geojson"))
    if len(csv_paths) != 1 or len(geojson_paths) != 1:
        raise SystemExit("Expected exactly one trace CSV and one trace GeoJSON in input/")
    with csv_paths[0].open(encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))
    gj = json.loads(geojson_paths[0].read_text(encoding="utf-8"))
    geometries = {str(feature["id"]): shape(feature["geometry"]) for feature in gj["features"]}
    by_pair = {}
    feature_rows = []
    for row in source_rows:
        pair_id = str(row["relation_sample_id"])
        side = str(row["side"])
        feature_id = f"sample-{pair_id}-{side}"
        if feature_id not in geometries:
            raise SystemExit(f"Missing geometry {feature_id}")
        geom = geometries[feature_id]
        if geom.is_empty or not geom.is_valid:
            raise SystemExit(f"Invalid geometry {feature_id}")
        tx, ty = int(row["source_tile_x"]), int(row["source_tile_y"])
        edge = edge_metrics(geom, tx, ty)
        rec = {**row, **edge}
        feature_rows.append(rec)
        by_pair.setdefault(pair_id, {})[side] = (row, geom, edge)
    pair_rows = []
    for pair_id, sides in sorted(by_pair.items(), key=lambda x: int(x[0])):
        if set(sides) != {"a", "b"}:
            raise SystemExit(f"Pair {pair_id} does not contain both sides")
        ra, ga, ea = sides["a"]
        rb, gb, eb = sides["b"]
        ma = transform(TO_3006, ga)
        mb = transform(TO_3006, gb)
        metrics = pair_metrics(ma, mb)
        edge_pattern = classify_edge_pattern(
            {**ra, **ea}, {**rb, **eb}
        )
        pair_rows.append({
            "relation_sample_id": pair_id,
            "review_priority": ra["review_priority"],
            "review_bucket": ra["review_bucket"],
            "relation_category": ra["relation_category"],
            "canonical_class_pair": ra["canonical_class_pair"],
            "motive_relation": ra["motive_relation"],
            "source_key_a": ra["source_key"],
            "source_key_b": rb["source_key"],
            "tile_a": f'{ra["source_tile_x"]}/{ra["source_tile_y"]}',
            "tile_b": f'{rb["source_tile_x"]}/{rb["source_tile_y"]}',
            "tile_edge_pattern": edge_pattern,
            "a_min_distance_to_tile_edge_m": ea["min_distance_to_tile_edge_m"],
            "b_min_distance_to_tile_edge_m": eb["min_distance_to_tile_edge_m"],
            "a_boundary_edge_share": ea["boundary_edge_share"],
            "b_boundary_edge_share": eb["boundary_edge_share"],
            "a_outside_tile_area_fraction": ea["outside_tile_area_fraction"],
            "b_outside_tile_area_fraction": eb["outside_tile_area_fraction"],
            **metrics,
            "identity_resolved": False,
            "interpretation": "tile_edge_diagnostic_only_no_identity_resolution",
        })
    feature_fields = list(feature_rows[0].keys()) if feature_rows else []
    pair_fields = list(pair_rows[0].keys()) if pair_rows else []
    for filename, rows, fields in [
        ("sca-mvt-tile-edge-feature-diagnostics.csv", feature_rows, feature_fields),
        ("sca-mvt-tile-edge-pair-diagnostics.csv", pair_rows, pair_fields),
    ]:
        with (OUT / filename).open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    patterns = Counter(r["tile_edge_pattern"] for r in pair_rows)
    buckets = Counter(r["review_bucket"] for r in pair_rows)
    summary = {
        "input_relations": len(pair_rows),
        "input_feature_sides": len(feature_rows),
        "edge_tolerance_m": EDGE_TOLERANCE_M,
        "tile_edge_pattern_counts": dict(patterns),
        "review_bucket_counts": dict(buckets),
        "outside_nominal_tile_feature_sides": sum(
            1 for r in feature_rows if float(r["outside_tile_area_fraction"]) >= 0.05
        ),
        "features_with_boundary_edge_share_over_5pct": sum(
            1 for r in feature_rows if float(r["boundary_edge_share"]) >= 0.05
        ),
        "median_overlap_smaller_fraction": sorted(float(r["overlap_smaller_fraction"]) for r in pair_rows)[len(pair_rows)//2] if pair_rows else None,
        "median_hausdorff_m_epsg3006": sorted(float(r["hausdorff_m_epsg3006"]) for r in pair_rows)[len(pair_rows)//2] if pair_rows else None,
        "identity_resolved_relations": 0,
        "limitations": [
            "The nominal XYZ tile rectangle is a diagnostic reference; decoded MVT geometries may extend beyond it due to tile buffer or rendering strategy.",
            "A geometry outside its nominal tile is not evidence of an error or a shared source object.",
            "Boundary proximity is a signal only and cannot establish whether two features are the same source object.",
            "All geometries are decoded MVT geometries reconstructed to EPSG:3857; metrics are calculated in EPSG:3006 where appropriate.",
            "No source geometry is changed, merged, dissolved or deleted.",
        ],
    }
    (OUT / "sca-mvt-tile-edge-diagnostic-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
