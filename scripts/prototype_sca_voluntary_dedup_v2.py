#!/usr/bin/env python3
"""Conservative SCA voluntary MVT cross-tile deduplication prototype v2.

All source feature geometries and source tile metadata are retained verbatim
in the artifact. Pair classification and candidate groups are diagnostics;
this workflow does not dissolve, discard, or overwrite source features.
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
ZOOM=12
RADIUS=4
STRONG_OVERLAP=0.80
MIN_INTERSECTION_M2=100.0
COMPAT_KEYS=("SKOTSEL_KL_resolved","MOTIV_resolved")

def xyz(lon,lat,z):
    n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
    return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def make_session():
    retry=Retry(total=3,connect=3,read=2,backoff_factor=1,
                status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
    s=requests.Session()
    s.headers.update({"User-Agent":"Skog-SCA-dedup-prototype/0.2"})
    s.mount("https://",HTTPAdapter(max_retries=retry))
    return s

def load_features(session,site,lon,lat):
    cx,cy=xyz(lon,lat,ZOOM)
    world=2*math.pi*6378137.0; span=world/(2**ZOOM)
    tiles=[]; features=[]
    for dy in range(-RADIUS,RADIUS+1):
      for dx in range(-RADIUS,RADIUS+1):
        x,y=cx+dx,cy+dy
        tile={"site":site,"z":ZOOM,"x":x,"y":y,"dx":dx,"dy":dy}
        try:
          r=session.get(BASE.format(z=ZOOM,x=x,y=y),timeout=(12,35))
          tile.update(http_status=r.status_code,bytes=len(r.content))
          if r.status_code==404: tile["state"]="not_found_404"
          elif r.status_code!=200: tile["state"]="http_error"
          else:
            decoded=mapbox_vector_tile.decode(r.content); tile["state"]="valid_mvt"
            count=0
            for layer_name,layer in decoded.items():
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
                  fid=f"{site}:{ZOOM}:{x}:{y}:{layer_name}:{idx}"
                  features.append({"feature_key":fid,"site":site,"tile":[x,y],
                    "layer":layer_name,"feature_index":idx,"mvt_id":f.get("id"),
                    "properties":props,"geometry":gm,"area_m2_3857":float(gm.area),
                    "geometry_sha256":hashlib.sha256(gm.normalize().wkb).hexdigest()})
                  count+=1
                except Exception as e:
                  tile.setdefault("geometry_errors",[]).append(str(e)[:160])
            tile["polygon_feature_records"]=count
        except Exception as e:
          tile.update(state="request_error",error=str(e)[:200])
        tiles.append(tile)
    return tiles,features

def classify_attributes(a,b):
    pa,pb=a["properties"],b["properties"]
    shared={k:(pa[k],pb[k]) for k in COMPAT_KEYS
            if pa.get(k) not in (None,"") and pb.get(k) not in (None,"")}
    matches=[k for k,(va,vb) in shared.items() if va==vb]
    conflicts=[k for k,(va,vb) in shared.items() if va!=vb]
    if conflicts: state="conflict"
    elif matches: state="compatible"
    else: state="unknown"
    return state,shared,matches,conflicts

def compare(features):
    pairs=[]
    for i,a in enumerate(features):
      for b in features[i+1:]:
        if a["tile"]==b["tile"]: continue
        dx=abs(a["tile"][0]-b["tile"][0]); dy=abs(a["tile"][1]-b["tile"][1])
        if dx>1 or dy>1: continue
        try: inter=a["geometry"].intersection(b["geometry"])
        except Exception as e: continue
        area=float(inter.area)
        if area<MIN_INTERSECTION_M2: continue
        smaller=min(a["area_m2_3857"],b["area_m2_3857"])
        ratio=area/smaller if smaller else 0.0
        attr_state,shared,matches,conflicts=classify_attributes(a,b)
        if ratio>=STRONG_OVERLAP and attr_state=="compatible":
          classification="same_object_candidate"
        elif ratio>=STRONG_OVERLAP:
          classification="needs_review"
        else:
          classification="partial_overlap"
        pairs.append({"feature_a":a["feature_key"],"feature_b":b["feature_key"],
          "tile_a":a["tile"],"tile_b":b["tile"],
          "intersection_m2_3857":area,"overlap_over_smaller":ratio,
          "area_a_m2_3857":a["area_m2_3857"],"area_b_m2_3857":b["area_m2_3857"],
          "attribute_state":attr_state,"shared_attributes":shared,
          "matching_attribute_keys":matches,"conflicting_attribute_keys":conflicts,
          "classification":classification,
          "geometry_hash_equal":a["geometry_sha256"]==b["geometry_sha256"]})
    # Connected components are generated only from strong pair candidates.
    by_key={f["feature_key"]:f for f in features}
    parent={k:k for k in by_key}
    def root(k):
      while parent[k]!=k:
        parent[k]=parent[parent[k]]; k=parent[k]
      return k
    for p in pairs:
      if p["classification"]=="same_object_candidate":
        ra,rb=root(p["feature_a"]),root(p["feature_b"])
        if ra!=rb: parent[rb]=ra
    groups=defaultdict(list)
    for k in by_key: groups[root(k)].append(k)
    candidates=[]
    for members in groups.values():
      if len(members)<2: continue
      member_set=set(members)
      edges=[p for p in pairs if p["classification"]=="same_object_candidate"
             and p["feature_a"] in member_set and p["feature_b"] in member_set]
      candidates.append({"candidate_group_id":"cand-"+hashlib.sha1("|".join(sorted(members)).encode()).hexdigest()[:12],
        "members":sorted(members),"edge_count":len(edges),
        "all_member_pairs_directly_linked":len(edges)==len(members)*(len(members)-1)//2,
        "edges":[{"a":p["feature_a"],"b":p["feature_b"],
          "overlap_over_smaller":p["overlap_over_smaller"],
          "intersection_m2_3857":p["intersection_m2_3857"]} for p in edges],
        "transitive_group_warning":"Connected membership does not prove every member is the same source object; inspect edges before merging."})
    return pairs,candidates

def main():
    session=make_session(); result={}
    for site,(lon,lat) in SITES.items():
      tiles,features=load_features(session,site,lon,lat)
      pairs,groups=compare(features)
      source_features=[{"feature_key":f["feature_key"],"site":f["site"],
        "tile":f["tile"],"layer":f["layer"],"feature_index":f["feature_index"],
        "mvt_id":f["mvt_id"],"properties":f["properties"],
        "area_m2_3857":f["area_m2_3857"],"geometry_sha256":f["geometry_sha256"],
        "geometry_epsg3857":mapping(f["geometry"])} for f in features]
      counts={c:sum(p["classification"]==c for p in pairs)
        for c in ("same_object_candidate","partial_overlap","needs_review")}
      result[site]={"tile_summary":{"total":len(tiles),
        "http_200":sum(t.get("http_status")==200 for t in tiles),
        "http_404":sum(t.get("http_status")==404 for t in tiles),
        "errors":sum(t.get("state") in ("http_error","request_error") for t in tiles)},
        "source_feature_count":len(source_features),"pair_classification_counts":counts,
        "candidate_group_count":len(groups),"candidate_groups":groups,
        "pairs":pairs,"source_features":source_features,"tile_requests":tiles}
    out={"purpose":"Conservative pairwise dedup prototype v2; no automatic geometry merge.",
      "zoom":ZOOM,"tile_radius":RADIUS,
      "thresholds":{"strong_overlap_over_smaller":STRONG_OVERLAP,
        "minimum_intersection_m2_3857":MIN_INTERSECTION_M2,
        "attribute_keys":list(COMPAT_KEYS)},
      "geometry_crs":"EPSG:3857 (diagnostic only; not official area)",
      "results":result,
      "rules":["same_object_candidate requires >=80% overlap of the smaller feature and at least one non-empty shared classification/motive field with equal values; any conflicting shared field prevents this label.",
        "partial_overlap is a material positive-area overlap that does not meet the strong candidate rule.",
        "needs_review is >=80% overlap but no non-empty shared classification/motive field is available.",
        "Intersections below 100 m2 in EPSG:3857 are omitted as likely minor numerical/buffer contacts; threshold is diagnostic.",
        "Only different immediately neighboring tiles are compared; same-tile and non-adjacent relationships are not tested.",
        "Original decoded features, properties, geometry and tile requests are retained; nothing is deleted or dissolved.",
        "Candidate groups are graph-connected components; all direct edges are reported and not assumed to imply universal identity.",
        "Only two 9x9 z12 neighborhoods are covered; no national conclusions."]}
    Path("sca-voluntary-dedup-prototype-v2.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:{"tiles":v["tile_summary"],"source_features":v["source_feature_count"],
      "pair_classification_counts":v["pair_classification_counts"],
      "candidate_groups":v["candidate_group_count"],
      "non_clique_groups":sum(not g["all_member_pairs_directly_linked"] for g in v["candidate_groups"])}
      for k,v in result.items()},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
