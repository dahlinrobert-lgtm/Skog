#!/usr/bin/env python3
"""Compare voluntary-area MVT geometries across neighboring tiles.

This is a diagnostic reconstruction test, not an authoritative feature-ID
recovery method. It looks for polygon overlap between different tile responses
in a local projected coordinate system and reports candidate cross-tile joins.
"""
from __future__ import annotations
import json, math, hashlib
from collections import defaultdict, Counter
from pathlib import Path
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape
from shapely.ops import transform, unary_union

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
SITES={"Lycksele":(18.67,64.60),"Solleftea":(17.27,63.17)}
ZOOM=12
OFFSETS=[(dx,dy) for dy in range(-2,3) for dx in range(-2,3)]

def xyz(lon,lat,z):
    n=2**z
    lat=max(-85.05112878,min(85.05112878,lat))
    return int((lon+180)/360*n), int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def session():
    retry=Retry(total=3,connect=3,read=2,backoff_factor=.8,
                status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
    s=requests.Session()
    s.headers.update({"User-Agent":"Skog-SCA-cross-tile-topology-audit/1.0"})
    s.mount("https://",HTTPAdapter(max_retries=retry))
    return s

def decode_site(s,site,lon,lat):
    cx,cy=xyz(lon,lat,ZOOM)
    rows=[]; features=[]
    world=2*math.pi*6378137.0
    span=world/(2**ZOOM)
    for dx,dy in OFFSETS:
        x,y=cx+dx,cy+dy
        row={"site":site,"tile":[x,y],"offset":[dx,dy],
             "url":BASE.format(z=ZOOM,x=x,y=y)}
        try:
            r=s.get(row["url"],timeout=(12,35))
            row.update(status=r.status_code,bytes=len(r.content))
            if r.status_code==404:
                row["state"]="not_found_404"
            elif r.status_code!=200:
                row["state"]="http_error"
            else:
                decoded=mapbox_vector_tile.decode(r.content)
                row["state"]="valid_mvt"
                count=0
                for lname,layer in decoded.items():
                    extent=layer.get("extent") or 4096
                    for idx,f in enumerate(layer.get("features",[])):
                        geom=f.get("geometry") or {}
                        try:
                            g=shape(geom)
                            if g.is_empty or g.geom_type not in ("Polygon","MultiPolygon"):
                                continue
                            ox=-world/2+x*span
                            oy=world/2-y*span
                            scale=span/extent
                            gm=transform(lambda a,b,z=None:(ox+a*scale,oy-b*scale),g)
                            if not gm.is_valid:
                                gm=gm.buffer(0)
                            if gm.is_empty: continue
                            features.append({
                                "site":site,"tile":[x,y],"offset":[dx,dy],
                                "feature_index":idx,"layer":lname,"mvt_id":f.get("id"),
                                "properties":f.get("properties") or {},
                                "geometry":gm,
                                "area_m2_3857":float(gm.area),
                                "geometry_hash":hashlib.sha256(gm.normalize().wkb).hexdigest()
                            })
                            count+=1
                        except Exception as e:
                            row.setdefault("geometry_errors",[]).append(str(e)[:160])
                row["feature_count"]=count
                row["layers"]=[{"name":k,"count":len(v.get("features",[]))} for k,v in decoded.items()]
        except Exception as e:
            row.update(state="request_error",error=str(e)[:200])
        rows.append(row)
    return rows,features

def analyze(site,features):
    # Only compare features from different neighboring tiles.
    # Positive-area intersections flag possible repeated/clipped source geometry.
    candidates=[]
    for i,a in enumerate(features):
        for b in features[i+1:]:
            if a["tile"]==b["tile"]: continue
            dx=abs(a["tile"][0]-b["tile"][0])
            dy=abs(a["tile"][1]-b["tile"][1])
            if dx>1 or dy>1: continue
            try:
                inter=a["geometry"].intersection(b["geometry"])
                area=float(inter.area)
            except Exception:
                continue
            if area>1.0:
                smaller=min(a["area_m2_3857"],b["area_m2_3857"])
                ratio=area/smaller if smaller>0 else 0
                candidates.append({
                    "tile_a":a["tile"],"index_a":a["feature_index"],
                    "tile_b":b["tile"],"index_b":b["feature_index"],
                    "intersection_m2_3857":area,
                    "intersection_over_smaller":ratio,
                    "area_a_m2_3857":a["area_m2_3857"],
                    "area_b_m2_3857":b["area_m2_3857"],
                    "properties_a":a["properties"],"properties_b":b["properties"],
                    "hash_equal":a["geometry_hash"]==b["geometry_hash"]
                })
    # Connected groups from any nontrivial overlaps; useful as candidate components.
    parent=list(range(len(features)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    for c in candidates:
        ia=next(i for i,f in enumerate(features) if f["tile"]==c["tile_a"] and f["feature_index"]==c["index_a"])
        ib=next(i for i,f in enumerate(features) if f["tile"]==c["tile_b"] and f["feature_index"]==c["index_b"])
        ra,rb=root(ia),root(ib)
        if ra!=rb: parent[rb]=ra
    groups=defaultdict(list)
    for i,f in enumerate(features): groups[root(i)].append(f)
    connected=[]
    for group in groups.values():
        if len(group)>1:
            connected.append({
                "member_count":len(group),
                "members":[{"tile":f["tile"],"feature_index":f["feature_index"],
                    "area_m2_3857":f["area_m2_3857"],"properties":f["properties"]} for f in group],
                "union_area_m2_3857":float(unary_union([f["geometry"] for f in group]).area),
                "sum_area_m2_3857":sum(f["area_m2_3857"] for f in group)
            })
    return candidates,connected

def main():
    s=session(); all_rows=[]; output={}
    for site,(lon,lat) in SITES.items():
        rows,fs=decode_site(s,site,lon,lat)
        candidates,groups=analyze(site,fs)
        all_rows.extend(rows)
        output[site]={
            "tile_summary":{
                "tiles_200":sum(r.get("status")==200 for r in rows),
                "tiles_404":sum(r.get("status")==404 for r in rows),
                "request_errors":sum(r.get("state")=="request_error" for r in rows)
            },
            "feature_records":len(fs),
            "features_touching_multiple_tiles_not_assumed":None,
            "cross_tile_overlap_pairs":len(candidates),
            "candidate_connected_groups":len(groups),
            "cross_tile_overlap_candidates":candidates,
            "candidate_groups":groups
        }
    out={
        "purpose":"Detect positive-area intersections among voluntary MVT polygon features in neighboring z12 tiles.",
        "zoom":ZOOM,"sites":SITES,"results":output,"tile_requests":all_rows,
        "interpretation_limits":[
            "A polygon overlap is a candidate relation, not proof that features represent the same source object.",
            "Overlaps can be caused by tile buffers, generalized geometries, or genuinely overlapping source polygons.",
            "No stable source ID is available in the tested MVT features.",
            "Areas are measured in EPSG:3857 and are diagnostic only, not official hectares.",
            "Only 5x5 neighborhoods around two reference points are tested."
        ]
    }
    Path("sca-voluntary-cross-tile-topology-audit.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps({k:{
        "tile_summary":v["tile_summary"],"feature_records":v["feature_records"],
        "cross_tile_overlap_pairs":v["cross_tile_overlap_pairs"],
        "candidate_connected_groups":v["candidate_connected_groups"]
    } for k,v in output.items()},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
