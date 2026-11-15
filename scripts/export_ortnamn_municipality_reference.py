#!/usr/bin/env python3
"""Export a municipality-scoped, read-only Ortnamn reference from a GeoPackage.

The source GeoPackage is never modified. The export retains source attributes,
geometry metadata, the source row index and a SHA-256 fingerprint of the input.
Ortnamn point coordinates may be cartographic label positions, not locality
centres, boundaries or incident locations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import pyogrio


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_value(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def export_municipality(frame, municipality_code: str) -> tuple[list[dict], dict]:
    """Build one output row per source feature belonging to the municipality."""
    if "kommunkod" not in frame.columns:
        raise ValueError("Required source field 'kommunkod' is missing")

    geometry_column = frame.geometry.name if getattr(frame, "geometry", None) is not None else None
    if not geometry_column:
        raise ValueError("The source layer has no active geometry column")

    selected = frame[frame["kommunkod"].astype(str).str.zfill(4) == municipality_code]
    rows: list[dict] = []
    detail_types: Counter[str] = Counter()
    name_counts: Counter[str] = Counter()
    for source_index, series in selected.iterrows():
        attributes = {
            str(key): json_value(value)
            for key, value in series.items()
            if key != geometry_column
        }
        geometry = series[geometry_column]
        geometry_type = "" if geometry is None or geometry.is_empty else geometry.geom_type
        x = y = ""
        bounds = ""
        if geometry is not None and not geometry.is_empty:
            minx, miny, maxx, maxy = geometry.bounds
            bounds = json.dumps([minx, miny, maxx, maxy])
            if geometry_type == "Point":
                x, y = geometry.x, geometry.y
        name = str(attributes.get("ortnamn") or "")
        detail_type = str(attributes.get("detaljtyp") or "")
        detail_types[detail_type or "(saknas)"] += 1
        name_counts[name or "(saknas)"] += 1
        rows.append({
            "municipality_code": municipality_code,
            "source_layer": str(getattr(frame, "name", "") or ""),
            "source_row_index": int(source_index),
            "ortnamn": name,
            "detaljtyp": detail_type,
            "source_lopnummer": attributes.get("lopnummer", ""),
            "geometry_type": geometry_type,
            "source_geometry_x": x,
            "source_geometry_y": y,
            "geometry_bounds": bounds,
            "crs": str(frame.crs) if frame.crs else "",
            "attributes_json": json.dumps(attributes, ensure_ascii=False, sort_keys=True),
        })

    summary = {
        "municipality_code": municipality_code,
        "source_feature_count": int(len(frame)),
        "exported_feature_count": len(rows),
        "detail_type_counts": dict(sorted(detail_types.items())),
        "name_counts_top_50": [
            {"name": name, "count": count}
            for name, count in name_counts.most_common(50)
        ],
        "geometry_type_counts": dict(sorted(Counter(row["geometry_type"] for row in rows).items())),
        "crs": str(frame.crs) if frame.crs else "",
        "source_row_index_note": "Row index is a locator within this source snapshot, not a persistent object identifier.",
        "lopnummer_note": "source_lopnummer is retained as a source attribute only; do not assume it is unique or stable.",
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpkg", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--report-json", required=True, type=Path)
    parser.add_argument("--layer", default="ortnamn")
    parser.add_argument("--municipality-code", default="2580")
    args = parser.parse_args()
    if not args.gpkg.is_file():
        parser.error(f"GeoPackage not found: {args.gpkg}")
    if not args.municipality_code.isdigit() or len(args.municipality_code) != 4:
        parser.error("--municipality-code must be a four-digit code")

    frame = pyogrio.read_dataframe(args.gpkg, layer=args.layer)
    rows, summary = export_municipality(frame, args.municipality_code)
    report = {
        "status": "completed_read_only",
        "source_file": str(args.gpkg),
        "source_file_size_bytes": args.gpkg.stat().st_size,
        "source_sha256": sha256_file(args.gpkg),
        "source_layer": args.layer,
        **summary,
        "interpretation": (
            "Municipality-scoped name reference only. Point coordinates may be "
            "cartographic label placement; they are not locality boundaries, "
            "locality centres or incident coordinates. No matching is performed."
        ),
    }
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "municipality_code", "source_layer", "source_row_index", "ortnamn",
        "detaljtyp", "source_lopnummer", "geometry_type", "source_geometry_x",
        "source_geometry_y", "geometry_bounds", "crs", "attributes_json",
    ]
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    args.report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"],
        "municipality_code": args.municipality_code,
        "exported_feature_count": len(rows),
        "source_sha256": report["source_sha256"],
        "output_csv": str(args.output_csv),
        "report_json": str(args.report_json),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
