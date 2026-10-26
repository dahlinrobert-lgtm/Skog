#!/usr/bin/env python3
"""Compare valid-data coverage and pixel values where Skogsstyrelsen rasters overlap."""
from __future__ import annotations

import json
import math
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = DATA_DIR / "overlap-analysis-report.json"
TIFFS = sorted(DATA_DIR.glob("*.zip"))
NODATA_FALLBACK = -1
BLOCK_W = 1024
BLOCK_H = 512


def extract_tif(archive_path: Path, target_dir: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        members = [m for m in archive.infolist()
                   if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
        if len(members) != 1:
            raise ValueError(f"{archive_path.name}: expected one TIFF, found {len(members)}")
        member = members[0]
        target = target_dir / Path(member.filename).name
        with archive.open(member) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        return target


def intersect_bounds(a, b):
    left, bottom = max(a.left, b.left), max(a.bottom, b.bottom)
    right, top = min(a.right, b.right), min(a.top, b.top)
    if right <= left or top <= bottom:
        return None
    return left, bottom, right, top


def overlap_windows(ds_a, ds_b, bbox):
    left, bottom, right, top = bbox
    rx, ry = ds_a.res
    # Ensure both data grids have identical alignment before comparing values.
    if ds_a.crs != ds_b.crs or ds_a.res != ds_b.res:
        raise ValueError("Rasters use different CRS or cell resolution")
    offsets = [
        (left - ds_a.bounds.left) / rx,
        (ds_a.bounds.top - top) / ry,
        (left - ds_b.bounds.left) / rx,
        (ds_b.bounds.top - top) / ry,
        (right - left) / rx,
        (top - bottom) / ry,
    ]
    if any(abs(v - round(v)) > 1e-6 for v in offsets):
        raise ValueError(f"Intersection is not aligned to both raster grids: {offsets}")
    col_a, row_a, col_b, row_b, width, height = [int(round(v)) for v in offsets]
    return (Window(col_a, row_a, width, height),
            Window(col_b, row_b, width, height), width, height)


def compare_pair(path_a: Path, path_b: Path) -> dict:
    with rasterio.open(path_a) as a, rasterio.open(path_b) as b:
        bbox = intersect_bounds(a.bounds, b.bounds)
        result = {
            "files": [path_a.name, path_b.name],
            "same_crs": a.crs == b.crs,
            "same_resolution": a.res == b.res,
            "overlap_bounds": list(bbox) if bbox else None,
        }
        if not bbox:
            result.update({
                "overlap_area_km2": 0,
                "overlap_pixels": 0,
                "both_nodata_pixels": 0,
                "only_first_has_value": 0,
                "only_second_has_value": 0,
                "both_have_values": 0,
                "both_zero_pixels": 0,
                "both_positive_pixels": 0,
                "equal_value_pixels_when_both_valid": 0,
                "different_value_pixels_when_both_valid": 0,
                "mean_absolute_difference_when_both_valid": None,
            })
            return result

        wa, wb, width, height = overlap_windows(a, b, bbox)
        nodata_a = a.nodata if a.nodata is not None else NODATA_FALLBACK
        nodata_b = b.nodata if b.nodata is not None else NODATA_FALLBACK
        counts = {
            "both_nodata_pixels": 0,
            "only_first_has_value": 0,
            "only_second_has_value": 0,
            "both_have_values": 0,
            "both_zero_pixels": 0,
            "both_positive_pixels": 0,
            "equal_value_pixels_when_both_valid": 0,
            "different_value_pixels_when_both_valid": 0,
        }
        absolute_difference_sum = 0
        both_valid_count = 0
        for row in range(0, height, BLOCK_H):
            h = min(BLOCK_H, height - row)
            for col in range(0, width, BLOCK_W):
                w = min(BLOCK_W, width - col)
                xa = a.read(1, window=Window(wa.col_off + col, wa.row_off + row, w, h))
                xb = b.read(1, window=Window(wb.col_off + col, wb.row_off + row, w, h))
                va = xa != nodata_a
                vb = xb != nodata_b
                both = va & vb
                only_a = va & ~vb
                only_b = ~va & vb
                counts["both_nodata_pixels"] += int(np.count_nonzero(~va & ~vb))
                counts["only_first_has_value"] += int(np.count_nonzero(only_a))
                counts["only_second_has_value"] += int(np.count_nonzero(only_b))
                counts["both_have_values"] += int(np.count_nonzero(both))
                counts["both_zero_pixels"] += int(np.count_nonzero(both & (xa == 0) & (xb == 0)))
                counts["both_positive_pixels"] += int(np.count_nonzero(both & (xa > 0) & (xb > 0)))
                if np.any(both):
                    diff = xa[both].astype(np.int32) - xb[both].astype(np.int32)
                    equal = diff == 0
                    counts["equal_value_pixels_when_both_valid"] += int(np.count_nonzero(equal))
                    counts["different_value_pixels_when_both_valid"] += int(diff.size - np.count_nonzero(equal))
                    absolute_difference_sum += int(np.abs(diff).sum(dtype=np.int64))
                    both_valid_count += int(diff.size)
        total = width * height
        result.update(counts)
        result.update({
            "overlap_pixel_width": width,
            "overlap_pixel_height": height,
            "overlap_pixels": total,
            "overlap_area_km2": round(total * abs(a.res[0] * a.res[1]) / 1_000_000, 3),
            "only_first_has_value_percent": round(100 * counts["only_first_has_value"] / total, 6),
            "only_second_has_value_percent": round(100 * counts["only_second_has_value"] / total, 6),
            "both_have_values_percent": round(100 * counts["both_have_values"] / total, 6),
            "both_nodata_percent": round(100 * counts["both_nodata_pixels"] / total, 6),
            "equal_value_percent_when_both_valid": (
                round(100 * counts["equal_value_pixels_when_both_valid"] / both_valid_count, 6)
                if both_valid_count else None
            ),
            "mean_absolute_difference_when_both_valid": (
                absolute_difference_sum / both_valid_count if both_valid_count else None
            ),
        })
        return result


def main() -> int:
    archives = sorted(DATA_DIR.glob("*.zip"))
    rasters = []
    errors = []
    pair_results = []
    with tempfile.TemporaryDirectory(prefix="skog-raster-overlap-") as temp:
        root = Path(temp)
        extracted = {}
        for archive in archives:
            try:
                member_dir = root / archive.stem
                member_dir.mkdir(parents=True, exist_ok=True)
                extracted[archive.name] = extract_tif(archive, member_dir)
            except Exception as exc:
                errors.append({"archive": archive.name, "error": f"{type(exc).__name__}: {exc}"})
        paths = sorted(extracted.values())
        for i, path_a in enumerate(paths):
            for path_b in paths[i + 1:]:
                try:
                    pair_results.append(compare_pair(path_a, path_b))
                except Exception as exc:
                    errors.append({"files": [path_a.name, path_b.name],
                                   "error": f"{type(exc).__name__}: {exc}"})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Local Skogsstyrelsen volume raster ZIPs stored in this repository",
        "method": {
            "reading": "Windowed 1024x512 blocks inside exact raster-grid intersections",
            "validity": "Only each raster's explicit NoData value (fallback -1) is treated as missing; zero is a valid encoded value",
            "comparisons": "Counts per-cell data presence and compares values where both cells are valid",
            "limitations": "Equal values do not prove two files are duplicates; rasters may represent different releases or calculation versions",
        },
        "pair_count": len(pair_results),
        "comparisons": pair_results,
        "errors": errors,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Compared {len(pair_results)} overlapping raster pair(s); errors: {len(errors)}")
    for item in pair_results:
        print(f"- {' vs '.join(item['files'])}: overlap={item['overlap_area_km2']} km2, "
              f"both have values={item.get('both_have_values_percent')}%, "
              f"equal where both valid={item.get('equal_value_percent_when_both_valid')}%")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if not archives or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
