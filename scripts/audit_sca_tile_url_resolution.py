#!/usr/bin/env python3
"""Extract the actual public SCA OLGA configuration; make no tile requests."""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

PAGE = "https://olga.scaskog.com/map/index.html"
JS = "https://olga.scaskog.com/map/olga.js"


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-source-config-audit/1.0"})
    page = session.get(PAGE, timeout=30)
    page.raise_for_status()
    bundle = session.get(JS, timeout=45)
    bundle.raise_for_status()

    match = re.search(r"olgaConfig\\s*=\\s*({)", page.text)
    if not match:
        raise RuntimeError("Could not find inline olgaConfig object")
    config, end = json.JSONDecoder().raw_decode(page.text[match.start(1):])
    layers = config.get("layers", [])
    vector_layers = []
    for layer in layers:
        source = layer.get("source") or {}
        if layer.get("type") == "VectorTile" or source.get("type") == "VectorTile":
            vector_layers.append({
                "name": layer.get("name"),
                "visible": layer.get("visible"),
                "renderMode": layer.get("renderMode"),
                "type": layer.get("type"),
                "source": source,
                "minResolution": layer.get("minResolution"),
                "maxResolution": layer.get("maxResolution"),
            })

    # Capture the offline-only implementation separately so it cannot be
    # confused with the public online VectorTile source configuration.
    offline_marker = "function x(t,e,n,r)"
    pos = bundle.text.find(offline_marker)
    offline_context = bundle.text[max(0, pos - 250):pos + 2200] if pos >= 0 else None

    output = {
        "page_url": PAGE,
        "page_status": page.status_code,
        "js_url": JS,
        "js_status": bundle.status_code,
        "map_view": config.get("view"),
        "vector_tile_layers": vector_layers,
        "online_layer_url_templates": [
            {"name": item["name"], "url": (item.get("source") or {}).get("url")}
            for item in vector_layers
        ],
        "offline_vector_tile_implementation_context": offline_context,
        "tile_requests_made": 0,
        "feature_data_downloaded": False,
    }
    Path("sca-tile-url-resolution-audit.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "page_status": page.status_code,
        "js_status": bundle.status_code,
        "map_view": output["map_view"],
        "vector_tile_layers": output["online_layer_url_templates"],
        "tile_requests_made": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
