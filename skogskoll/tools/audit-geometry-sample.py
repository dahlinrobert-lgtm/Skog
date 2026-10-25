#!/usr/bin/env python3
"""Diagnostic audit of a manually saved Min karta geometry response.

This tool deliberately treats the CRS as a hypothesis, not a verified fact.
It does not contact Min karta, infer CRS, or certify cadastral boundaries.
Requires: pip install pyproj shapely
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import transform as transform_geometry
from shapely.validation import explain_validity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved raw JSON response, not a HAR file")
    parser.add_argument("output", type=Path, help="JSON audit report output")
    parser.add_argument("--hypothesis-crs", required=True,
                        help="CRS to test diagnostically, e.g. EPSG:3006; this is NOT verified")
    parser.add_argument("--reference-lon", type=float, required=True,
                        help="Known reference longitude in WGS84")
    parser.add_argument("--reference-lat", type=float, required=True,
                        help="Known reference latitude in WGS84")
    args = parser.parse_args()

    source = CRS.from_user_input(args.hypothesis_crs)
    to_wgs84 = Transformer.from_crs(source, CRS.from_epsg(4326), always_xy=True)
    to_source = Transformer.from_crs(CRS.from_epsg(4326), source, always_xy=True)
    reference = Point(*to_source.transform(args.reference_lon, args.reference_lat))
    data = json.loads(args.input.read_text(encoding="utf-8"))
    results = []

    for unit in data.get("enhetsutbredning", []):
        for area in unit.get("yta", []):
            if area.get("type") != "Polygon":
                continue
            coords = area.get("coordinates") or []
            if not coords or not coords[0]:
                continue
            ring = coords[0]
            polygon = Polygon(ring)
            converted = transform_geometry(to_wgs84.transform, polygon)
            results.append({
                "area_number": unit.get("omradesnummer"),
                "object_identity": unit.get("objektidentitet"),
                "geometry_type": area.get("type"),
                "ring_position_count_including_closure": len(ring),
                "unique_outer_ring_vertices": max(0, len(ring) - (1 if ring and ring[0] == ring[-1] else 0)),
                "outer_ring_closed": bool(ring and ring[0] == ring[-1]),
                "valid_in_hypothesis_crs": bool(polygon.is_valid and not polygon.is_empty),
                "validity_reason": explain_validity(polygon),
                "area_square_metres_in_hypothesis_crs": round(polygon.area, 2),
                "bbox_wgs84_lon_lat": [round(v, 7) for v in converted.bounds],
                "centroid_wgs84_lon_lat": [round(converted.centroid.x, 7), round(converted.centroid.y, 7)],
                "distance_to_reference_metres_in_hypothesis_crs": round(polygon.distance(reference), 2),
                "reference_point_inside_polygon": bool(polygon.covers(reference)),
                "interpretation": "Diagnostic only; results depend on the unverified CRS hypothesis."
            })

    report = {
        "report_schema_version": 1,
        "input_object_identity": data.get("objektidentitet"),
        "input_object_type": data.get("typ"),
        "hypothesis_crs": source.to_string(),
        "source_crs_verified": False,
        "reference_point_wgs84": [args.reference_lon, args.reference_lat],
        "authoritative_boundary_verified": False,
        "feature_count": len(results),
        "overall_status": "diagnostic_only_crs_unverified",
        "limitations": [
            "The source response does not declare its CRS.",
            "Geometric validity and plausible location do not prove the CRS.",
            "The reference coordinate is a comparison point, not a surveyed boundary control point.",
            "This does not establish legal boundary accuracy."
        ],
        "features": results
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}: {len(results)} polygon(s); CRS hypothesis remains unverified.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
