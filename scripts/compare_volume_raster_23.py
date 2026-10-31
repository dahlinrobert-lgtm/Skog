#!/usr/bin/env python3
"""Exact, windowed pixel comparison of omdrev 2 and 3 raster 23."""
from __future__ import annotations
import json, os, tempfile, zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import requests
import numpy as np
import rasterio
from rasterio.windows import Window

DRIVE_ID = "FDA5CD345A37C354"
ITEMS = {
    "omdrev2_23": "FDA5CD345A37C354!saf730934d0d743ab9aaa8b1c440b87d0",
    "omdrev3_23": "FDA5CD345A37C354!sef562c75df7f4ba2b19bb045b5e11620",
}
def download_tiff(session, key, item_id, folder):
    meta=session.get(f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item_id}",timeout=60)
    meta.raise_for_status()
    item=meta.json()
    if "file" not in item: raise RuntimeError(f"{key}: OneDrive item is not a file")
    archive=Path(folder)/(key+".zip")
    url=f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item['id']}/content"
    with session.get(url,stream=True,allow_redirects=True,timeout=(60,900)) as response:
        response.raise_for_status()
        with archive.open("wb") as out:
            for chunk in response.iter_content(4*1024*1024):
                if chunk: out.write(chunk)
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad: raise RuntimeError(f"{key}: ZIP CRC failure in {bad}")
        members=[x for x in z.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in (".tif",".tiff")]
        if len(members)!=1: raise RuntimeError(f"{key}: expected one TIFF, found {len(members)}")
        tif=Path(folder)/(key+".tif")
        with z.open(members[0]) as src,tif.open("wb") as dst:
            while chunk:=src.read(4*1024*1024): dst.write(chunk)
    return tif, {"source_name":item.get("name"),"zip_size_bytes":item.get("size"),"tiff_member":members[0].filename,"tiff_size_bytes":members[0].file_size}
def percentile_from_hist(hist, total, q):
    target=max(1,int(np.ceil(total*q)))
    cumulative=0
    for value,count in sorted(hist.items()):
        cumulative+=count
        if cumulative>=target: return int(value)
    return None
def compare(a_path,b_path):
    with rasterio.open(a_path) as a, rasterio.open(b_path) as b:
        grid_a={"width":a.width,"height":a.height,"crs":a.crs.to_string() if a.crs else None,"transform":list(a.transform),"bounds":[a.bounds.left,a.bounds.bottom,a.bounds.right,a.bounds.top],"resolution":list(a.res),"dtype":a.dtypes[0],"nodata":a.nodata}
        grid_b={"width":b.width,"height":b.height,"crs":b.crs.to_string() if b.crs else None,"transform":list(b.transform),"bounds":[b.bounds.left,b.bounds.bottom,b.bounds.right,b.bounds.top],"resolution":list(b.res),"dtype":b.dtypes[0],"nodata":b.nodata}
        if grid_a!=grid_b: raise RuntimeError("Raster grids or storage types differ; refusing pixel-by-pixel comparison")
        if a.count!=1 or b.count!=1: raise RuntimeError("Expected one band in each raster")
        if a.nodata is None or b.nodata is None: raise RuntimeError("Both rasters must declare NoData")
        valid_a=valid_b=both=only_a=only_b=neither=0
        zeros_a=zeros_b=0
        changed=0; diff_sum=0; diff_sq=0; diff_min=None; diff_max=None
        hist=Counter(); rows_per_window=512
        for row in range(0,a.height,rows_per_window):
            h=min(rows_per_window,a.height-row); win=Window(0,row,a.width,h)
            x=a.read(1,window=win); y=b.read(1,window=win)
            vx=x!=a.nodata; vy=y!=b.nodata
            valid_a+=int(vx.sum()); valid_b+=int(vy.sum())
            both_mask=vx&vy; oa=vx&~vy; ob=~vx&vy; nn=~vx&~vy
            n=int(both_mask.sum()); both+=n; only_a+=int(oa.sum()); only_b+=int(ob.sum()); neither+=int(nn.sum())
            zeros_a+=int(((x==0)&vx).sum()); zeros_b+=int(((y==0)&vy).sum())
            if n:
                d=y[both_mask].astype(np.int32)-x[both_mask].astype(np.int32)
                changed+=int((d!=0).sum()); diff_sum+=int(d.sum()); diff_sq+=int(np.dot(d.astype(np.int64),d.astype(np.int64)))
                lo=int(d.min()); hi=int(d.max()); diff_min=lo if diff_min is None else min(diff_min,lo); diff_max=hi if diff_max is None else max(diff_max,hi)
                vals,counts=np.unique(d,return_counts=True)
                hist.update({int(v):int(c) for v,c in zip(vals,counts)})
        total=a.width*a.height
        mean=diff_sum/both if both else None
        variance=max(0,diff_sq/both-mean*mean) if both else None
        return {
            "grid":grid_a,"total_pixels":total,
            "valid_omdrev2":valid_a,"valid_omdrev3":valid_b,
            "valid_in_both":both,"valid_only_omdrev2":only_a,"valid_only_omdrev3":only_b,"nodata_in_both":neither,
            "valid_share_omdrev2":valid_a/total,"valid_share_omdrev3":valid_b/total,
            "zero_values_omdrev2":zeros_a,"zero_values_omdrev3":zeros_b,
            "changed_pixels":changed,"unchanged_pixels":both-changed,"changed_share_of_common_valid":changed/both if both else None,
            "difference_definition":"omdrev3 minus omdrev2; valid pixels only in both",
            "difference_min":diff_min,"difference_max":diff_max,"difference_mean":mean,
            "difference_std_population":variance**0.5 if variance is not None else None,
            "difference_median":percentile_from_hist(hist,both,0.5) if both else None,
            "difference_p90":percentile_from_hist(hist,both,0.9) if both else None,
            "difference_p10":percentile_from_hist(hist,both,0.1) if both else None,
        }
def main():
    token_resp=requests.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
      data={"client_id":os.environ["ONEDRIVE_CLIENT_ID"],"grant_type":"refresh_token",
            "refresh_token":os.environ["ONEDRIVE_REFRESH_TOKEN"],"scope":"https://graph.microsoft.com/Files.Read offline_access"},timeout=60)
    token_resp.raise_for_status(); token=token_resp.json()["access_token"]
    session=requests.Session(); session.headers.update({"Authorization":"Bearer "+token})
    Path("raster-comparison").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="skog-raster23-") as tmp:
        a,ma=download_tiff(session,"omdrev2_23",ITEMS["omdrev2_23"],tmp)
        print("Downloaded and extracted omdrev2_23",flush=True)
        b,mb=download_tiff(session,"omdrev3_23",ITEMS["omdrev3_23"],tmp)
        print("Downloaded and extracted omdrev3_23",flush=True)
        result=compare(a,b)
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"comparison":"omdrev2_23 vs omdrev3_23","sources":{"omdrev2_23":ma,"omdrev3_23":mb},"result":result}
    Path("raster-comparison/raster23-comparison.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__": main()
