#!/usr/bin/env python3
"""Inspect the public Skyddad skog frontend bundle for service/config references.

This is a bounded read-only probe: it downloads only frontend text assets,
does not call any discovered service endpoints, and does not fetch features.
"""
from __future__ import annotations
import json, re, sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import requests

APP_URL = "https://d3bhdkucripn4z.cloudfront.net/"
PAGE_URL = "https://www.skogsindustrierna.se/om-skogsindustrin/vad-gor-skogsindustrin/svensk-skog/frivilligt-avsatt-skog/karta/"
MAX_ASSET_COUNT = 20
MAX_ASSET_BYTES = 8_000_000
TIMEOUT = (15, 45)
HEADERS = {"User-Agent": "Skog-read-only-frontend-inspector/1.0"}

class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.assets = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"): self.assets.append(a["src"])
        if tag == "link" and a.get("href") and any(x in a.get("rel","").lower() for x in ("stylesheet","preload","modulepreload")):
            self.assets.append(a["href"])

def fetch(s, url):
    r = s.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    if len(r.content) > MAX_ASSET_BYTES:
        raise ValueError(f"asset exceeds {MAX_ASSET_BYTES} bytes")
    return r

def snippets(text, pattern, limit=30, radius=180):
    found=[]; seen=set()
    for m in re.finditer(pattern, text, re.I):
        start=max(0,m.start()-radius); end=min(len(text),m.end()+radius)
        value=text[start:end]
        key=value[:120]
        if key not in seen:
            seen.add(key); found.append({"match":m.group(0)[:500],"context":value[:700]})
        if len(found)>=limit: break
    return found

def main():
    s=requests.Session()
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "read_only":True,"feature_queries_performed":False,"geometries_downloaded":False,
      "snapshots_or_schedule_enabled":False,"app_url":APP_URL,"page_url":PAGE_URL,
      "assets":[],"service_hints":[],"config_hints":[],"errors":[]}
    try:
        r=fetch(s,APP_URL); parser=AssetParser(); parser.feed(r.text)
        report["app"]={"status":r.status_code,"final_url":r.url,"content_type":r.headers.get("content-type"),"html_bytes":len(r.content)}
        candidates=[urljoin(r.url,x) for x in parser.assets]
        report["asset_urls"]=candidates[:MAX_ASSET_COUNT]
        for url in candidates[:MAX_ASSET_COUNT]:
            try:
                a=fetch(s,url)
                ctype=a.headers.get("content-type","")
                if not any(t in ctype.lower() for t in ("javascript","text/css","json","text/plain","text/html")) and not url.lower().endswith((".js",".css",".json")):
                    continue
                text=a.text
                item={"url":url,"status":a.status_code,"content_type":ctype,"bytes":len(a.content)}
                item["service_hints"]=snippets(text,r"(?:https?:)?//[^\s\"'<>]{3,300}(?:arcgis|geoserver|mapserver|featureserver|wms|wfs)[^\s\"'<>]{0,500}|(?:arcgis|geoserver|mapserver|featureserver|wms|wfs)[^\s\"'<>]{0,300}",limit=80)
                item["url_literals"]=snippets(text,r"https?://[^\s\"'<>]{8,600}",limit=80,radius=100)
                item["config_hints"]=snippets(text,r"(?:baseURL|baseUrl|apiUrl|serviceUrl|services|layers|source|endpoint|graphql|mapbox|tileServer|featureServer)",limit=50)
                report["service_hints"].extend([{"asset":url,**x} for x in item["service_hints"]])
                report["config_hints"].extend([{"asset":url,**x} for x in item["config_hints"]])
                report["assets"].append(item)
            except Exception as e:
                report["errors"].append({"url":url,"error":str(e)})
    except Exception as e:
        report["errors"].append({"stage":"app","error":str(e)})
    report["summary"]={"assets_inspected":len(report["assets"]),"service_hint_count":len(report["service_hints"]),
      "config_hint_count":len(report["config_hints"]),"errors":len(report["errors"])}
    import os
    os.makedirs("artifacts",exist_ok=True)
    with open("artifacts/skogsindustrierna-frontend-inspection.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report["summary"],ensure_ascii=False))
    return 0 if report.get("app") else 1

if __name__=="__main__":
    sys.exit(main())
