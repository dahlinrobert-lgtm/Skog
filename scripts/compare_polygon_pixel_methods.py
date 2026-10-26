#!/usr/bin/env python3
"""Compare cell-centre and fractional-area raster statistics for polygon zones."""
import argparse
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from pyproj import CRS, Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform as transform_geometry

try:
    from scripts.analyze_volume_for_polygon import load_features
except ModuleNotFoundError:
    from analyze_volume_for_polygon import load_features


def compare_one(ds, geom, nodata):
    extent = box(ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
    clipped = geom.intersection(extent)
    if clipped.is_empty:
        return {"status": "outside_raster_extent",
                "polygon_area_ha": round(float(geom.area / 10000), 4),
                "intersection_area_ha": 0.0,
                "raster_extent_intersection_pct": 0.0}
    win = from_bounds(*clipped.bounds, transform=ds.transform).round_offsets().round_lengths()
    win = win.intersection(rasterio.windows.Window(0, 0, ds.width, ds.height))
    if win.width <= 0 or win.height <= 0:
        return {"status": "no_raster_cells_in_extent",
                "polygon_area_ha": round(float(geom.area / 10000), 4),
                "intersection_area_ha": round(float(clipped.area / 10000), 4),
                "raster_extent_intersection_pct": round(100 * clipped.area / geom.area, 2) if geom.area else 0.0}
    arr = ds.read(1, window=win, masked=False)
    trans = ds.window_transform(win)
    center_mask = geometry_mask([mapping(geom)], out_shape=arr.shape, transform=trans,
                                invert=True, all_touched=False)
    valid_center = center_mask & (arr != nodata)
    center_vals = arr[valid_center].astype(np.float64)
    pixel_area_ha = abs(ds.transform.a * ds.transform.e - ds.transform.b * ds.transform.d) / 10000.0
    center_volume = float(np.sum(center_vals[center_vals >= 0]) * pixel_area_ha)
    fractional_values, valid_fractions = [], []
    all_fractions = []
    nodata_fractions = []
    other_negative_fractions = []
    rows, cols = arr.shape
    for row in range(rows):
        for col in range(cols):
            value = arr[row, col]
            # This implementation assumes the source raster is north-up and unrotated.
            p1 = trans * (col, row)
            p2 = trans * (col + 1, row + 1)
            cell = box(min(p1[0], p2[0]), min(p1[1], p2[1]),
                       max(p1[0], p2[0]), max(p1[1], p2[1]))
            if not cell.intersects(clipped):
                continue
            covered = cell.intersection(clipped).area / cell.area
            if covered <= 0:
                continue
            all_fractions.append(float(covered))
            if value == nodata:
                nodata_fractions.append(float(covered))
            elif value < 0:
                other_negative_fractions.append(float(covered))
            else:
                fractional_values.append(float(value))
                valid_fractions.append(float(covered))
    geometric_frac_total = float(sum(all_fractions))
    nodata_frac_total = float(sum(nodata_fractions))
    other_negative_frac_total = float(sum(other_negative_fractions))
    valid_frac_total = float(sum(valid_fractions))
    frac_volume = float(sum(v * f * pixel_area_ha for v, f in zip(fractional_values, valid_fractions)))
    frac_mean = float(sum(v * f for v, f in zip(fractional_values, valid_fractions)) / valid_frac_total) if valid_frac_total else None
    center_mean = float(np.mean(center_vals)) if center_vals.size else None
    inside_centres = int(np.count_nonzero(center_mask))
    valid_centres = int(center_vals.size)
    nodata_center_cells = int(np.count_nonzero(center_mask & (arr == nodata)))
    status = "ok" if valid_frac_total else (
        "overlaps_raster_nodata_only" if all_fractions and nodata_frac_total else
        "overlaps_only_negative_values" if other_negative_frac_total else
        "no_valid_raster_cells")
    return {
        "status": status,
        "pixel_size_m": [abs(float(ds.transform.a)), abs(float(ds.transform.e))],
        "polygon_area_ha": round(float(geom.area / 10000), 4),
        "intersection_area_ha": round(float(clipped.area / 10000), 4),
        "raster_extent_intersection_pct": round(100 * clipped.area / geom.area, 2) if geom.area else 0.0,
        "cells_with_centres_inside_polygon": inside_centres,
        "valid_center_cells": valid_centres,
        "nodata_center_cells": nodata_center_cells,
        "fractional_intersecting_cells": len(all_fractions),
        "valid_fractional_intersecting_cells": len(valid_fractions),
        "nodata_fractional_intersecting_cells": len(nodata_fractions),
        "other_negative_fractional_intersecting_cells": len(other_negative_fractions),
        "fractional_equivalent_cells_all_raster_cells": round(geometric_frac_total, 4),
        "fractional_equivalent_valid_cells": round(valid_frac_total, 4),
        # Backward-compatible aliases: these historically meant valid-cell coverage.
        "fractional_equivalent_cells": round(valid_frac_total, 4),
        "fractional_coverage_ha": round(valid_frac_total * pixel_area_ha, 4),
        "fractional_raster_intersection_ha": round(geometric_frac_total * pixel_area_ha, 4),
        "fractional_nodata_coverage_ha": round(nodata_frac_total * pixel_area_ha, 4),
        "fractional_valid_coverage_ha": round(valid_frac_total * pixel_area_ha, 4),
        "fractional_valid_coverage_pct_of_raster_intersection": round(100 * valid_frac_total / geometric_frac_total, 2) if geometric_frac_total else 0.0,
        "center_mean_m3sk_ha": round(center_mean, 3) if center_mean is not None else None,
        "fractional_mean_m3sk_ha": round(frac_mean, 3) if frac_mean is not None else None,
        "center_estimated_volume_m3sk": round(center_volume, 3),
        "fractional_estimated_volume_m3sk": round(frac_volume, 3),
        "volume_difference_fractional_minus_center_m3sk": round(frac_volume - center_volume, 3),
        "note": "Fractional values weight each valid cell by polygon-covered area; NoData and negative values excluded, zero retained."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--polygon", required=True, type=Path)
    parser.add_argument("--raster", required=True, type=Path)
    parser.add_argument("--polygon-crs")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    features, inferred_crs = load_features(args.polygon)
    source_crs = CRS.from_user_input(args.polygon_crs) if args.polygon_crs else inferred_crs
    with tempfile.TemporaryDirectory(prefix="skog-fractional-") as tmp:
        raster_path = args.raster
        if raster_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(raster_path) as zf:
                members = [m for m in zf.namelist() if not m.endswith("/") and Path(m).suffix.lower() in {".tif", ".tiff"}]
                if len(members) != 1:
                    raise ValueError(f"Expected exactly one TIFF in ZIP, found {len(members)}")
                raster_path = Path(tmp) / Path(members[0]).name
                with zf.open(members[0]) as src, raster_path.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
        with rasterio.open(raster_path) as ds:
            transformer = Transformer.from_crs(source_crs, ds.crs, always_xy=True).transform
            nodata = ds.nodata if ds.nodata is not None else -1
            results = []
            for feature in features:
                geom = transform_geometry(transformer, feature["geometry"])
                results.append({"feature_id": feature["feature_id"],
                                "properties": feature["properties"],
                                "comparison": compare_one(ds, geom, nodata)})
            report = {"method": "cell-centre versus fractional-area weighting",
                      "raster": str(args.raster), "raster_crs": ds.crs.to_string(),
                      "polygon_crs": source_crs.to_string(), "polygons": results}
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}; polygons={len(results)}")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()
