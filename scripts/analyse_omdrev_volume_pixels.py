#!/usr/bin/env python3
"""Windowed volume-raster statistics and exact-grid Omdrev 2 vs 3 comparison."""
from __future__ import annotations
import json
import tempfile
import zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "omdrev-cross-round-pilot"
OUT = ROOT / "raster-three-omdrev" / "cross_round_pilot"
ROUNDS = ("1", "2", "3")
CODES = ("12", "21", "23")
BLOCK = 2048
HIST_SIZE = 65536
HIST_OFFSET = 32768

def extract_tif(archive: Path, directory: Path) -> Path:
    with zipfile.ZipFile(archive) as zf:
        members = [x for x in zf.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in {".tif", ".tiff"}]
        if len(members) != 1:
            raise RuntimeError(f"{archive.name}: expected one TIFF, found {len(members)}")
        target = directory / Path(members[0].filename).name
        with zf.open(members[0]) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
    return target

def hist_quantile(hist: np.ndarray, q: float) -> float | None:
    total = int(hist.sum())
    if not total:
        return None
    target = max(0, int(np.ceil(q * total)) - 1)
    idx = int(np.searchsorted(np.cumsum(hist, dtype=np.int64), target + 1))
    return float(idx - HIST_OFFSET)

def read_valid(ds, window):
    arr = ds.read(1, window=window, masked=False)
    valid = np.ones(arr.shape, dtype=bool)
    if ds.nodata is not None:
        valid &= arr != ds.nodata
    return arr, valid

def inspect_single(path: Path) -> dict:
    hist = np.zeros(HIST_SIZE, dtype=np.int64)
    count = nodata_count = total = total_sq = 0
    minimum = maximum = None
    with rasterio.open(path) as ds:
        for row in range(0, ds.height, BLOCK):
            for col in range(0, ds.width, BLOCK):
                window = Window(col, row, min(BLOCK, ds.width-col), min(BLOCK, ds.height-row))
                arr, valid = read_valid(ds, window)
                values = arr[valid].astype(np.int32)
                n = int(values.size)
                nodata_count += int(arr.size - n)
                if not n:
                    continue
                if values.min() < -HIST_OFFSET or values.max() >= HIST_OFFSET:
                    raise ValueError(f"{path.name}: values outside int16 histogram range")
                hist += np.bincount(values + HIST_OFFSET, minlength=HIST_SIZE)
                count += n
                total += int(values.sum(dtype=np.int64))
                total_sq += int(np.square(values.astype(np.int64)).sum(dtype=np.int64))
                vmin, vmax = int(values.min()), int(values.max())
                minimum = vmin if minimum is None else min(minimum, vmin)
                maximum = vmax if maximum is None else max(maximum, vmax)
        return {
            "width": ds.width, "height": ds.height, "crs": ds.crs.to_string() if ds.crs else None,
            "resolution_m": list(ds.res), "nodata_value": ds.nodata,
            "valid_pixels": count, "nodata_pixels": nodata_count,
            "valid_fraction": count / (count + nodata_count) if count + nodata_count else None,
            "minimum": minimum, "maximum": maximum,
            "mean_raw": total / count if count else None,
            "stddev_population_raw": max(0.0, total_sq / count - (total / count) ** 2) ** 0.5 if count else None,
            "p05_raw": hist_quantile(hist, .05), "p25_raw": hist_quantile(hist, .25),
            "p50_raw": hist_quantile(hist, .50), "p75_raw": hist_quantile(hist, .75),
            "p95_raw": hist_quantile(hist, .95),
        }

