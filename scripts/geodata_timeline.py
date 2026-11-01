#!/usr/bin/env python3
"""Weekly non-map change monitoring for Skogsdatalabbet Torvkarta and SIS."""
import hashlib, io, json, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, requests, tifffile
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config/area.json").read_text(encoding="utf-8"))
DATA=ROOT/"data"/"geodata_timeline"; SNAP=DATA/"snapshots"
USER=os.getenv("SKOGSSTYRELSEN_GEODATA_USERNAME","")
PASS=os.getenv("SKOGSSTYRELSEN_GEODATA_PASSWORD","")
WINDOW=1000; MAX_DIM=1024; TIMEOUT=(20,120)
SERVICES={
 "torvkarta":"https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/Torvkarta_1_0/ImageServer",
 "sis":"https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/SIS_1_0/ImageServer"}

def pixel_hash(a):
 a=np.ascontiguousarray(a); h=hashlib.sha256()
 h.update(str(a.shape).encode()); h.update(str(a.dtype).encode()); h.update(a.tobytes())
 return h.hexdigest()

def meta_subset(m):
 e=m.get("fullExtent") or m.get("extent") or {}; sr=e.get("spatialReference") or m.get("spatialReference") or {}
 return {"name":m.get("name"),"description":m.get("serviceDescription"),"pixel_type":m.get("pixelType"),
 "band_count":m.get("bandCount"),"pixel_size_x":m.get("pixelSizeX"),"pixel_size_y":m.get("pixelSizeY"),
 "wkid":sr.get("latestWkid") or sr.get("wkid"),
 "extent":{k:e.get(k) for k in ("xmin","ymin","xmax","ymax")} if e else None}

def get_bbox():
 t=Transformer.from_crs(4326,3006,always_xy=True); x,y=t.transform(CFG["longitude"],CFG["latitude"]); h=WINDOW/2
 return [x-h,y-h,x+h,y+h],[round(x,3),round(y,3)]

def fetch(session,key,url,bbox):
 r=session.get(url,params={"f":"json"},timeout=TIMEOUT); r.raise_for_status(); m=r.json()
 if m.get("error"): raise RuntimeError("ArcGIS metadata error")
 px=m.get("pixelSizeX") or m.get("pixelSizeY") or 4
 try: dim=max(1,min(MAX_DIM,round(WINDOW/abs(float(px)))))
 except (TypeError,ValueError,ZeroDivisionError): dim=250
 r=session.get(url+"/exportImage",params={"bbox":",".join(f"{v:.3f}" for v in bbox),
 "bboxSR":3006,"imageSR":3006,"size":f"{dim},{dim}","format":"tiff",
 "pixelType":m.get("pixelType","UNKNOWN"),"interpolation":"RSP_NearestNeighbor","f":"image"},timeout=TIMEOUT)
 r.raise_for_status()
 if "tif" not in r.headers.get("Content-Type","").lower() and r.content[:4] not in (b"II*\x00",b"MM\x00*"):
  raise RuntimeError("exportImage did not return TIFF")
 with tifffile.TiffFile(io.BytesIO(r.content)) as tif: a=tif.asarray()
 if not a.size: raise RuntimeError("empty raster sample")
 ms=meta_subset(m)
 return {"service_key":key,"status":"ok","metadata":ms,
 "metadata_hash":hashlib.sha256(json.dumps(ms,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
 "pixel_hash":pixel_hash(a),"array_shape":list(a.shape),"array_dtype":str(a.dtype),
 "sample_bbox_epsg3006":bbox,"sample_window_metres":WINDOW,"requested_dimensions":[dim,dim],"http_status":200}

def previous(key):
 for p in sorted(SNAP.glob("*.json"),reverse=True):
  try: d=json.loads(p.read_text(encoding="utf-8"))
  except (OSError,ValueError): continue
  x=next((x for x in d.get("services",[]) if x.get("service_key")==key and x.get("status")=="ok"),None)
  if x:return {"snapshot_id":d.get("snapshot_id"),**x}
 return None

def main():
 if not USER or not PASS: raise SystemExit("Required geodata account secrets are missing")
 now=datetime.now(timezone.utc); sid=now.strftime("%Y%m%dT%H%M%SZ"); bbox,centre=get_bbox(); SNAP.mkdir(parents=True,exist_ok=True)
 out={"snapshot_id":sid,"observed_at_utc":now.isoformat(),"purpose":"weekly information-flow change detection; not a map layer",
 "sample_area":{"name":CFG.get("name"),"centre_epsg3006":centre,"bbox_epsg3006":bbox,"width_metres":WINDOW,"height_metres":WINDOW},"services":[]}
 s=requests.Session(); s.auth=(USER,PASS); s.headers["User-Agent"]="Skog-geodata-timeline/1.0"
 for key,url in SERVICES.items():
  try:
   cur=fetch(s,key,url,bbox); old=previous(key)
   if old is None: cur.update(change_status="baseline",previous_snapshot_id=None)
   else:
    changes=[]
    if cur["metadata_hash"]!=old.get("metadata_hash"):changes.append("service_metadata_changed")
    if cur["pixel_hash"]!=old.get("pixel_hash"):changes.append("sample_pixels_changed")
    cur.update(change_status="changed" if changes else "unchanged",previous_snapshot_id=old.get("snapshot_id"),changes=changes)
    if changes:
     ev={"event_id":f"{key}:{sid}","observed_at_utc":now.isoformat(),"service_key":key,"event_type":"source_change_detected",
     "previous_snapshot_id":old.get("snapshot_id"),"snapshot_id":sid,"changes":changes,
     "previous_metadata_hash":old.get("metadata_hash"),"current_metadata_hash":cur["metadata_hash"],
     "previous_pixel_hash":old.get("pixel_hash"),"current_pixel_hash":cur["pixel_hash"],
     "note":"Difference observed between weekly samples; exact source edit time and cause are unknown."}
     with (DATA/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(ev,ensure_ascii=False)+"\n")
  except Exception as exc: cur={"service_key":key,"status":"error","error_type":type(exc).__name__}
  out["services"].append(cur)
 (SNAP/f"{sid}.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (DATA/"latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"snapshot_id":sid,"services":[{k:x.get(k) for k in ("service_key","status","change_status","changes","error_type")} for x in out["services"]]},ensure_ascii=False,indent=2))
 return int(any(x.get("status")!="ok" for x in out["services"]))
if __name__=="__main__": raise SystemExit(main())
