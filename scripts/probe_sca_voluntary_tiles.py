#!/usr/bin/env python3
"""Make two bounded HTTP probes against SCA's configured voluntary set-aside MVT layer."""
from __future__ import annotations

import json
from pathlib import Path

import requests

# Relative to /map/index.html, the configured template resolves under /map/.
# Two z=4 XYZ tiles are tested only as endpoint checks; this does not assert
# complete SCA coverage or prove that the layer uses the standard grid.
BASE = "https://olga.scaskog.com/map/omraden"
TILES = [(4, 8, 4), (4, 8, 5)]


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-SCA-bounded-tile-probe/1.0"})
    results = []
    for z, x, y in TILES:
        url = f"{BASE}/{z}/{x}/{y}.pbf"
        try:
            response = session.get(url, timeout=25)
            body = response.content
            results.append({
                "z": z, "x": x, "y": y,
                "url": url,
                "http_status": response.status_code,
                "content_type": response.headers.get("Content-Type"),
                "content_length_header": response.headers.get("Content-Length"),
                "body_bytes": len(body),
                "looks_like_html": body.lstrip().lower().startswith((b"<!doctype html", b"<html")),
                "error": None,
            })
        except requests.RequestException as exc:
            results.append({
                "z": z, "x": x, "y": y, "url": url,
                "http_status": None, "content_type": None,
                "content_length_header": None, "body_bytes": 0,
                "looks_like_html": None, "error": str(exc),
            })

    output = {
        "layer": "Frivilliga avsättningar",
        "configured_template": "omraden/{z}/{x}/{y}.pbf",
        "base_url": BASE,
        "tile_coordinates": "two bounded z=4 XYZ endpoint probes; grid still to be verified",
        "requests_made": len(TILES),
        "results": results,
        "feature_data_decoded": False,
        "bulk_download_performed": False,
    }
    Path("sca-voluntary-tile-probe.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
