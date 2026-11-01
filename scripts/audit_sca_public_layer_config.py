#!/usr/bin/env python3
"""Separate public SCA layer config from generic/offline OpenLayers code."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

PAGE_URL = "https://olga.scaskog.com/map/index.html"
UA = "Skog-public-layer-config-audit/1.0"
LABELS = ["Frivilliga avsättningar", "Alternativa metoder", "Anpassad hänsyn"]
TOKENS = ["omraden", "Frivilliga", "avsättningar", "VectorTile", ".pbf",
          "urlTemplate", "tileUrlFunction", "source:", "layers:"]


def contexts(text: str, terms: list[str], radius: int = 1100, limit: int = 80) -> list[dict]:
    results, seen = [], set()
    for term in terms:
        pos = 0
        while True:
            pos = text.find(term, pos)
            if pos < 0:
                break
            lo, hi = max(0, pos-radius), min(len(text), pos+radius)
            if (lo, hi) not in seen:
                seen.add((lo, hi))
                results.append({"term": term, "offset": pos, "context": text[lo:hi]})
            pos += len(term)
            if len(results) >= limit:
                return results
    return results


def main() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    page = session.get(PAGE_URL, timeout=30)
    page.raise_for_status()
    refs = re.findall(
        r"""(?:src|href)=["']([^"']+\.(?:js|mjs|json)(?:\?[^"']*)?)["']""",
        page.text, flags=re.I
    )
    assets = []
    for ref in refs:
        url = urljoin(PAGE_URL, ref)
        if urlparse(url).netloc != urlparse(PAGE_URL).netloc:
            continue
        response = session.get(url, timeout=45)
        assets.append({
            "url": url,
            "status": response.status_code,
            "bytes": len(response.content),
            "content_type": response.headers.get("Content-Type"),
            "layer_label_contexts": contexts(response.text, LABELS, 1400, 80),
            "tile_path_contexts": contexts(response.text, ["omraden", ".pbf", "urlTemplate",
                                                            "tileUrlFunction"], 1000, 80),
            "module_contexts": contexts(response.text, ["createVectorTileLayer"], 1000, 10),
        })

    output = {
        "page_url": PAGE_URL,
        "page_status": page.status_code,
        "page_bytes": len(page.content),
        "page_layer_label_contexts": contexts(page.text, LABELS, 1600, 80),
        "page_config_contexts": contexts(page.text, ["olgaConfig", "layers", "source",
                                                       "VectorTile", "omraden"], 900, 100),
        "asset_references": refs,
        "assets": assets,
        "interpretation": {
            "public_config_searches_page_html": True,
            "public_config_searches_assets": True,
            "offline_module_hits_are_separately_labelled": True,
            "tile_requests_made": 0,
            "feature_data_downloaded": False,
        },
    }
    Path("sca-public-layer-config-audit.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8"
    )
    print(json.dumps({
        "page_status": page.status_code,
        "asset_count": len(assets),
        "page_label_hits": len(output["page_layer_label_contexts"]),
        "page_config_hits": len(output["page_config_contexts"]),
        "asset_label_hits": sum(len(a["layer_label_contexts"]) for a in assets),
        "asset_tile_path_hits": sum(len(a["tile_path_contexts"]) for a in assets),
        "tile_requests_made": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
