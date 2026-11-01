#!/usr/bin/env python3
"""Trace the SCA voluntary set-asides layer from public HTML config into OLGA JS.

Bounded to same-host assets, source-context extraction and the single configured
layer's code references. No map tiles are fetched.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests

PAGE = "https://olga.scaskog.com/map/index.html"
HEADERS = {"User-Agent": "Skog-SCA-source-trace/1.0"}
NAME = re.compile(r"Frivilliga\s+avsättningar|Frivilliga.?avsättningar", re.I)
KEYS = re.compile(r"name|url|source|type|format|projection|tileGrid|tileUrlFunction|resolutions|origin|extent|matrixSet|visible|maxZoom", re.I)

def balanced_end(s, start, op, cl):
    depth=0; quote=False; esc=False
    for i in range(start,len(s)):
        c=s[i]
        if quote:
            if esc: esc=False
            elif c=="\\": esc=True
            elif c=='"': quote=False
        else:
            if c=='"': quote=True
            elif c==op:
                depth+=1
            elif c==cl:
                depth-=1
                if depth==0: return i
    raise ValueError("Unclosed block")

def extract_named_config(html):
    m=re.search(r"olgaConfig\s*=\s*\{",html)
    if not m: return {"found":False,"reason":"olgaConfig assignment missing"}
    start=html.find("{",m.start()); end=balanced_end(html,start,"{","}")
    raw=html[start:end+1]
    lm=re.search(r'"layers"\s*:\s*\[',raw)
    if not lm: return {"found":False,"reason":"layers array missing"}
    a=raw.find("[",lm.start()); z=balanced_end(raw,a,"[","]")
    arr=raw[a+1:z]
    # Emit concise diagnostics for every configured layer object and use
    # decoded JSON strings rather than matching only the literal display name.
    found=[]; inventory=[]; i=0
    while i<len(arr):
        if arr[i]=="{":
            e=balanced_end(arr,i,"{","}")
            obj=arr[i:e+1]
            try:
                decoded=json.loads(obj)
            except Exception:
                decoded={"raw":obj}
            inventory.append(decoded)
            searchable=json.dumps(decoded,ensure_ascii=False)
            if NAME.search(searchable) or any("frivillig" in str(v).casefold() or "avsättning" in str(v).casefold() or "avsattning" in str(v).casefold() for v in decoded.values()):
                found.append(decoded)
            i=e+1
        else: i+=1
    return {"found":bool(found),"layers":found,"total_inline_layer_objects":len(inventory),"layer_name_inventory":[{"name":x.get("name"),"keys":list(x.keys()),"source":x.get("source")} for x in inventory if isinstance(x,dict)]}

def windows(s, pos, before=1400, after=2400):
    return s[max(0,pos-before):min(len(s),pos+after)]

def main():
    sess=requests.Session(); sess.headers.update(HEADERS)
    page=sess.get(PAGE,timeout=30); page.raise_for_status()
    samehost=[]
    for src in re.findall(r"""<script[^>]+src=["']([^"']+)["']""",page.text,re.I):
        u=urljoin(PAGE,src)
        if urlparse(u).netloc==urlparse(PAGE).netloc and u not in samehost: samehost.append(u)
    assets=[]
    for u in samehost:
        r=sess.get(u,timeout=60); r.raise_for_status()
        js=r.text
        matches=[]
        # Search the entire script, not only first 80 generic term matches.
        for m in NAME.finditer(js):
            matches.append({"kind":"layer_name_occurrence","offset":m.start(),"context":windows(js,m.start())})
        # URL-template and tile-grid builders are only candidates until tied by a call site.
        for pat in [r"omraden",r"parseSource",r"parseTileGrid",r"tileUrlFunction",r"new .*TileGrid",r"VectorTile",r"createXYZ",r"getForProjection",r"tileGrid",r"projection"]:
            for m in list(re.finditer(pat,js,re.I))[:80]:
                matches.append({"kind":"candidate_"+pat.replace(" ","_"),"offset":m.start(),"context":windows(js,m.start(),500,1100)})
        assets.append({"url":u,"status":r.status_code,"bytes":len(r.content),"matches":matches})
    out={
      "page_url":PAGE,"http_status":page.status_code,"page_bytes":len(page.content),
      "named_layer_config":extract_named_config(page.text),
      "same_host_assets":assets,
      "interpretation":"Only a call-site chain joining the named layer object to a source factory/grid or URL function is conclusive. Candidate snippets are not proof.",
      "tile_requests":0
    }
    Path("sca-voluntary-source-trace.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"layer":out["named_layer_config"],"assets":[{"url":x["url"],"bytes":x["bytes"],"match_count":len(x["matches"]),"matches":x["matches"][:8]} for x in assets]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
