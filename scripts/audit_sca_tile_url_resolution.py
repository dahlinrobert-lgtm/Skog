#!/usr/bin/env python3
"""Locate SCA OLGA layer configuration in referenced public assets; no tile requests."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

PAGE = "https://olga.scaskog.com/map/index.html"
TERMS = ["Frivilliga avsättningar", "VectorTile", "omraden/{z}/{x}/{y}.pbf",
         "tileGrid", "matrixIds", "olgaConfig"]


def contexts(text: str, radius: int = 1200) -> list[dict]:
    found, seen = [], set()
    for term in TERMS:
        pos = 0
        while True:
            pos = text.find(term, pos)
            if pos < 0:
                break
            lo, hi = max(0, pos - radius), min(len(text), pos + radius)
            if (lo, hi) not in seen:
                seen.add((lo, hi))
                found.append({"term": term, "offset": pos, "context": text[lo:hi]})
            pos += len(term)
            if len(found) >= 60:
                return found
    return found


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-source-config-audit/1.0"})
    page = session.get(PAGE, timeout=30)
    page.raise_for_status()
    refs = re.findall(r"""(?:src|href)=["']([^"']+\.(?:js|mjs|json)(?:\?[^"']*)?)["']""",
                      page.text, flags=re.I)
    assets = []
    for ref in refs:
        url = urljoin(PAGE, ref)
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != urlparse(PAGE).netloc:
            continue
        try:
            response = session.get(url, timeout=45)
            assets.append({
                "url": url,
                "status": response.status_code,
                "bytes": len(response.content),
                "content_type": response.headers.get("Content-Type"),
                "matches": contexts(response.text) if response.ok else [],
            })
        except requests.RequestException as exc:
            assets.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    output = {
        "page_url": PAGE,
        "page_status": page.status_code,
        "page_bytes": len(page.content),
        "asset_references": refs,
        "assets": assets,
        "tile_requests_made": 0,
        "feature_data_downloaded": False,
    }
    Path("sca-tile-url-resolution-audit.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "page_status": page.status_code,
        "asset_count": len(assets),
        "successful_assets": sum(1 for a in assets if a.get("status") == 200),
        "matched_assets": [a["url"] for a in assets if a.get("matches")],
        "tile_requests_made": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
