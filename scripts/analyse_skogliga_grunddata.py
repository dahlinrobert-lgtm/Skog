#!/usr/bin/env python3
"""Windowed value and coverage analysis for Skogsstyrelsen volume rasters in ZIP archives."""
from __future__ import annotations

import json
import math
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = DATA_DIR / "pixel-analysis-report.json"
NODATA_FALLBACK = -1
# The source rasters are int16. A complete histogram gives exact percentiles without
# retaining the full raster in memory; windows limit peak memory use.
HIST_MIN = -32768
HIST_SIZE = 65536
PERCENTILES = (0, 1, 5, 25, 50, 75, 95, 99, 100)


def percentile_from_hist(hist: np.ndarray, count: int, p: float) -> int | None:
    if count == 0:
        return None
    rank = max(0, math.ceil((p / 100) * count) - 1)
    idx = int(np.searchsorted(np.cumsum(hist, dtype=np.uint64), rank + 1, side="left"))
    return HIST_MIN + idx


def analyse_raster(path: Path) -> dict:
    with rasterio.open(path) as ds:
        if ds.count < 1:
            raise ValueError("Raster has no bands")
        nodata = ds.nodata if ds.nodata is not None else NODATA_FALLBACK
        hist = np.zeros(HIST_SIZE, dtype=np.uint64)
        valid_count = 0
        nodata_count = 0
        min_value = None
        max_value = None
        sum_value = 0.0
        sum_squares = 0.0

        # Rasterio's block windows avoid loading a whole raster into memory.
        for _, window in ds.block_windows(1):
            arr = ds.read(1, window=window, masked=False)
            valid = arr != nodata
            nodata_count += int(arr.size - np.count_nonzero(valid))
            if not np.any(valid):
                continue
            vals = arr[valid].astype(np.int32, copy=False)
            lo, hi = int(vals.min()), int(vals.max())
            min_value = lo if min_value is None else min(min_value, lo)
            max_value = hi if max_value is None else max(max_value, hi)
            valid_count += int(vals.size)
            sum_value += float(vals.sum(dtype=np.int64))
            # Keep the sum of squares in float64 to avoid int64 overflow.
            fvals = vals.astype(np.float64)
            sum_squares += float(np.dot(fvals, fvals))
            hist += np.bincount(vals - HIST_MIN, minlength=HIST_SIZE).astype(np.uint64)

        mean = sum_value / valid_count if valid_count else None
        variance = max(0.0, sum_squares / valid_count - mean * mean) if valid_count else None
        bounds = [float(ds.bounds.left), float(ds.bounds.bottom),
                  float(ds.bounds.right), float(ds.bounds.top)]
        resolution = [float(ds.res[0]), float(ds.res[1])]
        result = {
            "file": path.name,
            "driver": ds.driver,
            "width": ds.width,
            "height": ds.height,
            "band_count": ds.count,
            "dtype": ds.dtypes[0],
            "crs": str(ds.crs) if ds.crs else None,
            "resolution": resolution,
            "bounds": bounds,
            "nodata": nodata,
            "total_pixels": int(ds.width * ds.height),
            "valid_pixels": valid_count,
            "nodata_pixels": nodata_count,
            "valid_percent": round(100 * valid_count / (ds.width * ds.height), 6) if ds.width * ds.height else None,
            "minimum": min_value,
            "maximum": max_value,
            "mean": mean,
            "standard_deviation": math.sqrt(variance) if variance is not None else None,
            "percentiles": {
                str(p): percentile_from_hist(hist, valid_count, p)
                for p in PERCENTILES
            },
        }
        return result


def overlap(a: list[float], b: list[float]) -> list[float] | None:
    left, bottom = max(a[0], b[0]), max(a[1], b[1])
    right, top = min(a[2], b[2]), min(a[3], b[3])
    if right <= left or top <= bottom:
        return None
    return [left, bottom, right, top]


def main() -> int:
    archives = sorted(DATA_DIR.glob("*.zip"))
    rasters = []
    errors = []
    for archive_path in archives:
        try:
            with zipfile.ZipFile(archive_path) as archive:
                candidates = [m for m in archive.infolist()
                              if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
                if not candidates:
                    errors.append({"archive": archive_path.name, "error": "No TIFF found"})
                    continue
                for member in candidates:
                    with tempfile.TemporaryDirectory(prefix="skog-volume-analysis-") as tmp:
                        target = Path(tmp) / Path(member.filename).name
                        with archive.open(member) as src, target.open("wb") as dst:
                            while chunk := src.read(1024 * 1024):
                                dst.write(chunk)
                        try:
                            item = analyse_raster(target)
                            item["archive"] = archive_path.name
                            rasters.append(item)
                        except Exception as exc:
                            errors.append({"archive": archive_path.name,
                                           "file": member.filename,
                                           "error": f"{type(exc).__name__}: {exc}"})
        except Exception as exc:
            errors.append({"archive": archive_path.name,
                           "error": f"{type(exc).__name__}: {exc}"})

    intersections = []
    for i, a in enumerate(rasters):
        for b in rasters[i + 1:]:
            common = overlap(a["bounds"], b["bounds"])
            intersections.append({
                "files": [a["file"], b["file"]],
                "bounding_box_overlap": common,
                "overlap_area_km2": round((common[2] - common[0]) * (common[3] - common[1]) / 1_000_000, 3) if common else 0,
                "same_crs": a["crs"] == b["crs"],
                "same_resolution": a["resolution"] == b["resolution"],
            })

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GitHub ZIP files: Skogsstyrelsen Skogliga grunddata – Volym, omdrev 3",
        "method": {
            "reading": "Windowed raster reads; originals are not modified",
            "nodata": "Excluded from statistics; source NoData used, or -1 if absent",
            "percentiles": "Exact integer percentiles from a full int16 histogram",
            "coverage_note": "Overlap uses bounding boxes only, not pixel-level valid-data footprints",
            "units_note": "Units/scaling are not inferred from pixel values; verify against product documentation",
        },
        "raster_count": len(rasters),
        "rasters": rasters,
        "bounding_box_comparisons": intersections,
        "errors": errors,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Analysed {len(rasters)} raster(s); errors: {len(errors)}; report: {OUT.relative_to(ROOT)}")
    for item in rasters:
        print(f"- {item['file']}: valid={item['valid_pixels']:,}, "
              f"NoData={item['nodata_pixels']:,}, min={item['minimum']}, "
              f"max={item['maximum']}, mean={item['mean']}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if not rasters or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
