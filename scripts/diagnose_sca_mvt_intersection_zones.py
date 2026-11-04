#!/usr/bin/env python3
"""Partition each sampled SCA MVT pair intersection by nominal tile zones.

The intersection is partitioned into area inside tile A, inside tile B, and
outside both nominal XYZ tile rectangles. Metrics are reported in EPSG:3006.
This is a rendering diagnostic and must not be interpreted as identity.
"""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform

INPUT = Path("input")
OUT = Path("output")
WORLD = 20037508.342789244
ZOOM = 12
SPAN = (2 * WORLD) / (2 ** ZOOM)
TO_3006 = Transformer.from_crs("EPSG:3857", "EPSG:3006", always_xy=True).transform


def nominal_tile_polygon(tx: int, ty: int):
    xmin = -WORLD + tx * SPAN
    xmax = xmin + SPAN
    ymax = WORLD - ty * SPAN
    ymin = ymax - SPAN
    return box(xmin, ymin, xmax, ymax)


def area_m2(geom):
    if geom.is_empty:
        return 0.0
    return transform(TO_3006, geom).area


def classify_zone(a_core_share: float, b_core_share: float, outside_share: float):
    if outside_share >= 0.5:
        return "mostly_outside_both_nominal_tiles"
    if a_core_share >= 0.8:
        return "mostly_in_tile_a_core"
    if b_core_share >= 0.8:
        return "mostly_in_tile_b_core"
    if a_core_share >= 0.2 and b_core_share >= 0.2:
        return "spread_across_both_tile_cores"
    if a_core_share > 0 and b_core_share > 0:
        return "mixed_small_core_intersections"
    if a_core_share > 0:
        return "tile_a_core_and_buffer"
    if b_core_share > 0:
        return "tile_b_core_and_buffer"
    return "buffer_only_outside_both_cores"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    trace_csvs = sorted(INPUT.rglob("sca-overlap-source-trace.csv"))
    trace_gjs = sorted(INPUT.rglob("sca-overlap-source-trace.geojson"))
    if len(trace_csvs) != 1 or len(trace_gjs) != 1:
        raise SystemExit("Expected exactly one trace CSV and GeoJSON")
    with trace_csvs[0].open(encoding="utf-8-sig", newline="") as f:
        trace_rows = list(csv.DictReader(f))
    gj = json.loads(trace_gjs[0].read_text(encoding="utf-8"))
    geometries = {str(x["id"]): shape(x["geometry"]) for x in gj["features"]}
    pairs = {}
    for row in trace_rows:
        key = (str(row["relation_sample_id"]), str(row["side"]))
        pairs.setdefault(key[0], {})[key[1]] = row
    output = []
    for pair_id in sorted(pairs, key=int):
        sides = pairs[pair_id]
        if set(sides) != {"a", "b"}:
            raise SystemExit(f"Missing side for pair {pair_id}")
        ra, rb = sides["a"], sides["b"]
        ga = geometries.get(f"sample-{pair_id}-a")
        gb = geometries.get(f"sample-{pair_id}-b")
        if ga is None or gb is None:
            raise SystemExit(f"Missing geometry for pair {pair_id}")
        if ga.is_empty or gb.is_empty or not ga.is_valid or not gb.is_valid:
            raise SystemExit(f"Invalid geometry for pair {pair_id}")
        ta = nominal_tile_polygon(int(ra["source_tile_x"]), int(ra["source_tile_y"]))
        tb = nominal_tile_polygon(int(rb["source_tile_x"]), int(rb["source_tile_y"]))
        inter = ga.intersection(gb)
        total = area_m2(inter)
        # Make the partition mutually exclusive. Adjacent nominal tiles may
        # share a boundary, while diagonal/overlapping tile footprints can
        # create area counted in both intersections. Assign overlap first to
        # A, then to B outside A, and finally to the area outside both.
        in_a = inter.intersection(ta)
        in_b_only = inter.intersection(tb).difference(ta)
        outside_both = inter.difference(ta.union(tb))
        area_a = area_m2(in_a)
        area_b = area_m2(in_b_only)
        area_out = area_m2(outside_both)
        accounted = area_a + area_b + area_out
        if total > 0 and abs(accounted - total) / total > 1e-5:
            raise SystemExit(f"Intersection zone accounting mismatch for pair {pair_id}")
        a_share = area_a / total if total else 0.0
        b_share = area_b / total if total else 0.0
        out_share = area_out / total if total else 0.0
        dx = int(rb["source_tile_x"]) - int(ra["source_tile_x"])
        dy = int(rb["source_tile_y"]) - int(ra["source_tile_y"])
        output.append({
            "relation_sample_id": pair_id,
            "review_priority": ra["review_priority"],
            "review_bucket": ra["review_bucket"],
            "relation_category": ra.get("relation_category", ""),
            "class_a": json.loads(ra["raw_properties_json"]).get("SKOTSEL_KL_resolved", ""),
            "class_b": json.loads(rb["raw_properties_json"]).get("SKOTSEL_KL_resolved", ""),
            "motive_a": json.loads(ra["raw_properties_json"]).get("MOTIV_resolved", ""),
            "motive_b": json.loads(rb["raw_properties_json"]).get("MOTIV_resolved", ""),
            "source_key_a": ra["source_key"],
            "source_key_b": rb["source_key"],
            "tile_a": f'{ra["source_tile_x"]}/{ra["source_tile_y"]}',
            "tile_b": f'{rb["source_tile_x"]}/{rb["source_tile_y"]}',
            "tile_dx_a_to_b": dx,
            "tile_dy_a_to_b": dy,
            "tile_neighborhood": "cardinal" if max(abs(dx), abs(dy)) == 1 and (dx == 0 or dy == 0) else "diagonal" if max(abs(dx), abs(dy)) == 1 else "other",
            "intersection_total_m2_epsg3006": total,
            "intersection_in_tile_a_m2_epsg3006": area_a,
            "intersection_in_tile_b_outside_a_m2_epsg3006": area_b,
            "intersection_outside_both_tiles_m2_epsg3006": area_out,
            "intersection_share_in_tile_a": a_share,
            "intersection_share_in_tile_b_outside_a": b_share,
            "intersection_share_outside_both_tiles": out_share,
            "intersection_zone_class": classify_zone(a_share, b_share, out_share),
            "identity_resolved": False,
            "interpretation": "intersection_zone_diagnostic_only_no_identity_resolution",
        })
    fields = list(output[0].keys()) if output else []
    with (OUT / "sca-mvt-intersection-zone-diagnostics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    summary = {
        "input_relations": len(output),
        "tile_zone_class_counts": dict(Counter(x["intersection_zone_class"] for x in output)),
        "review_bucket_counts": dict(Counter(x["review_bucket"] for x in output)),
        "cardinal_neighbor_relations": sum(x["tile_neighborhood"] == "cardinal" for x in output),
        "diagonal_neighbor_relations": sum(x["tile_neighborhood"] == "diagonal" for x in output),
        "relations_with_any_intersection": sum(x["intersection_total_m2_epsg3006"] > 0 for x in output),
        "relations_mostly_outside_both_tiles": sum(x["intersection_share_outside_both_tiles"] >= 0.5 for x in output),
        "identity_resolved_relations": 0,
        "limitations": [
            "Intersection zones are based on decoded MVT features reconstructed into EPSG:3857 and nominal XYZ tile rectangles.",
            "Tile buffer and rendering rules may extend beyond the nominal tile; zone classification is diagnostic only.",
            "Tile B intersection area is reported exclusive of tile A to avoid double-counting; the A-first assignment is an accounting convention, not a physical attribution.",
            "Overlap inside a tile core is not proof of same object identity; it may represent genuinely overlapping source objects.",
            "No geometry is merged, dissolved, modified or deleted.",
        ],
    }
    (OUT / "sca-mvt-intersection-zone-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
