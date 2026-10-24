#!/usr/bin/env python3
"""Gräsmyr cutting-notification and satellite catalogue monitor."""
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
HEADERS = {"User-Agent": "Skog-Grasmyr-monitor/0.3"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SCENE_INDEX_PATH = DATA / "scene_index.json"


def utc_now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def parse_dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cutting_notifications():
    base = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0/query"
    params = {
        "where": "1=1",
        "geometry": json.dumps({"x": LON, "y": LAT, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint", "inSR": 4326,
        "distance": int(R * 1000), "units": "esriSRUnit_Meter",
        "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
        "returnGeometry": "true", "outSR": 4326, "f": "geojson", "resultRecordCount": 2000
    }
    try:
        response = SESSION.get(base, params=params, timeout=45)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])
        return {"status": "ok", "url": response.url, "features": features, "count": len(features),
                "note": "Features intersect a 10 km point-distance query around the configured centre; this is not a cadastral or village boundary. A notification does not prove felling occurred."}
    except Exception as exc:
        return {"status": "error", "url": base, "error": str(exc), "features": [], "count": 0}


def query_scenes(collection):
    """Read paginated STAC results, but persist compact metadata rather than full polygons."""
    url = "https://stac.dataspace.copernicus.eu/v1/search"
    now = utc_now()
    history_days = int(CONFIG.get("source_filters", {}).get("catalogue_history_days", 550))
    limit = int(CONFIG.get("source_filters", {}).get("catalogue_page_size", 100))
    body = {
        "collections": [collection],
        "bbox": BBOX,
        "datetime": f"{iso(now - timedelta(days=history_days))}/{iso(now)}",
        "limit": limit,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }
    raw_items, next_links, seen_next = [], [], set()
    next_url, next_method, next_body = url, "POST", body
    try:
        while next_url and len(raw_items) < 5000:
            response = SESSION.request(next_method, next_url, json=next_body if next_method == "POST" else None, timeout=45)
            response.raise_for_status()
            data = response.json()
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                raw_items.append({
                    "id": feature.get("id"),
                    "collection": feature.get("collection") or collection,
                    "acquired_at": props.get("datetime") or props.get("start_datetime"),
                    "published_at": props.get("created") or props.get("published"),
                    "cloud_cover_percent": props.get("eo:cloud_cover"),
                    "bbox": feature.get("bbox")
                })
            next_link = next((link for link in data.get("links", []) if link.get("rel") == "next"), None)
            if not next_link:
                break
            href = urljoin(response.url, next_link.get("href", ""))
            if not href or href in seen_next:
                break
            seen_next.add(href)
            next_url = href
            next_method = next_link.get("method", "GET").upper()
            next_body = next_link.get("body")
            if next_method == "POST" and not isinstance(next_body, dict):
                next_body = body
        unique = {}
        for item in raw_items:
            if item.get("id"):
                unique[item["id"]] = item
        items = sorted(unique.values(), key=lambda item: item.get("acquired_at") or "", reverse=True)
        return {"status": "ok", "url": url, "collection": collection, "items": items, "count": len(items),
                "pagination_cap_reached": len(raw_items) >= 5000,
                "note": "Compact scene metadata. Cloud cover is scene-level and may not describe the Gräsmyr area itself."}
    except Exception as exc:
        return {"status": "error", "url": url, "collection": collection, "error": str(exc), "items": [], "count": 0}


def feature_identity(feature):
    props = feature.get("properties", {})
    return str(feature.get("id") or props.get("OBJECTID") or props.get("Beteckn") or "")


def feature_date(feature):
    value = feature.get("properties", {}).get("Inkomdatum")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    return parse_dt(value)


def load_scene_index():
    if not SCENE_INDEX_PATH.exists():
        return None
    try:
        value = json.loads(SCENE_INDEX_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main():
    now = utc_now()
    old_path = DATA / "latest.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    old_cut_ids = {
        feature_identity(feature)
        for feature in old.get("cutting_notifications", {}).get("features", [])
        if feature_identity(feature)
    }
    prior_index = load_scene_index()
    index_is_baseline = prior_index is not None

    cuts = cutting_notifications()
    sentinel1 = query_scenes("sentinel-1-grd")
    sentinel2 = query_scenes("sentinel-2-l2a")
    all_scenes = sentinel1.get("items", []) + sentinel2.get("items", [])
    prior_ids = set(prior_index.keys()) if prior_index is not None else set()
    current_index = {}
    for scene in all_scenes:
        if scene.get("id"):
            current_index[scene["id"]] = {
                "collection": scene.get("collection"),
                "acquired_at": scene.get("acquired_at"),
                "published_at": scene.get("published_at")
            }

    # A missing compact index means this run is establishing a baseline. This
    # avoids falsely labelling the rest of the 550-day archive as new scenes.
    new_scenes = []
    if index_is_baseline:
        for scene in all_scenes:
            scene_id = scene.get("id")
            if not scene_id or scene_id in prior_ids:
                continue
            acquired = parse_dt(scene.get("acquired_at"))
            published = parse_dt(scene.get("published_at"))
            prior_checked = parse_dt(old.get("checked_at"))
            # Allow a seven-day overlap so catalogue ingestion delays can be caught,
            # while avoiding alerts for old archive items absent from the old 100-item sample.
            recent_acquisition = acquired is not None and acquired >= now - timedelta(days=7)
            published_since_last_check = published is not None and prior_checked is not None and published >= prior_checked
            if recent_acquisition or published_since_last_check:
                new_scenes.append(scene)

    recent_days = int(CONFIG.get("source_filters", {}).get("recent_cutting_notification_days", 60))
    recent_cutoff = now - timedelta(days=recent_days)
    new_cut_features = [
        feature for feature in cuts.get("features", [])
        if feature_identity(feature) and feature_identity(feature) not in old_cut_ids
    ]
    recent_new_cut_features = [
        feature for feature in new_cut_features
        if feature_date(feature) is not None and feature_date(feature) >= recent_cutoff
    ]
    initial_run = not old
    result = {
        "checked_at": iso(now),
        "area": CONFIG,
        "bbox_wgs84": BBOX,
        "initial_run": initial_run,
        "scene_index_baseline_available": index_is_baseline,
        "cutting_notifications": cuts,
        "new_cutting_notification_ids_since_previous_run": new_cut_features if not initial_run else [],
        "recent_new_cutting_notification_ids_since_previous_run": recent_new_cut_features if not initial_run else [],
        "sentinel1": sentinel1,
        "sentinel2": sentinel2,
        "new_scenes_since_previous_run": new_scenes if index_is_baseline else [],
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
    SCENE_INDEX_PATH.write_text(json.dumps(current_index, ensure_ascii=False, indent=2), encoding="utf-8")
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    (SNAPSHOTS / f"{stamp}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "checked_at": result["checked_at"],
        "initial_run": initial_run,
        "scene_index_baseline_available": index_is_baseline,
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
