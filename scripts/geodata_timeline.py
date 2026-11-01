#!/usr/bin/env python3
"""Weekly non-map change monitoring for Skogsdatalabbet Torvkarta and SIS."""
import hashlib, io, json, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, requests, tifffile
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/"config/area.json").read_text(encoding="utf-8"))
DATA=ROOT/"data"/"geodata_timeline"; SNAP=DATA/"snapshots"; SAMPLES=DATA/"samples"
USER=os.getenv("SKOGSSTYRELSEN_GEODATA_USERNAME",""); PASS=os.getenv("SKOGSSTYRELSEN_GEODATA_PASSWORD","")
WINDOW=1000; MAX_DIM=1024; TIMEOUT=(20,120)
SERVICES={
 "torvkarta":"https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/Torvkarta_1_0/ImageServer",
 "sis":"https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/SIS_1_0/ImageServer"}

def pixel_hash(a):
 a=np.ascontiguousarray(a); h=hashlib.sha256()
 h.update(str(a.shape).encode()); h.update(str(a.dtype).encode()); h.update(a.tobytes())
 return h.hexdigest()

def band_arrays(a):
 # ArcGIS TIFF samples are normally rows x columns x bands. A single-band
 # raster may be rows x columns; normalize it to rows x columns x 1.
 if a.ndim==2: return a[:,:,None]
 if a.ndim==3:
  if a.shape[-1] <= 16: return a
  if a.shape[0] <= 16: return np.moveaxis(a,0,-1)
 raise ValueError("Unsupported raster array dimensions")

def compare_arrays(current, previous, bbox, current_metadata=None, previous_metadata=None):
 cur=band_arrays(current); old=band_arrays(previous)
 if cur.shape != old.shape:
  return {"comparison_status":"incomparable_shape","previous_shape":list(old.shape),"current_shape":list(cur.shape)}
 height,width,bands=cur.shape
 xmin,ymin,xmax,ymax=bbox
 cell_x=(xmax-xmin)/width; cell_y=(ymax-ymin)/height
 results=[]
 for band in range(bands):
  a=cur[:,:,band]; b=old[:,:,band]
  valid=np.ones(a.shape,dtype=bool)
  if np.issubdtype(a.dtype,np.floating): valid &= np.isfinite(a)
  if np.issubdtype(b.dtype,np.floating): valid &= np.isfinite(b)
  for metadata, values in ((current_metadata,a),(previous_metadata,b)):
   if not metadata: continue
   nodata=metadata.get("no_data_values")
   if nodata is None and metadata.get("no_data_value") is not None: nodata=[metadata["no_data_value"]]
   if nodata is None: continue
   if not isinstance(nodata,(list,tuple)): nodata=[nodata]
   nd=nodata[band] if len(nodata)>band else nodata[0]
   if nd is not None:
    try: valid &= values != np.asarray(nd,dtype=values.dtype)
    except (TypeError,ValueError): pass
  changed=valid & (a!=b)
  count=int(changed.sum()); valid_count=int(valid.sum())
  item={"band_index":band+1,"valid_pixel_count":valid_count,"changed_pixel_count":count,
        "changed_percent":round(100*count/valid_count,6) if valid_count else None}
  if count:
   rows,cols=np.where(changed)
   item["changed_bbox_epsg3006"]={
    "xmin":round(xmin+int(cols.min())*cell_x,3),
    "xmax":round(xmin+(int(cols.max())+1)*cell_x,3),
    "ymin":round(ymax-(int(rows.max())+1)*cell_y,3),
    "ymax":round(ymax-int(rows.min())*cell_y,3)}
   dif=(a.astype(np.float64)-b.astype(np.float64))[changed]
   item["difference_min"]=float(dif.min()); item["difference_max"]=float(dif.max())
   item["difference_mean"]=round(float(dif.mean()),6)
  results.append(item)
 return {"comparison_status":"compared","bands":results}

