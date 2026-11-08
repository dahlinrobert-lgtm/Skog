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
    # ArcGIS returnIdsOnly query: keep the exact parameters used by the successful
    # inventory count probe, but ask for IDs rather than a count.
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

def fetch_ids(layer_url):
    """Prefer spatially filtered IDs; fall back to all IDs plus local clipping on 400."""
    try:
        result=request_json(layer_url.rstrip("/")+"/query",query_params())
        return sorted(set(result.get("objectIds") or [])), "spatial-query"
    except Exception as exc:
        print(f"WARNING: spatial ID query failed for {layer_url}: {exc}; retrying unfiltered ID inventory",flush=True)
        result=request_json(layer_url.rstrip("/")+"/query",{
            "where":"1=1","returnIdsOnly":"true","returnGeometry":"false","f":"json"
        })
        return sorted(set(result.get("objectIds") or [])), "unfiltered-ids"

def save_layer(service_key, layer, ids, base_url, id_mode):
    layer_id=layer["id"]
    name=layer.get("name",f"layer-{layer_id}")
    safe="".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    folder=ROOT/DATE/service_key
    folder.mkdir(parents=True,exist_ok=True)
    out=folder/f"{layer_id:02d}-{safe}.geojson.gz"
    url=f"{base_url.rstrip('/')}/{layer_id}/query"
    features=[]
    oid_field=layer.get("objectIdField") or layer.get("objectIdFieldName")
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
            raise RuntimeError(f"Feature batch incomplete for layer {layer_id}: got {len(got)} of {len(batch)}")
        time.sleep(0.15)
    # If ArcGIS rejected the spatial query, clip the fetched GeoJSON locally to the
    # same WGS84 envelope. Points are retained when inside; lines/polygons are
    # spatially tested using their coordinate bounds (conservative bbox filter).
    if id_mode == "unfiltered-ids":
        def positions(coords):
            if isinstance(coords,(list,tuple)) and coords and isinstance(coords[0],(int,float)):
                yield coords
            elif isinstance(coords,(list,tuple)):
                for child in coords: yield from positions(child)
        def in_envelope(feature):
            coords=list(positions(feature.get("geometry",{}).get("coordinates",[])))
            if not coords: return False
            xs=[p[0] for p in coords]; ys=[p[1] for p in coords]
            return not (max(xs)<ENVELOPE["xmin"] or min(xs)>ENVELOPE["xmax"] or max(ys)<ENVELOPE["ymin"] or min(ys)>ENVELOPE["ymax"])
        features=[f for f in features if in_envelope(f)]
    collection={"type":"FeatureCollection","name":name,"features":features}
    raw=json.dumps(collection,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    with out.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream,mode="wb",mtime=0) as gz: gz.write(raw)
    return {
        "id":layer_id,"name":name,"geometry_type":layer.get("geometryType"),
        "id_query_mode":id_mode,"source_object_id_count":len(ids),"downloaded_feature_count":len(features),
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
            merged={**layer,**detail}
            ids,id_mode=fetch_ids(f"{base}/{layer['id']}")
            row=save_layer(key,merged,ids,base,id_mode)
            service["layers"].append(row); total+=row["downloaded_feature_count"]
            print(f"{key} layer {layer['id']} {layer.get('name')}: {row['downloaded_feature_count']} downloaded (ID mode: {id_mode})",flush=True)
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
