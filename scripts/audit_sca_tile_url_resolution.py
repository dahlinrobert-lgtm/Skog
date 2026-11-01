#!/usr/bin/env python3
"""Inspect SCA's published map configuration and vector-tile URL handling.

No tile requests are made. The output is limited to public client configuration
and short source-code excerpts needed to understand URL and grid resolution.
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


def excerpts(text: str, terms: list[str], radius: int = 700) -> list[dict]:
    found = []
    seen = set()
    for term in terms:
        start = 0
        while True:
            pos = text.find(term, start)
            if pos < 0:
                break
            lo, hi = max(0, pos - radius), min(len(text), pos + radius)
            key = (lo, hi)
            if key not in seen:
                seen.add(key)
                found.append({"term": term, "offset": pos, "context": text[lo:hi]})
            start = pos + len(term)
            if len(found) >= 30:
                return found
    return found


def main() -> None:
    s = requests.Session()
    s.headers.update(HEADERS)
    page = s.get(PAGE, timeout=30)
    page.raise_for_status()
    js = s.get(JS, timeout=45)
    js.raise_for_status()
    html, bundle = page.text, js.text

    labels = ["Frivilliga avsättningar", "Alternativa metoder",
              "Anpassad hänsyn", "SCA innehav"]
    layers = []
    for label in labels:
        raw = extract_object_containing(html, '"name": "' + label + '"')
        layers.append({"label": label, "raw_config_object": raw})

    base_tags = re.findall(r"<base\\b[^>]*>", html, flags=re.I)
    scripts = re.findall(r"<script\\b[^>]*src=['\\\"]([^'\\\"]+)", html, flags=re.I)
    html_terms = ["projection", "tileGrid", "matrixIds", "resolutions",
                  "origin", "extent", "center", "view"]
    js_terms = ["createVectorTileLayer", "VectorTile", "tileUrlFunction",
                "new URL(", "urlTemplate", "tileGrid", "matrixIds",
                "projection", "setUrl("]

    output = {
        "page_url": PAGE,
        "page_status": page.status_code,
        "js_url": JS,
        "js_status": js.status_code,
        "page_bytes": len(page.content),
        "js_bytes": len(js.content),
        "base_tags": base_tags,
        "script_references": scripts,
        "layer_configs": layers,
        "html_config_contexts": excerpts(html, html_terms, 900),
        "javascript_url_and_grid_contexts": excerpts(bundle, js_terms, 850),
        "tile_requests_made": 0,
    }
    Path("sca-tile-url-resolution-audit.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "page_status": output["page_status"],
        "js_status": output["js_status"],
        "layer_configs_found": [x["label"] for x in layers if x["raw_config_object"]],
        "base_tags": base_tags,
        "script_references": scripts,
        "html_context_count": len(output["html_config_contexts"]),
        "js_context_count": len(output["javascript_url_and_grid_contexts"]),
        "tile_requests_made": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
