#!/usr/bin/env python3
"""Fetch reproducible real completed-harvest polygons within each committed volume-raster extent."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import requests

URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query"
FIELDS = "OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,Avvdatum,Arealha"
EXTENTS = {
 "07": {"xmin":350000,"ymin":6200000,"xmax":600000,"ymax":6350000,"spatialReference":{"wkid":3006}},
 "10": {"xmin":450000,"ymin":6150000,"xmax":600000,"ymax":6300000,"spatialReference":{"wkid":3006}},
 "13": {"xmin":250000,"ymin":6200000,"xmax":450000,"ymax":6400000,"spatialReference":{"wkid":3006}},
}
def fetch(code, extent, limit):
 params={"where":"1=1","geometry":json.dumps(extent,separators=(",",":")),
 "geometryType":"esriGeometryEnvelope","inSR":"3006","spatialRel":"esriSpatialRelIntersects",
 "outFields":FIELDS,"returnGeometry":"true","outSR":"4326","f":"geojson",
 "resultRecordCount":min(limit,200),"resultOffset":0,"orderByFields":"OBJECTID ASC"}
 features=[]; more=False; page_size=min(limit,200)
 for offset in range(0,limit,page_size):
  params["resultRecordCount"]=min(page_size,limit-offset);params["resultOffset"]=offset
  r=requests.get(URL,params=params,timeout=90,headers={"User-Agent":"Skogskoll-volume-attributes/1.0"})
  r.raise_for_status(); data=r.json()
  if data.get("error"): raise RuntimeError(f"Raster {code}: ArcGIS error {data['error']}")
  page=data.get("features")
  if not isinstance(page,list): raise RuntimeError(f"Raster {code}: missing feature list")
  more=more or bool(data.get("exceededTransferLimit"))
  features.extend(f for f in page if f.get("geometry"))
  if len(page)<params["resultRecordCount"]: break
 return {"type":"FeatureCollection","name":f"real_completed_harvest_raster_{code}",
 "metadata":{"raster_code":code,"extent_epsg3006":extent,"source":URL,"source_layer":1,
 "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"count":len(features),
 "requested_limit":limit,"source_more_matching_features":more,
 "note":"Reproducible sample for volume-analysis validation; not a complete inventory."},
 "features":features}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--limit",type=int,default=40);a=p.parse_args()
 if not 1<=a.limit<=2000: raise ValueError("--limit must be 1..2000")
 doc={"type":"FeatureCollection","name":"real_completed_harvest_polygons_by_volume_raster",
 "metadata":{"source":"Skogsstyrelsen öppna utförda avverkningar","note":"Features are grouped by raster coverage; polygons may occur in more than one raster group at raster boundaries.","generated_at_utc":datetime.now(timezone.utc).isoformat()},
 "raster_groups":[fetch(code,extent,a.limit) for code,extent in EXTENTS.items()]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Fetched polygons by raster:",", ".join(f'{g["metadata"]["raster_code"]}={g["metadata"]["count"]}' for g in doc["raster_groups"]))
if __name__=="__main__": main()
