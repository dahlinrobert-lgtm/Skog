#!/usr/bin/env python3
"""Compare SCA voluntary points and polygons over a bounded neighborhood of XYZ tiles."""
from __future__ import annotations
import json, math
from collections import Counter, defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape
from shapely.ops import transform

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
POINT_ZOOMS=[9,11]
POLYGON_ZOOMS=[12,13]
OFFSETS=[(0,0),(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]

def xyz(lon,lat,z):
 n=2**z
 lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def session():
 retry=Retry(total=2,connect=2,read=1,backoff_factor=.7,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-neighborhood-correspondence/1.0"})
 s.mount("https://",HTTPAdapter(max_retries=retry)); return s

def map_geometry(raw,z,x,y,extent):
 world=2*math.pi*6378137.0
 span=world/(2**z)
 ox=-world/2+x*span
 oy=world/2-y*span
 scale=span/extent
 return transform(lambda a,b,zv=None:(ox+a*scale,oy-b*scale),shape(raw))

def main():
 s=session(); features=[]; tile_results=[]
 for site,(lon,lat) in SITES.items():
  for z in sorted(set(POINT_ZOOMS+POLYGON_ZOOMS)):
   cx,cy=xyz(lon,lat,z)
   offsets=OFFSETS if z in (12,13) else [(0,0)]
   for dx,dy in offsets:
    x,y=cx+dx,cy+dy; url=BASE.format(z=z,x=x,y=y)
    row={"site":site,"zoom":z,"x":x,"y":y,"dx":dx,"dy":dy,"url":url}
    try:
     r=s.get(url,timeout=(12,30)); row["status"]=r.status_code; row["bytes"]=len(r.content)
     if r.status_code==200:
      decoded=mapbox_vector_tile.decode(r.content); row["state"]="valid_mvt"
      for lname,layer in decoded.items():
       extent=layer.get("extent") or 4096
       for idx,f in enumerate(layer.get("features",[])):
        g=f.get("geometry") or {}
        try:
         geom=map_geometry(g,z,x,y,extent)
         features.append({"site":site,"zoom":z,"tile":[x,y],"layer_name":lname,"index":idx,
           "mvt_id":f.get("id"),"geom_type":geom.geom_type,"geom":geom,"props":f.get("properties") or {}})
        except Exception: pass
      row["layers"]=[{"name":n,"count":len(o.get("features",[])),
       "types":dict(Counter((f.get("geometry") or {}).get("type","unknown") for f in o.get("features",[])))} for n,o in decoded.items()]
     else: row["state"]="not_found_404" if r.status_code==404 else "http_error"
    except Exception as e: row.update(state="request_error",error=str(e)[:220])
    tile_results.append(row)
 comparisons={}
 for site in SITES:
  pts=[f for f in features if f["site"]==site and f["zoom"] in POINT_ZOOMS and f["geom_type"]=="Point"]
  polys=[f for f in features if f["site"]==site and f["zoom"] in POLYGON_ZOOMS and f["geom_type"] in ("Polygon","MultiPolygon")]
  by_point=[]
  for p in pts:
   matches=[]
   for q in polys:
    if q["geom"].buffer(0.05).covers(p["geom"]):
     matches.append({"polygon_zoom":q["zoom"],"polygon_tile":q["tile"],"polygon_properties":q["props"],
      "point_properties":p["props"],"polygon_area_m2_3857":q["geom"].area,
      "intersection_area_m2_3857":q["geom"].intersection(p["geom"].buffer(0.05)).area})
   if matches: by_point.append({"point_zoom":p["zoom"],"point_tile":p["tile"],"matches":matches[:5]})
  comparisons[site]={"point_features":len(pts),"polygon_features":len(polys),
   "point_features_with_polygon_match":len(by_point),"match_details_sample":by_point[:40],
   "note":"Cross-zoom comparison across center and neighboring polygon tiles. Point features are not assumed to be unique because low-zoom clusters can represent multiple objects."}
 summary={}
 for site in SITES:
  summary[site]={}
  for z in sorted(set(POINT_ZOOMS+POLYGON_ZOOMS)):
   rr=[r for r in tile_results if r["site"]==site and r["zoom"]==z]
   summary[site][str(z)]={"tiles_tested":len(rr),"200":sum(r.get("status")==200 for r in rr),
      "404":sum(r.get("status")==404 for r in rr),"request_errors":sum(r.get("state")=="request_error" for r in rr)}
 out={"purpose":"Reduce false no-match results by searching a 3x3 polygon tile neighborhood around each test location.",
  "tile_template":BASE,"sites":SITES,"point_zooms":POINT_ZOOMS,"polygon_zooms":POLYGON_ZOOMS,
  "summary":summary,"tile_results":tile_results,"correspondence":comparisons,
  "limitations":["Only a bounded 3x3 neighborhood at polygon zooms and one tile at point zooms.",
   "Low-zoom clustered points may represent multiple source objects.","MVT features may be clipped at tile edges.",
   "MVT feature IDs are not assumed stable.","Area calculations use Web Mercator and clipped tile geometry; not official hectares.",
   "At most 36 requests; no bulk collection."]}
 Path("sca-voluntary-neighborhood-correspondence.json").write_text(json.dumps(out,ensure_ascii=False,indent=2,default=lambda o:None)+"\n",encoding="utf-8")
 print(json.dumps({"summary":summary,"correspondence":{k:{a:v for a,v in x.items() if a!="match_details_sample"} for k,x in comparisons.items()}},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
