#!/usr/bin/env python3
"""Probe Skogsstyrelsen ImageServer and attempt a small GeoTIFF export.

This is diagnostic only: it does not replace the source ZIP files.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests
import rasterio
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = DATA_DIR / "rest-probe-report.json"
SERVICE = "https://geodata.skogsstyrelsen.se/arcgis/rest/services/Publikt/SkogligaGrunddata_3_1/ImageServer"
TIMEOUT = (15, 60)

# This small sample falls inside the extent of the uploaded county raster _10.
# SWEREF 99 TM (EPSG:3006); request a 500 m x 500 m sample.
BBOX = "500000,6250000,500500,6250500"


def main() -> int:
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "service_url": SERVICE,
        "purpose": "Check ImageServer metadata and whether a small GeoTIFF export is accessible",
        "sample": {"bbox": BBOX, "bbox_sr": 3006, "size": "50,50", "expected_cell_size_m": 10},
        "metadata": {},
        "export": {},
        "notes": [
            "An HTTP response alone does not prove pixel values match the local ZIP raster.",
            "The service may require a Skogsstyrelsen raster account; a 401/403 or login response is recorded, not treated as raster data."
        ],
    }
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-raster-rest-probe/1.0"})
    try:
        response = session.get(SERVICE, params={"f": "json"}, timeout=TIMEOUT)
        report["metadata"] = {
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "url": response.url,
        }
        if response.ok:
            try:
                payload = response.json()
                report["metadata"]["service_description"] = payload.get("description")
                report["metadata"]["service_name"] = payload.get("name")
                report["metadata"]["pixel_type"] = payload.get("pixelType")
                report["metadata"]["band_count"] = payload.get("bandCount")
                report["metadata"]["spatial_reference"] = payload.get("spatialReference")
                report["metadata"]["capabilities"] = payload.get("capabilities")
                report["metadata"]["error"] = payload.get("error")
            except ValueError:
                report["metadata"]["body_preview"] = response.text[:500]
        else:
            report["metadata"]["body_preview"] = response.text[:500]
    except requests.RequestException as exc:
        report["metadata"] = {"error": f"{type(exc).__name__}: {exc}"}

    params = {
        "f": "image",
        "bbox": BBOX,
        "bboxSR": 3006,
        "imageSR": 3006,
        "size": "50,50",
        "format": "tiff",
        "pixelType": "S16",
        "noData": "-1",
        "noDataInterpretation": "esriNoDataMatchAny",
        "interpolation": "RSP_NearestNeighbor",
        "mosaicRule": json.dumps({"where": "Omdrev=3"}, separators=(",", ":")),
        "renderingRule": json.dumps({"rasterFunction": "Volym_rod"}, separators=(",", ":")),
    }
    try:
        response = session.get(f"{SERVICE}/exportImage", params=params, timeout=TIMEOUT)
        export = {
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "content_length": len(response.content),
            "url": response.url,
        }
        if response.ok and response.content[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
            try:
                with MemoryFile(response.content) as mem:
                    with mem.open() as ds:
                        export["readable_as_raster"] = True
                        export["driver"] = ds.driver
                        export["width"] = ds.width
                        export["height"] = ds.height
                        export["band_count"] = ds.count
                        export["dtypes"] = list(ds.dtypes)
                        export["crs"] = str(ds.crs) if ds.crs else None
                        export["resolution"] = list(ds.res)
                        export["bounds"] = [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top]
                        export["nodata"] = ds.nodata
                        export["sample_values"] = [
                            int(v) if str(v).lstrip("-").isdigit() else str(v)
                            for v in ds.read(1, window=((0, min(5, ds.height)), (0, min(5, ds.width)))).flatten().tolist()
                        ]
            except Exception as exc:
                export["readable_as_raster"] = False
                export["raster_error"] = f"{type(exc).__name__}: {exc}"
        else:
            export["readable_as_raster"] = False
            export["body_preview"] = response.text[:500] if "text" in response.headers.get("content-type", "").lower() or "json" in response.headers.get("content-type", "").lower() else response.content[:80].hex()
            try:
                export["json"] = response.json()
            except ValueError:
                pass
        report["export"] = export
    except requests.RequestException as exc:
        report["export"] = {"error": f"{type(exc).__name__}: {exc}"}

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["export"].get("readable_as_raster") else 1


if __name__ == "__main__":
    raise SystemExit(main())
