#!/usr/bin/env python3
"""Build an exact-geometry-only SCA voluntary polygon inventory preview.

Only cross-tile features that are effectively geometrically identical are
collapsed to one canonical preview feature. Every original tile feature is
retained in a source manifest and provenance mapping. All other overlaps are
kept as separate features. This is a preview, not a national production layer.
"""
from __future__ import annotations
import json, math, hashlib, csv
from collections import defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import transform

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
Z=12; R=4; MIN_INTERSECTION=100.0
IDENTICAL_IOU=0.999999
IDENTICAL_AREA_RATIO=0.999999
IDENTICAL_HAUSDORFF_M=0.01
CLASS="SKOTSEL_KL_resolved"; MOTIVE="MOTIV_resolved"

def xyz(lon,lat,z):
 n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
def session():
 retry=Retry(total=3,connect=3,read=2,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-exact-geometry-preview/0.1"})
 s.mount("https://",HTTPAdapter(max_retries=retry)); return s
def load(s,site,lon,lat):
 cx,cy=xyz(lon,lat,Z); world=2*math.pi*6378137.; span=world/(2**Z); tiles=[]; fs=[]
 for dy in range(-R,R+1):
  for dx in range(-R,R+1):
   x,y=cx+dx,cy+dy; t={"site":site,"z":Z,"x":x,"y":y,"dx":dx,"dy":dy}
   try:
    r=s.get(BASE.format(z=Z,x=x,y=y),timeout=(12,35)); t.update(status=r.status_code,bytes=len(r.content))
    if r.status_code==404: t["state"]="not_found_404"
    elif r.status_code!=200: t["state"]="http_error"
    else:
     dec=mapbox_vector_tile.decode(r.content); t["state"]="valid_mvt"; count=0
     for ln,ly in dec.items():
      ext=ly.get("extent") or 4096
      for ix,f in enumerate(ly.get("features",[])):
       try:
        geom=shape(f.get("geometry") or {})
        if geom.is_empty or geom.geom_type not in ("Polygon","MultiPolygon"): continue
        ox=-world/2+x*span; oy=world/2-y*span; sc=span/ext
        gm=transform(lambda a,b,z=None:(ox+a*sc,oy-b*sc),geom)
        if not gm.is_valid: gm=gm.buffer(0)
        if gm.is_empty: continue
        props=f.get("properties") or {}; key=f"{site}:{Z}:{x}:{y}:{ln}:{ix}"
        fs.append({"key":key,"site":site,"tile":[x,y],"layer":ln,"index":ix,
          "mvt_id":f.get("id"),"properties":props,"geom":gm,"area":float(gm.area),
          "geometry_sha256":hashlib.sha256(gm.normalize().wkb).hexdigest()}); count+=1
       except Exception as e: t.setdefault("geometry_errors",[]).append(str(e)[:120])
     t["polygon_feature_records"]=count
   except Exception as e: t.update(state="request_error",error=str(e)[:160])
   tiles.append(t)
 return tiles,fs
def compatible(a,b):
 pa,pb=a["properties"],b["properties"]
 ca,cb=pa.get(CLASS),pb.get(CLASS); ma,mb=pa.get(MOTIVE),pb.get(MOTIVE)
 if ca and cb and ca!=cb: return False
 if ma and mb and ma!=mb: return False
 return bool(ca and cb and ca==cb)
def main():
 s=session(); site_results={}; all_geojson=[]; all_manifest=[]
 for site,(lon,lat) in SITES.items():
  tiles,fs=load(s,site,lon,lat)
  parent={f["key"]:f["key"] for f in fs}
  def root(k):
   while parent[k]!=k: parent[k]=parent[parent[k]]; k=parent[k]
   return k
  edges=[]
  for i,a in enumerate(fs):
   for b in fs[i+1:]:
    if a["tile"]==b["tile"]: continue
    if abs(a["tile"][0]-b["tile"][0])>1 or abs(a["tile"][1]-b["tile"][1])>1: continue
    if not compatible(a,b): continue
    try:
     inter=a["geom"].intersection(b["geom"]).area
     union=a["geom"].union(b["geom"]).area
     iou=float(inter/union) if union else 0.0
     ar=min(a["area"],b["area"])/max(a["area"],b["area"]) if max(a["area"],b["area"]) else 0.0
     hd=float(a["geom"].hausdorff_distance(b["geom"]))
    except Exception: continue
    if inter<MIN_INTERSECTION: continue
    if iou>=IDENTICAL_IOU and ar>=IDENTICAL_AREA_RATIO and hd<=IDENTICAL_HAUSDORFF_M:
     edges.append({"a":a["key"],"b":b["key"],"iou":iou,"area_ratio":ar,"hausdorff_m":hd})
     ra,rb=root(a["key"]),root(b["key"])
     if ra!=rb: parent[rb]=ra
  groups=defaultdict(list)
  for f in fs: groups[root(f["key"])].append(f)
  canonical=[]; duplicate_members=0
  for members in groups.values():
   members=sorted(members,key=lambda f:f["key"])
   canonical_feature=members[0]
   keys=[m["key"] for m in members]
   if len(members)>1: duplicate_members+=len(members)-1
   geom=mapping(canonical_feature["geom"])
   props={k:v for k,v in canonical_feature["properties"].items()}
   props.update({"preview_id":"sca-preview-"+hashlib.sha1("|".join(keys).encode()).hexdigest()[:12],
     "source_feature_count":len(members),"source_feature_keys":keys,
     "duplicate_resolution":"exact_geometry_candidate" if len(members)>1 else "single_source_feature",
     "source_tiles":[m["tile"] for m in members]})
   canonical.append({"type":"Feature","geometry":geom,"properties":props})
   for m in members:
    rec={"feature_key":m["key"],"site":site,"tile":m["tile"],"layer":m["layer"],
      "feature_index":m["index"],"mvt_id":m["mvt_id"],"properties":m["properties"],
      "area_m2_3857":m["area"],"geometry_sha256":m["geometry_sha256"],
      "canonical_preview_id":props["preview_id"],
      "dedup_status":"duplicate_member" if len(members)>1 else "retained_separate"}
    all_manifest.append(rec)
  all_geojson.extend(canonical)
  site_results[site]={"tiles":{"total":len(tiles),"http_200":sum(t.get("status")==200 for t in tiles),
    "http_404":sum(t.get("status")==404 for t in tiles),
    "errors":sum(t.get("state") in ("http_error","request_error") for t in tiles)},
    "source_feature_count":len(fs),"preview_feature_count":len(canonical),
    "removed_duplicate_representations":duplicate_members,
    "candidate_groups":[{"canonical_preview_id":f["properties"]["preview_id"],
      "source_feature_keys":f["properties"]["source_feature_keys"]} for f in canonical if f["properties"]["source_feature_count"]>1],
    "duplicate_edges":edges,"tile_requests":tiles}
 out={"type":"FeatureCollection","name":"SCA voluntary exact-geometry preview",
  "crs":{"type":"name","properties":{"name":"EPSG:3857"}},
  "features":all_geojson}
 Path("sca-voluntary-exact-geometry-preview.geojson").write_text(json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 Path("sca-voluntary-exact-geometry-source-manifest.json").write_text(json.dumps({"purpose":"Original tile provenance; no source features discarded.","records":all_manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 Path("sca-voluntary-exact-geometry-preview-summary.json").write_text(json.dumps({
  "purpose":"Exact-geometry-only deduplication preview over two local z12 neighborhoods.",
  "thresholds":{"iou":IDENTICAL_IOU,"area_ratio":IDENTICAL_AREA_RATIO,"hausdorff_m":IDENTICAL_HAUSDORFF_M,
  "requires_same_nonempty_class":True,"no_conflicting_motive":True},
  "sites":site_results,
  "limitations":["Only two 9x9 z12 neighborhoods; not national coverage.",
  "MVT geometry is a tile representation, not necessarily a complete authoritative source polygon.",
  "No stable source object identifier has been found.",
  "All original source geometries and properties are retained in the provenance manifest.",
  "The GeoJSON preview uses a canonical representative for exact duplicate candidates only; it does not merge partial overlaps.",
  "Coordinates and areas are in EPSG:3857 and are diagnostic only."]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(site_results,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
