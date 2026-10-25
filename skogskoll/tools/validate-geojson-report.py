#!/usr/bin/env python3
"""Produce a conservative QA report for exported WGS84 GeoJSON.

This report validates the geometry representation and its geographic bounds.
It does NOT establish the source CRS or that the input geometry matches an
authoritative property boundary. The source CRS must be independently
verified before conversion; this script only audits an already-exported file.

Requires: pip install shapely
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from shapely.geometry import shape
    from shapely.validation import explain_validity
except ImportError as exc:  # pragma: no cover - exercised in CLI context
    raise SystemExit("Missing dependency. Install with: python -m pip install shapely") from exc


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def inspect_feature(feature: dict[str, Any], index: int) -> dict[str, Any]:
    geometry_data = feature.get("geometry")
    properties = feature.get("properties") or {}
    result: dict[str, Any] = {
        "feature_index": index,
        "object_identity": properties.get("objektidentitet"),
        "area_number": properties.get("omradesnummer"),
        "geometry_type": geometry_data.get("type") if isinstance(geometry_data, dict) else None,
        "valid": False,
        "validity_reason": "missing or malformed geometry",
        "coordinate_pairs": 0,
        "closed_rings": 0,
        "ring_count": 0,
        "bounds_wgs84": None,
        "centroid_wgs84": None,
        "area_square_degrees": None,
        "warnings": [],
    }
    if not isinstance(geometry_data, dict):
        result["warnings"].append("No geometry object.")
        return result

    try:
        geom = shape(geometry_data)
    except Exception as exc:
        result["warnings"].append(f"Could not parse geometry: {type(exc).__name__}: {exc}")
        return result

    result["valid"] = bool(geom.is_valid and not geom.is_empty)
    result["validity_reason"] = explain_validity(geom) if not geom.is_valid else "Valid"
    if geom.is_empty:
        result["validity_reason"] = "Empty geometry"

    if geom.geom_type not in ("Polygon", "MultiPolygon"):
        result["warnings"].append(f"Unexpected geometry type: {geom.geom_type}")

    minx, miny, maxx, maxy = geom.bounds if not geom.is_empty else (None, None, None, None)
    result["bounds_wgs84"] = [minx, miny, maxx, maxy]
    if not geom.is_empty:
        centroid = geom.centroid
        result["centroid_wgs84"] = [centroid.x, centroid.y]
        # This is a diagnostic only, not a land area measurement.
        result["area_square_degrees"] = geom.area

    coords = geometry_data.get("coordinates")
    positions: list[list[float]] = []
    rings: list[list[Any]] = []

    def walk(value: Any) -> None:
        if not isinstance(value, list):
            return
        if len(value) >= 2 and finite_number(value[0]) and finite_number(value[1]):
            positions.append(value)
            return
        for child in value:
            walk(child)

    def collect_rings(value: Any) -> None:
        # Polygon: coordinate nesting [rings][positions]; MultiPolygon: [[rings][positions]]
        if not isinstance(value, list):
            return
        if value and isinstance(value[0], list) and value[0] and finite_number(value[0][0]) and finite_number(value[0][1]):
            rings.append(value)
            return
        for child in value:
            collect_rings(child)

    walk(coords)
    collect_rings(coords)
    result["coordinate_pairs"] = len(positions)
    result["ring_count"] = len(rings)
    result["closed_rings"] = sum(
        1 for ring in rings
        if len(ring) >= 4 and ring[0][:2] == ring[-1][:2]
    )
    if rings and result["closed_rings"] != len(rings):
        result["warnings"].append("One or more linear rings are not closed or have fewer than four positions.")

    if len(positions) == 0:
        result["warnings"].append("No coordinate pairs found.")
    elif any(not (-180 <= p[0] <= 180 and -90 <= p[1] <= 90) for p in positions):
        result["warnings"].append("Coordinates fall outside WGS84 longitude/latitude bounds; check CRS and axis order.")

    if isinstance(properties, dict):
        declared_target = properties.get("target_crs")
        if declared_target not in (None, "EPSG:4326"):
            result["warnings"].append(f"Properties say target_crs={declared_target!r}, expected EPSG:4326.")
        result["source_crs_claim"] = properties.get("source_crs")
        result["source_note"] = properties.get("source")
        result["source_warning"] = properties.get("warning")

    # Do not turn geographic plausibility into a CRS assertion.
    result["warnings"].append(
        "Geometry validity and WGS84 bounds do not verify source CRS or authoritative property boundaries."
    )
    return result


def make_report(data: dict[str, Any]) -> dict[str, Any]:
    features = data.get("features")
    if data.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise ValueError("Input must be a GeoJSON FeatureCollection with a features array.")

    inspected = [
        inspect_feature(feature if isinstance(feature, dict) else {}, idx)
        for idx, feature in enumerate(features)
    ]
    return {
        "report_schema_version": 1,
        "input_type": data.get("type"),
        "feature_count": len(inspected),
        "valid_feature_count": sum(1 for f in inspected if f["valid"]),
        "invalid_feature_count": sum(1 for f in inspected if not f["valid"]),
        "source_crs_verified": False,
        "authoritative_boundary_verified": False,
        "overall_status": "geometry_checks_only",
        "interpretation": (
            "This report checks GeoJSON structure, geometry validity, ring closure, "
            "and coordinate bounds. It cannot prove the source CRS or legal accuracy."
        ),
        "features": inspected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="WGS84 GeoJSON FeatureCollection")
    parser.add_argument("output", type=Path, help="JSON report output path")
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        report = make_report(data)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {args.output}: {report['feature_count']} feature(s), "
        f"{report['valid_feature_count']} valid, {report['invalid_feature_count']} invalid; "
        "source CRS remains unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
