#!/usr/bin/env python3
"""Audit how raster cell centres are assigned to multiple polygon features.

This does not polygonize raster values. It overlays polygon geometries on the
source raster's native grid and counts cells selected by each polygon.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.windows import from_bounds
from pyproj import CRS, Transformer
from shapely.geometry import mapping
from shapely.ops import transform as transform_geometry

from analyze_volume_for_polygon import load_features


def audit_cell_ownership(ds, features, source_crs):
    """Count cell-centre assignments and overlaps on the raster's native grid."""
    if ds.crs is None:
        raise ValueError("Raster has no CRS")
    transformer = Transformer.from_crs(source_crs, ds.crs, always_xy=True).transform
    projected = [transform_geometry(transformer, f["geometry"]) for f in features]
    raster_extent = __import__("shapely.geometry", fromlist=["box"]).box(
        ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top
    )
    clipped = [g.intersection(raster_extent) for g in projected]
    clipped = [g for g in clipped if not g.is_empty]
    if not clipped:
        return {
            "raster_crs": ds.crs.to_string(), "pixel_size": list(ds.res),
            "polygon_count": len(features), "polygon_cell_counts": [],
            "cells_selected_by_multiple_polygons": 0,
            "sum_polygon_cell_assignments": 0, "unique_cells_selected": 0,
            "double_count_excess": 0,
            "rule": "cell-centre inclusion; native raster grid; all_touched=False",
        }

    minx = min(g.bounds[0] for g in clipped)
    miny = min(g.bounds[1] for g in clipped)
    maxx = max(g.bounds[2] for g in clipped)
    maxy = max(g.bounds[3] for g in clipped)
    window = from_bounds(minx, miny, maxx, maxy, transform=ds.transform)
    window = window.round_offsets().round_lengths().intersection(
        rasterio.windows.Window(0, 0, ds.width, ds.height)
    )
    if window.width <= 0 or window.height <= 0:
        raise ValueError("Polygon extent does not intersect any raster cells")
    transform = ds.window_transform(window)
    counts = np.zeros((int(window.height), int(window.width)), dtype=np.uint32)
    per_polygon = []
    for feature, geom in zip(features, projected):
        mask = rasterize(
            [(mapping(geom), 1)], out_shape=counts.shape, transform=transform,
            fill=0, dtype="uint8", all_touched=False,
        ).astype(bool)
        counts += mask.astype(np.uint32)
        per_polygon.append({
            "feature_id": feature["feature_id"],
            "cell_assignments": int(mask.sum()),
            "properties": feature["properties"],
        })
    overlap_cells = int(np.count_nonzero(counts > 1))
    sum_assignments = int(sum(x["cell_assignments"] for x in per_polygon))
    unique_cells = int(np.count_nonzero(counts > 0))
    return {
        "raster_crs": ds.crs.to_string(),
        "pixel_size": [abs(float(ds.transform.a)), abs(float(ds.transform.e))],
        "raster_grid_origin": [float(ds.transform.c), float(ds.transform.f)],
        "polygon_count": len(features),
        "polygon_cell_counts": per_polygon,
        "cells_selected_by_multiple_polygons": overlap_cells,
        "sum_polygon_cell_assignments": sum_assignments,
        "unique_cells_selected": unique_cells,
        "double_count_excess": sum_assignments - unique_cells,
        "rule": "cell-centre inclusion; native raster grid; all_touched=False",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--polygon", required=True, type=Path)
    parser.add_argument("--raster", required=True, type=Path,
                        help="GeoTIFF or ZIP containing exactly one TIFF")
    parser.add_argument("--polygon-crs", help="Override GeoJSON CRS")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    features, inferred_crs = load_features(args.polygon)
    source_crs = CRS.from_user_input(args.polygon_crs) if args.polygon_crs else inferred_crs

    with tempfile.TemporaryDirectory(prefix="skog-cell-audit-") as tmp:
        raster_path = args.raster
        if raster_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(raster_path) as zf:
                tiffs = [m for m in zf.namelist()
                         if not m.endswith("/") and Path(m).suffix.lower() in {".tif", ".tiff"}]
                if len(tiffs) != 1:
                    raise ValueError(f"Expected exactly one TIFF in {raster_path.name}, found {len(tiffs)}")
                extracted = Path(tmp) / Path(tiffs[0]).name
                with zf.open(tiffs[0]) as src, extracted.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                raster_path = extracted
        with rasterio.open(raster_path) as ds:
            report = audit_cell_ownership(ds, features, source_crs)
    report["input_geojson"] = str(args.polygon)
    report["input_raster"] = str(args.raster)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}; polygons={report['polygon_count']}; "
              f"overlap_cells={report['cells_selected_by_multiple_polygons']}; "
              f"double_count_excess={report['double_count_excess']}")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
