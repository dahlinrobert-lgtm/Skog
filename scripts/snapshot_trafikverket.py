#!/usr/bin/env python3
"""Fetch immutable weekly Trafikverket GeoJSON snapshots for the Gräsmyr pilot."""
from __future__ import annotations
import hashlib, json, math, os, sys, time, urllib.parse, urllib.request, urllib.error, gzip
from datetime import datetime, timezone
from pathlib import Path

SERVICES = [
    ("miljowebb", "https://vektor.trafikverket.se/gis/rest/services/MWLEXGEO/MiljowebbGeo/MapServer"),
    ("viltolyckor", "https://vektor.trafikverket.se/gis/rest/services/NVDB_p%C3%A5_karta/Viltolyckor_NVDBpakarta/MapServer"),
]
CENTRE = {"longitude": 19.66455, "latitude": 63.74646}
HALF_H = 37_500 / 111_000
HALF_W = 37_500 / (111_000 * math.cos(math.radians(CENTRE["latitude"])))
ENVELOPE = {"xmin": CENTRE["longitude"]-HALF_W, "ymin": CENTRE["latitude"]-HALF_H,
            "xmax": CENTRE["longitude"]+HALF_W, "ymax": CENTRE["latitude"]+HALF_H,
            "spatialReference": {"wkid": 4326}}
ROOT = Path(os.environ.get("TRAFIKVERKET_SNAPSHOT_ROOT", "data/trafikverket/snapshots"))
DATE = os.environ.get("SNAPSHOT_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
BATCH_SIZE = int(os.environ.get("TRAFIKVERKET_BATCH_SIZE", "500"))

def request_json(url, params=None, attempts=5):
    query = urllib.parse.urlencode(params or {"f":"pjson"})
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + query,
        headers={"User-Agent":"Skog-Trafikverket-snapshot/1.0"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data=json.loads(response.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            if attempt == attempts-1: raise
            time.sleep(min(2 ** attempt, 20))

def query_params():
    return {
        "where":"1=1",
        "geometry":json.dumps(ENVELOPE,separators=(",",":")),
        "geometryType":"esriGeometryEnvelope",
        "inSR":"4326",
        "spatialRel":"esriSpatialRelIntersects",
        "returnIdsOnly":"true",
        "returnGeometry":"false",
        "f":"json",
    }

def save_layer(service_key, layer, ids, base_url):
    layer_id=layer["id"]
    name=layer.get("name",f"layer-{layer_id}")
    safe="".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    folder=ROOT/DATE/service_key
    folder.mkdir(parents=True,exist_ok=True)
    out=folder/f"{layer_id:02d}-{safe}.geojson.gz"
    url=f"{base_url.rstrip('/')}/{layer_id}/query"
    features=[]
    for start in range(0,len(ids),BATCH_SIZE):
        batch=ids[start:start+BATCH_SIZE]
        params={
            "objectIds":",".join(str(x) for x in batch),
            "outFields":"*",
            "returnGeometry":"true",
            "outSR":"4326",
            "f":"geojson",
        }
        payload=request_json(url,params)
        got=payload.get("features",[])
        features.extend(got)
        if len(got)!=len(batch):
            # Some services may omit inaccessible/deleted objects; record actual count in manifest.
            pass
        time.sleep(0.15)
    collection={"type":"FeatureCollection","name":name,"crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}},"features":features}
    raw=json.dumps(collection,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    with out.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream,mode="wb",mtime=0) as gz: gz.write(raw)
    return {
        "id":layer_id,"name":name,"geometry_type":layer.get("geometryType"),
        "source_object_id_count":len(ids),"downloaded_feature_count":len(features),
        "file":str(out),"compressed_bytes":out.stat().st_size,
        "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
        "fields":[f.get("name") for f in layer.get("fields",[])],
    }

def main():
    snapshot={"snapshot_date_utc":DATE,"created_at_utc":datetime.now(timezone.utc).isoformat(),
      "area":{"name":"Gräsmyr pilot","centre_wgs84":CENTRE,"envelope_wgs84":ENVELOPE,
      "description":"Approximate 75 km x 75 km discovery envelope; not a property boundary."},
      "services":[],"status":"complete"}
    total=0
    for key,base in SERVICES:
        meta=request_json(base,{"f":"pjson"})
        service={"key":key,"url":base,"spatial_reference":meta.get("spatialReference"),"layers":[]}
        for layer in meta.get("layers",[]):
            detail=request_json(f"{base}/{layer['id']}",{"f":"pjson"})
            if detail.get("type")!="Feature Layer" or not detail.get("geometryType"):
                continue
            ids_data=request_json(f"{base}/{layer['id']}/query",query_params())
            ids=ids_data.get("objectIds") or []
            ids=sorted(set(ids))
            row=save_layer(key,{**layer,**detail},ids,base)
            service["layers"].append(row); total+=row["downloaded_feature_count"]
            print(f"{key} layer {layer['id']} {layer.get('name')}: {row['downloaded_feature_count']}/{len(ids)} features")
        snapshot["services"].append(service)
    snapshot["total_downloaded_features"]=total
    snapshot["total_feature_layers"]=sum(len(s["layers"]) for s in snapshot["services"])
    snapshot["manifest_sha256"]=hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    manifest=ROOT/DATE/"manifest.json"
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Snapshot {DATE}: {snapshot['total_feature_layers']} layers, {total} features")
    print(f"Manifest: {manifest}")
    if total==0: raise RuntimeError("Snapshot contains zero features; refusing to report success.")
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); sys.exit(1)
