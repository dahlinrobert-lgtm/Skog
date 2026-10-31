#!/usr/bin/env python3
"""Read-only discovery probe for Skogsindustrierna's Skyddad skog map."""
from __future__ import annotations
import json, re, sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import requests

PAGE_URL = "https://www.skogsindustrierna.se/om-skogsindustrin/vad-gor-skogsindustrin/svensk-skog/frivilligt-avsatt-skog/karta/"
APP_URL = "https://d3bhdkucripn4z.cloudfront.net/"
TIMEOUT = (15, 45)
MAX_SCRIPTS = 30
MAX_JS_BYTES = 2_000_000
UA = "Skog-read-only-source-discovery/1.0"

class Assets(HTMLParser):
    def __init__(self):
        super().__init__(); self.scripts=[]; self.iframes=[]; self.links=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag == "script" and a.get("src"): self.scripts.append(a["src"])
        if tag == "iframe" and a.get("src"): self.iframes.append(a["src"])
        if tag == "link" and a.get("href"): self.links.append(a["href"])

def get(session, url):
    r=session.get(url, timeout=TIMEOUT, headers={"User-Agent":UA})
    r.raise_for_status()
    return r

def main():
    s=requests.Session()
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "source_page":PAGE_URL,"application_url":APP_URL,
            "read_only":True,"feature_download_performed":False,
            "snapshot_or_schedule_enabled":False,"errors":[],"page":{},
            "application":{},"discovered_service_candidates":[]}
    try:
        r=get(s,PAGE_URL); p=Assets(); p.feed(r.text)
        report["page"]={"status":r.status_code,"final_url":r.url,"content_type":r.headers.get("content-type"),
          "html_bytes":len(r.content),"title":(re.search(r"<title[^>]*>(.*?)</title>",r.text,re.I|re.S).group(1).strip() if re.search(r"<title[^>]*>(.*?)</title>",r.text,re.I|re.S) else None),
          "scripts":[urljoin(r.url,x) for x in p.scripts],
          "iframes":[urljoin(r.url,x) for x in p.iframes]}
    except Exception as e: report["errors"].append({"stage":"source_page","error":str(e)})
    try:
        r=get(s,APP_URL); p=Assets(); p.feed(r.text)
        report["application"]={"status":r.status_code,"final_url":r.url,"content_type":r.headers.get("content-type"),
          "html_bytes":len(r.content),"title":(re.search(r"<title[^>]*>(.*?)</title>",r.text,re.I|re.S).group(1).strip() if re.search(r"<title[^>]*>(.*?)</title>",r.text,re.I|re.S) else None),
          "scripts":[urljoin(r.url,x) for x in p.scripts],
          "iframes":[urljoin(r.url,x) for x in p.iframes],
          "html_service_hints":sorted(set(re.findall(r'https?[^"\\\'<> ]{0,500}(?:arcgis|geoserver|mapserver|featureserver|wms|wfs)[^"\\\'<> ]{0,500}',r.text,re.I)))[:100]}
        scripts=report["application"]["scripts"][:MAX_SCRIPTS]
        for u in scripts:
            try:
                js=get(s,u)
                if len(js.content)>MAX_JS_BYTES: continue
                txt=js.text
                candidates=set()
                patterns=[r'https?://[^"\\\'\\s<>]+',r'(?:(?:https?:)?//)?[^"\\\'\\s<>]*(?:arcgis|geoserver|mapserver|featureserver|wms|wfs)[^"\\\'\\s<>]*']
                for pat in patterns:
                    for value in re.findall(pat,txt,re.I):
                        value=value.rstrip('),;]}')
                        if any(k in value.lower() for k in ("arcgis","geoserver","mapserver","featureserver","wms","wfs","geojson","gpkg")):
                            candidates.add(value[:1000])
                report["discovered_service_candidates"].extend({"from_script":u,"candidate":x} for x in sorted(candidates)[:100])
            except Exception as e: report["errors"].append({"stage":"script","url":u,"error":str(e)})
    except Exception as e: report["errors"].append({"stage":"application","error":str(e)})
    # Keep unique candidate URL strings and a bounded diagnostic report.
    seen=set(); unique=[]
    for item in report["discovered_service_candidates"]:
        if item["candidate"] not in seen: seen.add(item["candidate"]); unique.append(item)
    report["discovered_service_candidates"]=unique[:300]
    report["summary"]={"page_loaded":bool(report["page"]),"app_loaded":bool(report["application"]),
      "script_count":len(report.get("application",{}).get("scripts",[])),
      "service_candidate_count":len(unique),"errors":len(report["errors"])}
    import os
    os.makedirs("artifacts",exist_ok=True)
    with open("artifacts/skogsindustrierna-map-discovery.json","w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report["summary"],ensure_ascii=False))
    if not report["application"]: return 1
    return 0

if __name__=="__main__": sys.exit(main())
