#!/usr/bin/env python3
"""Read-only inspection of SCA's publicly embedded forest map frontend."""
import json, os, re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import requests

START = "https://olga.scaskog.com/map/index.html"
ALLOWED_HOSTS = {"olga.scaskog.com"}
HEADERS = {"User-Agent": "Skog-read-only-SCA-map-inspection/1.0"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def safe_get(url, limit=12_000_000):
    p = urlparse(url)
    if p.scheme != "https" or p.netloc not in ALLOWED_HOSTS:
        raise ValueError("External asset host skipped: " + p.netloc)
    r = SESSION.get(url, timeout=(15, 45))
    r.raise_for_status()
    if len(r.content) > limit:
        raise ValueError("Asset exceeds size limit")
    return r

def main():
    page = safe_get(START)
    html = page.text
    refs = set()
    for pat in (r'<script[^>]+src=["\']([^"\']+)', r'<link[^>]+href=["\']([^"\']+)', r'import\s*\(["\']([^"\']+)'):
        refs.update(urljoin(START, x) for x in re.findall(pat, html, re.I))
    assets = []
    for url in sorted(refs):
        if urlparse(url).netloc not in ALLOWED_HOSTS:
            continue
        try:
            r = safe_get(url)
            if "javascript" not in r.headers.get("content-type", "").lower() and not url.endswith((".js", ".mjs")):
                continue
            assets.append({"url": url, "bytes": len(r.content), "text": r.text[:8_000_000]})
        except Exception as e:
            assets.append({"url": url, "error": str(e), "text": ""})
    # Include inline configuration and discovered JS snippets, but do not execute app code or call map/data endpoints.
    sources = [{"url": START, "text": html}] + assets
    patterns = {
        "service_urls": r'https?[^\s"\'<>]{0,250}(?:wms|wmts|arcgis|geoserver|mapserver|ows|features|featureserver)[^\s"\'<>]{0,350}',
        "service_terms": r'.{0,180}(?:GetMap|GetCapabilities|GetFeatureInfo|GetFeature|FeatureServer|MapServer|WFS|WMS|WMTS|OGC API|tileLayer|TileWMS|ImageWMS).{0,260}',
        "layer_terms": r'.{0,160}(?:avsättning|frivillig|naturvärde|mångfald|alternativ|skogsinnehav|layer|layers).{0,220}',
        "request_code": r'.{0,200}(?:fetch\(|axios\.|XMLHttpRequest|ol\.source|L\.tileLayer|wmsParams|LAYERS|SERVICE=).{0,300}',
    }
    results = {}
    for name, pat in patterns.items():
        found, seen = [], set()
        for src in sources:
            for m in re.finditer(pat, src["text"], re.I):
                value = m.group(0)[:700]
                key = (src["url"], value)
                if key in seen:
                    continue
                seen.add(key)
                found.append({"source": src["url"], "context": value})
                if len(found) >= 120:
                    break
            if len(found) >= 120:
                break
        results[name] = found
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "page_url": START,
        "page_bytes": len(page.content),
        "assets": [{"url": a["url"], "bytes": a.get("bytes"), "error": a.get("error")} for a in assets],
        "contexts": results,
        "application_executed": False,
        "map_service_requests_executed": False,
        "feature_data_downloaded": False,
        "geometries_downloaded": False,
        "snapshots_or_schedule_enabled": False,
        "scope": "Static HTML and same-host frontend asset inspection only; no map/API endpoints queried."
    }
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/sca-map-inspection.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"page_bytes": len(page.content), "assets": len(assets),
                      **{k: len(v) for k, v in results.items()}}, ensure_ascii=False))

if __name__ == "__main__":
    main()
