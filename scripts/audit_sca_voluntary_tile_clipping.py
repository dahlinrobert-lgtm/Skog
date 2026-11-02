#!/usr/bin/env python3
"""Inspect tile-clipping and duplicate geometry behavior in SCA voluntary MVT tiles."""
from __future__ import annotations
import json, math, hashlib
from collections import Counter, defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape
from shapely.ops import transform

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
ZOOM=12
OFFSETS=[(dx,dy) for dy in range(-2,3) for dx in range(-2,3)]

def xyz(lon,lat,z):
 n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def make_session():
 retry=Retry(total=2,connect=2,read=1,backoff_factor=.7,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-tile-clipping-audit/1.0"})
 s.mount("https://",HTTPAdapter(max_retries=retry)); return s

def main():
 s=make_session(); tiles=[]; features=[]
 for site,(lon,lat) in SITES.items():
  cx,cy=xyz(lon,lat,ZOOM)
  for dx,dy in OFFSETS:
   x,y=cx+dx,cy+dy; url=BASE.format(z=ZOOM,x=x,y=y)
   row={"site":site,"z":ZOOM,"x":x,"y":y,"dx":dx,"dy":dy,"url":url}
   try:
    r=s.get(url,timeout=(12,30)); row.update(status=r.status_code,bytes=len(r.content))
    if r.status_code==200:
     decoded=mapbox_vector_tile.decode(r.content); row["state"]="valid_mvt"
     for lname,layer in decoded.items():
      extent=layer.get("extent") or 4096
      for idx,f in enumerate(layer.get("features",[])):
       raw=f.get("geometry") or {}
       try:
        g=shape(raw)
        world=2*math.pi*6378137.0; span=world/(2**ZOOM)
        ox=-world/2+x*span; oy=world/2-y*span; scale=span/extent
        gm=transform(lambda a,b,zv=None:(ox+a*scale,oy-b*scale),g)
        minx,miny,maxx,maxy=g.bounds
        eps=1.0
        edge={"left":minx<=eps,"right":maxx>=extent-eps,"top":miny<=eps,"bottom":maxy>=extent-eps}
        wkb=gm.normalize().wkb
        sig=hashlib.sha256(wkb).hexdigest()
        props=f.get("properties") or {}
        features.append({"site":site,"tile":[x,y],"feature_index":idx,"layer":lname,
          "mvt_id":f.get("id"),"properties":props,"geom_type":g.geom_type,
          "area_m2_3857":float(gm.area),"length_m_3857":float(gm.length),
          "vertex_count":sum(len(poly.exterior.coords)+sum(len(r.coords) for r in poly.interiors) for poly in (gm.geoms if hasattr(gm,"geoms") else [gm]) if hasattr(poly,"exterior")),
          "touches_tile_edge":any(edge.values()),"tile_edges":edge,"geometry_sha256":sig,
          "bounds_3857":list(gm.bounds)})
       except Exception as e:
        row.setdefault("geometry_errors",[]).append(str(e)[:160])
     row["layers"]=[{"name":n,"feature_count":len(o.get("features",[]))} for n,o in decoded.items()]
    else: row["state"]="not_found_404" if r.status_code==404 else "http_error"
   except Exception as e: row.update(state="request_error",error=str(e)[:220])
   tiles.append(row)
 summary={}
 for site in SITES:
  fs=[f for f in features if f["site"]==site]
  bysig=defaultdict(list)
  for f in fs: bysig[f["geometry_sha256"]].append(f)
  summary[site]={"tiles_200":sum(t["site"]==site and t.get("status")==200 for t in tiles),
    "tiles_404":sum(t["site"]==site and t.get("status")==404 for t in tiles),
    "tile_feature_records":len(fs),"distinct_exact_geometry_hashes":len(bysig),
    "repeated_geometry_hash_groups":sum(len(v)>1 for v in bysig.values()),
    "features_touching_tile_edge":sum(f["touches_tile_edge"] for f in fs),
    "features_not_touching_tile_edge":sum(not f["touches_tile_edge"] for f in fs),
    "feature_id_values":dict(Counter(str(f["mvt_id"]) for f in fs)),
    "property_key_frequency":dict(Counter(k for f in fs for k in f["properties"])),
    "geometry_type_frequency":dict(Counter(f["geom_type"] for f in fs))}
 duplicates=[]
 for site in SITES:
  groups=defaultdict(list)
  for f in features:
   if f["site"]==site: groups[f["geometry_sha256"]].append(f)
  for sig,items in groups.items():
   if len(items)>1:
    duplicates.append({"site":site,"hash":sig,"copies":[{"tile":x["tile"],"properties":x["properties"],"touches_tile_edge":x["touches_tile_edge"]} for x in items]})
 out={"purpose":"Assess whether neighboring SCA MVT tiles repeat identical geometry or expose edge-clipped feature pieces.",
 "zoom":ZOOM,"sites":SITES,"summary":summary,"tiles":tiles,"features":features,"exact_duplicate_groups":duplicates,
 "limitations":["Only 5x5 tile neighborhoods around two reference points.","Exact geometry hashes identify byte-equivalent projected shapes only; clipped pieces of the same source feature will differ.","MVT geometries may include buffer beyond nominal tile bounds; edge contact is diagnostic, not proof of clipping.","Web Mercator area is not official area and must not be reported as SCA hectares.","No stable source object IDs have been established.","Maximum 50 requests."]}
 Path("sca-voluntary-tile-clipping-audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"summary":summary,"duplicate_groups":len(duplicates)},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
