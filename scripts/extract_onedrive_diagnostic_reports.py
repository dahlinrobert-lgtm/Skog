#!/usr/bin/env python3
"""Download a large private OneDrive diagnostic ZIP and extract only compact JSON reports."""
from __future__ import annotations
import json, os, tempfile, zipfile
from pathlib import Path
import requests

DRIVE_ID = "FDA5CD345A37C354"
ITEM_ID = "FDA5CD345A37C354!s6022642da76b433fa0d96f4407a83cf6"
OUT = Path("diagnostic-json")
MAX_JSON_BYTES = 50 * 1024 * 1024

def main():
    client_id=os.environ["ONEDRIVE_CLIENT_ID"]
    refresh_token=os.environ["ONEDRIVE_REFRESH_TOKEN"]
    token_response=requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data={"client_id":client_id,"grant_type":"refresh_token","refresh_token":refresh_token,
              "scope":"https://graph.microsoft.com/Files.Read offline_access"},timeout=60)
    if not token_response.ok:
        raise SystemExit(f"OneDrive OAuth refresh failed: HTTP {token_response.status_code} {token_response.text[:500]}")
    access_token=token_response.json().get("access_token")
    if not access_token: raise SystemExit("OAuth response contained no access token")
    session=requests.Session()
    session.headers.update({"Authorization":f"Bearer {access_token}","User-Agent":"Skogskoll-diagnostic-extractor/1.0"})
    meta=session.get(f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{ITEM_ID}",timeout=60)
    if not meta.ok: raise SystemExit(f"Could not resolve diagnostic ZIP: HTTP {meta.status_code} {meta.text[:500]}")
    item=meta.json()
    if "file" not in item: raise SystemExit("Configured OneDrive item is not a file")
    print(f"Source: {item.get('name')} ({item.get('size')} bytes)",flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="skog-diagnostic-") as tmp:
        archive=Path(tmp)/"diagnostic.zip"
        url=f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item['id']}/content"
        total=0
        with session.get(url,stream=True,allow_redirects=True,timeout=(60,300)) as response:
            if not response.ok: raise SystemExit(f"ZIP download failed: HTTP {response.status_code} {response.text[:500]}")
            with archive.open("wb") as f:
                for chunk in response.iter_content(4*1024*1024):
                    if chunk: f.write(chunk); total+=len(chunk)
        print(f"Downloaded {total} bytes to runner temporary storage",flush=True)
        extracted=[]
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            print(f"Archive entries: {len(infos)}",flush=True)
            for info in infos:
                name=Path(info.filename).name
                low=name.lower()
                if info.is_dir() or not low.endswith(".json"): continue
                if not any(k in low for k in ("raster-coverage","volume-report","metadata-outlier","diagnostic")): continue
                if info.file_size>MAX_JSON_BYTES:
                    print(f"SKIP oversized JSON {name}: {info.file_size} bytes",flush=True); continue
                target=OUT/name
                with z.open(info) as src,target.open("wb") as dst:
                    while chunk:=src.read(1024*1024): dst.write(chunk)
                extracted.append({"name":name,"bytes":info.file_size})
                print(f"Extracted {name}: {info.file_size} bytes",flush=True)
        manifest={"source_name":item.get("name"),"source_size_bytes":item.get("size"),
                  "archive_entry_count":len(infos),"extracted_json":extracted}
        (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if not extracted: raise SystemExit("No matching JSON reports found; inspect the archive listing in the workflow logs")
    print(f"Extracted {len(extracted)} JSON reports",flush=True)

if __name__=="__main__": main()
