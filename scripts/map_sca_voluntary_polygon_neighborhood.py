#!/usr/bin/env python3
"""Probe adjacent SCA voluntary polygon tiles around data-positive test centers at z12."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
ZOOM=12
OFFSETS=[(dx,dy) for dy in range(-2,3) for dx in range(-2,3)]

def xyz(lon,lat,z):
 n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def main():
 retry=Retry(total=2,connect=2,read=1,backoff_factor=.7,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-polygon-neighborhood-probe/1.0"}); s.mount("https://",HTTPAdapter(max_retries=retry))
 rows=[]
 for site,(lon,lat) in SITES.items():
  cx,cy=xyz(lon,lat,ZOOM)
  for dx,dy in OFFSETS:
   x,y=cx+dx,cy+dy; url=BASE.format(z=ZOOM,x=x,y=y)
   row={"site":site,"z":ZOOM,"x":x,"y":y,"dx":dx,"dy":dy}
   try:
    r=s.get(url,timeout=(12,30)); row.update(status=r.status_code,bytes=len(r.content))
    if r.status_code==200:
     decoded=mapbox_vector_tile.decode(r.content); row["state"]="valid_mvt"
     row["layers"]=[]
     for name,layer in decoded.items():
      feats=layer.get("features",[])
      row["layers"].append({"name":name,"count":len(feats),
       "types":dict(Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)),
       "id_values":[f.get("id") for f in feats[:10]],
       "property_keys":sorted({k for f in feats for k in ((f.get("properties") or {}).keys())}),
       "sample_properties":[f.get("properties") or {} for f in feats[:5]]})
    else: row["state"]="not_found_404" if r.status_code==404 else "http_error"
   except Exception as e: row.update(state="request_error",error=str(e)[:200])
   rows.append(row)
 summary={}
 for site in SITES:
  rr=[r for r in rows if r["site"]==site]
  summary[site]={"tiles_tested":len(rr),"http_200":sum(r.get("status")==200 for r in rr),
    "http_404":sum(r.get("status")==404 for r in rr),"request_errors":sum(r["state"]=="request_error" for r in rr),
    "tiles_with_voluntary_polygon":sum(any(l["name"]=="Frivilliga_Avsattningar" and l["count"]>0 for l in r.get("layers",[])) for r in rr)}
 out={"purpose":"Map where voluntary polygon tiles exist around the two test centers, and inspect property fields.",
 "zoom":ZOOM,"sites":SITES,"summary":summary,"results":rows,
 "caveats":["Only 5x5 tile neighborhood per site; not complete coverage.","Tiles may contain clipped pieces of the same feature.","Do not sum tile counts or tile-local polygon areas as unique hectares.","Maximum 50 requests."]}
 Path("sca-voluntary-polygon-neighborhood.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"summary":summary,"results":rows},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
