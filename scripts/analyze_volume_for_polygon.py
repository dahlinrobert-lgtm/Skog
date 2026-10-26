#!/usr/bin/env python3
"""Read Skogsstyrelsen volume rasters as a hidden background dataset for polygons.

The source raster is not rendered or published as a map layer. This script
returns per-polygon attributes/statistics for application code or reports.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geometry
from pyproj import CRS, Transformer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "skogliga-grunddata"
NODATA_FALLBACK = -1


def load_features(path: Path) -> tuple[list[dict[str, Any]], CRS]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    declared_crs = doc.get("crs")
    # GeoJSON RFC 7946 coordinates are WGS84 unless a legacy CRS member says otherwise.
    if declared_crs and isinstance(declared_crs, dict):
        name = declared_crs.get("properties", {}).get("name", "")
        source_crs = CRS.from_user_input(name.split(":")[-1] if name.upper().startswith("URN:OGC:DEF:CRS:EPSG::") else name)
    else:
        source_crs = CRS.from_epsg(4326)

    if doc.get("type") == "FeatureCollection":
        features = doc.get("features", [])
    elif doc.get("type") == "Feature":
        features = [doc]
    elif doc.get("type") in {"Polygon", "MultiPolygon"}:
        features = [{"type": "Feature", "properties": {}, "geometry": doc}]
    else:
        raise ValueError("Input must be a GeoJSON Polygon, MultiPolygon, Feature or FeatureCollection.")

    clean = []
    for i, feature in enumerate(features):
        geom_json = feature.get("geometry")
        if not geom_json or geom_json.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        geom = shape(geom_json)
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Feature {i} has an empty or invalid polygon geometry.")
        clean.append({
            "feature_id": str(feature.get("id", feature.get("properties", {}).get("id", i))),
            "properties": feature.get("properties") or {},
            "geometry": geom,
        })
    if not clean:
        raise ValueError("No valid Polygon or MultiPolygon features found.")
    return clean, source_crs


def extract_tif(archive_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = [m for m in archive.infolist()
                   if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
        if len(members) != 1:
            raise ValueError(f"{archive_path.name}: expected exactly one TIFF, found {len(members)}")
        target = target_dir / Path(members[0].filename).name
        with archive.open(members[0]) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        return target


def summarize_feature(ds: rasterio.io.DatasetReader, geom, nodata: float | int) -> dict[str, Any]:
    if not geom.intersects(shape({
        "type": "Polygon",
        "coordinates": [[
            [ds.bounds.left, ds.bounds.bottom], [ds.bounds.right, ds.bounds.bottom],
            [ds.bounds.right, ds.bounds.top], [ds.bounds.left, ds.bounds.top],
            [ds.bounds.left, ds.bounds.bottom]
        ]]
    })):
        return empty_stats("outside_raster_extent")

    intersection = geom.intersection(shape({
        "type": "Polygon",
        "coordinates": [[
            [ds.bounds.left, ds.bounds.bottom], [ds.bounds.right, ds.bounds.bottom],
            [ds.bounds.right, ds.bounds.top], [ds.bounds.left, ds.bounds.top],
            [ds.bounds.left, ds.bounds.bottom]
        ]]
    }))
    if intersection.is_empty:
        return empty_stats("outside_raster_extent")

    win = from_bounds(*intersection.bounds, transform=ds.transform)
    win = win.round_offsets().round_lengths()
    win = win.intersection(rasterio.windows.Window(0, 0, ds.width, ds.height))
    if win.width <= 0 or win.height <= 0:
        return empty_stats("no_raster_cells_in_extent")
    arr = ds.read(1, window=win, masked=False)
    transform = ds.window_transform(win)
    inside = geometry_mask([mapping(geom)], out_shape=arr.shape, transform=transform, invert=True, all_touched=False)
    valid = inside & (arr != nodata)
    zeros = valid & (arr == 0)
    positive = valid & (arr > 0)
    other_negative = valid & (arr < 0)
    vals = arr[valid].astype(np.float64)
    valid_count = int(vals.size)
    zero_count = int(np.count_nonzero(zeros))
    positive_count = int(np.count_nonzero(positive))
    neg_count = int(np.count_nonzero(other_negative))
    pixel_area_ha = abs(ds.transform.a * ds.transform.e - ds.transform.b * ds.transform.d) / 10000.0
    total_estimate = float(np.sum(vals[vals >= 0]) * pixel_area_ha)
    return {
        "status": "ok" if valid_count else "no_valid_cells",
        "cells_inside_polygon": int(np.count_nonzero(inside)),
        "valid_cells": valid_count,
        "zero_cells": zero_count,
        "positive_cells": positive_count,
        "other_negative_cells": neg_count,
        "nodata_cells_inside_polygon": int(np.count_nonzero(inside & ~valid)),
        "valid_coverage_pct": round(100 * valid_count / max(1, int(np.count_nonzero(inside))), 2),
        "mean_volume_m3sk_per_ha_including_zero": round(float(np.mean(vals)), 2) if valid_count else None,
        "median_volume_m3sk_per_ha_including_zero": round(float(np.median(vals)), 2) if valid_count else None,
        "p90_volume_m3sk_per_ha_including_zero": round(float(np.percentile(vals, 90)), 2) if valid_count else None,
        "estimated_volume_m3sk_from_valid_cells": round(total_estimate, 2) if valid_count else None,
        "pixel_area_ha": pixel_area_ha,
        "method": "cell-centre inclusion; raster cell value treated as m3sk/ha; NoData excluded; zero retained",
    }


def empty_stats(status: str) -> dict[str, Any]:
    return {
        "status": status, "cells_inside_polygon": 0, "valid_cells": 0,
        "zero_cells": 0, "positive_cells": 0, "other_negative_cells": 0,
        "nodata_cells_inside_polygon": 0, "valid_coverage_pct": 0.0,
        "mean_volume_m3sk_per_ha_including_zero": None,
        "median_volume_m3sk_per_ha_including_zero": None,
        "p90_volume_m3sk_per_ha_including_zero": None,
        "estimated_volume_m3sk_from_valid_cells": None,
        "pixel_area_ha": None,
        "method": "cell-centre inclusion; raster cell value treated as m3sk/ha; NoData excluded; zero retained",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--polygon", required=True, type=Path, help="GeoJSON Polygon/MultiPolygon; WGS84 by default")
    parser.add_argument("--polygon-crs", help="Override input CRS, e.g. EPSG:3006")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path, help="Optional output JSON path; stdout if omitted")
    args = parser.parse_args()

    features, inferred_crs = load_features(args.polygon)
    source_crs = CRS.from_user_input(args.polygon_crs) if args.polygon_crs else inferred_crs
    archives = sorted(args.data_dir.glob("*.zip"))
    if not archives:
        raise FileNotFoundError(f"No raster ZIPs found in {args.data_dir}")

    transformer_cache = {}
    results = []
    errors = []
    with tempfile.TemporaryDirectory(prefix="skog-polygon-volume-") as temp:
        for archive in archives:
            try:
                tif = extract_tif(archive, Path(temp) / archive.stem)
                with rasterio.open(tif) as ds:
                    if ds.crs is None or ds.crs.to_epsg() != 3006:
                        raise ValueError(f"Expected EPSG:3006 raster, got {ds.crs}")
                    key = (source_crs.to_string(), ds.crs.to_string())
                    if key not in transformer_cache:
                        transformer_cache[key] = Transformer.from_crs(source_crs, ds.crs, always_xy=True).transform
                    project = transformer_cache[key]
                    nodata = ds.nodata if ds.nodata is not None else NODATA_FALLBACK
                    per_feature = []
                    for feature in features:
                        geom = transform_geometry(project, feature["geometry"])
                        stats = summarize_feature(ds, geom, nodata)
                        per_feature.append({
                            "feature_id": feature["feature_id"],
                            "properties": feature["properties"],
                            "stats": stats,
                        })
                    results.append({
                        "source_archive": archive.name,
                        "raster": tif.name,
                        "crs": ds.crs.to_string(),
                        "pixel_size_m": list(ds.res),
                        "nodata_value": nodata,
                        "per_polygon": per_feature,
                    })
            except Exception as exc:
                errors.append({"archive": archive.name, "error": f"{type(exc).__name__}: {exc}"})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "Skogsstyrelsen Skogliga grunddata – Volym omdrev 3",
        "purpose": "Background polygon attributes only; this script does not create or render a map layer",
        "input_geojson": str(args.polygon),
        "input_crs": source_crs.to_string(),
        "polygon_count": len(features),
        "value_unit": "m³sk/ha",
        "warnings": [
            "Modelled raster estimates describe the forest at the local laser-scanning date, not necessarily the current date.",
            "Zero means no volume estimate was produced for low vegetation/open areas; it is retained as a valid raster value.",
            "Estimated total volume is a coarse cell-based estimate over cell centres inside the polygon; it is not a forest inventory or a cadastral/legal determination.",
            "Only source rasters available in the data directory are analysed; absence of coverage is reported as no valid cells."
        ],
        "rasters": results,
        "errors": errors,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}; polygons={len(features)}; rasters={len(results)}; errors={len(errors)}")
    else:
        print(payload, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
