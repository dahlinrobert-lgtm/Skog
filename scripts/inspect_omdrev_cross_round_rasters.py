#!/usr/bin/env python3
"""Inspect and compare GeoTIFF metadata for matching volume tiles across Omdrev 1-3."""
from __future__ import annotations
import csv, json, math, tempfile, zipfile
from pathlib import Path
import rasterio

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"omdrev-cross-round-pilot"
OUT=ROOT/"raster-three-omdrev"/"cross_round_pilot"
ROUNDS=("1","2","3")
CODES=("12","21","23")

def inspect(path:Path)->dict:
 with tempfile.TemporaryDirectory(prefix="skog-omdrev-audit-") as tmp:
  with zipfile.ZipFile(path) as z:
   tifs=[x for x in z.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in {".tif",".tiff"}]
   if len(tifs)!=1: raise RuntimeError(f"{path.name}: expected exactly one TIFF, found {len(tifs)}")
   member=tifs[0]; local=Path(tmp)/Path(member.filename).name
   with z.open(member) as src,local.open("wb") as dst:
    while chunk:=src.read(1024*1024): dst.write(chunk)
  with rasterio.open(local) as ds:
   b=ds.bounds
   return {
    "archive":path.name,"tiff_member":member.filename,"archive_bytes":path.stat().st_size,
    "crs":ds.crs.to_string() if ds.crs else None,"epsg":ds.crs.to_epsg() if ds.crs else None,
    "width":ds.width,"height":ds.height,"band_count":ds.count,
    "dtypes":list(ds.dtypes),"nodatavals":list(ds.nodatavals),
    "res_x":float(ds.res[0]),"res_y":float(ds.res[1]),
    "transform":[float(x) for x in ds.transform[:6]],
    "bounds":{"xmin":float(b.left),"ymin":float(b.bottom),"xmax":float(b.right),"ymax":float(b.top)},
    "descriptions":list(ds.descriptions),"units":list(ds.units),
    "scales":list(ds.scales),"offsets":list(ds.offsets),
    "tags":ds.tags(),
    "band_tags":[ds.tags(i) for i in range(1,ds.count+1)],
   }

def same(a,b,tol=1e-8):
 return len(a)==len(b) and all(abs(x-y)<=tol for x,y in zip(a,b))

def main():
 rows=[]
 for r in ROUNDS:
  for c in CODES:
   p=DATA/f"sks_Volym_omdrev{r}_{c}.zip"
   if not p.is_file(): raise FileNotFoundError(p)
   x=inspect(p); x["survey_round"]=int(r); x["tile_code"]=c; rows.append(x)
 comparisons=[]
 for c in CODES:
  group={str(x["survey_round"]):x for x in rows if x["tile_code"]==c}
  for a,b in (("1","2"),("2","3"),("1","3")):
   x,y=group[a],group[b]
   comparisons.append({
    "tile_code":c,"round_a":int(a),"round_b":int(b),
    "same_crs":x["crs"]==y["crs"],"same_resolution":same([x["res_x"],x["res_y"]],[y["res_x"],y["res_y"]]),
    "same_transform":same(x["transform"],y["transform"]),
    "same_dimensions":[x["width"],x["height"]]==[y["width"],y["height"]],
    "same_bounds":same([x["bounds"][k] for k in ("xmin","ymin","xmax","ymax")],[y["bounds"][k] for k in ("xmin","ymin","xmax","ymax")]),
    "bands_a":x["band_count"],"bands_b":y["band_count"],
   })
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/"volume_raster_manifest.json").write_text(json.dumps({"purpose":"Metadata-only audit of nine matching volume raster archives","assets":rows,"grid_comparisons":comparisons},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 cols=["survey_round","tile_code","archive","archive_bytes","crs","epsg","width","height","band_count","dtypes","nodatavals","res_x","res_y","transform","bounds","descriptions","units","scales","offsets"]
 with (OUT/"volume_raster_manifest.csv").open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
  for x in rows:w.writerow({k:json.dumps(x[k],ensure_ascii=False) if isinstance(x.get(k),(list,dict)) else x.get(k) for k in cols})
 summary={
  "assets_inspected":len(rows),"rounds":list(map(int,ROUNDS)),"tile_codes":list(CODES),
  "all_epsg_3006":all(x["epsg"]==3006 for x in rows),
  "band_counts":{str(n):sum(x["band_count"]==n for x in rows) for n in sorted({x["band_count"] for x in rows})},
  "grid_comparisons":comparisons,
  "next_checks":[
   "If single-product GeoTIFFs contain one band, query the Skogsstyrelsen ImageServer UnixDay band separately.",
   "Only calculate cross-round pixel differences where CRS, resolution, pixel alignment and valid-data overlap are verified.",
   "Do not infer scan date from ZIP publication or download date."
  ]
 }
 (OUT/"volume_raster_audit_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":main()
