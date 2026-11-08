#!/usr/bin/env python3
"""Compare parent point-cluster coordinates with point features in positive z9 neighbours.

This is a correspondence diagnostic, not object identity resolution. It reports
nearest distances and source attributes without merging or deduplicating features.
"""
from __future__ import annotations
import argparse, hashlib, json, math, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import mapbox_vector_tile, requests
from requests.adapters import HTTPAdapter
from shapely.geometry import Point, shape
from shapely.ops import transform
from urllib3.util.retry import Retry

URL="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORLD=20037508.342789244
LOCAL=threading.local()

def tile_to_world(raw,extent,z,x,y):
    geom=shape(raw); span=2*WORLD/(2**z); ox=-WORLD+x*span; oy=WORLD-y*span
    # mapbox_vector_tile.decode defaults to y_coord_down=False and returns
    # tile-local coordinates with origin at bottom-left (Y increases up).
    # Convert from that local system to the XYZ tile's EPSG:3857 bounds.
    ymin=oy-span
    return transform(lambda a,b,zc=None:(ox+a*span/extent,ymin+b*span/extent),geom)

def session():
    if getattr(LOCAL,"session",None) is None:
        retry=Retry(total=3,connect=3,read=2,status=2,backoff_factor=.8,
                    status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
        s=requests.Session()
        s.headers["User-Agent"]="Skog-SCA-neighbour-point-correspondence/1.0"
        s.mount("https://",HTTPAdapter(max_retries=retry,pool_connections=4,pool_maxsize=4))
        LOCAL.session=s
    return LOCAL.session

def fetch_decode(tile):
    z,x,y=tile["z"],tile["x"],tile["y"]
    url=URL.format(z=z,x=x,y=y)
    try:
        r=session().get(url,timeout=(20,60))
        result={"z":z,"x":x,"y":y,"status":r.status_code,
                "sha256":hashlib.sha256(r.content).hexdigest() if r.content else None}
        if r.status_code!=200: return {**result,"state":"not_found_404" if r.status_code==404 else "http_error"}
        try:
            decoded=mapbox_vector_tile.decode(r.content)
            result.update(state="valid_mvt",decoded=decoded)
            return result
        except Exception as e: return {**result,"state":"decode_error","error":str(e)[:200]}
    except Exception as e: return {"z":z,"x":x,"y":y,"state":"request_error","error":str(e)[:200]}

def tile_fetch_args(key):
    """Convert a unique (z, x, y) key to the fetcher input shape."""
    z, x, y = key
    return {"z": z, "x": x, "y": y}


def run(input_path,out_path,workers=4):
    data=json.loads(Path(input_path).read_text(encoding="utf-8"))
    points=data.get("points",[])
    tiles=[t for t in data.get("tile_results",[])
           if t.get("z")==9 and t.get("state")=="valid_mvt_with_features"]
    unique={(t["z"],t["x"],t["y"]):(t["z"],t["x"],t["y"]) for t in tiles}
    decoded={}
    with ThreadPoolExecutor(max_workers=max(1,workers)) as pool:
        futures = {
            pool.submit(fetch_decode, tile_fetch_args(key)): key
            for key in unique.values()
        }
        for future in as_completed(futures):
            key=futures[future]
            try: decoded[key]=future.result()
            except Exception as e: decoded[key]={"z":key[0],"x":key[1],"y":key[2],"state":"worker_error","error":str(e)[:200]}
    output=[]
    for point in points:
        px=float(point["x_epsg3857"]); py=float(point["y_epsg3857"])
        candidates=[]
        for key,record in decoded.items():
            if record.get("state")!="valid_mvt": continue
            z,x,y=key
            for layer_name,layer in record.get("decoded",{}).items():
                extent=int(layer.get("extent") or 4096)
                for idx,feature in enumerate(layer.get("features",[])):
                    raw=feature.get("geometry")
                    if not raw: continue
                    try:
                        geom=tile_to_world(raw,extent,z,x,y)
                        distance=float(geom.distance(Point(px,py)))
                        candidates.append({"tile":{"z":z,"x":x,"y":y},"layer":layer_name,
                            "feature_index":idx,"mvt_id":feature.get("id"),
                            "properties":feature.get("properties") or {},
                            "geometry_type":geom.geom_type,"distance_m_epsg3857":distance,
                            "geometry_bounds_epsg3857":list(geom.bounds)})
                    except Exception: continue
        candidates.sort(key=lambda item:item["distance_m_epsg3857"])
        output.append({"source_point_id":point.get("point_id"),
            "source_child_z9":point.get("source_child_z9"),
            "source_layer":point.get("source_layer"),
            "source_properties":point.get("source_properties"),
            "source_coordinate_epsg3857":[px,py],
            "nearest_positive_neighbour_features":candidates[:10],
            "features_within_100m":sum(c["distance_m_epsg3857"]<=100 for c in candidates),
            "features_within_500m":sum(c["distance_m_epsg3857"]<=500 for c in candidates),
            "features_within_2000m":sum(c["distance_m_epsg3857"]<=2000 for c in candidates)})
    summary={"schema_version":1,"purpose":"Measure spatial proximity between parent point-cluster representations and features in positive z9 neighbour tiles.",
        "source_point_count":len(points),"positive_z9_neighbour_tiles":len(unique),
        "unique_neighbour_tiles_decoded":len(decoded),
        "tile_decode_states":{state:sum(1 for v in decoded.values() if v.get("state")==state)
                              for state in sorted({v.get("state") for v in decoded.values()})},
        "points":output,
        "interpretation_limits":["Distance is diagnostic in EPSG:3857, not a geodesic measurement.",
        "Nearest features are not declared to be the same source objects.",
        "Parent cluster coordinates may be generalized or displaced representations.",
        "No geometry is merged, dissolved, or identity-resolved."]}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:summary[k] for k in ("source_point_count","positive_z9_neighbour_tiles","unique_neighbour_tiles_decoded","tile_decode_states")},indent=2))
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="output/sca-cluster-point-targeted-probes.json")
    p.add_argument("--out",default="output/sca-neighbour-point-correspondence.json")
    p.add_argument("--workers",type=int,default=4)
    a=p.parse_args();run(a.input,a.out,a.workers)
if __name__=="__main__":main()
