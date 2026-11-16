#!/usr/bin/env python3
"""Read-only inventory of county NVDB GeoPackage ZIP archives.

The script inspects ZIP metadata and GeoPackage layer metadata through GDAL's
/vsizip/ virtual filesystem. It does not extract, rewrite, or modify source
archives. A successful metadata probe is not a validation of all features or
of the legal reuse conditions for the source product.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

import pyogrio


ROAD_LAYER = "NVDB_DK_O_111_Vagnummer"
ROAD_FIELDS = ("ELEMENT_ID", "Europavag", "Huvudnummer", "Lankroll")


def inspect_archive(archive: Path) -> dict:
    result = {
        "archive": archive.name,
        "archive_path": str(archive),
        "archive_bytes": archive.stat().st_size,
        "gpkg_members": [],
        "layers": [],
        "road_layer_found": False,
        "road_layer_missing_fields": [],
        "status": "error",
        "errors": [],
    }

    try:
        with zipfile.ZipFile(archive) as zipped:
            members = [
                item for item in zipped.infolist()
                if not item.is_dir() and item.filename.casefold().endswith(".gpkg")
            ]
            result["gpkg_members"] = [
                {
                    "member": item.filename,
                    "uncompressed_bytes": item.file_size,
                    "compressed_bytes": item.compress_size,
                    "crc32": f"{item.CRC:08x}",
                }
                for item in members
            ]
    except (OSError, zipfile.BadZipFile) as exc:
        result["errors"].append(f"ZIP could not be opened: {exc}")
        return result

    if not members:
        result["errors"].append("No .gpkg member found in ZIP archive")
        return result

    for member in members:
        vsi_path = f"/vsizip/{archive.resolve().as_posix()}/{member.filename}"
        try:
            listed = pyogrio.list_layers(vsi_path)
            layer_names = [str(row[0]) for row in listed]
            for layer_name in layer_names:
                try:
                    info = pyogrio.read_info(vsi_path, layer=layer_name)
                    fields = [str(field) for field in info.get("fields", [])]
                    layer = {
                        "member": member.filename,
                        "layer": layer_name,
                        "feature_count": info.get("features"),
                        "geometry_type": info.get("geometry_type"),
                        "crs": str(info.get("crs") or ""),
                        "fields": fields,
                        "field_count": len(fields),
                        "status": "metadata_read",
                    }
                    if layer_name == ROAD_LAYER:
                        missing = [field for field in ROAD_FIELDS if field not in fields]
                        layer["required_fields_missing"] = missing
                        result["road_layer_found"] = True
                        result["road_layer_missing_fields"] = missing
                        layer["status"] = "compatible" if not missing else "schema_mismatch"
                    result["layers"].append(layer)
                except Exception as exc:
                    result["errors"].append(
                        f"Layer metadata failed ({member.filename}::{layer_name}): {exc}"
                    )
        except Exception as exc:
            result["errors"].append(f"Layer listing failed ({member.filename}): {exc}")

    if result["errors"]:
        result["status"] = "partial"
    elif not result["road_layer_found"]:
        result["status"] = "road_layer_missing"
    elif result["road_layer_missing_fields"]:
        result["status"] = "schema_mismatch"
    else:
        result["status"] = "compatible"
    return result


def build_report(directory: Path, pattern: str, expected_archives: int | None) -> dict:
    archives = sorted(path for path in directory.glob(pattern) if path.is_file())
    results = [inspect_archive(path) for path in archives]
    status_counts: dict[str, int] = {}
    for item in results:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    errors = []
    if expected_archives is not None and len(archives) != expected_archives:
        errors.append(
            f"Expected {expected_archives} archives, found {len(archives)}"
        )
    if any(item["status"] != "compatible" for item in results):
        errors.append("One or more archives are not fully compatible")

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed" if not errors else "partial",
        "source_directory": str(directory.resolve()),
        "archive_pattern": pattern,
        "expected_archive_count": expected_archives,
        "archive_count": len(archives),
        "archive_bytes_total": sum(item["archive_bytes"] for item in results),
        "status_counts": status_counts,
        "errors": errors,
        "read_only": True,
        "source_archives_modified": False,
        "feature_geometries_scanned": False,
        "archives": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True,
                        help="Directory containing the county ZIP archives.")
    parser.add_argument("--pattern", default="*_GeoPackage.zip")
    parser.add_argument("--expected-archives", type=int, default=21,
                        help="Expected archive count; use 0 to disable the count check.")
    parser.add_argument("--output", type=Path, required=True,
                        help="New JSON report path; source archives remain untouched.")
    args = parser.parse_args()

    if not args.directory.is_dir():
        parser.error(f"Directory does not exist: {args.directory}")
    expected = None if args.expected_archives == 0 else args.expected_archives
    if expected is not None and expected < 1:
        parser.error("--expected-archives must be positive or 0 to disable")
    if not args.pattern:
        parser.error("--pattern cannot be empty")

    report = build_report(args.directory, args.pattern, expected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "archive_count": report["archive_count"],
        "archive_bytes_total": report["archive_bytes_total"],
        "status_counts": report["status_counts"],
        "errors": report["errors"],
        "output": str(args.output),
        "read_only": report["read_only"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
