#!/usr/bin/env python3
"""Compare volume rasters across Omdrev 1/2/3 on an exact common 50 m grid.

The source rasters have 12.5 m cells in Omdrev 1 and 10 m cells in Omdrev 2/3.
Because their origins and bounds align, each 50 m output cell is an exact 4x4
or 5x5 block average. A block is valid only when every source pixel is valid;
this avoids silently treating NoData as zero or changing the support area.
"""
from __future__ import annotations
import json, os, tempfile, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import requests
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

DRIVE_ID = "FDA5CD345A37C354"
ITEMS = {
    "13": {
        "omdrev1": "FDA5CD345A37C354!sdb15fb674ddd418393936ad842e04756",
        "omdrev2": "FDA5CD345A37C354!s7ccd57e80b1a4a7ab4eb8e70b3042669",
        "omdrev3": "FDA5CD345A37C354!s1043b1d143e549b291ea228b102b81e8",
    },
    "21": {
        "omdrev1": "FDA5CD345A37C354!sb678a8aa934a4fddb270a9a62c7136a5",
        "omdrev2": "FDA5CD345A37C354!sb5bc592777ec4233a6458b68aa666380",
        "omdrev3": "FDA5CD345A37C354!s526b9a7e2484409ba34e90af3aacd216",
    },
    "23": {
        "omdrev1": "FDA5CD345A37C354!sdfdc85ba7c9f450dae0f0d0ef2df16d7",
        "omdrev2": "FDA5CD345A37C354!saf730934d0d743ab9aaa8b1c440b87d0",
        "omdrev3": "FDA5CD345A37C354!sef562c75df7f4ba2b19bb045b5e11620",
    },
}
EXPECTED = {
    "13": (250000, 6200000, 450000, 6400000),
    "21": (450000, 6650000, 700000, 6950000),
    "23": (300000, 6800000, 650000, 7250000),
}
NODATA = -1
OUT_RES = 50
def download(session, key, item_id, folder):
    r=session.get(f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item_id}",timeout=60)
    r.raise_for_status(); meta=r.json()
    if "file" not in meta: raise RuntimeError(f"{key}: Graph item is not a file")
    zpath=Path(folder)/(key+".zip")
    url=f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{meta['id']}/content"
    with session.get(url,stream=True,allow_redirects=True,timeout=(60,900)) as response:
        response.raise_for_status()
        with zpath.open("wb") as out:
            for chunk in response.iter_content(4*1024*1024):
                if chunk: out.write(chunk)
    with zipfile.ZipFile(zpath) as z:
        bad=z.testzip()
        if bad: raise RuntimeError(f"{key}: ZIP CRC failure: {bad}")
        tiffs=[x for x in z.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in (".tif",".tiff")]
        if len(tiffs)!=1: raise RuntimeError(f"{key}: expected exactly one TIFF, got {len(tiffs)}")
        path=Path(folder)/(key+".tif")
        with z.open(tiffs[0]) as src,path.open("wb") as dst:
            while chunk:=src.read(4*1024*1024): dst.write(chunk)
    return path, {"name":meta.get("name"),"zip_bytes":meta.get("size"),"tiff_member":tiffs[0].filename}
def inspect(path, label, area):
    with rasterio.open(path) as ds:
        bounds=(int(ds.bounds.left),int(ds.bounds.bottom),int(ds.bounds.right),int(ds.bounds.top))
        res=ds.res
        factor=4 if label=="omdrev1" else 5
        if ds.count!=1 or ds.crs.to_epsg()!=3006: raise RuntimeError(f"{area}/{label}: expected one band EPSG:3006")
        if ds.nodata is None or int(ds.nodata)!=NODATA: raise RuntimeError(f"{area}/{label}: unexpected NoData {ds.nodata}")
        if bounds!=EXPECTED[area]: raise RuntimeError(f"{area}/{label}: bounds {bounds} != expected {EXPECTED[area]}")
        if not (abs(res[0]-({1:12.5,2:10,3:10}[int(label[-1])]))<1e-8 and abs(res[1]-res[0])<1e-8):
            raise RuntimeError(f"{area}/{label}: unexpected resolution {res}")
        if ds.width%factor or ds.height%factor: raise RuntimeError(f"{area}/{label}: dimensions do not divide by {factor}")
        return {"width":ds.width,"height":ds.height,"bounds":list(bounds),"resolution":list(res),"dtype":ds.dtypes[0],"nodata":ds.nodata,"factor":factor}