def meta_subset(m):
 e=m.get("fullExtent") or m.get("extent") or {}; sr=e.get("spatialReference") or m.get("spatialReference") or {}
 return {"name":m.get("name"),"description":m.get("serviceDescription"),"pixel_type":m.get("pixelType"),
 "band_count":m.get("bandCount"),"pixel_size_x":m.get("pixelSizeX"),"pixel_size_y":m.get("pixelSizeY"),
 "wkid":sr.get("latestWkid") or sr.get("wkid"),"no_data_value":m.get("noDataValue"),"no_data_values":m.get("noDataValues"),
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
 if "tif" not in r.headers.get("Content-Type","").lower() and r.content[:4] not in (b"II*\\x00",b"MM\\x00*"):
  raise RuntimeError("exportImage did not return TIFF")
 with tifffile.TiffFile(io.BytesIO(r.content)) as tif: a=tif.asarray()
 if not a.size: raise RuntimeError("empty raster sample")
 ms=meta_subset(m)
 return a,{"service_key":key,"status":"ok","metadata":ms,
 "metadata_hash":hashlib.sha256(json.dumps(ms,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
 "pixel_hash":pixel_hash(a),"array_shape":list(a.shape),"array_dtype":str(a.dtype),
 "sample_bbox_epsg3006":bbox,"sample_window_metres":WINDOW,"requested_dimensions":[dim,dim],"http_status":200}

def previous(key):
 for p in sorted(SNAP.glob("*.json"),reverse=True):
  try: d=json.loads(p.read_text(encoding="utf-8"))
  except (OSError,ValueError): continue
  x=next((x for x in d.get("services",[]) if x.get("service_key")==key and x.get("status")=="ok"),None)
  if x:
   sample=SAMPLES/f"{d.get('snapshot_id')}_{key}.npz"
   return {"snapshot_id":d.get("snapshot_id"),"item":x,"sample_path":sample if sample.exists() else None}
 return None

def main():
 if not USER or not PASS: raise SystemExit("Required geodata account secrets are missing")
 now=datetime.now(timezone.utc); sid=now.strftime("%Y%m%dT%H%M%SZ"); bbox,centre=get_bbox()
 SNAP.mkdir(parents=True,exist_ok=True); SAMPLES.mkdir(parents=True,exist_ok=True)
 out={"snapshot_id":sid,"observed_at_utc":now.isoformat(),
 "purpose":"weekly information-flow change detection; not a map layer",
 "sample_area":{"name":CFG.get("name"),"centre_epsg3006":centre,"bbox_epsg3006":bbox,
 "width_metres":WINDOW,"height_metres":WINDOW},"services":[]}
 s=requests.Session(); s.auth=(USER,PASS); s.headers["User-Agent"]="Skog-geodata-timeline/1.1"
 for key,url in SERVICES.items():
  try:
   pixels,cur=fetch(s,key,url,bbox); old=previous(key)
   sample_path=SAMPLES/f"{sid}_{key}.npz"
   np.savez_compressed(sample_path,pixels=pixels)
   cur["sample_file"]=str(sample_path.relative_to(ROOT))
   if old is None:
    cur.update(change_status="baseline",previous_snapshot_id=None,
               changes=[],comparison_status="baseline_only_no_previous_pixel_array")
   else:
    old_item=old["item"]; changes=[]
    metadata_changed=cur["metadata_hash"]!=old_item.get("metadata_hash")
    pixel_hash_changed=cur["pixel_hash"]!=old_item.get("pixel_hash")
    if metadata_changed: changes.append("service_metadata_changed")
    if pixel_hash_changed: changes.append("sample_pixels_changed")
    same_grid=(cur["sample_bbox_epsg3006"]==old_item.get("sample_bbox_epsg3006")
               and cur["array_shape"]==old_item.get("array_shape")
               and cur["array_dtype"]==old_item.get("array_dtype"))
    if old["sample_path"] is not None and same_grid:
     with np.load(old["sample_path"],allow_pickle=False) as archive:
      previous_pixels=archive["pixels"]
     cur["pixel_comparison"]=compare_arrays(pixels,previous_pixels,bbox,cur.get("metadata"),old_item.get("metadata"))
    elif old["sample_path"] is None:
     cur["pixel_comparison"]={"comparison_status":"previous_array_unavailable",
                              "note":"Previous metadata/hash baseline exists but has no stored NPZ array."}
    else:
     cur["pixel_comparison"]={"comparison_status":"incomparable_grid",
                              "note":"Sample extent, dimensions or dtype changed; pixel-level difference is not calculated."}
    if cur["pixel_comparison"].get("comparison_status")=="compared":
     band_changed=any(b.get("changed_pixel_count",0)>0 for b in cur["pixel_comparison"].get("bands",[]))
     cur["pixel_content_changed"]=band_changed
    else:
     cur["pixel_content_changed"]=None
    cur.update(change_status="changed" if changes else "unchanged",
               previous_snapshot_id=old["snapshot_id"],changes=changes,
               metadata_changed=metadata_changed,pixel_hash_changed=pixel_hash_changed,
               comparable_grid=same_grid)
    if changes or cur["pixel_content_changed"] is True:
     event={"event_id":f"{key}:{sid}","observed_at_utc":now.isoformat(),"service_key":key,
     "event_type":"source_change_detected","previous_snapshot_id":old["snapshot_id"],"snapshot_id":sid,
     "changes":changes,"pixel_comparison":cur["pixel_comparison"],
     "note":"Observed difference between weekly samples; exact source edit time and cause are unknown."}
     with (DATA/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(event,ensure_ascii=False)+"\n")
  except Exception as exc: cur={"service_key":key,"status":"error","error_type":type(exc).__name__}
  out["services"].append(cur)
 (SNAP/f"{sid}.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 (DATA/"latest.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
 print(json.dumps({"snapshot_id":sid,"services":[{k:x.get(k) for k in ("service_key","status","change_status","changes","pixel_comparison","error_type")} for x in out["services"]]},ensure_ascii=False,indent=2))
 return int(any(x.get("status")!="ok" for x in out["services"]))
if __name__=="__main__": raise SystemExit(main())
