#!/usr/bin/env python3
"""Collect Skogsstyrelsen 2.5 km laser-scan metadata for Omdrev raster extents."""
from __future__ import annotations
import csv, json, re, time
from pathlib import Path
import requests

LAYER = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0"
AREAS = {"13":(250000,6200000,450000,6400000),"21":(450000,6650000,700000,6950000),"23":(300000,6800000,650000,7250000)}
OUT=Path("raster-three-omdrev/flight_metadata")

def getj(session,url,params):
    response=session.get(url,params=params,timeout=120)
    response.raise_for_status()
    data=response.json()
    if "error" in data:
        raise RuntimeError(json.dumps(data["error"],ensure_ascii=False))
    return data

def postj(session,url,data):
    """POST long ArcGIS query parameters to avoid oversized request URLs."""
    response=session.post(url,data=data,timeout=120)
    response.raise_for_status()
    payload=response.json()
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"],ensure_ascii=False))
    return payload

def choose_field(fields, candidates):
    lookup={name.lower():name for name in fields}
    return next((lookup[name.lower()] for name in candidates if name.lower() in lookup),None)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    session=requests.Session()
    session.headers["User-Agent"]="Skogskoll-flight-metadata/1.2"
    layer=getj(session,LAYER,{"f":"json"})
    definitions=layer.get("fields",[])
    fields=[field["name"] for field in definitions]
    if not fields:
        raise RuntimeError("ArcGIS metadata layer returned no fields")
    # The official 2025 and 2026 product descriptions use different field spellings.
    field_map={
        "index_tile":choose_field(fields,["Indexruta"]),
        "scan_file":choose_field(fields,["Las_Namn","LasNamn"]),
        "scan_date":choose_field(fields,["Datum","datum"]),
        "leaf_status":choose_field(fields,["Lov_Avlov"]),
    }
    if not field_map["index_tile"] or not field_map["scan_date"]:
        raise RuntimeError(f"Required fields missing. Resolved={field_map}; available={fields}")
    oid_field=layer.get("objectIdField") or next(
        (field["name"] for field in definitions if field.get("type")=="esriFieldTypeOID"),None)
    if not oid_field:
        raise RuntimeError("Could not identify ArcGIS object ID field")

    features={}
    area_ids={}
    for area,(xmin,ymin,xmax,ymax) in AREAS.items():
        query={
            "f":"json","where":"1=1","returnIdsOnly":"true",
            "geometry":json.dumps({"xmin":xmin,"ymin":ymin,"xmax":xmax,"ymax":ymax,
                                   "spatialReference":{"wkid":3006}}),
            "geometryType":"esriGeometryEnvelope","inSR":3006,
            "spatialRel":"esriSpatialRelIntersects"
        }
        ids=getj(session,LAYER+"/query",query).get("objectIds") or []
        area_ids[area]=set(ids)
        for offset in range(0,len(ids),500):
            batch=ids[offset:offset+500]
            result=postj(session,LAYER+"/query",{
                "f":"json","objectIds":",".join(map(str,batch)),
                "outFields":"*","returnGeometry":"true","outSR":3006
            })
            for feature in result.get("features",[]):
                oid=feature.get("attributes",{}).get(oid_field)
                if oid is not None:
                    features[oid]=feature
            time.sleep(0.1)
        print(f"Area {area}: {len(ids)} intersecting index tiles",flush=True)

    rows=[]
    for oid,feature in features.items():
        attrs=feature.get("attributes",{})
        row={"object_id":oid,
             "areas":";".join(area for area,ids in area_ids.items() if oid in ids)}
        for key,source_name in field_map.items():
            row[key]=attrs.get(source_name) if source_name else None
        laz=str(row.get("scan_file") or "")
        # Convenience parse only; never replace or reinterpret the source filename.
        block_match=re.search(r"(?<![A-Za-z0-9])\d{2}[A-Z]\d{3}(?![A-Za-z0-9])",laz)
        row["scan_block_candidate"]=block_match.group(0) if block_match else None
        for name in fields:
            row["source_"+name]=attrs.get(name)
        rows.append(row)

    columns=["object_id","areas",*field_map.keys(),"scan_block_candidate",
             *("source_"+name for name in fields)]
    with (OUT/"laser_scan_index_tiles.csv").open("w",newline="",encoding="utf-8-sig") as output:
        writer=csv.DictWriter(output,fieldnames=columns,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    geojson={"type":"FeatureCollection","name":"skogsstyrelsen_laser_scan_metadata",
      "crs":{"type":"name","properties":{"name":"EPSG:3006"}},
      "features":[{"type":"Feature","id":oid,"properties":feature.get("attributes",{}),
                   "geometry":feature.get("geometry")} for oid,feature in features.items()]}
    (OUT/"laser_scan_index_tiles.geojson").write_text(
        json.dumps(geojson,ensure_ascii=False),encoding="utf-8")

    summary={
      "service":LAYER,"service_name":layer.get("name"),
      "spatial_reference":layer.get("extent",{}).get("spatialReference"),
      "object_id_field":oid_field,"field_mapping":field_map,"source_fields":fields,
      "feature_count":len(rows),
      "area_intersections":{area:len(ids) for area,ids in area_ids.items()},
      "date_semantics":"The published tile date is the latest scan date when a tile has been scanned on multiple dates; it is not a complete flight history.",
      "leaf_status_semantics":{"1":"with leaves","2":"without leaves"},
      "scan_block_candidate":"Heuristically parsed from the LAZ filename; the original filename and all source attributes are retained.",
      "limitations":["This service is a 2.5 km tile metadata layer. It does not by itself prove which exact source scan date was used for each raster pixel.",
        "Features intersect raster outer extents; exact overlap with valid raster cells is a subsequent step."]}
    (OUT/"laser_scan_metadata_summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":
    main()
