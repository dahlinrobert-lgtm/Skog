#!/usr/bin/env python3
"""Inspect SCA voluntary set-aside polygon tiles and compare them with low-zoom points."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape
from shapely.ops import transform

BASE={"ownership":"https://olga.scaskog.com/map/sca_mark/{z}/{x}/{y}.pbf",
      "voluntary":"https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"}
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
ZOOMS=[9,11,12,13,14,15]

def xyz(lon,lat,z):
 n=2**z
 lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def session():
 retry=Retry(total=2,connect=2,read=1,backoff_factor=0.8,
             status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-polygon-detail-probe/1.0"})
 s.mount("https://",HTTPAdapter(max_retries=retry)); return s

def geom_metrics(g):
 try:
  geom=shape(g)
  # MVT coordinates are tile-local; area and perimeter are reported in tile-coordinate units only.
  return {"type":geom.geom_type,"is_valid":bool(geom.is_valid),"area_tile_units2":float(geom.area),
          "perimeter_tile_units":float(geom.length),"bounds_tile_units":list(geom.bounds),
          "vertices":sum(len(getattr(poly,"exterior",[]).coords) if hasattr(poly,"exterior") else 0 for poly in (geom.geoms if hasattr(geom,"geoms") else [geom]) if hasattr(poly,"exterior"))}
 except Exception as e: return {"error":str(e)[:200]}

def main():
 s=session(); results=[]
 for site,(lon,lat) in SITES.items():
  for z in ZOOMS:
   x,y=xyz(lon,lat,z)
   for layer,template in BASE.items():
    url=template.format(z=z,x=x,y=y)
    row={"site":site,"zoom":z,"x":x,"y":y,"layer":layer,"url":url}
    try:
     r=s.get(url,timeout=(12,30)); row.update(http_status=r.status_code,content_type=r.headers.get("Content-Type"),bytes=len(r.content))
     if r.status_code==200:
      decoded=mapbox_vector_tile.decode(r.content); row["layers"]=[]
      for name,obj in decoded.items():
       feats=obj.get("features",[]); gc=Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)
       row["layers"].append({"name":name,"extent":obj.get("extent"),"feature_count":len(feats),
        "geometry_types":dict(gc),"id_values_sample":[f.get("id") for f in feats[:12]],
        "property_keys":sorted({k for f in feats for k in (f.get("properties") or {})}),
        "features":[{"id":f.get("id"),"properties":f.get("properties") or {},
                     "geometry":geom_metrics(f.get("geometry") or {})} for f in feats[:100]]})
    except Exception as e: row["error"]=str(e)[:250]
    results.append(row)
 summary={}
 for layer in BASE:
  rows=[r for r in results if r["layer"]==layer]
  summary[layer]={"200":sum(r.get("http_status")==200 for r in rows),"404":sum(r.get("http_status")==404 for r in rows),"request_errors":sum("error" in r for r in rows)}
 out={"purpose":"Inspect multiscale SCA voluntary-set-aside representation in selected tiles.",
      "sites":SITES,"zooms":ZOOMS,"summary":summary,"results":results,
      "limitations":["Tile coordinates are local MVT coordinates; not converted to map CRS in this report.",
      "Overlapping adjacent tiles may repeat clipped features; counts must not be summed as unique area.",
      "Feature IDs are not presumed stable.","At most 24 requests; no bulk collection."]}
 Path("sca-voluntary-multiscale-geometry.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"summary":summary,"results":results},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
