#!/usr/bin/env python3
"""Extract the exact SCA map layer and view configuration; do not request tiles."""
import json
import re
from urllib.parse import urljoin
import requests

PAGE = "https://olga.scaskog.com/map/index.html"
HOST = "olga.scaskog.com"
session = requests.Session()
session.headers.update({"User-Agent": "Skog-read-only-SCA-tile-grid-config/1.0"})


def extract_json_assignment(source, variable):
    match = re.search(r"\\b" + re.escape(variable) + r"\\s*=\\s*", source)
    if not match:
        raise ValueError(f"{variable} assignment not found")
    start = source.find("{", match.end())
    if start < 0:
        raise ValueError("Object start not found")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(source[start:index + 1])
    raise ValueError("Unclosed configuration object")


def main():
    response = session.get(PAGE, timeout=(15, 45))
    response.raise_for_status()
    response.raise_for_status()
    config = extract_json_assignment(response.text, "olgaConfig")
    layers = config.get("layers", [])
    selected = []
    for layer in layers:
        name = layer.get("name", "")
        if "avs" in name.lower() or "frivillig" in name.lower():
            source = layer.get("source", {})
            selected.append({
                "name": name,
                "type": layer.get("type"),
                "renderMode": layer.get("renderMode"),
                "source": source,
                "resolved_url_template": urljoin(PAGE, source.get("url", "")),
                "metadata": layer.get("metadata", {}),
                "projection": layer.get("projection"),
                "tileGrid": layer.get("tileGrid") or source.get("tileGrid"),
                "maxZoom": source.get("maxZoom"),
            })
    report = {
        "page": PAGE,
        "page_bytes": len(response.content),
        "top_level_config_keys": sorted(config.keys()),
        "map_config": {k: config.get(k) for k in config if k.lower() in ("projection", "view", "map", "tilegrid", "extent", "center", "zoom", "resolutions")},
        "matching_layers": selected,
        "all_layer_names": [x.get("name") for x in layers],
        "tile_requests_made": False,
        "feature_data_downloaded": False,
        "scope": "Read only olgaConfig from same-host public HTML; no map or tile endpoint requests."
    }
    with open("sca-tile-grid-config.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