def block_mean(arr, factor, nodata):
    h,w=arr.shape
    blocks=arr.reshape(h//factor,factor,w//factor,factor).transpose(0,2,1,3)
    valid=blocks!=nodata
    count=valid.sum(axis=(2,3))
    # Require a complete valid 50 m block: no partial coverage bias.
    sums=np.where(valid,blocks,0).astype(np.int64).sum(axis=(2,3))
    out=np.full(count.shape,np.nan,dtype=np.float32)
    ok=count==factor*factor
    out[ok]=(sums[ok]/(factor*factor)).astype(np.float32)
    return out,ok
def main():
    token_resp=requests.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
      data={"client_id":os.environ["ONEDRIVE_CLIENT_ID"],"grant_type":"refresh_token",
            "refresh_token":os.environ["ONEDRIVE_REFRESH_TOKEN"],"scope":"https://graph.microsoft.com/Files.Read offline_access"},timeout=60)
    token_resp.raise_for_status(); session=requests.Session()
    session.headers.update({"Authorization":"Bearer "+token_resp.json()["access_token"]})
    Path("raster-three-omdrev").mkdir(exist_ok=True)
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"common_grid_resolution_m":OUT_RES,
      "aggregation":"exact block mean (4x4 at 12.5m; 5x5 at 10m); output valid only if all source pixels in a block are valid",
      "difference_definition":"later omdrev minus earlier omdrev","areas":{}}
    with tempfile.TemporaryDirectory(prefix="skog-three-omdrev-") as tmp:
      for area,items in ITEMS.items():
        paths={}; source_meta={}; meta={}
        for label,item_id in items.items():
          key=f"area{area}_{label}"
          paths[label],source_meta[label]=download(session,key,item_id,tmp)
          meta[label]=inspect(paths[label],label,area)
          print(f"OK {key}: {meta[label]['width']}x{meta[label]['height']} at {meta[label]['resolution']}",flush=True)
        bounds=EXPECTED[area]; w=(bounds[2]-bounds[0])//OUT_RES; h=(bounds[3]-bounds[1])//OUT_RES
        arrays={}; masks={}
        for label,path in paths.items():
          factor=meta[label]["factor"]
          with rasterio.open(path) as ds:
            # Read in rows sized to keep memory use bounded; source height is divisible by factor.
            arr=np.empty((h,w),dtype=np.float32); mask=np.empty((h,w),dtype=bool)
            out_row=0; src_rows=factor*256
            for src_row in range(0,ds.height,src_rows):
              nh=min(src_rows,ds.height-src_row)
              raw=ds.read(1,window=Window(0,src_row,ds.width,nh))
              means,valid=block_mean(raw,factor,NODATA)
              n=means.shape[0]; arr[out_row:out_row+n]=means; mask[out_row:out_row+n]=valid
              out_row+=n
            arrays[label]=arr; masks[label]=mask
        profile={"driver":"GTiff","height":h,"width":w,"count":1,"dtype":"float32","crs":"EPSG:3006",
                 "transform":from_origin(bounds[0],bounds[3],OUT_RES,OUT_RES),"nodata":-9999.0,
                 "compress":"deflate","predictor":3,"tiled":True,"blockxsize":256,"blockysize":256}
        area_report={"bounds":list(bounds),"grid_width":w,"grid_height":h,"sources":meta,"comparisons":{}}
        for earlier,later in [("omdrev1","omdrev2"),("omdrev2","omdrev3"),("omdrev1","omdrev3")]:
          common=masks[earlier]&masks[later]
          n=int(common.sum())
          diff=arrays[later][common]-arrays[earlier][common]
          hist=Counter(np.rint(diff).astype(np.int32).tolist())
          # Stats are calculated on full-precision float block means, not rounded histogram values.
          cmp={"common_valid_cells":n,"common_valid_area_km2":n*OUT_RES*OUT_RES/1e6,
               "valid_earlier_cells":int(masks[earlier].sum()),"valid_later_cells":int(masks[later].sum()),
               "changed_cells":int(np.count_nonzero(diff)),"unchanged_cells":int(np.count_nonzero(diff==0)),
               "positive_cells":int(np.count_nonzero(diff>0)),"negative_cells":int(np.count_nonzero(diff<0)),
               "mean_difference":float(diff.mean()) if n else None,"median_difference":float(np.median(diff)) if n else None,
               "p10_difference":float(np.percentile(diff,10)) if n else None,"p90_difference":float(np.percentile(diff,90)) if n else None,
               "min_difference":float(diff.min()) if n else None,"max_difference":float(diff.max()) if n else None}
          area_report["comparisons"][f"{earlier}_to_{later}"]=cmp
          diff_arr=np.full((h,w),-9999.0,dtype=np.float32); diff_arr[common]=arrays[later][common]-arrays[earlier][common]
          out=Path("raster-three-omdrev")/f"area{area}_{earlier}_to_{later}_diff_50m.tif"
          with rasterio.open(out,"w",**profile) as dst:
            dst.write(diff_arr,1); dst.set_band_description(1,f"{later} minus {earlier}; block-mean difference at 50 m")
            dst.update_tags(AREA=area,EARLIER=earlier,LATER=later,RESAMPLING="Exact block mean",SOURCE_RESOLUTIONS="12.5m/10m",NODATA_POLICY="All source pixels in block must be valid")
        report["areas"][area]=area_report
    Path("raster-three-omdrev/report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__": main()
