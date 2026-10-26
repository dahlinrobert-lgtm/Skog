#!/usr/bin/env python3
"""Inspect Skogsstyrelsen Skogliga grunddata ZIP files without modifying originals."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = DATA_DIR / "validation-report.json"
MAX_MEMBER_SIZE = 2_000_000_000  # refuse suspiciously large extracted members
RASTER_SUFFIXES = {".tif", ".tiff", ".vrt", ".img", ".jp2"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_raster(path: Path) -> dict:
    with rasterio.open(path) as ds:
        bounds = ds.bounds
        return {
            "file": path.name,
            "driver": ds.driver,
            "width": ds.width,
            "height": ds.height,
            "band_count": ds.count,
            "dtypes": list(ds.dtypes),
            "crs": str(ds.crs) if ds.crs else None,
            "resolution": list(ds.res),
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "nodata": ds.nodata,
            "band_descriptions": list(ds.descriptions),
            "tags": ds.tags(),
        }


def inspect_zip(path: Path) -> dict:
    result = {
        "archive": path.name,
        "archive_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "members": [],
        "rasters": [],
        "errors": [],
    }
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                result["errors"].append(f"CRC check failed: {bad_member}")
            for member in archive.infolist():
                if member.is_dir():
                    continue
                item = {
                    "name": member.filename,
                    "compressed_bytes": member.compress_size,
                    "uncompressed_bytes": member.file_size,
                }
                result["members"].append(item)
                suffix = Path(member.filename).suffix.lower()
                if suffix not in RASTER_SUFFIXES:
                    continue
                if member.file_size > MAX_MEMBER_SIZE:
                    result["errors"].append(
                        f"Skipped oversized raster member {member.filename} ({member.file_size} bytes)"
                    )
                    continue
                with tempfile.TemporaryDirectory(prefix="skog-raster-") as tmp:
                    extracted = Path(tmp) / Path(member.filename).name
                    with archive.open(member) as src, extracted.open("wb") as dst:
                        while chunk := src.read(1024 * 1024):
                            dst.write(chunk)
                    try:
                        raster_info = inspect_raster(extracted)
                        raster_info["archive_member"] = member.filename
                        result["rasters"].append(raster_info)
                    except Exception as exc:
                        result["errors"].append(
                            f"Could not read raster {member.filename}: {type(exc).__name__}: {exc}"
                        )
    except Exception as exc:
        result["errors"].append(f"Could not inspect ZIP: {type(exc).__name__}: {exc}")
    return result


def main() -> int:
    archives = sorted(DATA_DIR.glob("*.zip"))
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Skogsstyrelsen, Skogliga grunddata – Volym, omdrev 3",
        "checks": ["ZIP integrity", "archive inventory", "SHA-256", "raster metadata"],
        "archives": [inspect_zip(path) for path in archives],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Inspected {len(archives)} ZIP file(s); report: {OUT.relative_to(ROOT)}")
    for archive in report["archives"]:
        print(f"- {archive['archive']}: {len(archive['members'])} member(s), "
              f"{len(archive['rasters'])} readable raster(s), {len(archive['errors'])} error(s)")
        for error in archive["errors"]:
            print(f"  ERROR: {error}")
    return 1 if not archives or any(a["errors"] or not a["rasters"] for a in report["archives"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
