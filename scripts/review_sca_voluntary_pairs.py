#!/usr/bin/env python3
"""Review SCA voluntary MVT cross-tile polygon pairs without modifying sources."""
from __future__ import annotations
import json, math, hashlib
from collections import defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
Z=12; R=4; MIN_INTERSECTION=100.0; HIGH_OVERLAP=.95
CLASS="SKOTSEL_KL_resolved"; MOTIVE="MOTIV_resolved"

def xyz(lon,lat,z):
 n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
def get_session():
 retry=Retry(total=3,connect=3,read=2,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-pair-review/0.1"})
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
def compare_attrs(a,b):
 pa,pb=a["properties"],b["properties"]
 ca,cb=pa.get(CLASS),pb.get(CLASS); ma,mb=pa.get(MOTIVE),pb.get(MOTIVE)
 c_conf=bool(ca and cb and ca!=cb); m_conf=bool(ma and mb and ma!=mb)
 c_match=bool(ca and cb and ca==cb); m_match=bool(ma and mb and ma==mb)
 if c_conf or m_conf: state="conflict"
 elif c_match: state="class_agrees_motive_agrees" if m_match else "class_agrees_motive_missing"
 else: state="insufficient"
 return state,{"class_a":ca,"class_b":cb,"motive_a":ma,"motive_b":mb},c_match,m_match,c_conf or m_conf
def main():
 s=get_session(); result={}
 for site,(lon,lat) in SITES.items():
  tiles,fs=load(s,site,lon,lat); pairs=[]
  for i,a in enumerate(fs):
   for b in fs[i+1:]:
    if a["tile"]==b["tile"]: continue
    if abs(a["tile"][0]-b["tile"][0])>1 or abs(a["tile"][1]-b["tile"][1])>1: continue
    try: inter=a["geom"].intersection(b["geom"])
    except Exception: continue
    area=float(inter.area)
    if area<MIN_INTERSECTION: continue
    smaller=min(a["area"],b["area"]); ratio=area/smaller if smaller else 0
    attr,vals,c_match,m_match,conflict=compare_attrs(a,b)
    if ratio>=HIGH_OVERLAP and c_match and not conflict: label="high_confidence_candidate"
    elif ratio>=.80 and c_match and not conflict: label="review_candidate"
    else: label="partial_or_conflicting_overlap"
    pairs.append({"a":a["key"],"b":b["key"],"tile_a":a["tile"],"tile_b":b["tile"],
      "intersection_m2_3857":area,"overlap_over_smaller":ratio,"label":label,
      "attribute_state":attr,"attributes":vals,"geometry_hash_equal":a["hash"]==b["hash"]})
  strong=[p for p in pairs if p["label"]=="high_confidence_candidate"]
  bykey={f["key"]:f for f in fs}; parent={k:k for k in bykey}
  def root(k):
   while parent[k]!=k: parent[k]=parent[parent[k]]; k=parent[k]
   return k
  for p in strong:
   x,y=root(p["a"]),root(p["b"])
   if x!=y: parent[y]=x
  groups=defaultdict(list)
  for k in bykey: groups[root(k)].append(k)
  candidates=[]
  for members in groups.values():
   if len(members)<2: continue
   ms=set(members); edges=[p for p in strong if p["a"] in ms and p["b"] in ms]
   geoms=[bykey[k]["geom"] for k in members]; union=unary_union(geoms)
   candidates.append({"group_id":"sca-"+hashlib.sha1("|".join(sorted(members)).encode()).hexdigest()[:12],
    "members":sorted(members),"edge_count":len(edges),
    "all_pairs_directly_linked":len(edges)==len(members)*(len(members)-1)//2,
    "sum_area_m2_3857":sum(g.area for g in geoms),"union_area_m2_3857":float(union.area),
    "overlap_excess_m2_3857":sum(g.area for g in geoms)-float(union.area),"edges":edges})
  result[site]={"tile_summary":{"total":len(tiles),"http_200":sum(t.get("status")==200 for t in tiles),
    "http_404":sum(t.get("status")==404 for t in tiles),
    "errors":sum(t.get("state") in ("http_error","request_error") for t in tiles)},
    "source_feature_count":len(fs),
    "pair_counts":{k:sum(p["label"]==k for p in pairs) for k in
      ("high_confidence_candidate","review_candidate","partial_or_conflicting_overlap")},
    "candidate_groups":candidates,"pairs":pairs,
    "source_features":[{"key":f["key"],"tile":f["tile"],"layer":f["layer"],"index":f["index"],
      "mvt_id":f["mvt_id"],"properties":f["properties"],"area_m2_3857":f["area"],
      "geometry_sha256":f["hash"],"geometry_epsg3857":mapping(f["geom"])} for f in fs],
    "tile_requests":tiles}
 out={"purpose":"SCA voluntary polygon pair review; original source features retained, no dissolve.",
  "zoom":Z,"radius":R,"thresholds":{"min_intersection_m2_3857":MIN_INTERSECTION,
  "high_confidence_overlap":HIGH_OVERLAP,"class_key":CLASS,"motive_key":MOTIVE},
  "limitations":["Candidate is not confirmed object identity; no stable source IDs are available.",
  "Missing motive is not treated as a match; matching class is required.",
  "Only adjacent tiles in two 9x9 z12 neighborhoods are compared.",
  "EPSG:3857 areas are diagnostic, not official SCA hectares.",
  "No geometry is deleted, merged or overwritten."],"sites":result}
 Path("sca-voluntary-pair-review.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:{"tiles":v["tile_summary"],"features":v["source_feature_count"],
  "pair_counts":v["pair_counts"],"candidate_groups":len(v["candidate_groups"])} for k,v in result.items()},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
