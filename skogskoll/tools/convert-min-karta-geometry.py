#!/usr/bin/env python3
"""Convert a Min karta geometry JSON response to WGS84 GeoJSON.

The input endpoint is undocumented. This tool is for manual diagnostics only.
CRS must be explicitly supplied; coordinate magnitude is not enough to infer it.
Requires: pip install pyproj
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pyproj import CRS, Transformer


def walk_positions(value: Any):
    """Yield coordinate pairs from nested GeoJSON coordinate arrays."""
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            yield value
        else:
            for child in value:
                yield from walk_positions(child)


def transform_position(position, transformer):
    x, y = transformer.transform(float(position[0]), float(position[1]))
    if not (-180 <= x <= 180 and -90 <= y <= 90):
        raise ValueError(f"Transformed coordinate is outside WGS84 bounds: {[x, y]}")
    return [x, y, *position[2:]] if len(position) > 2 else [x, y]


def transform_nested(value, transformer):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            return transform_position(value, transformer)
        return [transform_nested(child, transformer) for child in value]
    raise ValueError(f"Unexpected coordinate structure: {value!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Raw JSON downloaded from the manual probe")
    parser.add_argument("output", type=Path, help="Output GeoJSON path")
    parser.add_argument("--source-crs", required=True, help="Verified source CRS, e.g. EPSG:3006")
    parser.add_argument("--confirm-crs", action="store_true",
                        help="Confirm that source CRS was independently verified, not guessed from coordinate size")
    args = parser.parse_args()
    if not args.confirm_crs:
        parser.error("Before conversion, verify the source CRS independently and pass --confirm-crs")

    source = CRS.from_user_input(args.source_crs)
    target = CRS.from_epsg(4326)
    transformer = Transformer.from_crs(source, target, always_xy=True)

    data = json.loads(args.input.read_text(encoding="utf-8"))
    features = []
    total_polygons = 0
    for unit in data.get("enhetsutbredning", []):
        polygons = []
        for area in unit.get("yta", []):
            if area.get("type") != "Polygon":
                continue
            coords = area.get("coordinates")
            if not isinstance(coords, list) or not coords:
                continue
            polygons.append(transform_nested(coords, transformer))
            total_polygons += 1
        if not polygons:
            continue
        geometry = {"type": "MultiPolygon", "coordinates": polygons}
        feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "objektidentitet": unit.get("objektidentitet"),
                "omradesnummer": unit.get("omradesnummer"),
                "typ": unit.get("typ"),
                "source": "manual Min karta geometry probe",
                "source_crs": source.to_string(),
                "target_crs": "EPSG:4326",
                "warning": "Indicative geometry only; not legally authoritative."
            }
        }
        features.append(feature)

    if not features:
        raise ValueError("No Polygon geometries found under enhetsutbredning[].yta[].")
    result = {"type": "FeatureCollection", "features": features}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}: {len(features)} feature(s), {total_polygons} polygon(s), {args.source_crs} -> EPSG:4326")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
