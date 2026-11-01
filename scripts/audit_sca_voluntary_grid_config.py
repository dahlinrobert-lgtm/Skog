#!/usr/bin/env python3
"""Inspect SCA OLGA online tile-grid configuration and related JS call sites.

This is a bounded source audit: fetch the public map HTML and same-host script
references, then report only relevant config fields and small source contexts.
It does not download map tiles or infer a grid from offline-only code.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

PAGE = "https://olga.scaskog.com/map/index.html"
TERMS = re.compile(
    r"omraden|tileGrid|tileUrlFunction|createXYZ|resolutions|"
    r"origin|tileUrl|projection|tileSize|maxZoom|tileCoord",
    re.IGNORECASE,
)
HEADERS = {"User-Agent": "Skog-SCA-online-grid-audit/1.0"}


def balanced_end(source: str, start: int, opening: str, closing: str) -> int:
    depth, quoted, escaped = 0, False, False
    for i in range(start, len(source)):
        ch = source[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
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
    raise ValueError(f"Unclosed {opening} block")


def extract_layer_config(html: str) -> list[dict]:
    m = re.search(r"olgaConfig\\s*=\\s*\\{", html)
    if not m:
        return []
    start = html.find("{", m.start())
    end = balanced_end(html, start, "{", "}")
    config = html[start:end + 1]
    lm = re.search(r'"layers"\s*:\s*\[', config)
    if not lm:
        return []
    a = config.find("[", lm.start())
    z = balanced_end(config, a, "[", "]")
    # The public config is JSON-compatible in this page. If parsing fails,
    # retain the raw named-layer object rather than silently guessing.
    try:
        parsed = json.loads(config)
        layers = parsed.get("layers", [])
        return [x for x in layers if "frivillig" in str(x.get("name", "")).casefold()
                or "avsättning" in str(x.get("name", "")).casefold()
                or "avsattning" in str(x.get("name", "")).casefold()]
    except Exception:
        arr = config[a + 1:z]
        spans, i = [], 0
        while i < len(arr):
            if arr[i] == "{":
                e = balanced_end(arr, i, "{", "}")
                raw = arr[i:e + 1]
                if re.search(r"Frivilliga.?avsättningar", raw, re.I):
                    spans.append({"raw_config": raw})
                i = e + 1
            else:
                i += 1
        return spans


def contexts(source: str, source_url: str) -> list[dict]:
    found, seen = [], set()
    for match in TERMS.finditer(source):
        start, end = max(0, match.start() - 260), min(len(source), match.end() + 420)
        snippet = re.sub(r"\\s+", " ", source[start:end]).strip()
        key = snippet[:180]
        if key in seen:
            continue
        seen.add(key)
        found.append({"term": match.group(0), "offset": match.start(), "context": snippet})
        if len(found) >= 80:
            break
    return found


def main() -> None:
    session = requests.Session()
    session.headers.update(HEADERS)
    page_response = session.get(PAGE, timeout=30)
    page_response.raise_for_status()
    html = page_response.text
    host = urlparse(PAGE).netloc
    scripts = []
    for src in re.findall(r"""<script[^>]+src=["']([^"']+)["']""", html, re.I):
        url = urljoin(PAGE, src)
        if urlparse(url).netloc == host and url not in scripts:
            scripts.append(url)

    script_results = []
    for url in scripts:
        try:
            response = session.get(url, timeout=45)
            response.raise_for_status()
            js = response.text
            script_results.append({
                "url": url, "http_status": response.status_code,
                "bytes": len(response.content),
                "matches": contexts(js, url),
            })
        except Exception as exc:
            script_results.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    output = {
        "page_url": PAGE,
        "page_status": page_response.status_code,
        "page_bytes": len(page_response.content),
        "named_layer_config": extract_layer_config(html),
        "same_host_scripts": script_results,
        "interpretation_guardrails": [
            "A matching string alone does not prove it configures the named online layer.",
            "Separate source contexts for online layer setup from offline/export helpers.",
            "Do not infer EPSG, origin, resolutions or URL template unless tied to the named layer's source object."
        ],
        "tile_requests_made": 0,
    }
    Path("sca-voluntary-grid-config-audit.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
