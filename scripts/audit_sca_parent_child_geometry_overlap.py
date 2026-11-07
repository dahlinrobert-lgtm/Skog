#!/usr/bin/env python3
"""Diagnostic: intersect positive z8 parent MVT geometries with sampled z9 404 children."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path
import mapbox_vector_tile, requests
from requests.adapters import HTTPAdapter
from shapely.geometry import box, shape
from shapely.ops import transform
from urllib3.util.retry import Retry

URL="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORLD=20037508.342789244
def tile_bounds(z,x,y):
    span=2*WORLD/(2**z); xmin=-WORLD+x*span; ymax=WORLD-y*span
    return xmin,ymax-span,xmin+span,ymax
def mvt_to_world(raw,extent,z,x,y):
    # mapbox_vector_tile.decode() defaults to y_coord_down=False and flips
    # MVT's screen-oriented y axis to a Cartesian y-up coordinate system.
    # Decoded local (0, 0) is therefore the tile's bottom-left, not top-left.
    geom=shape(raw); span=2*WORLD/(2**z); xmin,ymin,xmax,ymax=tile_bounds(z,x,y)
    return transform(lambda a,b,zc=None:(xmin+a*span/extent,ymin+b*span/extent),geom)
def intersect_child(geom,bounds):
    hit=geom.intersection(box(*bounds))
    if hit.is_empty: return None
    return {"intersection_type":hit.geom_type,"area_m2_epsg3857":float(hit.area),
            "length_m_epsg3857":float(hit.length),"bounds_epsg3857":list(hit.bounds)}
def run(audit_path,out_path):
    audit=json.loads(Path(audit_path).read_text(encoding="utf-8"))
    seeds=[s for s in audit.get("sampled_z9_seeds",[]) if s.get("class") in
           {"not_found_404_z9","ownership_positive_voluntary_404_z9"}]
    probes={(int(r["z"]),int(r["x"]),int(r["y"])):r for r in audit.get("probe_results",[])}
    candidates={}
    for seed in seeds:
        parent=(8,int(seed["x"])//2,int(seed["y"])//2)
        p=probes.get(parent)
        if p and p.get("state")=="valid_mvt_with_features":
            candidates[(int(seed["x"]),int(seed["y"]))]=(seed,parent)
    retry=Retry(total=3,connect=3,read=2,status=2,backoff_factor=1,
                status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
    sess=requests.Session(); sess.headers["User-Agent"]="Skog-SCA-parent-child-geometry-audit/1.0"
    sess.mount("https://",HTTPAdapter(max_retries=retry))
    cache={}; rows=[]
    for (cx,cy),(seed,(z,px,py)) in sorted(candidates.items()):
        key=(z,px,py)
        if key not in cache:
            url=URL.format(z=z,x=px,y=py)
            try:
                r=sess.get(url,timeout=(20,60))
                rec={"status":r.status_code,"url":url,"bytes":len(r.content),
                     "sha256":hashlib.sha256(r.content).hexdigest() if r.content else None}
                if r.status_code==200:
                    try: rec.update(state="valid_mvt",decoded=mapbox_vector_tile.decode(r.content))
                    except Exception as e: rec.update(state="decode_error",error=str(e)[:200])
                else: rec["state"]="not_found_404" if r.status_code==404 else "http_error"
                cache[key]=rec
            except Exception as e: cache[key]={"state":"request_error","error":str(e)[:200]}
        rec=cache[key]; bounds=tile_bounds(9,cx,cy); hits=[]; errors=[]
        for lname,layer in rec.get("decoded",{}).items():
            extent=int(layer.get("extent") or 4096)
            for i,f in enumerate(layer.get("features",[])):
                if not f.get("geometry"): continue
                try:
                    geom=mvt_to_world(f["geometry"],extent,z,px,py)
                    hit=intersect_child(geom,bounds)
                    if hit is not None:
                        hits.append({"layer":lname,"feature_index":i,"mvt_id":f.get("id"),
                                     "properties":f.get("properties") or {},
                                     "parent_geometry_type":geom.geom_type,**hit})
                except Exception as e: errors.append(str(e)[:160])
        rows.append({"child_z9":{"x":cx,"y":cy,"class":seed["class"],
                    "sampling_stratum":seed.get("sampling_stratum")},
            "parent_z8":{"x":px,"y":py,"state":rec["state"]},
            "parent_sha256":rec.get("sha256"),"parent_bytes":rec.get("bytes"),
            "child_bounds_epsg3857":list(bounds),"parent_layer_feature_counts":{
                n:len(v.get("features",[])) for n,v in rec.get("decoded",{}).items()},
            "feature_count_intersecting_child":len(hits),"intersections":hits,
            "geometry_errors":errors,
            "result":"parent_geometry_overlaps_z9_404_child" if hits else
                     "no_parent_geometry_overlap_in_child_core" if rec["state"]=="valid_mvt" else
                     "parent_geometry_unavailable"})
    counts=Counter(x["result"] for x in rows)
    out={"schema_version":1,"purpose":"Diagnostic spatial intersection of positive z8 parent MVT features with sampled z9 children returning 404.",
         "candidate_child_tiles":len(rows),"unique_parent_tiles_fetched":len(cache),
         "result_counts":dict(counts),"rows":rows,
         "limitations":["Parent geometry intersection is not proof that z9 endpoint should return a feature.",
         "MVT geometry may be generalized or buffered by zoom.","404 is unavailable/unknown, not proof of geographic absence.",
         "No geometries are merged, dissolved, or assigned global identity.","EPSG:3857 areas are diagnostic only."]}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("candidate_child_tiles","unique_parent_tiles_fetched","result_counts")},indent=2))
    return out
def main():
    p=argparse.ArgumentParser(); p.add_argument("--audit",default="output/sca-multizoom-coverage-audit.json")
    p.add_argument("--out",default="output/sca-parent-child-geometry-overlap.json"); a=p.parse_args()
    run(a.audit,a.out)
if __name__=="__main__": main()
