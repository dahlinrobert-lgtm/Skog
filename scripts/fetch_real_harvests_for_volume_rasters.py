#!/usr/bin/env python3
"""Fetch reproducible real completed-harvest polygons within each committed volume-raster extent."""
from __future__ import annotations
import argparse, json, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
import requests
import rasterio

URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query"
FIELDS = "OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,Avvdatum,Arealha"
RASTER_CODES = ("07", "10", "13")
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "skogliga-grunddata"

def raster_extent(code):
 archive_path=DATA_DIR / f"sks_Volym_omdrev3_{code}.zip"
 with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory() as temp:
  members=[m for m in archive.namelist() if not m.endswith("/") and Path(m).suffix.lower() in {".tif",".tiff"}]
  if len(members)!=1: raise ValueError(f"{archive_path.name}: expected one TIFF, found {len(members)}")
  target=Path(temp)/Path(members[0]).name
  with archive.open(members[0]) as src,target.open("wb") as dst:
   while chunk:=src.read(1024*1024): dst.write(chunk)
  with rasterio.open(target) as ds:
   if ds.crs is None or ds.crs.to_epsg()!=3006: raise ValueError(f"Raster {code} expected EPSG:3006, got {ds.crs}")
   b=ds.bounds
   return {"xmin":b.left,"ymin":b.bottom,"xmax":b.right,"ymax":b.top,"spatialReference":{"wkid":3006}}

def fetch(code, extent, limit):
 params={"where":"1=1","geometry":json.dumps(extent,separators=(",",":")),
 "geometryType":"esriGeometryEnvelope","inSR":"3006","spatialRel":"esriSpatialRelIntersects",
 "outFields":FIELDS,"returnGeometry":"true","outSR":"4326","f":"geojson",
 "resultRecordCount":200,"resultOffset":0,"orderByFields":"OBJECTID ASC"}
 features=[]; offset=0; more=False
 while True:
  params["resultOffset"]=offset
  r=requests.get(URL,params=params,timeout=90,headers={"User-Agent":"Skogskoll-volume-attributes/1.0"})
  r.raise_for_status(); data=r.json()
  if data.get("error"): raise RuntimeError(f"Raster {code}: ArcGIS error {data['error']}")
  page=data.get("features")
  if not isinstance(page,list): raise RuntimeError(f"Raster {code}: missing feature list")
  more=more or bool(data.get("exceededTransferLimit"))
  features.extend(f for f in page if f.get("geometry"))
  offset+=len(page)
  print(f"Raster {code}: fetched {offset} features", flush=True)
  if not page or len(page)<params["resultRecordCount"] or (limit and len(features)>=limit): break
 if limit and len(features)>limit: features=features[:limit]
 return {"type":"FeatureCollection","name":f"real_completed_harvest_raster_{code}",
 "metadata":{"raster_code":code,"extent_epsg3006":extent,"source":URL,"source_layer":1,
 "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"count":len(features),
 "requested_limit":limit or "all","source_more_matching_features":more,
 "note":"Polygons intersecting the exact original raster extent; limit 0 means all returned features."},
 "features":features}

def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--limit",type=int,default=0,help="Maximum features per raster; 0 fetches all");p.add_argument("--raster-codes",default="07,10,13");a=p.parse_args()
 if a.limit<0: raise ValueError("--limit must be >= 0")
 codes=tuple(x.strip() for x in a.raster_codes.split(",") if x.strip())
 if not codes or any(x not in RASTER_CODES for x in codes): raise ValueError("--raster-codes must contain 07, 10 and/or 13")
 doc={"type":"FeatureCollection","name":"real_completed_harvest_polygons_by_volume_raster",
 "metadata":{"source":"Skogsstyrelsen öppna utförda avverkningar","note":"Features are grouped by raster coverage; polygons may occur in more than one raster group at raster boundaries.","generated_at_utc":datetime.now(timezone.utc).isoformat()},
 "raster_groups":[fetch(code,raster_extent(code),a.limit) for code in codes]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Fetched polygons by raster:",", ".join(f'{g["metadata"]["raster_code"]}={g["metadata"]["count"]}' for g in doc["raster_groups"]))
if __name__=="__main__": main()
