#!/usr/bin/env python3
"""Extract SCA map's static layer/service configuration without calling data services."""
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests

START = "https://olga.scaskog.com/map/index.html"
HOST = "olga.scaskog.com"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Skog-read-only-SCA-config-audit/1.0"})


def get(url, cap=15_000_000):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != HOST:
        raise ValueError("Skipped non-approved host: " + parsed.netloc)
    response = SESSION.get(url, timeout=(15, 45))
    response.raise_for_status()
    if len(response.content) > cap:
        raise ValueError("Asset exceeds size limit")
    return response


def extract_contexts(text, patterns, source, max_each=100):
    output = {}
    for name, pattern in patterns.items():
        rows, seen = [], set()
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            value = re.sub(r"\s+", " ", match.group(0))[:1600]
            if value not in seen:
                seen.add(value)
                rows.append({"source": source, "context": value})
            if len(rows) >= max_each:
                break
        output[name] = rows
    return output


def main():
    page = get(START)
    html = page.text
    asset_refs = set(
        urljoin(START, value)
        for value in re.findall(r"""(?:src|href)=["']([^"']+)["']""", html, re.IGNORECASE)
    )
    asset_refs = {
        url for url in asset_refs
        if urlparse(url).netloc == HOST
        and urlparse(url).path.lower().endswith((".js", ".json", ".geojson", ".xml"))
    }

    documents = [{"url": START, "text": html, "bytes": len(page.content)}]
    for url in sorted(asset_refs):
        try:
            response = get(url)
            documents.append({"url": url, "text": response.text[:12_000_000], "bytes": len(response.content)})
        except Exception as exc:
            documents.append({"url": url, "error": str(exc), "text": "", "bytes": 0})

    patterns = {
        "wfs_configuration": r".{0,500}(?:VectorWFS|featureType|TYPENAME|OUTPUTFORMAT|baseUrl).{0,900}",
        "layer_configuration": r".{0,400}(?:frivillig|avsättning|avsatt|skydd|naturvärde|skogsinnehav).{0,700}",
        "service_hosts_and_paths": r"""https?://[^\s"'<>]{1,400}""",
        "config_references": r".{0,300}(?:config|layers|metadata|mapconfig|olga).{0,400}",
        "wfs_builders": r".{0,300}(?:SERVICE=WFS|REQUEST=GetFeature|GetFeature|CQL_FILTER|BBOX).{0,500}",
    }

    results = {}
    for document in documents:
        if document.get("error"):
            continue
        partial = extract_contexts(document["text"], patterns, document["url"])
        for key, values in partial.items():
            results.setdefault(key, []).extend(values)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "page_url": START,
        "documents": [
            {"url": doc["url"], "bytes": doc["bytes"], "error": doc.get("error")}
            for doc in documents
        ],
        "contexts": results,
        "network_scope": "Only same-host static HTML/JS/JSON/XML assets referenced by page.",
        "no_map_or_feature_endpoint_requests": True,
        "no_feature_downloads": True,
        "no_geometry_snapshots_or_schedules": True,
    }
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/sca-wfs-layer-config.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({
        "documents": report["documents"],
        **{key: len(value) for key, value in results.items()},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