def compare_round_2_3(path2: Path, path3: Path) -> dict:
    diff_hist = np.zeros(2 * HIST_SIZE - 1, dtype=np.int64)
    overlap = only2 = only3 = total = total_abs = total_sq = 0
    min_diff = max_diff = None
    with rasterio.open(path2) as a, rasterio.open(path3) as b:
        if a.crs != b.crs or a.transform != b.transform or a.width != b.width or a.height != b.height:
            raise RuntimeError("Omdrev 2/3 grids are not exactly aligned; refusing pixelwise comparison")
        if a.res != b.res or a.bounds != b.bounds:
            raise RuntimeError("Omdrev 2/3 resolution/bounds differ; refusing pixelwise comparison")
        for row in range(0, a.height, BLOCK):
            for col in range(0, a.width, BLOCK):
                window = Window(col, row, min(BLOCK, a.width-col), min(BLOCK, a.height-row))
                ar, av = read_valid(a, window)
                br, bv = read_valid(b, window)
                both = av & bv
                only2 += int((av & ~bv).sum())
                only3 += int((~av & bv).sum())
                d = br[both].astype(np.int32) - ar[both].astype(np.int32)
                if not d.size:
                    continue
                overlap += int(d.size)
                total += int(d.sum(dtype=np.int64))
                total_abs += int(np.abs(d).sum(dtype=np.int64))
                total_sq += int(np.square(d.astype(np.int64)).sum(dtype=np.int64))
                lo, hi = int(d.min()), int(d.max())
                min_diff = lo if min_diff is None else min(min_diff, lo)
                max_diff = hi if max_diff is None else max(max_diff, hi)
                diff_hist += np.bincount(d + HIST_SIZE - 1, minlength=2 * HIST_SIZE - 1)
    def qvalue(q):
        if not overlap:
            return None
        pos = max(1, int(np.ceil(q * overlap)))
        return float(np.searchsorted(np.cumsum(diff_hist, dtype=np.int64), pos) - (HIST_SIZE - 1))
    return {
        "valid_overlap_pixels": overlap, "valid_only_omdrev2_pixels": only2,
        "valid_only_omdrev3_pixels": only3,
        "overlap_fraction_of_grid": overlap / (a.width * a.height),
        "difference_direction": "omdrev3_minus_omdrev2",
        "difference_minimum_raw": min_diff, "difference_maximum_raw": max_diff,
        "difference_mean_raw": total / overlap if overlap else None,
        "difference_mean_absolute_raw": total_abs / overlap if overlap else None,
        "difference_stddev_population_raw": max(0.0, total_sq / overlap - (total / overlap) ** 2) ** .5 if overlap else None,
        "difference_p05_raw": qvalue(.05), "difference_p50_raw": qvalue(.50), "difference_p95_raw": qvalue(.95),
    }

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"purpose": "Windowed raw-value statistics; direct pixel differences only on identical Omdrev 2/3 grids.",
              "value_interpretation": "Raw GeoTIFF integer values; unit and scale are not inferred.",
              "assets": [], "omdrev2_vs_3": []}
    with tempfile.TemporaryDirectory(prefix="skog-volume-stats-") as tmp:
        temp = Path(tmp)
        extracted = {}
        for r in ROUNDS:
            for c in CODES:
                archive = DATA / f"sks_Volym_omdrev{r}_{c}.zip"
                if not archive.is_file():
                    raise FileNotFoundError(archive)
                tif = extract_tif(archive, temp)
                extracted[(r, c)] = tif
                result["assets"].append({"survey_round": int(r), "tile_code": c, "archive": archive.name, **inspect_single(tif)})
        for c in CODES:
            result["omdrev2_vs_3"].append({"tile_code": c, **compare_round_2_3(extracted[("2", c)], extracted[("3", c)])})
    result["notes"] = [
        "Omdrev 1 uses 12.5 m pixels; Omdrev 2 and 3 use 10 m pixels. No Omdrev 1 pixelwise difference is calculated.",
        "Stored values are raw integers. Do not label them m3sk/ha until product encoding and scale are independently confirmed.",
        "Omdrev 2/3 grid alignment is rechecked at runtime before any pixelwise comparison.",
        "Cross-round differences are not automatically forest growth: acquisition dates, model versions, methods, leaf status and data quality may differ."
    ]
    path = OUT / "volume_pixel_statistics.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
