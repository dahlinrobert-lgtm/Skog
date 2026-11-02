#!/usr/bin/env python3
"""SCA voluntary polygon geometric concordance audit v3.

Important correction: overlap / smaller-area alone is not a duplicate test.
This audit computes IoU, relative area, symmetric difference and Hausdorff
distance before assigning conservative duplicate-review labels. All source
features and tile provenance remain preserved; no dissolve is performed.
"""
from __future__ import annotations
import json, math, hashlib
from collections import defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape, mapping
from shapely.ops import transform

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
Z=12; R=4; MIN_INTERSECTION=100.0
DUP_IOU=.98; DUP_AREA_RATIO=.95; DUP_HAUSDORFF_M=10.0
REVIEW_IOU=.75; REVIEW_AREA_RATIO=.75; REVIEW_HAUSDORFF_M=150.0
CLASS="SKOTSEL_KL_resolved"; MOTIVE="MOTIV_resolved"

def xyz(lon,lat,z):
 n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
def session():
 retry=Retry(total=3,connect=3,read=2,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-geometric-concordance/0.3"})
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
        g=shape(f.get("geometry") or {})
        if g.is_empty or g.geom_type not in ("Polygon","MultiPolygon"): continue
        ox=-world/2+x*span; oy=world/2-y*span; sc=span/ext
        gm=transform(lambda a,b,z=None:(ox+a*sc,oy-b*sc),g)
        if not gm.is_valid: gm=gm.buffer(0)
        if gm.is_empty: continue
        props=f.get("properties") or {}; key=f"{site}:{Z}:{x}:{y}:{ln}:{ix}"
        fs.append({"key":key,"tile":[x,y],"layer":ln,"index":ix,"mvt_id":f.get("id"),
          "properties":props,"geom":gm,"area":float(gm.area),
          "hash":hashlib.sha256(gm.normalize().wkb).hexdigest()}); count+=1
       except Exception as e: t.setdefault("geometry_errors",[]).append(str(e)[:120])
     t["polygon_feature_records"]=count
   except Exception as e: t.update(state="request_error",error=str(e)[:160])
   tiles.append(t)
 return tiles,fs
def pair_metrics(a,b):
 inter=a["geom"].intersection(b["geom"]).area
 union=a["geom"].union(b["geom"]).area
 smaller=min(a["area"],b["area"]); larger=max(a["area"],b["area"])
 iou=inter/union if union else 0.0
 cover=inter/smaller if smaller else 0.0
 area_ratio=smaller/larger if larger else 0.0
 symdiff=(a["geom"].symmetric_difference(b["geom"]).area/union) if union else 0.0
 haus=float(a["geom"].hausdorff_distance(b["geom"]))
 pa,pb=a["properties"],b["properties"]
 ca,cb=pa.get(CLASS),pb.get(CLASS); ma,mb=pa.get(MOTIVE),pb.get(MOTIVE)
 class_match=bool(ca and cb and ca==cb); class_conflict=bool(ca and cb and ca!=cb)
 motive_match=bool(ma and mb and ma==mb); motive_conflict=bool(ma and mb and ma!=mb)
 conflict=class_conflict or motive_conflict
 if class_match and not conflict and iou>=DUP_IOU and area_ratio>=DUP_AREA_RATIO and haus<=DUP_HAUSDORFF_M:
  label="duplicate_geometry_candidate"
 elif class_match and not conflict and iou>=REVIEW_IOU and area_ratio>=REVIEW_AREA_RATIO and haus<=REVIEW_HAUSDORFF_M:
  label="near_duplicate_manual_review"
 elif cover>=.95 and iou<.75:
  label="contained_or_nested_overlap"
 elif inter>=MIN_INTERSECTION:
  label="partial_or_unrelated_overlap"
 else:
  label="minor_intersection_ignored"
 return {"feature_a":a["key"],"feature_b":b["key"],"tile_a":a["tile"],"tile_b":b["tile"],
  "intersection_m2_3857":float(inter),"union_m2_3857":float(union),
  "overlap_over_smaller":float(cover),"iou":float(iou),"area_ratio_smaller_over_larger":float(area_ratio),
  "symmetric_difference_over_union":float(symdiff),"hausdorff_distance_m_3857":haus,
  "class_match":class_match,"motive_match":motive_match,"attribute_conflict":conflict,
  "class_a":ca,"class_b":cb,"motive_a":ma,"motive_b":mb,
  "geometry_hash_equal":a["hash"]==b["hash"],"classification":label}
def main():
 s=session(); out={}
 for site,(lon,lat) in SITES.items():
  tiles,fs=load(s,site,lon,lat); pairs=[]
  for i,a in enumerate(fs):
   for b in fs[i+1:]:
    if a["tile"]==b["tile"]: continue
    if abs(a["tile"][0]-b["tile"][0])>1 or abs(a["tile"][1]-b["tile"][1])>1: continue
    try: p=pair_metrics(a,b)
    except Exception: continue
    if p["intersection_m2_3857"]>=MIN_INTERSECTION: pairs.append(p)
  # Only geometrically strict pairs become candidate groups.
  parent={f["key"]:f["key"] for f in fs}
  def root(k):
   while parent[k]!=k: parent[k]=parent[parent[k]]; k=parent[k]
   return k
  for p in pairs:
   if p["classification"]=="duplicate_geometry_candidate":
    x,y=root(p["feature_a"]),root(p["feature_b"])
    if x!=y: parent[y]=x
  groups=defaultdict(list)
  for f in fs: groups[root(f["key"])].append(f["key"])
  cand=[]
  for mem in groups.values():
   if len(mem)<2: continue
   ms=set(mem); edges=[p for p in pairs if p["classification"]=="duplicate_geometry_candidate"
                        and p["feature_a"] in ms and p["feature_b"] in ms]
   cand.append({"group_id":"sca-"+hashlib.sha1("|".join(sorted(mem)).encode()).hexdigest()[:12],
    "members":sorted(mem),"edge_count":len(edges),"all_pairs_directly_linked":len(edges)==len(mem)*(len(mem)-1)//2,
    "edges":edges})
  counts={k:sum(p["classification"]==k for p in pairs) for k in
   ("duplicate_geometry_candidate","near_duplicate_manual_review","contained_or_nested_overlap","partial_or_unrelated_overlap")}
  out[site]={"tile_summary":{"total":len(tiles),"http_200":sum(t.get("status")==200 for t in tiles),
    "http_404":sum(t.get("status")==404 for t in tiles),
    "errors":sum(t.get("state") in ("http_error","request_error") for t in tiles)},
    "source_feature_count":len(fs),"pair_classification_counts":counts,
    "candidate_groups":cand,"pairs":pairs,
    "source_features":[{"key":f["key"],"tile":f["tile"],"layer":f["layer"],"index":f["index"],
      "mvt_id":f["mvt_id"],"properties":f["properties"],"area_m2_3857":f["area"],
      "geometry_sha256":f["hash"],"geometry_epsg3857":mapping(f["geom"])} for f in fs],
    "tile_requests":tiles}
 result={"purpose":"Geometric concordance audit correcting overlap/smaller-area false positives.",
  "zoom":Z,"radius":R,"thresholds":{"min_intersection_m2_3857":MIN_INTERSECTION,
   "duplicate_iou":DUP_IOU,"duplicate_area_ratio":DUP_AREA_RATIO,"duplicate_hausdorff_m":DUP_HAUSDORFF_M,
   "review_iou":REVIEW_IOU,"review_area_ratio":REVIEW_AREA_RATIO,"review_hausdorff_m":REVIEW_HAUSDORFF_M},
  "definitions":["IoU = intersection / union; unlike overlap/smaller-area it penalizes a small polygon contained in a much larger one.",
   "duplicate_geometry_candidate requires compatible class and no attribute conflict plus very high IoU, similar area, and close boundaries.",
   "near_duplicate_manual_review is a less strict similarity flag only; never auto-merge.",
   "contained_or_nested_overlap indicates the smaller geometry is mostly inside the larger but overall geometries differ substantially.",
   "EPSG:3857 metrics are diagnostic only, not official SCA area.",
   "Only adjacent tiles in two 9x9 z12 neighborhoods are tested; no authoritative IDs are available.",
   "All source geometries, properties and tile provenance are retained; no geometry is merged or deleted."],
  "sites":out}
 Path("sca-voluntary-geometric-concordance-v3.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:{"tiles":v["tile_summary"],"features":v["source_feature_count"],
  "pairs":v["pair_classification_counts"],"candidate_groups":len(v["candidate_groups"])}
  for k,v in out.items()},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
