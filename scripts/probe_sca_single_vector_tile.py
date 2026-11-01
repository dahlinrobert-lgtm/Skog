#!/usr/bin/env python3
"""Fetch and inspect exactly one public SCA vector tile near Gräsmyr."""
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import mapbox_vector_tile

URL = "https://olga.scaskog.com/map/omraden/12/2271/1098.pbf"
HOST = "olga.scaskog.com"
MAX_BYTES = 5_000_000


def main():
    parsed = urlparse(URL)
    if parsed.scheme != "https" or parsed.netloc != HOST:
        raise RuntimeError("Tile host rejected")
    response = requests.get(
        URL,
        headers={"User-Agent": "Skog-read-only-SCA-single-tile-probe/1.0",
                 "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf"},
        timeout=(15, 45),
    )
    response.raise_for_status()
    if len(response.content) > MAX_BYTES:
        raise RuntimeError(f"Tile exceeds size limit: {len(response.content)} bytes")

    raw = response.content
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tile_url": URL,
        "tile": {"z": 12, "x": 2271, "y": 1098},
        "response": {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type"),
            "content_encoding": response.headers.get("Content-Encoding"),
            "bytes": len(raw),
            "magic_hex": raw[:16].hex(),
        },
        "decoded": None,
        "limits": {
            "one_tile_only": True,
            "feature_download_scope": "One tile intersecting the Gräsmyr area",
            "no_bulk_download": True,
            "no_snapshots_or_schedule": True,
            "commercial_reuse_not_assessed": True,
        },
    }
    decoded = mapbox_vector_tile.decode(raw)
    layers = {}
    for name, layer in decoded.items():
        features = layer.get("features", [])
        geometry_types = {}
        property_keys = set()
        for feature in features:
            geom_type = feature.get("geometry", {}).get("type", "unknown")
            geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
            property_keys.update(feature.get("properties", {}).keys())
        layers[name] = {
            "feature_count": len(features),
            "geometry_types": geometry_types,
            "property_keys": sorted(property_keys),
            "extent": layer.get("extent"),
            "version": layer.get("version"),
        }
    report["decoded"] = {"layer_count": len(layers), "layers": layers}

    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/sca-single-tile-probe.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
