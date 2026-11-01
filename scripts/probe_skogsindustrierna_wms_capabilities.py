#!/usr/bin/env python3
"""Read-only WMS GetCapabilities probe for the public Skogsindustrierna map."""
import json, os, re, requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

BASE = "https://d3bhdkucripn4z.cloudfront.net/wms?"
PARAMS = {"service":"WMS","request":"GetCapabilities","version":"1.3.0"}
HOST = "d3bhdkucripn4z.cloudfront.net"
EXPECTED = [
"nationalpark","naturreservat","biotopskydd","naturavtal","ekopark",
"mangfoldspark","kunskapsskog","nyckelbiotop","fastverk_snus","fa",
"fastverk_fa","holmen_fa","sca_fa","sveaskog_fa","kyrkan_fa","bso_fa",
"kopparfors_fa","natura2000","mark_fastverk","mark_holmen","mark_sca",
"mark_sveaskog","mark_kyrkan","mark_bso","mark_kopparfors"
]

def local(tag):
    return tag.rsplit("}",1)[-1]

def main():
    s=requests.Session()
    r=s.get(BASE,params=PARAMS,headers={"User-Agent":"Skog-read-only-WMS-capabilities/1.0","Accept":"application/xml,text/xml,*/*"},timeout=(15,60))
    r.raise_for_status()
    final=urlparse(r.url)
    if final.scheme!="https" or final.netloc!=HOST:
        raise RuntimeError("Unexpected redirect outside approved public host")
    if len(r.content)>10_000_000:
        raise RuntimeError("Capabilities document exceeds 10 MB safety limit")
    content_type=r.headers.get("content-type","")
    body=r.text
    if not body.lstrip().startswith("<"):
        raise RuntimeError("WMS response is not XML; response starts: "+body[:300])
    root=ET.fromstring(r.content)
    layers=[]
    for node in root.iter():
        if local(node.tag)!="Layer":
            continue
        item={}
        for child in list(node):
            key=local(child.tag)
            if key in ("Name","Title","Abstract","CRS","SRS","Queryable"):
                val=(child.text or "").strip()
                if key in ("CRS","SRS"):
                    item.setdefault(key,[]).append(val)
                elif val:
                    item[key]=val
        if "Name" in item or "Title" in item:
            layers.append(item)
    names={x.get("Name") for x in layers}
    service={}
    for node in root.iter():
        key=local(node.tag)
        if key in ("Title","Abstract","OnlineResource","Fees","AccessConstraints"):
            val=(node.text or "").strip()
            if val and key not in service:
                service[key]=val[:2000]
    report={
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "request_url":r.url,"http_status":r.status_code,"content_type":content_type,
      "response_bytes":len(r.content),"wms_version":root.attrib.get("version"),
      "service_metadata":service,"layers":layers,
      "expected_layer_presence":{n:(n in names) for n in EXPECTED},
      "all_expected_layers_found":all(n in names for n in EXPECTED),
      "read_only":True,"feature_info_queries_performed":False,
      "map_images_requested":False,"geometries_downloaded":False,
      "snapshots_or_schedule_enabled":False
    }
    os.makedirs("artifacts",exist_ok=True)
    with open("artifacts/skogsindustrierna-wms-capabilities.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({"status":r.status_code,"content_type":content_type,"bytes":len(r.content),
      "wms_version":report["wms_version"],"layer_count":len(layers),
      "expected_layers_found":sum(report["expected_layer_presence"].values()),
      "all_expected_layers_found":report["all_expected_layers_found"]},ensure_ascii=False))
if __name__=="__main__":
    main()
