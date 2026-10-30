#!/usr/bin/env python3
"""Download and inventory selected private OneDrive volume-raster ZIPs without modifying source files."""
from __future__ import annotations
import hashlib, json, os, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
import requests
import rasterio

DRIVE_ID = "FDA5CD345A37C354"
ITEMS = {
    "omdrev2_01": "FDA5CD345A37C354!sb15f8df0832541ee970a797220e1dd9c",
    "omdrev2_03": "FDA5CD345A37C354!s232671cbd4ed43dfbb5bb4de7d75ab3f",
    "omdrev2_05": "FDA5CD345A37C354!se88f3496a5c84a9f919469a2c5859ff4",
    "omdrev2_06": "FDA5CD345A37C354!sb2ce70d793344425b7c682c81d8f497e",
    "omdrev2_10": "FDA5CD345A37C354!sf16672efd8134bf7bbe1142ee798ec12",
    "omdrev2_13": "FDA5CD345A37C354!s7ccd57e80b1a4a7ab4eb8e70b3042669",
    "omdrev2_21": "FDA5CD345A37C354!sb5bc592777ec4233a6458b68aa666380",
    "omdrev2_23": "FDA5CD345A37C354!saf730934d0d743ab9aaa8b1c440b87d0",
    "omdrev3_07": "FDA5CD345A37C354!sdc72ca667c7446538bb62f85d8e98895",
    "omdrev3_10": "FDA5CD345A37C354!s4d697f8d870f4b5f854c87aab15ad80a",
    "omdrev3_12": "FDA5CD345A37C354!s54aeac4e38e74c73a2dc743948312fe9",
    "omdrev3_13": "FDA5CD345A37C354!s1043b1d143e549b291ea228b102b81e8",
    "omdrev3_21": "FDA5CD345A37C354!s526b9a7e2484409ba34e90af3aacd216",
    "omdrev3_22": "FDA5CD345A37C354!s50c302d083804adab37e758d70815537",
    "omdrev3_23": "FDA5CD345A37C354!sef562c75df7f4ba2b19bb045b5e11620",
    "omdrev3_24": "FDA5CD345A37C354!s93986bbcf1cd440ea7d28c4dace4cffc",
    "omdrev3_25": "FDA5CD345A37C354!s25fc875486ce42698717a91cad7d825d",
}
def raster_info(path):
    with rasterio.open(path) as ds:
        return {
            "width": ds.width, "height": ds.height, "bands": ds.count,
            "crs": ds.crs.to_string() if ds.crs else None,
            "bounds": [ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top],
            "resolution": list(ds.res), "transform": list(ds.transform),
            "dtype": list(ds.dtypes), "nodata": list(ds.nodatavals),
            "block_shapes": [list(x) for x in ds.block_shapes],
            "compression": [str(x) if x else None for x in ds.compression],
            "overviews": [ds.overviews(i) for i in range(1, ds.count + 1)],
            "units": list(ds.units), "scales": list(ds.scales), "offsets": list(ds.offsets),
            "descriptions": list(ds.descriptions), "dataset_tags": ds.tags(),
            "band_tags": [ds.tags(i) for i in range(1, ds.count + 1)],
        }
def main():
    selected=[x.strip() for x in os.getenv("RASTER_KEYS", ",".join(ITEMS)).split(",") if x.strip()]
    unknown=sorted(set(selected)-set(ITEMS))
    if unknown: raise SystemExit("Unknown raster key(s): "+", ".join(unknown))
    client=os.environ["ONEDRIVE_CLIENT_ID"]; refresh=os.environ["ONEDRIVE_REFRESH_TOKEN"]
    tr=requests.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data={"client_id":client,"grant_type":"refresh_token","refresh_token":refresh,
              "scope":"https://graph.microsoft.com/Files.Read offline_access"},timeout=60)
    if not tr.ok: raise SystemExit(f"OAuth refresh failed: HTTP {tr.status_code} {tr.text[:400]}")
    token=tr.json().get("access_token")
    if not token: raise SystemExit("OAuth response did not contain access_token")
    s=requests.Session(); s.headers.update({"Authorization":f"Bearer {token}","User-Agent":"Skogskoll-raster-inventory/1.0"})
    results=[]
    with tempfile.TemporaryDirectory(prefix="skog-raster-inventory-") as tmp:
      for key in selected:
        row={"key":key,"status":"started"}
        try:
          meta=s.get(f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{ITEMS[key]}",timeout=60)
          if not meta.ok: raise RuntimeError(f"Graph metadata HTTP {meta.status_code}: {meta.text[:300]}")
          item=meta.json(); row.update({"source_name":item.get("name"),"onedrive_size_bytes":item.get("size")})
          if "file" not in item: raise RuntimeError("Graph item is not a file")
          archive=Path(tmp)/(key+".zip"); digest=hashlib.sha256(); downloaded=0
          url=f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item['id']}/content"
          with s.get(url,stream=True,allow_redirects=True,timeout=(60,600)) as response:
            if not response.ok: raise RuntimeError(f"Download HTTP {response.status_code}: {response.text[:300]}")
            with archive.open("wb") as out:
              for chunk in response.iter_content(4*1024*1024):
                if chunk: out.write(chunk); digest.update(chunk); downloaded+=len(chunk)
          row.update({"downloaded_bytes":downloaded,"sha256":digest.hexdigest()})
          with zipfile.ZipFile(archive) as z:
            bad=z.testzip()
            if bad: raise RuntimeError(f"ZIP CRC failure in member {bad}")
            tiffs=[x for x in z.infolist() if not x.is_dir() and Path(x.filename).suffix.lower() in (".tif",".tiff")]
            row["zip_members"]=[{"name":x.filename,"size_bytes":x.file_size,"compressed_bytes":x.compress_size} for x in z.infolist() if not x.is_dir()]
            if len(tiffs)!=1: raise RuntimeError(f"Expected exactly one TIFF; found {len(tiffs)}")
            tif=Path(tmp)/(key+".tif")
            with z.open(tiffs[0]) as src,tif.open("wb") as dst:
              while chunk:=src.read(4*1024*1024): dst.write(chunk)
          row["tiff"]=raster_info(tif)
          row["status"]="ok"
          print(f"OK {key}: {downloaded} bytes, {row['tiff']['width']}x{row['tiff']['height']}, {row['tiff']['crs']}",flush=True)
        except Exception as exc:
          row.update({"status":"error","error":str(exc)})
          print(f"ERROR {key}: {exc}",flush=True)
        results.append(row)
    Path("raster-inventory").mkdir(exist_ok=True)
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"selected_count":len(selected),
            "success_count":sum(x["status"]=="ok" for x in results),"error_count":sum(x["status"]!="ok" for x in results),
            "rasters":results}
    Path("raster-inventory/inventory.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if report["error_count"]: raise SystemExit(f"{report['error_count']} raster(s) failed inventory; see artifact/logs")
if __name__=="__main__": main()
