#!/usr/bin/env python3
"""Inspect SCA's published map layer configuration and vector-tile URL handling.

No tile requests are made. The output captures public client configuration
needed to resolve the map's actual layer names, URLs and tile-grid semantics.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

PAGE = "https://olga.scaskog.com/map/index.html"
JS = "https://olga.scaskog.com/map/olga.js"
HEADERS = {"User-Agent": "Skog-source-config-audit/1.0"}


def extract_object_containing(text: str, needle: str) -> str | None:
    pos = text.find(needle)
    if pos < 0:
        return None
    start = text.rfind("{", 0, pos)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def all_named_vector_layers(html: str) -> list[dict]:
    layers = []
    for match in re.finditer(r'"name"\\s*:\\s*"([^"]+)"', html):
        name = match.group(1)
        raw = extract_object_containing(html, match.group(0))
        if raw and '"VectorTile"' in raw:
            layers.append({"name": name, "config": raw})
    # Keep first occurrence if the same name appears more than once.
    unique = {}
    for layer in layers:
        unique.setdefault(layer["name"], layer)
    return list(unique.values())


def excerpts(text: str, terms: list[str], radius: int = 700) -> list[dict]:
    found, seen = [], set()
    for term in terms:
        start = 0
        while True:
            pos = text.find(term, start)
            if pos < 0:
                break
            lo, hi = max(0, pos - radius), min(len(text), pos + radius)
            if (lo, hi) not in seen:
                seen.add((lo, hi))
                found.append({"term": term, "offset": pos, "context": text[lo:hi]})
            start = pos + len(term)
            if len(found) >= 40:
                return found
    return found


def main() -> None:
    session = requests.Session()
    session.headers.update(HEADERS)
    page = session.get(PAGE, timeout=30)
    page.raise_for_status()
    js = session.get(JS, timeout=45)
    js.raise_for_status()
    html, bundle = page.text, js.text

    output = {
        "page_url": PAGE,
        "page_status": page.status_code,
        "js_url": JS,
        "js_status": js.status_code,
        "page_bytes": len(page.content),
        "js_bytes": len(js.content),
        "base_tags": re.findall(r"<base\\b[^>]*>", html, flags=re.I),
        "script_references": re.findall(
            r"<script\\b[^>]*src=['\\\"]([^'\\\"]+)", html, flags=re.I
        ),
        "vector_tile_layers": all_named_vector_layers(html),
        "html_config_contexts": excerpts(
            html, ["olgaConfig", "tileGrid", "matrixIds", "resolutions",
                   "origin", "projection", "renderMode"], 1000
        ),
        "javascript_url_and_grid_contexts": excerpts(
            bundle, ["tileUrlFunction", "setUrl(", "setUrls(", "urlTemplate",
                     "VectorTile", "getTileCoordForCoordAndResolution"], 1000
        ),
        "tile_requests_made": 0,
    }
    Path("sca-tile-url-resolution-audit.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "page_status": output["page_status"],
        "js_status": output["js_status"],
        "vector_tile_layer_names": [x["name"] for x in output["vector_tile_layers"]],
        "base_tags": output["base_tags"],
        "script_references": output["script_references"],
        "tile_requests_made": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
