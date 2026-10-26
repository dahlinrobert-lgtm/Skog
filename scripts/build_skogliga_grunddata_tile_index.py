#!/usr/bin/env python3
"""Build a sparse 5 km tile index for Skogsstyrelsen volume rasters."""
from __future__ import annotations

import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = DATA_DIR / "tile-index-5km.json"
TILE_METRES = 5000
CELL_METRES = 10
CELLS_PER_TILE = TILE_METRES // CELL_METRES
NODATA_FALLBACK = -1


def extract_tif(archive_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = [m for m in archive.infolist()
                   if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
        if len(members) != 1:
            raise ValueError(f"{archive_path.name}: expected exactly one TIFF, found {len(members)}")
        member = members[0]
        target = target_dir / Path(member.filename).name
        with archive.open(member) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        return target


def main() -> int:
    archives = sorted(DATA_DIR.glob("*.zip"))
    if not archives:
        raise RuntimeError(f"No source ZIP files found in {DATA_DIR}")

    rasters = []
    errors = []
    with tempfile.TemporaryDirectory(prefix="skog-tile-index-") as temp:
        for archive in archives:
            try:
                tif = extract_tif(archive, Path(temp) / archive.stem)
                tiles = []
                with rasterio.open(tif) as ds:
                    if ds.crs is None or ds.crs.to_epsg() != 3006:
                        raise ValueError(f"Expected EPSG:3006, got {ds.crs}")
                    xres, yres = abs(ds.res[0]), abs(ds.res[1])
                    if not (abs(xres - CELL_METRES) < 1e-6 and abs(yres - CELL_METRES) < 1e-6):
                        raise ValueError(f"Expected 10 m cells, got {ds.res}")
                    nodata = ds.nodata if ds.nodata is not None else NODATA_FALLBACK
                    total_valid = total_zero = total_positive = total_nodata = 0
                    tile_rows = (ds.height + CELLS_PER_TILE - 1) // CELLS_PER_TILE
                    tile_cols = (ds.width + CELLS_PER_TILE - 1) // CELLS_PER_TILE
                    for tile_row in range(tile_rows):
                        row_off = tile_row * CELLS_PER_TILE
                        height = min(CELLS_PER_TILE, ds.height - row_off)
                        for tile_col in range(tile_cols):
                            col_off = tile_col * CELLS_PER_TILE
                            width = min(CELLS_PER_TILE, ds.width - col_off)
                            arr = ds.read(1, window=Window(col_off, row_off, width, height))
                            valid = arr != nodata
                            zero = valid & (arr == 0)
                            positive = valid & (arr > 0)
                            other_negative = valid & (arr < 0)
                            valid_count = int(np.count_nonzero(valid))
                            zero_count = int(np.count_nonzero(zero))
                            positive_count = int(np.count_nonzero(positive))
                            nodata_count = int(arr.size - valid_count)
                            total_valid += valid_count
                            total_zero += zero_count
                            total_positive += positive_count
                            total_nodata += nodata_count
                            # Sparse index: retain only tiles containing at least one valid cell.
                            if valid_count:
                                left = ds.transform.c + col_off * ds.transform.a
                                top = ds.transform.f + row_off * ds.transform.e
                                right = left + width * ds.transform.a
                                bottom = top + height * ds.transform.e
                                tiles.append({
                                    "tile_id": f"{archive.stem}:{tile_row:04d}:{tile_col:04d}",
                                    "tile_row": tile_row,
                                    "tile_col": tile_col,
                                    "bounds_epsg3006": [
                                        round(min(left, right), 3), round(min(bottom, top), 3),
                                        round(max(left, right), 3), round(max(bottom, top), 3)
                                    ],
                                    "width_cells": width,
                                    "height_cells": height,
                                    "valid_cells": valid_count,
                                    "zero_cells": zero_count,
                                    "positive_cells": positive_count,
                                    "other_negative_cells": int(np.count_nonzero(other_negative)),
                                    "nodata_cells": nodata_count,
                                })
                    rasters.append({
                        "archive": archive.name,
                        "raster": tif.name,
                        "crs": ds.crs.to_string(),
                        "cell_size_m": [xres, yres],
                        "bounds_epsg3006": [
                            round(ds.bounds.left, 3), round(ds.bounds.bottom, 3),
                            round(ds.bounds.right, 3), round(ds.bounds.top, 3)
                        ],
                        "width_cells": ds.width,
                        "height_cells": ds.height,
                        "nodata_value": nodata,
                        "tile_size_m": TILE_METRES,
                        "tile_size_cells": CELLS_PER_TILE,
                        "grid_tiles_scanned": tile_rows * tile_cols,
                        "occupied_tiles": len(tiles),
                        "valid_cells": total_valid,
                        "zero_cells": total_zero,
                        "positive_cells": total_positive,
                        "nodata_cells": total_nodata,
                        "tiles": tiles,
                    })
            except Exception as exc:
                errors.append({"archive": archive.name, "error": f"{type(exc).__name__}: {exc}"})

    if errors or not rasters:
        print(json.dumps({"errors": errors, "rasters_completed": len(rasters)}, ensure_ascii=False))
        return 1

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "ZIP rasters in data/skogliga-grunddata",
        "purpose": "Sparse discovery index; not a replacement for source pixels or a cadastral boundary",
        "crs": "EPSG:3006",
        "tile_size_m": TILE_METRES,
        "tile_size_cells": CELLS_PER_TILE,
        "cell_size_m": CELL_METRES,
        "value_semantics": {
            "nodata": "NoData, excluded from valid-cell counts",
            "zero": "Valid raster value; not NoData",
            "positive": "Positive volume value in m³sk/ha",
            "other_negative": "Counted separately for quality control"
        },
        "raster_count": len(rasters),
        "occupied_tile_count": sum(r["occupied_tiles"] for r in rasters),
        "rasters": rasters,
        "errors": errors,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Created {OUT.relative_to(ROOT)}; rasters={len(rasters)}; occupied_tiles={report['occupied_tile_count']}; errors=0")
    for raster in rasters:
        print(f"{raster['archive']}: occupied_tiles={raster['occupied_tiles']}, valid={raster['valid_cells']}, zero={raster['zero_cells']}, positive={raster['positive_cells']}, nodata={raster['nodata_cells']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
