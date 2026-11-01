#!/usr/bin/env python3
"""Probe a small, fixed set of SCA voluntary set-aside vector tiles.

This is a bounded access test only: it does not archive tile payloads or
attempt to enumerate the service.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urljoin

import requests

PAGE_URL = "https://olga.scaskog.com/map/index.html"
LAYER_PATH = "omraden/{z}/{x}/{y}.pbf"
ZOOM = 12
LOCATIONS = {
    "Sundsvall": (62.3908, 17.3069),
    "Timra": (62.4870, 17.3260),
    "Umea": (63.8258, 20.2630),
    "Grasmyr": (63.74646, 19.66455),
}


def xyz_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    x = math.floor((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = math.floor((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def main() -> None:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Skog-data-source-probe/1.0 (bounded diagnostic)",
        "Referer": PAGE_URL,
        "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf, */*",
    })
    results = []
    for name, (lat, lon) in LOCATIONS.items():
        x, y = xyz_tile(lat, lon, ZOOM)
        relative = LAYER_PATH.format(z=ZOOM, x=x, y=y)
        url = urljoin(PAGE_URL, relative)
        item = {
            "location": name,
            "zoom": ZOOM,
            "x": x,
            "y": y,
            "url": url,
        }
        try:
            response = session.get(url, timeout=25)
            body = response.content
            item.update({
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if body else None,
                "looks_like_pbf": bool(body) and response.status_code == 200
                    and "text/html" not in response.headers.get("Content-Type", "").lower(),
            })
        except requests.RequestException as exc:
            item["request_error"] = f"{type(exc).__name__}: {exc}"
        results.append(item)

    output = {
        "page": PAGE_URL,
        "layer": "Frivilliga avsättningar",
        "format": "MVT/PBF",
        "tile_url_template": LAYER_PATH,
        "coordinate_scheme": "XYZ / EPSG:3857",
        "probe_count": len(results),
        "payloads_archived": False,
        "results": results,
    }
    Path("sca-voluntary-set-aside-tile-probe.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
