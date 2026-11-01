#!/usr/bin/env python3
"""Decode one verified SCA voluntary set-aside MVT tile and summarize its schema."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import mapbox_vector_tile
import requests

URL = "https://olga.scaskog.com/map/omraden/4/8/4.pbf"


def main() -> None:
    response = requests.get(URL, timeout=30, headers={
        "User-Agent": "Skog-SCA-single-tile-schema-probe/1.0"
    })
    response.raise_for_status()
    if "protobuf" not in response.headers.get("Content-Type", "").lower():
        raise RuntimeError(f"Unexpected content type: {response.headers.get('Content-Type')}")

    decoded = mapbox_vector_tile.decode(response.content)
    layer_summaries = []
    for layer_name, layer in decoded.items():
        features = layer.get("features", [])
        geometry_types = Counter()
        property_keys = set()
        samples = {}
        for feature in features:
            geometry = feature.get("geometry") or {}
            geometry_types[geometry.get("type", "unknown")] += 1
            props = feature.get("properties") or {}
            property_keys.update(props)
            for key, value in props.items():
                if key not in samples and value is not None:
                    samples[key] = {
                        "python_type": type(value).__name__,
                        "sample": value if isinstance(value, (str, int, float, bool)) else str(value)[:120],
                    }
        layer_summaries.append({
            "layer_name": layer_name,
            "feature_count": len(features),
            "geometry_types": dict(geometry_types),
            "property_keys": sorted(property_keys),
            "property_value_samples": samples,
            "extent": layer.get("extent"),
            "version": layer.get("version"),
        })

    output = {
        "source_url": URL,
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "tile_bytes": len(response.content),
        "decoded_mvt": True,
        "layers": layer_summaries,
        "scope": "one tile only; no bulk download or full coverage inference",
    }
    Path("sca-voluntary-mvt-schema.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
