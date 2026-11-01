#!/usr/bin/env python3
"""Extract literal WMS/WMTS configuration and layer IDs from the public map bundle."""
import json, re, requests, os
from datetime import datetime, timezone
from urllib.parse import urlparse

ENTRY = "https://d3bhdkucripn4z.cloudfront.net/assets/index-BXBy2hpv.js"
HOST = "d3bhdkucripn4z.cloudfront.net"
HEADERS = {"User-Agent": "Skog-read-only-WMS-config-probe/1.0"}

def main():
    r = requests.get(ENTRY, headers=HEADERS, timeout=(15,45))
    r.raise_for_status()
    if urlparse(r.url).netloc != HOST or len(r.content) > 8_000_000:
        raise RuntimeError("Unexpected redirect host or asset size")
    entry = r.text
    imp = re.search(r'["\']([^"\']*MapView-[^"\']+\.js)["\']', entry)
    if not imp:
        raise RuntimeError("MapView lazy module not found")
    from urllib.parse import urljoin
    url = urljoin(ENTRY, imp.group(1))
    if urlparse(url).scheme != "https" or urlparse(url).netloc != HOST:
        raise RuntimeError("MapView import outside approved host")
    m = requests.get(url, headers=HEADERS, timeout=(15,45))
    m.raise_for_status()
    if len(m.content) > 8_000_000:
        raise RuntimeError("MapView asset exceeds size cap")
    src = m.text
    constants = {}
    for name in ("jf", "Py"):
        hits = []
        for pattern in (rf'\b(?:const|let|var)\s+{name}\s*=\s*([^,;]+)', rf'\b{name}\s*=\s*(["\'][^"\']+["\'])'):
            for match in re.finditer(pattern, src):
                hits.append(match.group(1)[:1000])
        constants[name] = list(dict.fromkeys(hits))[:10]
    qf = re.search(r'const\s+qf\s*=\s*(\[.*?\])\s*;', src)
    layer_ids = list(dict.fromkeys(re.findall(r'\bid:"([a-zA-Z0-9_-]+)"', qf.group(1)))) if qf else []
    # Preserve only the bounded config fragment, not the complete minified application.
    config_context = []
    for token in ("wmsLayerUrl", "WMTSLayerConfig", "const qf="):
        pos = src.find(token)
        if pos >= 0:
            config_context.append({"token": token, "context": src[max(0,pos-500):pos+2500]})
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True, "feature_queries_performed": False,
        "geometries_downloaded": False, "snapshots_or_schedule_enabled": False,
        "entry_url": ENTRY, "map_module_url": url,
        "map_module_bytes": len(m.content),
        "literal_candidates": constants, "layer_ids": layer_ids,
        "layer_config_found": bool(qf), "config_context": config_context,
        "note": "Candidates are extracted from the public frontend bundle; values require validation before use."
    }
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/skogsindustrierna-wms-config.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({"module_bytes":len(m.content),"literal_candidates":constants,
                      "layer_ids":layer_ids,"layer_config_found":bool(qf)},ensure_ascii=False))
if __name__ == "__main__":
    main()
