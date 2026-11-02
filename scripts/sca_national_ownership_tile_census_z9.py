#!/usr/bin/env python3
"""Nationwide SCA ownership-led tile census (phase 1).

Enumerates XYZ tiles covering a broad Sweden bounding box at z9, queries the
public SCA ownership layer, and queries the voluntary-set-asides layer only
for tiles where ownership features are decoded. This is a coverage census,
not yet a complete polygon inventory: MVT features may be generalized,
clipped, buffered or absent at this zoom.
"""
from __future__ import annotations
import json, math, time
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

Z=9
BBOX={"west":10.5,"south":55.0,"east":24.5,"north":69.5}
OWN="https://olga.scaskog.com/map/sca_mark/{z}/{x}/{y}.pbf"
VOL="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORKERS=8
TIMEOUT=(10,30)

def xyz(lon,lat,z):
 n=2**z; lat=max(-85.05112878,min(85.05112878,lat))
 return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
def tile_range(b,z):
 x0,y1=xyz(b["west"],b["south"],z); x1,y0=xyz(b["east"],b["north"],z)
 n=2**z
 return [(x,y) for x in range(max(0,x0),min(n-1,x1)+1)
               for y in range(max(0,y0),min(n-1,y1)+1)]
def new_session():
 retry=Retry(total=2,connect=2,read=1,backoff_factor=.4,
  status_forcelist=[429,500,502,503,504],allowed_methods=["GET"])
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-national-tile-census/0.1",
  "Accept":"application/vnd.mapbox-vector-tile, application/x-protobuf, */*"})
 s.mount("https://",HTTPAdapter(max_retries=retry)); return s
def fetch_decode(session,url):
 try:
  r=session.get(url,timeout=TIMEOUT)
  base={"status":r.status_code,"bytes":len(r.content)}
  if r.status_code==404: return {**base,"state":"not_found_404","layers":[]}
  if r.status_code!=200: return {**base,"state":"http_error","layers":[]}
  try:
   dec=mapbox_vector_tile.decode(r.content); layers=[]
   for name,ly in dec.items():
    feats=ly.get("features",[])
    types=Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)
    keys=sorted({k for f in feats for k in (f.get("properties") or {})})
    layers.append({"name":name,"feature_count":len(feats),"geometry_types":dict(types),"property_keys":keys})
   n=sum(x["feature_count"] for x in layers)
   return {**base,"state":"valid_mvt_with_features" if n else "valid_mvt_empty","layers":layers}
  except Exception as e: return {**base,"state":"decode_error","error":str(e)[:180],"layers":[]}
 except Exception as e: return {"state":"request_error","error":str(e)[:180],"layers":[]}
def main():
 tiles=tile_range(BBOX,Z)
 # A worker-local session avoids sharing requests.Session across threads.
 def ownership_job(xy):
  x,y=xy; d=fetch_decode(new_session(),OWN.format(z=Z,x=x,y=y))
  n=sum(l["feature_count"] for l in d.get("layers",[]))
  return {"z":Z,"x":x,"y":y,"ownership":d,"ownership_feature_records":n}
 ownership=[]
 with ThreadPoolExecutor(max_workers=WORKERS) as ex:
  futs=[ex.submit(ownership_job,xy) for xy in tiles]
  for f in as_completed(futs): ownership.append(f.result())
 ownership.sort(key=lambda r:(r["x"],r["y"]))
 candidates=[r for r in ownership if r["ownership_feature_records"]>0]
 def voluntary_job(row):
  x,y=row["x"],row["y"]
  d=fetch_decode(new_session(),VOL.format(z=Z,x=x,y=y))
  n=sum(l["feature_count"] for l in d.get("layers",[]))
  return {"z":Z,"x":x,"y":y,"voluntary":d,"voluntary_feature_records":n}
 voluntary=[]
 with ThreadPoolExecutor(max_workers=WORKERS) as ex:
  futs=[ex.submit(voluntary_job,r) for r in candidates]
  for f in as_completed(futs): voluntary.append(f.result())
 voluntary.sort(key=lambda r:(r["x"],r["y"]))
 vmap={(r["x"],r["y"]):r for r in voluntary}
 joined=[]
 for r in ownership:
  v=vmap.get((r["x"],r["y"]))
  joined.append({**r,"voluntary":v["voluntary"] if v else None,
    "voluntary_feature_records":v["voluntary_feature_records"] if v else None,
    "voluntary_queried":v is not None})
 def counts(rows,key):
  return dict(Counter(r[key].get("state","unknown") for r in rows))
 summary={"bbox":BBOX,"zoom":Z,"tiles_in_bbox":len(tiles),
  "ownership_states":counts(ownership,"ownership"),
  "ownership_tiles_with_features":len(candidates),
  "ownership_feature_records":sum(r["ownership_feature_records"] for r in ownership),
  "voluntary_queries_on_ownership_tiles":len(voluntary),
  "voluntary_states":counts(voluntary,"voluntary"),
  "voluntary_tiles_with_features":sum(r["voluntary_feature_records"]>0 for r in voluntary),
  "voluntary_feature_records":sum(r["voluntary_feature_records"] for r in voluntary),
  "ownership_tiles_without_voluntary_features":sum(r["voluntary_feature_records"]==0 for r in voluntary)}
 out={"purpose":"Phase 1 national ownership-led SCA tile census at z9.",
  "source_layers":{"ownership":OWN,"voluntary":VOL},"summary":summary,
  "tile_results":joined,
  "interpretation":["A tile with ownership features is a candidate tile for detailed voluntary-layer collection.",
   "A 404 is unavailable/not published, not proof of no SCA land or no voluntary set-asides.",
   "Only decoded empty MVT means no features were returned for that layer/tile at z9.",
   "Feature counts are tile feature records, not unique parcels or unique voluntary areas.",
   "Voluntary layer queried only where ownership features were returned; edge and low-zoom omissions remain possible.",
   "This census covers a broad Sweden bounding box, including some non-Swedish land and sea; it is not a legal ownership boundary.",
   "No geometries are merged or deduplicated in this phase."]}
 Path("sca-national-ownership-tile-census-z9.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
