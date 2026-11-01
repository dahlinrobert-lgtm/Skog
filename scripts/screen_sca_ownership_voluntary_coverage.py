#!/usr/bin/env python3
"""Compare SCA ownership tiles with voluntary set-aside tiles at stratified northern Sweden sample points."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests, mapbox_vector_tile

TEMPLATES={
 "sca_ownership":"https://olga.scaskog.com/map/sca_mark/{z}/{x}/{y}.pbf",
 "voluntary":"https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf",
}
# Regional screening points only, not asserted parcel locations or confirmed SCA properties.
SITES={
 "Galtstrom_Sundsvall":(17.45,62.22),
 "Solleftea":(17.27,63.17),
 "Ornskoldsvik":(18.72,63.29),
 "Umea":(20.26,63.83),
 "Lycksele":(18.67,64.60),
 "Pitea":(21.48,65.32),
 "Lulea":(22.15,65.58),
 "Haparanda":(24.14,65.84),
}
ZOOMS=[9,11]

def xyz(lon,lat,z):
 n=2**z; x=int((lon+180)/360*n)
 lat=max(-85.05112878,min(85.05112878,lat))
 y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
 return x,y

def decode_response(r):
 info={"status":r.status_code,"content_type":r.headers.get("Content-Type"),"bytes":len(r.content)}
 if r.status_code!=200: return info
 try:
  decoded=mapbox_vector_tile.decode(r.content)
  info["decoded"]=True; info["layers"]=[]
  for name,layer in decoded.items():
   feats=layer.get("features",[])
   geom=Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)
   props=sorted({k for f in feats for k in (f.get("properties") or {})})
   info["layers"].append({"name":name,"feature_count":len(feats),"geometry_types":dict(geom),"property_keys":props})
 except Exception as e:
  info["decoded"]=False; info["decode_error"]=str(e)[:200]
 return info

def main():
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-coverage-screen/1.0"})
 rows=[]
 for site,(lon,lat) in SITES.items():
  for z in ZOOMS:
   x,y=xyz(lon,lat,z)
   row={"site":site,"lon":lon,"lat":lat,"zoom":z,"x":x,"y":y,"tests":{}}
   for key,template in TEMPLATES.items():
    url=template.format(z=z,x=x,y=y)
    try:
     r=s.get(url,timeout=25); row["tests"][key]=decode_response(r)
    except Exception as e: row["tests"][key]={"error":str(e)[:200]}
   rows.append(row)
 out={"purpose":"Coverage-aware screening: test SCA ownership layer alongside voluntary-set-aside layer before interpreting voluntary 404s",
      "sites":SITES,"zooms":ZOOMS,"tile_templates":TEMPLATES,"results":rows,
      "caveats":["Regional points are screening locations, not verified SCA-owned parcels.","A tile with no ownership features does not prove no SCA land in the wider region.","A voluntary tile 404 is not equivalent to zero voluntary set-aside features.","No bulk download; 32 tile requests maximum."]}
 Path("sca-ownership-voluntary-coverage-screen.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
