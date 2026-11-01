#!/usr/bin/env python3
"""Compare SCA voluntary point and polygon representations with true map coordinates."""
from __future__ import annotations
import json, math
from collections import Counter, defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape, Point
from shapely.ops import transform

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
ZOOMS=[9,11,12,13,14,15]
EXTENT_DEFAULT=4096

def xyz(lon,lat,z):
 n=2**z
 lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def make_session():
 retry=Retry(total=2,connect=2,read=1,backoff_factor=0.7,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-point-polygon-correspondence/1.0"})
 s.mount("https://",HTTPAdapter(max_retries=retry)); return s

def tile_transform(z,x,y,extent):
 # Vector tile local coordinates -> Web Mercator EPSG:3857.
 world=2*math.pi*6378137.0
 span=world/(2**z)
 origin_x=-world/2+x*span
 origin_y=world/2-y*span
 scale=span/extent
 return lambda tx,ty: (origin_x+tx*scale,origin_y-ty*scale)

def decode(session,site,lon,lat,z):
 x,y=xyz(lon,lat,z); url=BASE.format(z=z,x=x,y=y)
 row={"site":site,"zoom":z,"x":x,"y":y,"url":url}
 try:
  r=session.get(url,timeout=(12,30))
  row.update(http_status=r.status_code,bytes=len(r.content),content_type=r.headers.get("Content-Type"))
  if r.status_code!=200: row["state"]="not_found_404" if r.status_code==404 else "http_error"; return row,[]
  decoded=mapbox_vector_tile.decode(r.content)
  row["state"]="valid_mvt_empty" if not decoded or all(not v.get("features",[]) for v in decoded.values()) else "valid_mvt_with_features"
  feats_out=[]
  for lname,layer in decoded.items():
   extent=layer.get("extent") or EXTENT_DEFAULT
   to_map=tile_transform(z,x,y,extent)
   for idx,f in enumerate(layer.get("features",[])):
    geom=f.get("geometry") or {}
    try:
     shp=shape(geom)
     mapped=transform(lambda a,b,zv=None: to_map(a,b),shp)
     props=f.get("properties") or {}
     feats_out.append({"layer_name":lname,"tile_feature_index":idx,"mvt_id":f.get("id"),
       "geometry_type":shp.geom_type,"properties":props,"shape":mapped})
    except Exception:
     continue
   row.setdefault("layers",[]).append({"name":lname,"extent":extent,"version":layer.get("version"),
     "feature_count":len(layer.get("features",[])),
     "geometry_types":dict(Counter((f.get("geometry") or {}).get("type","unknown") for f in layer.get("features",[]))),
     "property_keys":sorted({k for f in layer.get("features",[]) for k in ((f.get("properties") or {}).keys())}),
     "features_with_nonzero_id":sum(f.get("id") not in (None,0) for f in layer.get("features",[])),
     "sample_properties":[f.get("properties") or {} for f in layer.get("features",[])[:5]]})
  return row,feats_out
 except Exception as e:
  row.update(state="request_error",error=str(e)[:260]); return row,[]

def main():
 session=make_session(); rows=[]; bysite=defaultdict(dict)
 for site,(lon,lat) in SITES.items():
  for z in ZOOMS:
   row,features=decode(session,site,lon,lat,z)
   rows.append(row); bysite[site][z]=features
 comparisons={}
 for site in SITES:
  points=[f for f in bysite[site].get(9,[])+bysite[site].get(11,[]) if f["geometry_type"]=="Point"]
  polygons=[f for f in bysite[site].get(12,[])+bysite[site].get(13,[])+bysite[site].get(14,[])+bysite[site].get(15,[]) if f["geometry_type"] in ("Polygon","MultiPolygon")]
  pairs=[]
  for p in points:
   for poly in polygons:
    if poly["shape"].covers(p["shape"]):
     pairs.append({"point_zoom_property_keys":sorted(p["properties"].keys()),
       "point_properties":p["properties"],"polygon_zoom_property_keys":sorted(poly["properties"].keys()),
       "polygon_properties":poly["properties"],"polygon_area_m2_webmercator":float(poly["shape"].area),
       "polygon_bounds_3857":list(poly["shape"].bounds)})
  comparisons[site]={"low_zoom_points":len(points),"high_zoom_polygons":len(polygons),
   "point_inside_polygon_matches":len(pairs),"matches_sample":pairs[:30],
   "note":"Point/polygon matching is within the sampled XYZ tile at each zoom. Polygons may be clipped and duplicates may occur across tiles."}
 summary={}
 for z in ZOOMS:
  rr=[r for r in rows if r["zoom"]==z]
  summary[str(z)]={"200":sum(r.get("http_status")==200 for r in rr),"404":sum(r.get("http_status")==404 for r in rr),
                   "other_or_error":sum(r.get("http_status") not in (200,404) for r in rr)}
 out={"purpose":"Establish point-to-polygon correspondence and stable identifiers for SCA voluntary set-aside MVT.",
 "tile_template":BASE,"sites":SITES,"zooms":ZOOMS,"summary":summary,"results":rows,"correspondence":comparisons,
 "limitations":["Only one tile per site and zoom; no full coverage inference.","MVT geometries are transformed from tile-local coordinates to EPSG:3857 using XYZ tile bounds.","Polygon areas are calculated from clipped tile geometry; do not sum as official set-aside hectares.","MVT ID zero/absence is not treated as a stable identifier.","No bulk download; at most 12 requests."]}
 Path("sca-voluntary-point-polygon-correspondence.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
