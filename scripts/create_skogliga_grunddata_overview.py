#!/usr/bin/env python3
"""Create a lightweight map overview of Skogsstyrelsen volume raster ZIPs."""
from __future__ import annotations

import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import rasterio
from rasterio.enums import Resampling

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT_PNG = DATA_DIR / "raster-overview.png"
OUT_JSON = DATA_DIR / "raster-overview-report.json"
MAX_SIDE = 700
NODATA_FALLBACK = -1


def extract_tif(archive_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        members = [m for m in archive.infolist()
                   if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
        if len(members) != 1:
            raise ValueError(f"Expected one TIFF, found {len(members)}")
        member = members[0]
        target = target_dir / Path(member.filename).name
        with archive.open(member) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        return target


def main() -> int:
    archives = sorted(DATA_DIR.glob("*.zip"))
    summaries = []
    panels = []
    errors = []
    with tempfile.TemporaryDirectory(prefix="skog-raster-overview-") as temp:
        for archive in archives:
            try:
                tif = extract_tif(archive, Path(temp) / archive.stem)
                with rasterio.open(tif) as ds:
                    nodata = ds.nodata if ds.nodata is not None else NODATA_FALLBACK
                    scale = min(1.0, MAX_SIDE / max(ds.width, ds.height))
                    out_w = max(1, round(ds.width * scale))
                    out_h = max(1, round(ds.height * scale))
                    arr = ds.read(1, out_shape=(out_h, out_w), resampling=Resampling.nearest)
                    # 0 = NoData, 1 = valid zero, 2 = positive volume, 3 = unexpected negative value.
                    cls = np.zeros(arr.shape, dtype=np.uint8)
                    cls[(arr != nodata) & (arr == 0)] = 1
                    cls[(arr != nodata) & (arr > 0)] = 2
                    cls[(arr != nodata) & (arr < 0)] = 3
                    total = ds.width * ds.height
                    full_valid = int(np.count_nonzero(arr != nodata))
                    summaries.append({
                        "archive": archive.name,
                        "raster": tif.name,
                        "crs": str(ds.crs) if ds.crs else None,
                        "resolution_m": list(ds.res),
                        "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
                        "width": ds.width,
                        "height": ds.height,
                        "nodata": nodata,
                        "overview_width": out_w,
                        "overview_height": out_h,
                        "overview_sampling": "nearest neighbour, display-only downsampling",
                        "valid_pixels_in_overview": int(np.count_nonzero(cls > 0)),
                        "zero_pixels_in_overview": int(np.count_nonzero(cls == 1)),
                        "positive_pixels_in_overview": int(np.count_nonzero(cls == 2)),
                        "unexpected_negative_pixels_in_overview": int(np.count_nonzero(cls == 3)),
                        "note": "Pixel counts above are from the downsampled overview, not exact full-resolution counts."
                    })
                    panels.append((archive.name, cls, [ds.bounds.left, ds.bounds.right, ds.bounds.bottom, ds.bounds.top]))
            except Exception as exc:
                errors.append({"archive": archive.name, "error": f"{type(exc).__name__}: {exc}"})

    if not panels:
        print(f"No raster overview created; errors={errors}")
        return 1

    cmap = ListedColormap(["#e5e7eb", "#f5d76e", "#237a57", "#c2410c"])
    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 7), constrained_layout=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (name, cls, extent) in zip(axes, panels):
        ax.imshow(cls, extent=extent, origin="upper", interpolation="nearest",
                  cmap=cmap, vmin=0, vmax=3, aspect="equal")
        ax.set_title(name.replace("sks_Volym_", "").replace(".zip", ""), fontsize=11)
        ax.set_xlabel("SWEREF 99 TM Easting (m)")
        ax.set_ylabel("SWEREF 99 TM Northing (m)")
        ax.ticklabel_format(style="plain", axis="both", useOffset=False)
        ax.grid(True, linewidth=0.3, alpha=0.3)
    from matplotlib.patches import Patch
    legend = [
        Patch(facecolor="#e5e7eb", edgecolor="#9ca3af", label="NoData (-1)"),
        Patch(facecolor="#f5d76e", edgecolor="#9ca3af", label="Valid zero"),
        Patch(facecolor="#237a57", edgecolor="#9ca3af", label="Positive volume"),
        Patch(facecolor="#c2410c", edgecolor="#9ca3af", label="Other negative value"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("Skogsstyrelsen – Volym, omdrev 3: rasteröversikt", fontsize=14)
    fig.savefig(OUT_PNG, dpi=160, bbox_inches="tight")
    plt.close(fig)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "ZIP rasters stored in this repository",
        "purpose": "Visual coverage check, not a map for measurement",
        "legend": {"0": "NoData", "1": "valid zero", "2": "positive volume", "3": "unexpected negative value"},
        "note": "Display is downsampled with nearest-neighbour resampling. Use source rasters for any calculations.",
        "raster_count": len(summaries),
        "rasters": summaries,
        "errors": errors,
        "png": str(OUT_PNG.relative_to(ROOT)),
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {OUT_PNG.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}; rasters={len(summaries)}; errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
