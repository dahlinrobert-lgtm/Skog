#!/usr/bin/env python3
"""Initial Gräsmyr cutting-notification and Sentinel-2 catalogue monitor."""
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/area.json").read_text(encoding="utf-8"))
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
DATA.mkdir(exist_ok=True)
SNAPSHOTS.mkdir(exist_ok=True)
LAT, LON = CONFIG["latitude"], CONFIG["longitude"]
R = CONFIG["radius_km"]
LAT_D = R / 110.574
LON_D = R / (111.320 * max(0.1, math.cos(math.radians(LAT))))
BBOX = [LON - LON_D, LAT - LAT_D, LON + LON_D, LAT + LAT_D]
HEADERS = {"User-Agent": "Skog-Grasmyr-monitor/0.1"}


def cutting_notifications():
    base = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0/query"
    params = {
        "where": "1=1",
        "geometry": json.dumps({"xmin": BBOX[0], "ymin": BBOX[1], "xmax": BBOX[2], "ymax": BBOX[3], "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryEnvelope", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
        "returnGeometry": "true", "outSR": 4326, "f": "geojson", "resultRecordCount": 2000
    }
    try:
        r = requests.get(base, params=params, headers=HEADERS, timeout=45)
        r.raise_for_status()
        data = r.json()
        return {"status": "ok", "url": r.url, "features": data.get("features", []), "count": len(data.get("features", [])),
                "note": "Not a cadastral property match; notification does not prove felling has occurred."}
    except Exception as e:
        return {"status": "error", "url": base, "error": str(e), "features": [], "count": 0}


def query_scenes(collection):
    """Search the current Copernicus Data Space STAC v1 catalogue."""
    url = "https://stac.dataspace.copernicus.eu/v1/search"
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(days=550)).isoformat().replace("+00:00", "Z")
    end_time = now.isoformat().replace("+00:00", "Z")
    body = {
        "collections": [collection],
        "bbox": BBOX,
        "datetime": f"{start_time}/{end_time}",
        "limit": 100,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }
    try:
        r = requests.post(url, json=body, headers={**HEADERS, "Content-Type": "application/json"}, timeout=45)
        r.raise_for_status()
        data = r.json()
        items = []
        for f in data.get("features", []):
            p = f.get("properties", {})
            items.append({
                "id": f.get("id"),
                "collection": f.get("collection") or collection,
                "acquired_at": p.get("datetime") or p.get("start_datetime"),
                "published_at": p.get("created") or p.get("published"),
                "cloud_cover_percent": p.get("eo:cloud_cover"),
                "geometry": f.get("geometry"),
                "links": f.get("links", [])
            })
        items.sort(key=lambda x: x.get("acquired_at") or "", reverse=True)
        return {
            "status": "ok", "url": url, "collection": collection,
            "items": items, "count": len(items),
            "note": "Cloud cover is scene-level and may not describe Gräsmyr itself; radar scenes do not have optical cloud cover."
        }
    except Exception as e:
        return {"status": "error", "url": url, "collection": collection, "error": str(e), "items": [], "count": 0}


def main():
    old_path = DATA / "latest.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    old_ids = {x.get("id") for source in ("sentinel1", "sentinel2") for x in old.get(source, {}).get("items", []) if x.get("id")}
    cuts = cutting_notifications()
    sentinel1 = query_scenes("sentinel-1-grd")
    sentinel2 = query_scenes("sentinel-2-l2a")
    all_scenes = sentinel1.get("items", []) + sentinel2.get("items", [])
    new_scenes = [x for x in all_scenes if x.get("id") and x.get("id") not in old_ids]
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "area": CONFIG, "bbox_wgs84": BBOX,
        "cutting_notifications": cuts, "sentinel1": sentinel1, "sentinel2": sentinel2,
        "new_scenes_since_previous_run": new_scenes,
        "commercial_imagery": {
            "status": "manual_verification_required",
            "services": [
                {"name": "Hitta.se", "url": "https://www.hitta.se/"},
                {"name": "Min karta", "url": "https://minkarta.lantmateriet.se/"},
                {"name": "Lantmäteriet GeoLex", "url": "https://geolex.lantmateriet.se/"},
                {"name": "Google Earth", "url": "https://earth.google.com/"}
            ],
            "note": "Do not infer aerial-photo acquisition dates from website modification dates. Add a provider only when image date/version metadata can be verified."
        }
    }
    old_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (SNAPSHOTS / f"{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checked_at": result["checked_at"], "cutting_status": cuts["status"], "cutting_count": cuts["count"],
                      "sentinel1_status": sentinel1["status"], "sentinel1_count": sentinel1["count"],
                      "sentinel2_status": sentinel2["status"], "sentinel2_count": sentinel2["count"], "new_scenes": len(new_scenes),
                      "latest_sentinel1": (sentinel1.get("items") or [{}])[0].get("acquired_at"),
                      "latest_sentinel2": (sentinel2.get("items") or [{}])[0].get("acquired_at")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
