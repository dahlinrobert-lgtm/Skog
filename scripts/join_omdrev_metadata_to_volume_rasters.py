#!/usr/bin/env python3
"""Join 2.5 km laser-scan metadata polygons to valid pixels in Omdrev 3 volume rasters.

The output is an evidence table, not a claim that every pixel's source flight has
been individually identified. Metadata dates belong to scan-index polygons;
volume values belong to the published Omdrev 3 raster.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, from_bounds

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
METADATA_DIR = ROOT / "raster-three-omdrev" / "flight_metadata"
SOURCE_JSON = METADATA_DIR / "laser_scan_index_tiles_esrijson.json"
OUT_CSV = METADATA_DIR / "laser_scan_raster_tile_join.csv"
OUT_SUMMARY = METADATA_DIR / "laser_scan_raster_tile_join_summary.json"
DEFAULT_CODES = ("12", "21", "23")
NODATA_FALLBACK = -1


def esri_polygon_to_geojson(geometry: dict) -> dict:
    """Convert ArcGIS polygon rings to GeoJSON Polygon coordinates."""
    rings = geometry.get("rings") or []
    if not rings:
        raise ValueError("Metadata feature has no polygon rings")
    # The published index polygons in this service are simple single-ring squares.
    # Preserve additional rings if present; the first is the exterior ring.
    return {"type": "Polygon", "coordinates": rings}


def geometry_key(geometry: dict) -> str:
    raw = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def open_raster_from_zip(archive_path: Path):
    """Extract one TIFF to temporary storage and open it read-only."""
    if not archive_path.is_file():
        raise FileNotFoundError(f"Missing raster archive: {archive_path}")
    temp = tempfile.TemporaryDirectory(prefix="skog-tile-join-")
    temp_path = Path(temp.name)
    with zipfile.ZipFile(archive_path) as archive:
        members = [
            item for item in archive.infolist()
            if not item.is_dir()
            and Path(item.filename).suffix.lower() in {".tif", ".tiff"}
        ]
        if len(members) != 1:
            temp.cleanup()
            raise ValueError(f"{archive_path.name}: expected exactly one TIFF, found {len(members)}")
        member = members[0]
        tif_path = temp_path / Path(member.filename).name
        with archive.open(member) as source, tif_path.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
    dataset = rasterio.open(tif_path)
    if dataset.crs is None or dataset.crs.to_epsg() != 3006:
        dataset.close()
        temp.cleanup()
        raise ValueError(f"{archive_path.name}: expected EPSG:3006, got {dataset.crs}")
    if dataset.count < 1:
        dataset.close()
        temp.cleanup()
        raise ValueError(f"{archive_path.name}: no raster band")
    return temp, dataset


def tile_statistics(dataset, polygon: dict) -> dict:
    """Count exact pixel-centre coverage and calculate volume summaries in a tile."""
    ring = polygon["coordinates"][0]
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    bounds = dataset.bounds

    ixmin = max(xmin, bounds.left)
    ixmax = min(xmax, bounds.right)
    iymin = max(ymin, bounds.bottom)
    iymax = min(ymax, bounds.top)
    if ixmin >= ixmax or iymin >= iymax:
        return {
            "status": "outside_raster_extent", "total_cells": 0,
            "valid_cells": 0, "zero_cells": 0, "positive_cells": 0,
            "nodata_cells": 0, "valid_coverage_pct": None,
            "mean_m3sk_ha": None, "median_m3sk_ha": None, "p90_m3sk_ha": None,
        }

    # Convert the polygon bounds to a clamped raster window. The service grid is
    # 10 m and the metadata polygon is nominally 2.5 km square.
    raw_window = from_bounds(ixmin, iymin, ixmax, iymax, transform=dataset.transform)
    col0 = max(0, math.floor(raw_window.col_off + 1e-8))
    row0 = max(0, math.floor(raw_window.row_off + 1e-8))
    col1 = min(dataset.width, math.ceil(raw_window.col_off + raw_window.width - 1e-8))
    row1 = min(dataset.height, math.ceil(raw_window.row_off + raw_window.height - 1e-8))
    if col1 <= col0 or row1 <= row0:
        return {
            "status": "no_raster_cells", "total_cells": 0,
            "valid_cells": 0, "zero_cells": 0, "positive_cells": 0,
            "nodata_cells": 0, "valid_coverage_pct": None,
            "mean_m3sk_ha": None, "median_m3sk_ha": None, "p90_m3sk_ha": None,
        }

    window = Window(col0, row0, col1 - col0, row1 - row0)
    arr = dataset.read(1, window=window, masked=False)
    win_transform = dataset.window_transform(window)
    inside = geometry_mask(
        [polygon], out_shape=arr.shape, transform=win_transform,
        invert=True, all_touched=False,
    )
    nodata = dataset.nodata if dataset.nodata is not None else NODATA_FALLBACK
    selected = arr[inside]
    total = int(selected.size)
    is_nodata = selected == nodata
    valid = selected[~is_nodata]
    zero = valid == 0
    positive = valid > 0
    values = valid.astype(np.float64, copy=False)
    return {
        "status": "intersects_valid_raster_window",
        "total_cells": total,
        "valid_cells": int(valid.size),
        "zero_cells": int(np.count_nonzero(zero)),
        "positive_cells": int(np.count_nonzero(positive)),
        "nodata_cells": int(np.count_nonzero(is_nodata)),
        "valid_coverage_pct": round(100.0 * valid.size / total, 4) if total else None,
        "mean_m3sk_ha": round(float(values.mean()), 3) if values.size else None,
        "median_m3sk_ha": round(float(np.median(values)), 3) if values.size else None,
        "p90_m3sk_ha": round(float(np.percentile(values, 90)), 3) if values.size else None,
    }


def main() -> None:
    import os

    codes = [
        code.strip()
        for code in os.environ.get("RASTER_CODES", ",".join(DEFAULT_CODES)).split(",")
        if code.strip()
    ]
    if not SOURCE_JSON.is_file():
        raise FileNotFoundError(f"Missing metadata geometry file: {SOURCE_JSON}")
    source = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    features = source.get("features") or []
    if not features:
        raise RuntimeError("Metadata geometry file contains no features")

    # Cache by exact geometry hash: Omdrev 1/2/3 records often share a tile
    # geometry, so read and evaluate its raster window once per raster code.
    geometry_cache: dict[tuple[str, str], dict] = {}
    rows: list[dict] = []
    summaries = {}

    for code in codes:
        archive = DATA_DIR / f"sks_Volym_omdrev3_{code}.zip"
        temp, dataset = open_raster_from_zip(archive)
        try:
            cache_for_raster = {}
            count = Counter()
            for feature in features:
                attrs = feature.get("attributes") or {}
                geometry = feature.get("geometry") or {}
                if not geometry.get("rings"):
                    continue
                polygon = esri_polygon_to_geojson(geometry)
                gkey = geometry_key(geometry)
                cache_key = (code, gkey)
                if cache_key not in geometry_cache:
                    geometry_cache[cache_key] = tile_statistics(dataset, polygon)
                stats = geometry_cache[cache_key]
                # Only retain a record for tiles that intersect the raster extent.
                if stats["status"] == "outside_raster_extent":
                    continue
                oid = attrs.get("ObjectId")
                row = {
                    "raster_code": code,
                    "object_id": oid,
                    "index_tile": attrs.get("Indexruta"),
                    "survey_round": attrs.get("Omdrev"),
                    "scan_date": attrs.get("Datum"),
                    "scan_file": attrs.get("Las_Namn"),
                    "leaf_status": attrs.get("Lov_Avlov"),
                    "scanner_model": attrs.get("Skannermodell"),
                    "flight_block": attrs.get("Block"),
                    "center_county": attrs.get("CenterLanNamn"),
                    "center_municipality": attrs.get("CenterKommunNamn"),
                    **stats,
                }
                rows.append(row)
                count[stats["status"]] += 1
                count["valid_pixels"] += stats["valid_cells"]
                count["nodata_pixels"] += stats["nodata_cells"]
                count["zero_pixels"] += stats["zero_cells"]
                count["positive_pixels"] += stats["positive_cells"]
            summaries[code] = {
                "raster": archive.name,
                "crs": dataset.crs.to_string(),
                "resolution_m": [float(dataset.res[0]), float(dataset.res[1])],
                "metadata_records_overlapping_extent": sum(
                    1 for feature in features
                    if feature.get("attributes", {}).get("ObjectId") is not None
                    and (code, geometry_key(feature["geometry"])) in geometry_cache
                ),
                "records_by_status": dict(count),
                "unique_geometry_windows_evaluated": len(
                    [key for key in geometry_cache if key[0] == code]
                ),
            }
            print(f"Raster {code}: joined {len([r for r in rows if r['raster_code']==code])} metadata records", flush=True)
        finally:
            dataset.close()
            temp.cleanup()

    columns = [
        "raster_code", "object_id", "index_tile", "survey_round", "scan_date",
        "scan_file", "leaf_status", "scanner_model", "flight_block",
        "center_county", "center_municipality", "status", "total_cells",
        "valid_cells", "zero_cells", "positive_cells", "nodata_cells",
        "valid_coverage_pct", "mean_m3sk_ha", "median_m3sk_ha", "p90_m3sk_ha",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "method": (
            "Each 2.5 km metadata polygon is intersected with the actual 10 m "
            "Omdrev 3 volume raster. Raster windows are read only once per exact "
            "polygon geometry and raster; pixel centres are tested against polygon "
            "geometry. Zero is valid data; NoData is counted separately."
        ),
        "source_metadata": str(SOURCE_JSON.relative_to(ROOT)),
        "raster_codes": codes,
        "metadata_features_in_source": len(features),
        "joined_rows": len(rows),
        "raster_summaries": summaries,
        "interpretation_limitations": [
            "This links Omdrev 3 raster values spatially to scan-index metadata records; it does not prove the exact scan strip used for every raster pixel.",
            "Metadata for Omdrev 1 and 2 is scan-history context. The local volume archives in this workflow are Omdrev 3 only.",
            "The service may contain multiple records or scan dates for an index tile; retain survey_round, scan_date and scan_file as separate observations.",
            "Pixel-value summaries describe raster estimates, not field-verified timber volume.",
        ],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
