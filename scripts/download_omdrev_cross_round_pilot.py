#!/usr/bin/env python3
"""Download a small, identical-tile volume raster sample from Omdrev 1-3."""
from __future__ import annotations
import hashlib, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "omdrev-cross-round-pilot"
DRIVE = "FDA5CD345A37C354"
ITEMS = {
 "1": {
  "12":"FDA5CD345A37C354!s0b77a785d3d74dd9bc01393897ca24e4",
  "21":"FDA5CD345A37C354!sb678a8aa934a4fddb270a9a62c7136a5",
  "23":"FDA5CD345A37C354!sdfdc85ba7c9f450dae0f0d0ef2df16d7",
 },
 "2": {
  "12":"FDA5CD345A37C354!s83141868918049daa7a5b66273e8977c",
  "21":"FDA5CD345A37C354!sb5bc592777ec4233a6458b68aa666380",
  "23":"FDA5CD345A37C354!saf730934d0d743ab9aaa8b1c440b87d0",
 },
 "3": {
  "12":"FDA5CD345A37C354!s54aeac4e38e74c73a2dc743948312fe9",
  "21":"FDA5CD345A37C354!s526b9a7e2484409ba34e90af3aacd216",
  "23":"FDA5CD345A37C354!sef562c75df7f4ba2b19bb045b5e11620",
 },
}

def main():
 rounds=[x.strip() for x in os.getenv("RASTER_ROUNDS","1,2,3").split(",") if x.strip()]
 codes=[x.strip() for x in os.getenv("RASTER_CODES","12,21,23").split(",") if x.strip()]
 invalid=[f"{r}:{c}" for r in rounds for c in codes if r not in ITEMS or c not in ITEMS[r]]
 if invalid: raise SystemExit("No OneDrive item mapping: "+", ".join(invalid))
 client=os.getenv("ONEDRIVE_CLIENT_ID","")
 refresh=os.getenv("ONEDRIVE_REFRESH_TOKEN","")
 if not client or not refresh: raise SystemExit("Missing ONEDRIVE_CLIENT_ID / ONEDRIVE_REFRESH_TOKEN")
 token_response=requests.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token",data={
  "client_id":client,"grant_type":"refresh_token","refresh_token":refresh,
  "scope":"https://graph.microsoft.com/Files.Read offline_access"},timeout=60)
 token_response.raise_for_status()
 token=token_response.json().get("access_token")
 if not token: raise SystemExit("OAuth response did not contain access_token")
 session=requests.Session()
 session.headers.update({"Authorization":f"Bearer {token}","User-Agent":"Skogskoll-omdrev-cross-round-audit/1.0"})
 DATA.mkdir(parents=True,exist_ok=True)
 for round_id in rounds:
  for code in codes:
   target=DATA/f"sks_Volym_omdrev{round_id}_{code}.zip"
   if target.exists() and target.stat().st_size>1024:
    print(f"Already downloaded: {target.name} ({target.stat().st_size} bytes)",flush=True); continue
   item_id=ITEMS[round_id][code]
   meta=session.get(f"https://graph.microsoft.com/v1.0/drives/{DRIVE}/items/{item_id}",timeout=60)
   meta.raise_for_status()
   item=meta.json()
   expected=f"sks_Volym_omdrev{round_id}_{code}.zip"
   if item.get("name") != expected or "file" not in item:
    raise RuntimeError(f"Unexpected OneDrive item for {round_id}/{code}: {item.get('name')!r}")
   tmp=target.with_suffix(".zip.part")
   digest=hashlib.sha256(); size=0
   with session.get(f"https://graph.microsoft.com/v1.0/drives/{DRIVE}/items/{item_id}/content",stream=True,allow_redirects=True,timeout=(60,300)) as response:
    response.raise_for_status()
    with tmp.open("wb") as out:
     for chunk in response.iter_content(1024*1024):
      if chunk: out.write(chunk); digest.update(chunk); size+=len(chunk)
   if size != item.get("size"):
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"Size mismatch for {expected}: downloaded {size}, Graph says {item.get('size')}")
   tmp.replace(target)
   print(f"Downloaded {expected}: {size} bytes sha256={digest.hexdigest()}",flush=True)

if __name__=="__main__": main()
