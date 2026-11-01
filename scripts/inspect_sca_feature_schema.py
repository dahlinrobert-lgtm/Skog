#!/usr/bin/env python3
"""Decode SCA ownership and voluntary MVT schemas in two data-positive regional test areas."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests, mapbox_vector_tile

TEMPLATES={
 "sca_ownership":"https://olga.scaskog.com/map/sca_mark/{z}/{x}/{y}.pbf",
 "voluntary":"https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf",
}
SITES={"Solleftea":(17.27,63.17),"Lycksele":(18.67,64.60)}
ZOOMS=[9,11,13]

def xyz(lon,lat,z):
 n=2**z; x=int((lon+180)/360*n)
 lat=max(-85.05112878,min(85.05112878,lat))
 y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
 return x,y

def coord_summary(geometry):
 coords=geometry.get("coordinates") if geometry else None
 points=[]
 def walk(v):
  if isinstance(v,(list,tuple)):
   if len(v)>=2 and all(isinstance(x,(int,float)) for x in v[:2]): points.append((v[0],v[1]))
   else:
    for x in v: walk(x)
 walk(coords)
 if not points: return None
 return {"vertex_count":len(points),"tile_coord_bounds":[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]}

def decode(url):
 r=requests.get(url,timeout=30,headers={"User-Agent":"Skog-SCA-feature-schema-probe/1.0"})
 out={"status":r.status_code,"content_type":r.headers.get("Content-Type"),"bytes":len(r.content)}
 if r.status_code!=200:
  out["state"]="not_found_404" if r.status_code==404 else "http_error"
  return out
 try:
  decoded=mapbox_vector_tile.decode(r.content)
 except Exception as e:
  out.update(state="decode_error",error=str(e)[:240]); return out
 out["state"]="valid_mvt_empty" if not decoded or all(not v.get("features",[]) for v in decoded.values()) else "valid_mvt_with_features"
 out["layers"]=[]
 for name,layer in decoded.items():
  features=layer.get("features",[])
  geom_counts=Counter((f.get("geometry") or {}).get("type","unknown") for f in features)
  keys=sorted({k for f in features for k in (f.get("properties") or {})})
  samples=[]
  for f in features[:8]:
   props=f.get("properties") or {}
   samples.append({"id":f.get("id"),"properties":props,"geometry_type":(f.get("geometry") or {}).get("type"),"geometry_summary":coord_summary(f.get("geometry") or {})})
  out["layers"].append({"name":name,"extent":layer.get("extent"),"version":layer.get("version"),
    "feature_count":len(features),"geometry_types":dict(geom_counts),"property_keys":keys,
    "features_with_id":sum(f.get("id") is not None for f in features),"sample_features":samples})
 return out

def main():
 rows=[]
 for site,(lon,lat) in SITES.items():
  for z in ZOOMS:
   x,y=xyz(lon,lat,z)
   for key,t in TEMPLATES.items():
    url=t.format(z=z,x=x,y=y)
    rows.append({"site":site,"lon":lon,"lat":lat,"zoom":z,"x":x,"y":y,"layer":key,"url":url,"result":decode(url)})
 summary={}
 for key in TEMPLATES:
  rr=[x for x in rows if x["layer"]==key]
  summary[key]={state:sum(x["result"].get("state")==state for x in rr) for state in ["valid_mvt_with_features","valid_mvt_empty","not_found_404","http_error","decode_error"]}
 out={"purpose":"Inspect feature geometry, IDs and attributes for SCA-owned forest layer and voluntary set-aside layer in Sollefteå and Lycksele.",
 "sites":SITES,"zooms":ZOOMS,"summary":summary,"results":rows,
 "caveats":["Two regional point samples only; not a coverage estimate.","MVT feature IDs may be tile-local or generalized and are not assumed stable.","Tile coordinate bounds are in each MVT layer's local extent, not map coordinates.","No bulk download; 12 tile requests maximum."]}
 Path("sca-feature-schema-solleftea-lycksele.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
