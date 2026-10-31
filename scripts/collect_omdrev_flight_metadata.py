#!/usr/bin/env python3
"""Collect Skogsstyrelsen 2.5 km laser-scan metadata for raster extents."""
from __future__ import annotations
import csv, json, re, time
from pathlib import Path
import requests

LAYER = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0"
AREAS = {"13":(250000,6200000,450000,6400000),"21":(450000,6650000,700000,6950000),"23":(300000,6800000,650000,7250000)}
OUT=Path("raster-three-omdrev/flight_metadata")
def getj(s,url,p):
    r=s.get(url,params=p,timeout=120); r.raise_for_status(); d=r.json()
    if "error" in d: raise RuntimeError(json.dumps(d["error"],ensure_ascii=False))
    return d
def main():
    OUT.mkdir(parents=True,exist_ok=True); s=requests.Session()
    s.headers["User-Agent"]="Skogskoll-flight-metadata/1.1"
    layer=getj(s,LAYER,{"f":"json"}); defs=layer.get("fields",[]); fields=[x["name"] for x in defs]
    if not fields: raise RuntimeError("ArcGIS layer metadata returned no fields")
    lookup={x.lower():x for x in fields}
    candidates={"index_tile":["Indexruta"],"scan_file":["LasNamn","Las_Namn"],"scan_date":["datum","Datum"],"leaf_status":["Lov_Avlov"]}
    mapping={k:next((lookup[n.lower()] for n in v if n.lower() in lookup),None) for k,v in candidates.items()}
    if not mapping["index_tile"] or not mapping["scan_date"]:
        raise RuntimeError(f"Required fields missing. Mapping={mapping}; available={fields}")
    oid_field=layer.get("objectIdField") or next((x["name"] for x in defs if x.get("type")=="esriFieldTypeOID"),None)
    if not oid_field: raise RuntimeError("Could not identify object ID field")
    feats={}; memberships={}
    for area,(xmin,ymin,xmax,ymax) in AREAS.items():
        ids=getj(s,LAYER+"/query",{"f":"json","where":"1=1","returnIdsOnly":"true","geometry":json.dumps({"xmin":xmin,"ymin":ymin,"xmax":xmax,"ymax":ymax,"spatialReference":{"wkid":3006}}),"geometryType":"esriGeometryEnvelope","inSR":3006,"spatialRel":"esriSpatialRelIntersects"}).get("objectIds") or []
        memberships[area]=set(ids)
        for i in range(0,len(ids),500):
            d=getj(s,LAYER+"/query",{"f":"json","objectIds":",".join(map(str,ids[i:i+500])),"outFields":"*","returnGeometry":"true","outSR":3006})
            for feat in d.get("features",[]):
                oid=feat.get("attributes",{}).get(oid_field)
                if oid is not None: feats[oid]=feat
            time.sleep(.1)
        print(f"Area {area}: {len(ids)} intersecting index tiles",flush=True)
    rows=[]
    for oid,feat in feats.items():
        attrs=feat.get("attributes",{}); row={"object_id":oid,"areas":";".join(k for k,v in memberships.items() if oid in v)}
        row.update({k:(attrs.get(v) if v else None) for k,v in mapping.items()})
        m=re.search(r"([0-9]{2}[A-Z][0-9]{3})",str(row.get("scan_file") or ""))
        row["scan_block_candidate"]=m.group(1) if m else None
        row.update({"source_"+name:attrs.get(name) for name in fields}); rows.append(row)
    columns=["object_id","areas",*mapping.keys(),"scan_block_candidate",*("source_"+n for n in fields)]
    with (OUT/"laser_scan_index_tiles.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    gj={"type":"FeatureCollection","name":"skogsstyrelsen_laser_scan_metadata","crs":{"type":"name","properties":{"name":"EPSG:3006"}},"features":[{"type":"Feature","id":oid,"properties":feat.get("attributes",{}),"geometry":feat.get("geometry")} for oid,feat in feats.items()]}
    (OUT/"laser_scan_index_tiles.geojson").write_text(json.dumps(gj,ensure_ascii=False),encoding="utf-8")
    summary={"service":LAYER,"service_name":layer.get("name"),"spatial_reference":layer.get("extent",{}).get("spatialReference"),"field_mapping":mapping,"source_fields":fields,"feature_count":len(rows),"area_intersections":{k:len(v) for k,v in memberships.items()},"date_semantics":"If an index tile was scanned on multiple dates, the published metadata gives the latest scan date; it is not a complete flight history.","leaf_status_semantics":{"1":"with leaves","2":"without leaves"},"scan_block_candidate":"Heuristically extracted from LasNamn; original filename and all source attributes are retained.","notes":["Features intersect raster outer extents; exact overlap with valid raster cells remains to be calculated.","All original service attributes and geometries are retained."]}
    (OUT/"laser_scan_metadata_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__": main()
