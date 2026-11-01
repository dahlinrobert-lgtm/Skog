#!/usr/bin/env python3
"""Inspect SCA page scripts for layer and tile-grid configuration; no tile requests."""
import json
import re
from urllib.parse import urljoin, urlparse
import requests

PAGE = "https://olga.scaskog.com/map/index.html"
HOST = "olga.scaskog.com"
session = requests.Session()
session.headers.update({"User-Agent": "Skog-read-only-SCA-tile-grid-config/1.1"})


def main():
    page = session.get(PAGE, timeout=(15, 45))
    page.raise_for_status()
    html = page.text
    refs = set()
    for value in re.findall(r"""(?:src|href)=["']([^"']+)["']""", html, re.I):
        url = urljoin(PAGE, value)
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc == HOST:
            refs.add(url)

    docs = [{"url": PAGE, "text": html, "bytes": len(page.content)}]
    for url in sorted(refs):
        if not urlparse(url).path.lower().endswith((".js", ".mjs", ".json")):
            continue
        try:
            response = session.get(url, timeout=(15, 45))
            response.raise_for_status()
            if len(response.content) <= 15_000_000:
                docs.append({"url": url, "text": response.text, "bytes": len(response.content)})
        except Exception as exc:
            docs.append({"url": url, "error": str(exc), "text": "", "bytes": 0})

    patterns = {
        "tile_layer_context": r".{0,500}(?:Frivilliga avsättningar|frivillig[a-zåäö ]*avsättningar|omraden/).{0,1200}",
        "vector_tile_context": r".{0,500}(?:VectorTile|VectorTileLayer|VectorSource|\.pbf|MVT|tileUrlFunction).{0,1200}",
        "projection_grid_context": r".{0,400}(?:tileGrid|tilegrid|resolutions|matrixIds|projection|EPSG:3006|EPSG:3857).{0,900}",
        "base_url_context": r".{0,400}(?:baseUrl|baseURL|basePath|urlTemplate|url:).{0,800}",
        "script_references": r"""(?:src|href)=["'][^"']+["']""",
    }
    results = {}
    for doc in docs:
        if doc.get("error"):
            continue
        for name, pattern in patterns.items():
            matches = []
            for match in re.finditer(pattern, doc["text"], re.I | re.S):
                snippet = re.sub(r"\s+", " ", match.group(0))[:1800]
                if snippet not in [x["context"] for x in matches]:
                    matches.append({"source": doc["url"], "context": snippet})
                if len(matches) >= 80:
                    break
            results.setdefault(name, []).extend(matches)

    report = {
        "page": PAGE,
        "documents": [{"url": d["url"], "bytes": d["bytes"], "error": d.get("error")} for d in docs],
        "script_assets": [d["url"] for d in docs[1:] if not d.get("error")],
        "contexts": results,
        "tile_requests_made": False,
        "feature_data_downloaded": False,
        "scope": "Same-host HTML and referenced static JS/JSON only. No map or tile endpoint requests."
    }
    with open("sca-tile-grid-config.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"documents": report["documents"],
                      **{key: len(value) for key, value in results.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
