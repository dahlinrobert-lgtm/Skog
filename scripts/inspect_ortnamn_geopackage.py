#!/usr/bin/env python3
"""Read-only discovery of Lantmäteriet Ortnamn names in a GeoPackage.

The script discovers vector layers and text fields from GeoPackage metadata,
then exports records whose attribute values contain the requested place names.
It never edits the source GeoPackage. Point coordinates are reported as
source geometry coordinates; they may be cartographic label positions.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

import pyogrio


def normalise_name(value: object) -> str:
    """Normalise whitespace/case while preserving Swedish letters."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value)).casefold()
    return re.sub(r"\s+", " ", text).strip()


def find_name_matches(row: dict, targets: list[str]) -> list[dict[str, str]]:
    """Return target/field/value triples for substring matches in text values."""
    matches = []
    normalised_targets = [(target, normalise_name(target)) for target in targets]
    for field, value in row.items():
        if value is None:
            continue
        text = normalise_name(value)
        if not text:
            continue
        for target, needle in normalised_targets:
            if needle and needle in text:
                matches.append({
                    "target": target,
                    "field": str(field),
                    "value": str(value),
                })
    return matches


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


def geopackage_layers(path: Path) -> list[dict[str, str]]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT c.table_name, c.data_type, c.identifier,
                   g.column_name, g.srs_id
            FROM gpkg_contents AS c
            LEFT JOIN gpkg_geometry_columns AS g
              ON g.table_name = c.table_name
            WHERE c.data_type IN ('features', 'attributes')
            ORDER BY c.table_name
            """
        ).fetchall()
    return [
        {
            "table_name": row[0],
            "data_type": row[1],
            "identifier": row[2] or "",
            "geometry_column": row[3] or "",
            "srs_id": "" if row[4] is None else str(row[4]),
        }
        for row in rows
    ]


def scan_geopackage(path: Path, targets: list[str]) -> tuple[list[dict], dict]:
    layers = geopackage_layers(path)
    matches_out: list[dict] = []
    layer_report = []
    for layer_info in layers:
        layer_name = layer_info["table_name"]
        if layer_info["data_type"] != "features":
            layer_report.append({**layer_info, "status": "attribute_table_not_scanned"})
            continue
        try:
            frame = pyogrio.read_dataframe(path, layer=layer_name)
        except Exception as exc:  # keep scanning other layers, report the failure
            layer_report.append({
                **layer_info, "status": "read_failed",
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        layer_match_count = 0
        geometry_column = frame.geometry.name if getattr(frame, "geometry", None) is not None else None
        for row_index, series in frame.iterrows():
            attributes = {
                str(key): json_value(value)
                for key, value in series.items()
                if key != geometry_column
            }
            hits = find_name_matches(attributes, targets)
            if not hits:
                continue
            layer_match_count += len(hits)
            geometry = series[geometry_column] if geometry_column else None
            geom_type = ""
            source_x = source_y = centroid_x = centroid_y = ""
            bounds = ""
            if geometry is not None and not geometry.is_empty:
                geom_type = geometry.geom_type
                minx, miny, maxx, maxy = geometry.bounds
                bounds = json.dumps([minx, miny, maxx, maxy])
                if geom_type == "Point":
                    source_x, source_y = geometry.x, geometry.y
                centroid = geometry.centroid
                centroid_x, centroid_y = centroid.x, centroid.y

            for hit in hits:
                matches_out.append({
                    "target": hit["target"],
                    "layer": layer_name,
                    "row_index": int(row_index),
                    "matched_field": hit["field"],
                    "matched_value": hit["value"],
                    "geometry_type": geom_type,
                    "source_geometry_x": source_x,
                    "source_geometry_y": source_y,
                    "geometry_centroid_x": centroid_x,
                    "geometry_centroid_y": centroid_y,
                    "geometry_bounds": bounds,
                    "crs": str(frame.crs) if frame.crs else "",
                    "attributes_json": json.dumps(attributes, ensure_ascii=False, sort_keys=True),
                })
        layer_report.append({
            **layer_info,
            "status": "scanned",
            "feature_count": int(len(frame)),
            "matched_text_hits": layer_match_count,
            "crs": str(frame.crs) if frame.crs else "",
            "columns": [str(column) for column in frame.columns if column != geometry_column],
        })
    report = {
        "status": "completed_read_only",
        "source_file": str(path),
        "targets": targets,
        "layer_count": len(layers),
        "layers": layer_report,
        "match_row_count": len(matches_out),
        "interpretation": (
            "Ortnamn geometry is a name-reference clue. Point coordinates may be "
            "cartographic label placement and must not be treated as exact locality "
            "boundaries or incident coordinates."
        ),
    }
    return matches_out, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpkg", required=True, type=Path, help="Path to ortnamn_se.gpkg")
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--report-json", required=True, type=Path)
    parser.add_argument(
        "--targets", default="Sunderbyn,Notviken",
        help="Comma-separated names to search (default: Sunderbyn,Notviken)",
    )
    args = parser.parse_args()
    if not args.gpkg.is_file():
        parser.error(f"GeoPackage not found: {args.gpkg}")
    targets = [item.strip() for item in args.targets.split(",") if item.strip()]
    if not targets:
        parser.error("At least one target name is required")

    matches, report = scan_geopackage(args.gpkg, targets)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "target", "layer", "row_index", "matched_field", "matched_value",
        "geometry_type", "source_geometry_x", "source_geometry_y",
        "geometry_centroid_x", "geometry_centroid_y", "geometry_bounds",
        "crs", "attributes_json",
    ]
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(matches)
    args.report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "layer_count": report["layer_count"],
        "match_row_count": report["match_row_count"],
        "output_csv": str(args.output_csv),
        "report_json": str(args.report_json),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
