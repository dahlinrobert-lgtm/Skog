#!/usr/bin/env python3
"""Extract SCA map's static layer/service configuration without calling data services."""
import json, os, re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import requests

START = "https://olga.scaskog.com/map/index.html"
HOST = "olga.scaskog.com"
S = requests.Session()
S.headers.update({"User-Agent": "Skog-read-only-SCA-config-audit/1.0"})

def get(url, cap=15_000_000):
    p=urlparse(url)
    if p.scheme!="https" or p.netloc!=HOST:
        raise ValueError("Skipped non-approved host: "+p.netloc)
    r=S.get(url,timeout=(15,45)); r.raise_for_status()
    if len(r.content)>cap: raise ValueError("Size cap exceeded")
    return r

def contexts(text, patterns, source, max_each=100):
    out={}
    for name,pat in patterns.items():
        rows=[]; seen=set()
        for m in re.finditer(pat,text,re.I|re.S):
            x=re.sub(r"\\s+"," ",m.group(0))[:1600]
            if x not in seen:
                seen.add(x); rows.append({"source":source,"context":x})
            if len(rows)>=max_each: break
        out[name]=rows
    return out

def main():
    page=get(START); html=page.text
    refs=set(urljoin(START,x) for x in re.findall(r'(?:src|href)=["\\']([^"\\']+)["\\']',html,re.I))
    refs={u for u in refs if urlparse(u).netloc==HOST and urlparse(u).path.lower().endswith((".js",".json",".geojson",".xml"))}
    docs=[{"url":START,"text":html,"bytes":len(page.content)}]
    for u in sorted(refs):
        try:
            r=get(u)
            docs.append({"url":u,"text":r.text[:12_000_000],"bytes":len(r.content)})
        except Exception as e:
            docs.append({"url":u,"error":str(e),"text":"","bytes":0})
    pats={
      "wfs_configuration":r".{0,500}(?:VectorWFS|featureType|TYPENAME|OUTPUTFORMAT|baseUrl).{0,900}",
      "layer_configuration":r".{0,400}(?:frivillig|avsättning|avsatt|skydd|naturvärde|skogsinnehav).{0,700}",
      "service_hosts_and_paths":r"https?://[^\\s\"'<>]{1,400}",
      "config_references":r".{0,300}(?:config|layers|metadata|mapconfig|olga).{0,400}",
      "wfs_builders":r".{0,300}(?:SERVICE=WFS|REQUEST=GetFeature|GetFeature|CQL_FILTER|BBOX).{0,500}"
    }
    result={}
    for d in docs:
        if d.get("error"): continue
        partial=contexts(d["text"],pats,d["url"],100)
        for k,v in partial.items(): result.setdefault(k,[]).extend(v)
    report={
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "page_url":START,
      "documents":[{"url":d["url"],"bytes":d["bytes"],"error":d.get("error")} for d in docs],
      "contexts":result,
      "network_scope":"Only same-host static HTML/JS/JSON/XML assets referenced by page.",
      "no_map_or_feature_endpoint_requests":True,
      "no_feature_downloads":True,
      "no_geometry_snapshots_or_schedules":True
    }
    os.makedirs("artifacts",exist_ok=True)
    with open("artifacts/sca-wfs-layer-config.json","w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({"documents":report["documents"],**{k:len(v) for k,v in result.items()}},ensure_ascii=False))
if __name__=="__main__": main()
