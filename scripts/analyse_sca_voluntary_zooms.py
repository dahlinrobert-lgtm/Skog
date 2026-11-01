#!/usr/bin/env python3
"""Compare a small set of nested SCA voluntary-set-aside tiles across zoom levels."""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import mapbox_vector_tile
import requests

BASE = "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
# Center of the already verified XYZ tile 4/8/4. Descendant tiles are
# calculated from this fixed geographic point, not from the offline grid code.
Z0, X0, Y0 = 4, 8, 4
ZOOMS = [4, 5, 7, 9, 12, 15]


def tile_center_lonlat(z: int, x: int, y: int) -> tuple[float, float]:
    n = 2 ** z
    lon = (x + 0.5) / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n)))
    return lon, math.degrees(lat_rad)


def xyz_for_lonlat(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def main() -> None:
    lon, lat = tile_center_lonlat(Z0, X0, Y0)
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-SCA-zoom-schema-probe/1.0"})
    results = []
    for z in ZOOMS:
        x, y = xyz_for_lonlat(lon, lat, z)
        url = BASE.format(z=z, x=x, y=y)
        item = {
            "z": z, "x": x, "y": y, "url": url,
            "http_status": None, "content_type": None, "bytes": 0,
            "layers": [], "error": None,
        }
        try:
            response = session.get(url, timeout=30)
            item["http_status"] = response.status_code
            item["content_type"] = response.headers.get("Content-Type")
            item["bytes"] = len(response.content)
            if response.status_code == 200 and "protobuf" in item["content_type"].lower():
                decoded = mapbox_vector_tile.decode(response.content)
                for layer_name, layer in decoded.items():
                    features = layer.get("features", [])
                    geom_types = Counter()
                    keys = set()
                    sample_values = {}
                    for feature in features:
                        geom = feature.get("geometry") or {}
                        geom_types[geom.get("type", "unknown")] += 1
                        props = feature.get("properties") or {}
                        keys.update(props)
                        for key, value in props.items():
                            if key not in sample_values and value is not None:
                                sample_values[key] = str(value)[:100]
                    item["layers"].append({
                        "name": layer_name,
                        "feature_count": len(features),
                        "geometry_types": dict(geom_types),
                        "property_keys": sorted(keys),
                        "sample_values": sample_values,
                        "extent": layer.get("extent"),
                    })
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        results.append(item)

    output = {
        "layer": "Frivilliga avsättningar",
        "reference_tile": f"{Z0}/{X0}/{Y0}",
        "reference_tile_center_lon_lat": [lon, lat],
        "zooms_tested": ZOOMS,
        "results": results,
        "scope": "one nested tile path at six zoom levels; not a coverage survey",
        "bulk_download": False,
    }
    Path("sca-voluntary-zoom-analysis.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
