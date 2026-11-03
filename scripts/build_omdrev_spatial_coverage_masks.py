#!/usr/bin/env python3
"""Build 2 km valid-data coverage masks for Omdrev 1-3 volume rasters."""
from __future__ import annotations
import csv, json, math, os, tempfile, zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "omdrev-cross-round-pilot"
OUT = ROOT / "raster-three-omdrev" / "cross_round_pilot"
ROUNDS = ("1", "2", "3")
DEFAULT_CODES = ("12", "21", "23")
CELL_M = 2000.0

def extract_tif(archive, directory):
    with zipfile.ZipFile(archive) as zf:
        members = [m for m in zf.infolist() if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
        if len(members) != 1:
            raise RuntimeError(f"{archive.name}: expected one TIFF, found {len(members)}")
        target = directory / f"{archive.stem}.tif"
        with zf.open(members[0]) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
    return target

def inspect_grid(path, round_id, code):
    rows = []
    with rasterio.open(path) as ds:
        if ds.crs is None or ds.crs.to_epsg() != 3006 or ds.count != 1:
            raise RuntimeError(f"{path.name}: expected one-band EPSG:3006 raster")
        rx, ry = abs(ds.res[0]), abs(ds.res[1])
        px, py = round(CELL_M / rx), round(CELL_M / ry)
        if not math.isclose(px * rx, CELL_M, abs_tol=1e-7) or not math.isclose(py * ry, CELL_M, abs_tol=1e-7):
            raise RuntimeError(f"{path.name}: 2 km cell is not pixel-aligned")
        if not math.isclose(ds.bounds.left / CELL_M, round(ds.bounds.left / CELL_M), abs_tol=1e-7):
            raise RuntimeError(f"{path.name}: left edge is not aligned to 2 km grid")
        if not math.isclose(ds.bounds.top / CELL_M, round(ds.bounds.top / CELL_M), abs_tol=1e-7):
            raise RuntimeError(f"{path.name}: top edge is not aligned to 2 km grid")
        nr, nc = math.ceil(ds.height / py), math.ceil(ds.width / px)
        valid_total = pixels_total = 0
        for gr in range(nr):
            for gc in range(nc):
                r0, c0 = gr * py, gc * px
                h, w = min(py, ds.height-r0), min(px, ds.width-c0)
                arr = ds.read(1, window=Window(c0, r0, w, h), masked=False)
                valid = np.ones(arr.shape, dtype=bool) if ds.nodata is None else arr != ds.nodata
                vn, pn = int(valid.sum()), int(arr.size)
                valid_total += vn
                pixels_total += pn
                left = ds.bounds.left + c0 * rx
                right = left + w * rx
                top = ds.bounds.top - r0 * ry
                bottom = top - h * ry
                rows.append({
                    "survey_round": int(round_id), "tile_code": code,
                    "grid_row": gr, "grid_col": gc,
                    "xmin_epsg3006": round(left, 3), "ymin_epsg3006": round(bottom, 3),
                    "xmax_epsg3006": round(right, 3), "ymax_epsg3006": round(top, 3),
                    "pixel_count": pn, "valid_pixels": vn, "nodata_pixels": pn-vn,
                    "valid_fraction": vn/pn if pn else None
                })
        summary = {
            "survey_round": int(round_id), "tile_code": code, "archive": path.name,
            "crs": ds.crs.to_string(), "resolution_m": [rx, ry],
            "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
            "grid_cells": len(rows), "valid_pixels": valid_total,
            "total_pixels": pixels_total, "valid_fraction": valid_total/pixels_total,
            "cell_size_m": CELL_M
        }
    return rows, summary

def main():
    codes = [v.strip() for v in os.environ.get("RASTER_CODES", ",".join(DEFAULT_CODES)).split(",") if v.strip()]
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows, summaries, lookup = [], [], {}
    with tempfile.TemporaryDirectory(prefix="skog-omdrev-mask-") as tmp:
        temp = Path(tmp)
        for rnd in ROUNDS:
            for code in codes:
                archive = DATA / f"sks_Volym_omdrev{rnd}_{code}.zip"
                if not archive.is_file():
                    raise FileNotFoundError(archive)
                tif = extract_tif(archive, temp)
                rows, summary = inspect_grid(tif, rnd, code)
                all_rows.extend(rows)
                summaries.append(summary)
                lookup[(rnd, code)] = {(x["grid_row"], x["grid_col"]): x for x in rows}
    comparisons = []
    for code in codes:
        a, b = lookup[("2", code)], lookup[("3", code)]
        if set(a) != set(b):
            raise RuntimeError(f"Tile {code}: Omdrev 2/3 grid cells differ")
        states = {"both_valid": 0, "only_omdrev2_valid": 0, "only_omdrev3_valid": 0, "neither_valid": 0}
        deltas = []
        for key in sorted(a):
            x, y = a[key], b[key]
            for bound in ("xmin_epsg3006", "ymin_epsg3006", "xmax_epsg3006", "ymax_epsg3006"):
                if x[bound] != y[bound]:
                    raise RuntimeError(f"Tile {code}, cell {key}: spatial bounds differ")
            xv, yv = x["valid_pixels"] > 0, y["valid_pixels"] > 0
            state = "both_valid" if xv and yv else "only_omdrev2_valid" if xv else "only_omdrev3_valid" if yv else "neither_valid"
            states[state] += 1
            deltas.append(y["valid_fraction"] - x["valid_fraction"])
        comparisons.append({
            "tile_code": code, "grid_cells": len(a), "cell_states": states,
            "cells_with_lower_omdrev3_coverage": sum(d < -1e-12 for d in deltas),
            "cells_with_higher_omdrev3_coverage": sum(d > 1e-12 for d in deltas),
            "cells_with_equal_coverage": sum(abs(d) <= 1e-12 for d in deltas),
            "mean_cell_valid_fraction_change": float(np.mean(deltas)) if deltas else None
        })
    csv_path = OUT / "volume_spatial_coverage_2km.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    result = {
        "purpose": "Spatial valid-data masks for matched Omdrev 1-3 volume rasters",
        "cell_size_m": CELL_M, "crs": "EPSG:3006",
        "validity_rule": "A pixel is valid when it differs from the GeoTIFF NoData value; zero remains valid.",
        "assets": summaries, "omdrev2_vs_3_cell_coverage": comparisons,
        "limitations": [
            "The 2 km grid describes valid raster cells, not laser-flight footprints.",
            "NoData does not prove that no laser scanning occurred; it may reflect processing or masking.",
            "Overlay this CSV with scan-index polygons and, if verified, pixel-level UnixDay scan-date data.",
            "Raw volume values and their scale are not interpreted."
        ]
    }
    (OUT / "volume_spatial_coverage_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
