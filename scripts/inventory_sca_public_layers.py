#!/usr/bin/env python3
"""Inventory the inline public SCA OLGA layer configuration without tile requests."""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

PAGE = "https://olga.scaskog.com/map/index.html"


def matching_end(source: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(source)):
        ch = source[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unclosed {opening} block at offset {start}")


def object_spans(source: str, start: int, end: int):
    i = start
    while i < end:
        if source[i] == "{":
            j = matching_end(source, i, "{", "}")
            yield source[i:j + 1]
            i = j + 1
        else:
            i += 1


def main() -> None:
    response = requests.get(PAGE, timeout=30, headers={
        "User-Agent": "Skog-public-layer-inventory/1.0"
    })
    response.raise_for_status()
    html = response.text
    config_match = re.search(r"olgaConfig\\s*=\\s*\\{", html)
    if not config_match:
        raise RuntimeError("Inline olgaConfig assignment not found")
    config_start = html.find("{", config_match.start())
    config_end = matching_end(html, config_start, "{", "}")
    config_text = html[config_start:config_end + 1]
    layers_match = re.search(r'"layers"\\s*:\\s*\\[', config_text)
    if not layers_match:
        raise RuntimeError("olgaConfig.layers array not found")
    array_start = config_text.find("[", layers_match.start())
    array_end = matching_end(config_text, array_start, "[", "]")

    layers = []
    for raw in object_spans(config_text, array_start + 1, array_end):
        def get(pattern):
            m = re.search(pattern, raw)
            return m.group(1) if m else None
        name = get(r'"name"\\s*:\\s*"([^"]+)"')
        if not name:
            continue
        layers.append({
            "name": name,
            "type": get(r'"type"\\s*:\\s*"([^"]+)"'),
            "source_type": get(r'"source"\\s*:\\s*\\{[^}]*"type"\\s*:\\s*"([^"]+)"'),
            "url_template": get(r'"url"\\s*:\\s*"([^"]+)"'),
            "format": get(r'"type"\\s*:\\s*"MVT"'),
            "max_zoom": int(get(r'"maxZoom"\\s*:\\s*(\\d+)') or 0) or None,
            "visible": (get(r'"visible"\\s*:\\s*(true|false)') or "").lower() == "true",
        })
        layers[-1]["format"] = "MVT" if '"MVT"' in raw else None

    output = {
        "page_url": PAGE,
        "http_status": response.status_code,
        "config_layer_count": len(layers),
        "layers": layers,
        "voluntary_set_asides_named_layer_found": any(
            "frivillig" in layer["name"].casefold()
            or "avsättning" in layer["name"].casefold()
            or "avsattning" in layer["name"].casefold()
            for layer in layers
        ),
        "tile_requests_made": 0,
        "feature_data_downloaded": False,
    }
    Path("sca-public-layer-inventory.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
