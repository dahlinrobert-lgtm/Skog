#!/usr/bin/env python3
"""Expanded SCA voluntary polygon cross-tile overlap audit (9x9, z12)."""
from __future__ import annotations
import json, math, hashlib
from collections import defaultdict
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape
from shapely.ops import transform, unary_union

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
ZOOM=12
RADIUS=4

def xyz(lon,lat,z):
    n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
    return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def get_session():
    retry=Retry(total=3,connect=3,read=2,backoff_factor=1,
                status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
    s=requests.Session()
    s.headers.update({"User-Agent":"Skog-SCA-expanded-cross-tile-audit/1.0"})
    s.mount("https://",HTTPAdapter(max_retries=retry))
    return s

def read_site(session,site,lon,lat):
    cx,cy=xyz(lon,lat,ZOOM)
    world=2*math.pi*6378137.0; span=world/(2**ZOOM)
    tiles=[]; features=[]
    for dy in range(-RADIUS,RADIUS+1):
      for dx in range(-RADIUS,RADIUS+1):
        x,y=cx+dx,cy+dy
        row={"site":site,"tile":[x,y],"offset":[dx,dy]}
        try:
          r=session.get(BASE.format(z=ZOOM,x=x,y=y),timeout=(12,35))
          row.update(status=r.status_code,bytes=len(r.content))
          if r.status_code==404: row["state"]="not_found_404"
          elif r.status_code!=200: row["state"]="http_error"
          else:
            decoded=mapbox_vector_tile.decode(r.content); row["state"]="valid_mvt"
            nfeat=0
            for lname,layer in decoded.items():
              extent=layer.get("extent") or 4096
              for idx,f in enumerate(layer.get("features",[])):
                try:
                  g=shape(f.get("geometry") or {})
                  if g.is_empty or g.geom_type not in ("Polygon","MultiPolygon"): continue
                  ox=-world/2+x*span; oy=world/2-y*span; scale=span/extent
                  gm=transform(lambda a,b,z=None:(ox+a*scale,oy-b*scale),g)
                  if not gm.is_valid: gm=gm.buffer(0)
                  if gm.is_empty: continue
                  props=f.get("properties") or {}
                  features.append({"site":site,"tile":[x,y],"offset":[dx,dy],
                    "feature_index":idx,"layer":lname,"mvt_id":f.get("id"),
                    "properties":props,"geometry":gm,"area":float(gm.area),
                    "hash":hashlib.sha256(gm.normalize().wkb).hexdigest()})
                  nfeat+=1
                except Exception as e:
                  row.setdefault("geometry_errors",[]).append(str(e)[:160])
            row["polygon_feature_records"]=nfeat
        except Exception as e: row.update(state="request_error",error=str(e)[:200])
        tiles.append(row)
    return tiles,features

def compare(features):
    pairs=[]
    # Only compare neighboring tiles, including diagonal neighbors.
    for i,a in enumerate(features):
      for b in features[i+1:]:
        if a["tile"]==b["tile"]: continue
        dx=abs(a["tile"][0]-b["tile"][0]); dy=abs(a["tile"][1]-b["tile"][1])
        if dx>1 or dy>1: continue
        try: inter=a["geometry"].intersection(b["geometry"])
        except Exception: continue
        ia=float(inter.area)
        if ia<=1: continue
        smaller=min(a["area"],b["area"])
        ratio=ia/smaller if smaller else 0
        # Record all meaningful intersections; flag strong likely duplicate candidates.
        pairs.append({"tile_a":a["tile"],"index_a":a["feature_index"],
          "tile_b":b["tile"],"index_b":b["feature_index"],
          "intersection_m2_3857":ia,"intersection_over_smaller":ratio,
          "area_a_m2_3857":a["area"],"area_b_m2_3857":b["area"],
          "properties_equal":a["properties"]==b["properties"],
          "properties_a":a["properties"],"properties_b":b["properties"],
          "hash_equal":a["hash"]==b["hash"],
          "likely_duplicate_candidate":ratio>=0.80 and a["properties"]==b["properties"]})
    # Build connected components from likely duplicate candidate edges.
    parent=list(range(len(features)))
    def root(i):
      while parent[i]!=i:
        parent[i]=parent[parent[i]]; i=parent[i]
      return i
    index={(f["tile"][0],f["tile"][1],f["feature_index"],f["layer"]):i for i,f in enumerate(features)}
    for p in pairs:
      if not p["likely_duplicate_candidate"]: continue
      # Tile+feature index identifies the feature in this single-layer source.
      ia=next((i for i,f in enumerate(features) if f["tile"]==p["tile_a"] and f["feature_index"]==p["index_a"]),None)
      ib=next((i for i,f in enumerate(features) if f["tile"]==p["tile_b"] and f["feature_index"]==p["index_b"]),None)
      if ia is not None and ib is not None:
        ra,rb=root(ia),root(ib)
        if ra!=rb: parent[rb]=ra
    groups=defaultdict(list)
    for i,f in enumerate(features): groups[root(i)].append(f)
    output=[]
    for group in groups.values():
      if len(group)<2: continue
      geoms=[f["geometry"] for f in group]
      output.append({"member_count":len(group),
        "members":[{"tile":f["tile"],"feature_index":f["feature_index"],
          "area_m2_3857":f["area"],"properties":f["properties"]} for f in group],
        "union_area_m2_3857":float(unary_union(geoms).area),
        "sum_area_m2_3857":sum(f["area"] for f in group)})
    return pairs,output

def main():
  session=get_session(); results={}; all_tiles=[]
  for site,(lon,lat) in SITES.items():
    tiles,features=read_site(session,site,lon,lat); pairs,groups=compare(features); all_tiles.extend(tiles)
    results[site]={"tile_summary":{"total":len(tiles),
      "http_200":sum(t.get("status")==200 for t in tiles),
      "http_404":sum(t.get("status")==404 for t in tiles),
      "other_or_request_errors":sum(t.get("state") in ("http_error","request_error") for t in tiles)},
      "feature_records":len(features),
      "cross_tile_intersection_pairs":len(pairs),
      "strong_duplicate_candidates":sum(p["likely_duplicate_candidate"] for p in pairs),
      "candidate_groups":groups,"pairs":pairs}
  out={"purpose":"Expanded neighborhood test for cross-tile polygon overlap and likely duplicate fragments.",
    "zoom":ZOOM,"tile_radius":RADIUS,"tiles_per_site":(2*RADIUS+1)**2,
    "results":results,"tile_requests":all_tiles,
    "limits":["A strong overlap plus equal attributes is still only a candidate, not authoritative identity.",
      "MVT buffers/generalization may create overlap; real source polygons may overlap too.",
      "No stable source object IDs have been identified.",
      "EPSG:3857 areas are diagnostic only, not official hectares.",
      "Only two 9x9 tile neighborhoods are covered."]}
  Path("sca-voluntary-expanded-cross-tile-audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps({k:{"tiles":v["tile_summary"],"feature_records":v["feature_records"],
    "overlap_pairs":v["cross_tile_intersection_pairs"],
    "strong_candidates":v["strong_duplicate_candidates"],
    "groups":len(v["candidate_groups"])} for k,v in results.items()},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
