#!/usr/bin/env python3
"""Create lightweight, georeferenced PNG overlays for the experimental volume-raster map layer."""
from __future__ import annotations
import json, tempfile, zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, transform_bounds
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "skogliga-grunddata"
OUT = ROOT / "docs" / "volume-overlays"
MAX_SIDE = 700
NODATA_FALLBACK = -1

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"title": "Skogsstyrelsen Volym omdrev 3 – testlager",
                "note": "Nedskalad visningsbild, inte för mätning. Grå=NoData, gul=giltigt nollvärde, grön=positiv volym.",
                "rasters": []}
    with tempfile.TemporaryDirectory(prefix="volume-overlay-") as temp:
        for archive_path in sorted(DATA.glob("*.zip")):
            with zipfile.ZipFile(archive_path) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith((".tif", ".tiff"))]
                if len(names) != 1:
                    raise ValueError(f"{archive_path.name}: expected one TIFF, got {len(names)}")
                tif = Path(temp) / Path(names[0]).name
                with zf.open(names[0]) as src, tif.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
            with rasterio.open(tif) as src:
                nodata = src.nodata if src.nodata is not None else NODATA_FALLBACK
                scale = min(1.0, MAX_SIDE / max(src.width, src.height))
                width, height = max(1, round(src.width * scale)), max(1, round(src.height * scale))
                arr = src.read(1, out_shape=(height, width), resampling=Resampling.nearest)
                valid = arr != nodata
                rgba = np.zeros((height, width, 4), dtype=np.uint8)
                # Transparent NoData keeps the basemap visible. Valid zero is yellow; positive volume green.
                rgba[valid & (arr == 0)] = [245, 215, 110, 205]
                rgba[valid & (arr > 0)] = [35, 122, 87, 205]
                rgba[valid & (arr < 0)] = [194, 65, 12, 205]
                # Nearest-neighbour overview retains the class semantics without pretending to be full resolution.
                image_name = archive_path.stem + ".png"
                Image.fromarray(rgba, mode="RGBA").save(OUT / image_name, optimize=True)
                bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds, densify_pts=21)
                manifest["rasters"].append({
                    "archive": archive_path.name, "image": image_name,
                    "bounds_wgs84": list(bounds),
                    "display_resolution": [width, height],
                    "crs_source": str(src.crs),
                    "source_resolution_m": list(src.res),
                    "note": "Downsampled nearest-neighbour display only; source raster must be used for analysis."
                })
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(manifest['rasters'])} georeferenced PNG overlays in docs/volume-overlays")
if __name__ == "__main__":
    main()
