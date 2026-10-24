#!/usr/bin/env python3
"""Gräsmyr cutting-notification and satellite catalogue monitor.

The monitor deliberately distinguishes scene acquisition time from catalogue
publication/creation time. The 10 km search box is a candidate-search extent,
not a cadastral or village boundary.
"""
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

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
HEADERS = {"User-Agent": "Skog-Grasmyr-monitor/0.2"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def cutoff_iso(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


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
        r = SESSION.get(base, params=params, timeout=45)
        r.raise_for_status()
        data = r.json()
        features = data.get("features", [])
        # New/changed IDs are determined from the prior snapshot; recentness is a
        # separate filter so historic features don't appear to be new alerts.
        return {"status": "ok", "url": r.url, "features": features, "count": len(features),
                "note": "Candidate features within a rectangular search bbox only; not parcel matched. Notifications do not prove felling occurred."}
    except Exception as e:
        return {"status": "error", "url": base, "error": str(e), "features": [], "count": 0}


def query_scenes(collection):
    """Search STAC using pagination until there are enough items or the date window ends."""
    url = "https://stac.dataspace.copernicus.eu/v1/search"
    end_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    start_time = cutoff_iso(CONFIG.get("source_filters", {}).get("catalogue_history_days", 550))
    limit = int(CONFIG.get("source_filters", {}).get("catalogue_page_size", 100))
    body = {
        "collections": [collection],
        "bbox": BBOX,
        "datetime": f"{start_time}/{end_time}",
        "limit": limit,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }
    items, seen_next = [], set()
    next_url, next_method, next_body = url, "POST", body
    try:
        while next_url:
            r = SESSION.request(next_method, next_url, json=next_body if next_method == "POST" else None, timeout=45)
            r.raise_for_status()
            data = r.json()
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
            links = data.get("links", [])
            next_link = next((link for link in links if link.get("rel") == "next"), None)
            if not next_link:
                break
            href = urljoin(r.url, next_link.get("href", ""))
            if not href or href in seen_next:
                break
            seen_next.add(href)
            next_url = href
            next_method = next_link.get("method", "GET").upper()
            next_body = next_link.get("body")
            # Link object may use merge semantics for POST body. Keep the original
            # search if the API only provides a bare next link.
            if next_method == "POST" and not isinstance(next_body, dict):
                next_body = body
            if len(items) >= 5000:
                break
        unique = {}
        for item in items:
            if item.get("id"):
                unique[item["id"]] = item
        items = sorted(unique.values(), key=lambda x: x.get("acquired_at") or "", reverse=True)
        return {"status": "ok", "url": url, "collection": collection, "items": items, "count": len(items),
                "note": "Scene metadata only; scene footprint and cloud conditions may differ over the area of interest."}
    except Exception as e:
        return {"status": "error", "url": url, "collection": collection, "error": str(e), "items": [], "count": 0}


def feature_identity(feature):
    props = feature.get("properties", {})
    return str(feature.get("id") or props.get("OBJECTID") or props.get("Beteckn") or "")


def feature_date(feature):
    props = feature.get("properties", {})
    # ArcGIS returns epoch milliseconds for Inkomdatum.
    value = props.get("Inkomdatum")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def main():
    old_path = DATA / "latest.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    old_cut_ids = {feature_identity(x) for x in old.get("cutting_notifications", {}).get("features", []) if feature_identity(x)}
    old_scene_ids = {
        x.get("id")
        for key in ("sentinel1", "sentinel2")
        for x in old.get(key, {}).get("items", [])
        if x.get("id")
    }

    cuts = cutting_notifications()
    sentinel1 = query_scenes("sentinel-1-grd")
    sentinel2 = query_scenes("sentinel-2-l2a")
    all_scenes = sentinel1.get("items", []) + sentinel2.get("items", [])
    new_scenes = [x for x in all_scenes if x.get("id") and x.get("id") not in old_scene_ids]

    now = datetime.now(timezone.utc)
    recent_days = int(CONFIG.get("source_filters", {}).get("recent_cutting_notification_days", 60))
    recent_cutoff = now - timedelta(days=recent_days)
    current_cut_features = cuts.get("features", [])
    new_cut_features = [x for x in current_cut_features if feature_identity(x) and feature_identity(x) not in old_cut_ids]
    recent_new_cut_features = [x for x in new_cut_features if (feature_date(x) is None or feature_date(x) >= recent_cutoff)]
    initial_run = not old
    result = {
        "checked_at": now.isoformat(),
        "area": CONFIG,
        "bbox_wgs84": BBOX,
        "initial_run": initial_run,
        "cutting_notifications": cuts,
        "new_cutting_notification_ids_since_previous_run": new_cut_features if not initial_run else [],
        "recent_new_cutting_notification_ids_since_previous_run": recent_new_cut_features if not initial_run else [],
        "sentinel1": sentinel1,
        "sentinel2": sentinel2,
        "new_scenes_since_previous_run": new_scenes if not initial_run else [],
        "commercial_imagery": {
            "status": "manual_verification_required",
            "services": [
                {"name": "Hitta.se", "url": "https://www.hitta.se/"},
                {"name": "Min karta", "url": "https://minkarta.lantmateriet.se/"},
                {"name": "Lantmäteriet GeoLex", "url": "https://geolex.lantmateriet.se/"},
                {"name": "Google Earth", "url": "https://earth.google.com/"}
            ],
            "note": "Do not infer image acquisition dates from website modification dates. Add a provider only when image date/version metadata can be verified."
        }
    }
    old_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    (SNAPSHOTS / f"{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "checked_at": result["checked_at"],
        "initial_run": initial_run,
        "cutting_status": cuts["status"],
        "cutting_count": cuts["count"],
        "new_cutting_notification_count": len(result["new_cutting_notification_ids_since_previous_run"]),
        "recent_new_cutting_notification_count": len(result["recent_new_cutting_notification_ids_since_previous_run"]),
        "sentinel1_status": sentinel1["status"],
        "sentinel1_count": sentinel1["count"],
        "sentinel2_status": sentinel2["status"],
        "sentinel2_count": sentinel2["count"],
        "new_scenes": len(result["new_scenes_since_previous_run"]),
        "latest_sentinel1": (sentinel1.get("items") or [{}])[0].get("acquired_at"),
        "latest_sentinel2": (sentinel2.get("items") or [{}])[0].get("acquired_at")
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
