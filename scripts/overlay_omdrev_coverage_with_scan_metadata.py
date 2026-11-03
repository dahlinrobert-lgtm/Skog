#!/usr/bin/env python3
"""Spatially overlay 2 km volume-raster coverage cells with scan-index metadata.

Metadata polygons are 2.5 km index areas, not exact aircraft flight tracks.
The output therefore records spatial association and overlap fraction only.
"""
from __future__ import annotations
import csv, json
from collections import Counter, defaultdict
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "raster-three-omdrev" / "cross_round_pilot"
MASK_CSV = BASE / "volume_spatial_coverage_2km.csv"
METADATA_JSON = ROOT / "raster-three-omdrev" / "flight_metadata" / "laser_scan_index_tiles_esrijson.json"
OUT_CSV = BASE / "volume_coverage_scan_metadata_overlay.csv"
OUT_SUMMARY = BASE / "volume_coverage_scan_metadata_overlay_summary.json"

def polygon_from_esri(geometry):
    rings = geometry.get("rings") or []
    if not rings:
        return None
    # The source layer represents index areas as simple rectangular polygons.
    poly = Polygon(rings[0], rings[1:])
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if not poly.is_empty else None

def main():
    for path in (MASK_CSV, METADATA_JSON):
        if not path.is_file():
            raise FileNotFoundError(path)
    features = json.loads(METADATA_JSON.read_text(encoding="utf-8")).get("features", [])
    metadata = []
    for f in features:
        attrs = f.get("attributes") or {}
        poly = polygon_from_esri(f.get("geometry") or {})
        if poly is None:
            continue
        metadata.append((attrs, poly))
    if not metadata:
        raise RuntimeError("No usable scan-index metadata geometries")
    geoms = [x[1] for x in metadata]
    tree = STRtree(geoms)

    out_rows = []
    summary_counts = Counter()
    cell_meta_counts = defaultdict(set)
    coverage_totals = defaultdict(lambda: {"cells": 0, "metadata_cells": 0, "valid_pixels": 0, "pixel_count": 0})
    with MASK_CSV.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rnd = int(row["survey_round"])
            code = str(row["tile_code"])
            cell = box(float(row["xmin_epsg3006"]), float(row["ymin_epsg3006"]),
                       float(row["xmax_epsg3006"]), float(row["ymax_epsg3006"]))
            key = (rnd, code, int(row["grid_row"]), int(row["grid_col"]))
            valid_pixels = int(row["valid_pixels"])
            pixel_count = int(row["pixel_count"])
            cov = coverage_totals[(rnd, code)]
            cov["cells"] += 1
            cov["valid_pixels"] += valid_pixels
            cov["pixel_count"] += pixel_count
            indices = tree.query(cell, predicate="intersects")
            hits = []
            for idx in indices:
                attrs, poly = metadata[int(idx)]
                area = cell.intersection(poly).area
                if area <= 0:
                    continue
                hits.append((attrs, area / cell.area))
            # Keep unique matching source records but preserve all records for a
            # cell because one index square can have multiple scan-round dates.
            seen = set()
            for attrs, fraction in hits:
                oid = attrs.get("ObjectId", attrs.get("OBJECTID"))
                identity = (str(oid), str(attrs.get("Omdrev")), str(attrs.get("Datum")), str(attrs.get("Las_Namn")))
                if identity in seen:
                    continue
                seen.add(identity)
                survey_round = attrs.get("Omdrev")
                scan_date = attrs.get("Datum")
                out_rows.append({
                    "raster_survey_round": rnd,
                    "raster_tile_code": code,
                    "grid_row": key[2], "grid_col": key[3],
                    "cell_xmin_epsg3006": row["xmin_epsg3006"],
                    "cell_ymin_epsg3006": row["ymin_epsg3006"],
                    "cell_xmax_epsg3006": row["xmax_epsg3006"],
                    "cell_ymax_epsg3006": row["ymax_epsg3006"],
                    "raster_valid_fraction": row["valid_fraction"],
                    "metadata_object_id": oid,
                    "metadata_survey_round": survey_round,
                    "metadata_scan_date_raw": scan_date,
                    "metadata_index_tile": attrs.get("Indexruta"),
                    "metadata_scan_file": attrs.get("Las_Namn"),
                    "metadata_leaf_status": attrs.get("Lov_Avlov"),
                    "metadata_flight_block": attrs.get("Block"),
                    "metadata_scanner_model": attrs.get("Skannermodell"),
                    "metadata_county": attrs.get("CenterLanNamn"),
                    "metadata_municipality": attrs.get("CenterKommunNamn"),
                    "cell_area_overlap_fraction": round(fraction, 6)
                })
                summary_counts[(rnd, code, str(survey_round), str(scan_date))] += 1
                cell_meta_counts[key].add(identity)
            if hits:
                coverage_totals[(rnd, code)]["metadata_cells"] += 1

    if not out_rows:
        raise RuntimeError("No scan-index polygons intersect the coverage cells")
    columns = list(out_rows[0])
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(out_rows)

    by_group = []
    for (rnd, code), stats in sorted(coverage_totals.items()):
        by_group.append({
            "raster_survey_round": rnd, "tile_code": code,
            "grid_cells": stats["cells"],
            "cells_intersecting_scan_metadata": stats["metadata_cells"],
            "cells_without_scan_metadata_intersection": stats["cells"] - stats["metadata_cells"],
            "raster_valid_fraction": stats["valid_pixels"] / stats["pixel_count"] if stats["pixel_count"] else None,
        })
    metadata_groups = [
        {"raster_survey_round": k[0], "tile_code": k[1],
         "metadata_survey_round": k[2], "metadata_scan_date_raw": k[3],
         "intersecting_cell_metadata_records": n}
        for k, n in sorted(summary_counts.items())
    ]
    summary = {
        "method": "STRtree intersection between 2 km raster coverage cells and scan-index metadata polygons.",
        "metadata_feature_count": len(metadata),
        "overlay_record_count": len(out_rows),
        "overlay_cells_with_metadata": len(cell_meta_counts),
        "by_raster_round_and_tile": by_group,
        "by_metadata_round_and_date": metadata_groups,
        "limitations": [
            "A scan-index polygon is a 2.5 km reference area, not an exact aircraft flight footprint.",
            "Intersection establishes spatial association only; it does not prove that a specific pixel was produced from that scan record.",
            "The metadata service may contain multiple survey-round observations for an index tile; records are retained separately.",
            "The layer's date is not necessarily a complete flight-by-flight history.",
            "Raster valid-data coverage is not proof of forest coverage or actual laser acquisition."
        ]
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
