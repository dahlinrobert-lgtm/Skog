#!/usr/bin/env python3
"""Follow bounded JS module imports for Skyddad skog and inspect map-data config."""
from __future__ import annotations
import json, re, sys
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import requests

APP_URL = "https://d3bhdkucripn4z.cloudfront.net/"
ENTRY = "https://d3bhdkucripn4z.cloudfront.net/assets/index-BXBy2hpv.js"
HOST = "d3bhdkucripn4z.cloudfront.net"
MAX_MODULES = 20
MAX_BYTES = 8_000_000
TIMEOUT = (15, 45)
HEADERS = {"User-Agent": "Skog-read-only-map-module-inspector/1.0"}

def fetch(s, url):
    p=urlparse(url)
    if p.scheme!="https" or p.netloc!=HOST:
        raise ValueError("Refusing asset outside approved public app host")
    r=s.get(url,headers=HEADERS,timeout=TIMEOUT); r.raise_for_status()
    if len(r.content)>MAX_BYTES: raise ValueError("Asset exceeds size cap")
    return r

def extract_context(text, pattern, limit=60, radius=260):
    out=[]; seen=set()
    for m in re.finditer(pattern,text,re.I):
        a=max(0,m.start()-radius); b=min(len(text),m.end()+radius)
        ctx=text[a:b]
        if ctx not in seen:
            seen.add(ctx); out.append({"match":m.group(0)[:500],"context":ctx[:900]})
        if len(out)>=limit: break
    return out

def main():
    s=requests.Session(); queue=deque([ENTRY]); visited=set(); modules=[]
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"read_only":True,
      "feature_queries_performed":False,"geometries_downloaded":False,"snapshots_or_schedule_enabled":False,
      "entry":ENTRY,"modules":[],"service_hints":[],"map_data_hints":[],"errors":[]}
    while queue and len(visited)<MAX_MODULES:
        url=queue.popleft()
        if url in visited: continue
        visited.add(url)
        try:
            r=fetch(s,url); text=r.text
            imports=set(re.findall(r'''(?:import\s*\(|from\s*)["']([^"']+\.js(?:\?[^"']*)?)["']''',text))
            for path in imports:
                child=urljoin(url,path)
                if urlparse(child).netloc==HOST and child not in visited and len(queue)+len(visited)<MAX_MODULES:
                    queue.append(child)
            service=extract_context(text,r"(?:https?://|wss?://)[^\s\"'<>]{6,500}|(?:arcgis|geoserver|mapserver|featureserver|wms|wfs|geojson|pmtiles|mapbox|vector.?tile|tilejson)",limit=100)
            data=extract_context(text,r"(?:fetch\(|axios\.|\.get\(|new URL\(|sourceLayer|source-layer|tilejson|tiles\s*:|url\s*:|layers\s*:|geojson|pmtiles|\.pbf|\.mvt|\.json)",limit=100)
            item={"url":url,"bytes":len(r.content),"content_type":r.headers.get("content-type"),
              "imports":sorted(imports),"service_hints":service,"map_data_hints":data}
            report["modules"].append(item)
            report["service_hints"].extend([{"module":url,**x} for x in service])
            report["map_data_hints"].extend([{"module":url,**x} for x in data])
        except Exception as e: report["errors"].append({"url":url,"error":str(e)})
    report["summary"]={"modules_inspected":len(report["modules"]),"service_hints":len(report["service_hints"]),
      "map_data_hints":len(report["map_data_hints"]),"errors":len(report["errors"]),"module_limit":MAX_MODULES}
    import os
    os.makedirs("artifacts",exist_ok=True)
    with open("artifacts/skogsindustrierna-map-modules.json","w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report["summary"],ensure_ascii=False))
    return 0 if report["modules"] else 1

if __name__=="__main__": sys.exit(main())
