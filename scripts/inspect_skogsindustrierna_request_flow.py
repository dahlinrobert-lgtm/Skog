#!/usr/bin/env python3
"""Inspect the public MapView bundle for actual map request construction."""
import json,re,requests,os
from datetime import datetime,timezone
from urllib.parse import urljoin,urlparse
ENTRY="https://d3bhdkucripn4z.cloudfront.net/assets/index-BXBy2hpv.js"
HOST="d3bhdkucripn4z.cloudfront.net"
H={"User-Agent":"Skog-read-only-map-request-flow/1.0"}
def main():
 r=requests.get(ENTRY,headers=H,timeout=(15,45)); r.raise_for_status()
 if urlparse(r.url).netloc!=HOST or len(r.content)>8_000_000: raise RuntimeError("Entry host/size validation failed")
 m0=re.search(r'["\']([^"\']*MapView-[^"\']+\.js)["\']',r.text)
 if not m0: raise RuntimeError("MapView chunk not found")
 u=urljoin(ENTRY,m0.group(1))
 if urlparse(u).netloc!=HOST or urlparse(u).scheme!="https": raise RuntimeError("Chunk host rejected")
 m=requests.get(u,headers=H,timeout=(15,45)); m.raise_for_status()
 if len(m.content)>8_000_000: raise RuntimeError("Chunk exceeds limit")
 s=m.text
 patterns={
  "wms_url":r'https?[^"\']{0,300}(?:wms|mapserver)[^"\']{0,300}',
  "ows_url":r'https?[^"\']{0,300}(?:ows|service)[^"\']{0,300}',
  "request_builders":r'.{0,250}(?:GetMap|GetCapabilities|GetFeatureInfo|LAYERS|layers=|FORMAT=|SERVICE=WMS|wmsLayerUrl).{0,350}',
  "proxy_and_fetch":r'.{0,220}(?:fetch\(|axios\.|XMLHttpRequest|Image\(|tileLoadFunction|imageLoadFunction|url\s*:).{0,350}',
  "layer_definitions":r'.{0,180}(?:sveaskog_fa|holmen_fa|nationalpark|naturreservat|sca_fa).{0,220}'
 }
 out={}
 for name,pat in patterns.items():
  arr=[]; seen=set()
  for mt in re.finditer(pat,s,re.I):
   x=mt.group(0)
   if x not in seen: seen.add(x); arr.append(x[:800])
   if len(arr)>=80: break
  out[name]=arr
 report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"module_url":u,"module_bytes":len(m.content),"contexts":out,
 "network_calls_executed":False,"feature_requests_executed":False,"geometries_downloaded":False,"snapshots_or_schedule_enabled":False}
 os.makedirs("artifacts",exist_ok=True)
 with open("artifacts/skogsindustrierna-request-flow.json","w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
 print(json.dumps({"module_bytes":len(m.content),**{k:len(v) for k,v in out.items()}},ensure_ascii=False))
if __name__=="__main__": main()
