#!/usr/bin/env python3
"""Diagnose SCA voluntary MVT tile availability around Gräsmyr at zoom 9-15."""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
import requests, mapbox_vector_tile

BASE="https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
CENTER=(19.66455,63.74646)
ZOOMS=[9,10,11,12,13,14,15]
OFFSETS=[(0,0),(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]

def xyz(lon,lat,z):
    n=2**z
    x=int((lon+180)/360*n)
    lat=max(-85.05112878,min(85.05112878,lat))
    y=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
    return x,y

def main():
    s=requests.Session()
    s.headers.update({"User-Agent":"Skog-SCA-bounded-zoom-availability/1.0"})
    results=[]
    for z in ZOOMS:
        cx,cy=xyz(*CENTER,z)
        for dx,dy in OFFSETS:
            x,y=cx+dx,cy+dy
            if x<0 or y<0 or x>=2**z or y>=2**z: continue
            url=BASE.format(z=z,x=x,y=y)
            try:
                r=s.get(url,timeout=25)
                item={"z":z,"x":x,"y":y,"dx":dx,"dy":dy,"status":r.status_code,
                      "content_type":r.headers.get("Content-Type"),"bytes":len(r.content)}
                if r.status_code==200:
                    try:
                        decoded=mapbox_vector_tile.decode(r.content)
                        item["decoded"]=True
                        item["layers"]=[]
                        for name,layer in decoded.items():
                            feats=layer.get("features",[])
                            geom=Counter((f.get("geometry") or {}).get("type","unknown") for f in feats)
                            item["layers"].append({"name":name,"features":len(feats),"geometry_types":dict(geom)})
                    except Exception as e:
                        item["decoded"]=False; item["decode_error"]=str(e)[:200]
                results.append(item)
            except Exception as e:
                results.append({"z":z,"x":x,"y":y,"error":str(e)[:200]})
    summary={}
    for z in ZOOMS:
        rows=[r for r in results if r.get("z")==z]
        summary[str(z)]={"tested":len(rows),"http_200":sum(r.get("status")==200 for r in rows),
                         "http_404":sum(r.get("status")==404 for r in rows),
                         "other":sum(r.get("status") not in (200,404) for r in rows)}
    out={"center_lon_lat":CENTER,"tile_template":BASE,"offsets":OFFSETS,"zooms":ZOOMS,
         "summary":summary,"results":results,
         "scope":"at most 63 individual tile requests around one point; not a coverage harvest"}
    Path("sca-voluntary-zoom-availability.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"summary":summary,"results":results},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
