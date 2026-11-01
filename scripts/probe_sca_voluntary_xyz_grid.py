#!/usr/bin/env python3
"""Probe a bounded set of SCA voluntary-set-aside XYZ tiles at known Swedish locations."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests
import mapbox_vector_tile

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
PLACES={
    "Grasmyr":(19.66455,63.74646),
    "Umea":(20.2630,63.8258),
    "Sundsvall":(17.3069,62.3908),
    "Timra":(17.3250,62.4860),
}
ZOOMS=[4,5,7,9,12,15]
MAX_LAT=85.05112878

def xyz(lon,lat,z):
    lat=max(-MAX_LAT,min(MAX_LAT,lat))
    n=2**z
    x=int((lon+180.0)/360.0*n)
    lat_rad=math.radians(lat)
    y=int((1.0-math.asinh(math.tan(lat_rad))/math.pi)/2.0*n)
    return max(0,min(n-1,x)),max(0,min(n-1,y))

def main():
    s=requests.Session()
    s.headers.update({"User-Agent":"Skog-SCA-bounded-XYZ-grid-probe/1.0"})
    results=[]
    for place,(lon,lat) in PLACES.items():
        for z in ZOOMS:
            x,y=xyz(lon,lat,z)
            url=BASE.format(z=z,x=x,y=y)
            try:
                r=s.get(url,timeout=30)
                item={"place":place,"lon":lon,"lat":lat,"z":z,"x":x,"y":y,
                      "url":url,"status":r.status_code,
                      "content_type":r.headers.get("Content-Type"),
                      "bytes":len(r.content)}
                if r.status_code==200 and ("protobuf" in (r.headers.get("Content-Type") or "").lower() or r.content[:1]!=b"<"):
                    try:
                        decoded=mapbox_vector_tile.decode(r.content)
                        layers=[]
                        for name,layer in decoded.items():
                            feats=layer.get("features",[])
                            types=Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)
                            keys=sorted({k for f in feats for k in (f.get("properties") or {})})
                            layers.append({"name":name,"features":len(feats),"geometry_types":dict(types),"property_keys":keys})
                        item["decoded"]=True
                        item["layers"]=layers
                    except Exception as e:
                        item["decoded"]=False
                        item["decode_error"]=str(e)[:240]
                results.append(item)
            except Exception as e:
                results.append({"place":place,"z":z,"x":x,"y":y,"url":url,"error":str(e)[:240]})
    out={"source_template":BASE,"grid_hypothesis":"OpenLayers VectorTile default XYZ grid in default EPSG:3857 projection; tested by direct tile responses, not assumed proven by configuration alone","places":PLACES,"zooms":ZOOMS,"results":results,"request_count":len(results),"scope":"24 individual tile requests only; no bulk coverage collection"}
    Path("sca-voluntary-xyz-grid-probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
