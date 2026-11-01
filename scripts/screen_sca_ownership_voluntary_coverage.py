#!/usr/bin/env python3
"""Coverage-aware SCA tile screen with explicit distinctions between 404, empty MVT and features."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests, mapbox_vector_tile

TEMPLATES={
 "sca_ownership":"https://olga.scaskog.com/map/sca_mark/{z}/{x}/{y}.pbf",
 "voluntary":"https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf",
}
SITES={
 "Galtstrom_Sundsvall":(17.45,62.22),"Solleftea":(17.27,63.17),
 "Ornskoldsvik":(18.72,63.29),"Umea":(20.26,63.83),
 "Lycksele":(18.67,64.60),"Pitea":(21.48,65.32),
 "Lulea":(22.15,65.58),"Haparanda":(24.14,65.84),
}
ZOOMS=[9,11]

def xyz(lon,lat,z):
 n=2**z; x=int((lon+180)/360*n)
 lat=max(-85.05112878,min(85.05112878,lat))
 y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
 return x,y

def decode_response(r):
 info={"status":r.status_code,"content_type":r.headers.get("Content-Type"),"bytes":len(r.content)}
 if r.status_code==404:
  info["state"]="not_found_404"; return info
 if r.status_code!=200:
  info["state"]="http_error"; return info
 try:
  decoded=mapbox_vector_tile.decode(r.content)
  info["decoded"]=True
  info["state"]="valid_mvt_empty" if not decoded or all(not layer.get("features",[]) for layer in decoded.values()) else "valid_mvt_with_features"
  info["layers"]=[]
  for name,layer in decoded.items():
   feats=layer.get("features",[])
   geom=Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)
   props=sorted({k for f in feats for k in (f.get("properties") or {})})
   samples={}
   for f in feats[:3]:
    for k,v in (f.get("properties") or {}).items():
     samples.setdefault(k,[])
     if v not in samples[k] and len(samples[k])<3: samples[k].append(v)
   info["layers"].append({"name":name,"feature_count":len(feats),"geometry_types":dict(geom),"property_keys":props,"sample_values":samples})
 except Exception as e:
  info["decoded"]=False; info["state"]="decode_error"; info["decode_error"]=str(e)[:200]
 return info

def main():
 s=requests.Session(); s.headers.update({"User-Agent":"Skog-SCA-coverage-screen/2.0"})
 rows=[]
 for site,(lon,lat) in SITES.items():
  for z in ZOOMS:
   x,y=xyz(lon,lat,z)
   row={"site":site,"lon":lon,"lat":lat,"zoom":z,"x":x,"y":y,"tests":{}}
   for key,template in TEMPLATES.items():
    try:
     r=s.get(template.format(z=z,x=x,y=y),timeout=25)
     row["tests"][key]=decode_response(r)
    except Exception as e: row["tests"][key]={"state":"request_error","error":str(e)[:200]}
   rows.append(row)
 summary={}
 for layer in TEMPLATES:
  summary[layer]={state:sum(row["tests"].get(layer,{}).get("state")==state for row in rows)
                  for state in ["valid_mvt_with_features","valid_mvt_empty","not_found_404","http_error","decode_error","request_error"]}
 out={"purpose":"Compare the public ownership and voluntary layers at 8 regional screening points and 2 zoom levels.",
      "interpretation":"A 404 is unavailable tile response, not proof of zero features. Only a successfully decoded MVT with zero features is classified as valid_mvt_empty.",
      "sites":SITES,"zooms":ZOOMS,"tile_templates":TEMPLATES,"summary":summary,"results":rows,
      "caveats":["Points are not verified SCA-owned parcels; this is not an ownership coverage estimate.","A tile without ownership features cannot prove absence of SCA land beyond that tile.","No bulk download; 32 individual tile requests maximum."]}
 Path("sca-ownership-voluntary-coverage-screen.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"summary":summary,"results":rows},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
