#!/usr/bin/env python3
"""Small, rate-limited polygon-to-property pilot for Skogsstyrelsen notifications.

Uses a few interior and boundary samples per notification. This is an approximation,
not a cadastral intersection; a full polygon may cross additional properties.
Min karta endpoint is an observed internal web-app endpoint, not a documented public API.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/area.json").read_text(encoding="utf-8"))
LATEST = json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))
PREFIX = str(CONFIG.get("property_tract_prefix", "Gräsmyr")).casefold()
BASE = "https://minkarta.lantmateriet.se/api/positionsinformation/positionsinformation/registerenhetermedbuffer/v1"
DELAY_SECONDS = 3
MAX_FEATURES = 3
MAX_SAMPLES_PER_FEATURE = 5


def feature_date(feature):
    value = feature.get("properties", {}).get("Inkomdatum")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


def sample_points(geometry, limit=MAX_SAMPLES_PER_FEATURE):
    """Return representative interior point plus evenly spaced exterior vertices."""
    geom = shape(geometry)
    points = []
    components = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    # One point safely inside each polygon component where possible.
    for component in components:
        if len(points) >= limit:
            break
        p = component.representative_point()
        points.append((p.x, p.y, "interior"))
    # Sample exterior vertices spread across all polygon components.
    vertices = []
    for component in components:
        if not hasattr(component, "exterior"):
            continue
        coords = list(component.exterior.coords)[:-1]
        if coords:
            vertices.extend(coords)
    remaining = max(0, limit - len(points))
    if remaining and vertices:
        indexes = sorted(set(round(i * (len(vertices) - 1) / max(1, remaining - 1)) for i in range(remaining)))
        for idx in indexes:
            x, y = vertices[idx]
            candidate = (x, y)
            if all(abs(x - px) > 1e-8 or abs(y - py) > 1e-8 for px, py, _ in points):
                points.append((x, y, "boundary_sample"))
    return points[:limit]


def lookup(east, north, session):
    params = {"transactionId": str(uuid.uuid4()), "east": east, "north": north, "buffer": 1}
    response = session.get(BASE, params=params, timeout=25)
    response.raise_for_status()
    data = response.json()
    entries = data.get("fastigheter") or data.get("registerenheter") or []
    return [
        {"designation": item.get("objectText"), "type": item.get("registerenhetstyp"),
         "object_id": item.get("objectId")}
        for item in entries if item.get("objectText")
    ]


def main():
    all_features = LATEST.get("cutting_notifications", {}).get("features", [])
    features = [
        f for f in all_features
        if f.get("geometry") and str(f.get("properties", {}).get("Kommunnr", "")) == "2401"
    ]
    features.sort(key=feature_date, reverse=True)
    features = features[:MAX_FEATURES]
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Skog-Grasmyr-monitor/0.3 (limited polygon pilot)",
        "Referer": "https://minkarta.lantmateriet.se/",
    })
    results = []
    request_count = 0
    for feature in features:
        props = feature.get("properties", {})
        samples = sample_points(feature["geometry"])
        observations = []
        for i, (lon, lat, sample_kind) in enumerate(samples):
            # Skogsstyrelsen geometry is WGS84; Min karta endpoint expects SWEREF99 TM.
            from pyproj import Transformer
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
            east, north = transformer.transform(lon, lat)
            try:
                found = lookup(east, north, session)
                request_count += 1
                observations.append({
                    "sample_kind": sample_kind, "wgs84": {"lon": lon, "lat": lat},
                    "sweref99tm": {"east": east, "north": north},
                    "properties": found,
                    "grasmyr_matches": [x for x in found if x["designation"].split()[0].casefold().startswith(PREFIX)],
                    "status": "ok"
                })
            except Exception as exc:
                request_count += 1
                observations.append({
                    "sample_kind": sample_kind, "wgs84": {"lon": lon, "lat": lat},
                    "status": "error", "error": str(exc), "properties": [], "grasmyr_matches": []
                })
            if request_count < MAX_FEATURES * MAX_SAMPLES_PER_FEATURE:
                time.sleep(DELAY_SECONDS)
        unique = {}
        for obs in observations:
            for item in obs.get("properties", []):
                unique[item.get("designation")] = item
        grasmyr = [item for item in unique.values()
                   if item.get("designation", "").split() and
                   item["designation"].split()[0].casefold().startswith(PREFIX)]
        results.append({
            "notification_id": props.get("Beteckn") or feature.get("id"),
            "objectid": feature.get("id"),
            "municipality": props.get("Kommun"),
            "notification_date": feature_date(feature).isoformat(),
            "reported_area_ha": props.get("AnmaldHa"),
            "geometry_type": feature["geometry"].get("type"),
            "sample_count": len(observations),
            "unique_properties_observed": sorted(unique.keys()),
            "unique_property_count": len(unique),
            "grasmyr_matches": sorted(x["designation"] for x in grasmyr),
            "grasmyr_match_count": len(grasmyr),
            "observations": observations,
            "interpretation": (
                "Gräsmyr match observed in one or more samples; candidate only, not proof the full polygon belongs to that property."
                if grasmyr else
                "No Gräsmyr-prefixed designation observed in these samples; not proof there is no intersection."
            )
        })
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "method": "Up to 5 samples per polygon: representative interior point(s) and evenly spaced exterior vertices. Min karta results are aggregated.",
        "limitations": [
            "Sampling is approximate and does not calculate exact polygon-to-cadastral-parcel intersections.",
            "A sample may fall on a neighbouring property, especially near boundaries.",
            "No Gräsmyr match among samples does not prove that a polygon does not intersect a Gräsmyr property.",
            "Min karta endpoint is an observed internal web-app endpoint, not a documented public API."
        ],
        "request_count": request_count,
        "delay_seconds_between_requests": DELAY_SECONDS,
        "features_tested": len(results),
        "results": results
    }
    out = ROOT / "data" / "property_lookup_pilot.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "checked_at": report["checked_at"], "features_tested": len(results),
        "request_count": request_count, "report_path": str(out),
        "results": [{
            "notification_id": x["notification_id"],
            "unique_property_count": x["unique_property_count"],
            "unique_properties_observed": x["unique_properties_observed"],
            "grasmyr_matches": x["grasmyr_matches"],
            "sample_count": x["sample_count"]
        } for x in results],
        "limitations": report["limitations"]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
