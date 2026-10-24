#!/usr/bin/env python3
"""Rate-limited Gräsmyr-focused polygon-to-property pilot.

Samples interior points and polygon boundary vertices. This is a candidate finder,
not an exact cadastral overlay. The Min karta endpoint is an observed internal
web-app endpoint, not a documented public API.
"""
import json
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/area.json").read_text(encoding="utf-8"))
LATEST = json.loads((ROOT / "data/latest.json").read_text(encoding="utf-8"))
PREFIX = str(CONFIG.get("property_tract_prefix", "Gräsmyr")).strip().casefold()
CENTER_LON = float(CONFIG["longitude"])
CENTER_LAT = float(CONFIG["latitude"])
RADIUS_KM = float(CONFIG.get("radius_km", 10))
BASE = "https://minkarta.lantmateriet.se/api/positionsinformation/positionsinformation/registerenhetermedbuffer/v1"
DELAY_SECONDS = 3
MAX_FEATURES = 20
MAX_SAMPLES_PER_FEATURE = 6
TO_SWEREF = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
TO_WGS84 = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)
CENTER_E, CENTER_N = TO_SWEREF.transform(CENTER_LON, CENTER_LAT)


def feature_date(feature):
    value = feature.get("properties", {}).get("Inkomdatum")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


def tract_from_designation(value):
    """Min karta usually returns 'NORDMALING GRÄSMYR 6:43'; tolerate no municipality."""
    parts = str(value or "").strip().split()
    if not parts:
        return ""
    if len(parts) > 1 and parts[0].casefold() in {
        "nordmaling", "umeå", "umea", "bjurholm", "vännäs", "vannas"
    }:
        return " ".join(parts[1:])
    return " ".join(parts)


def is_target_tract(value):
    return tract_from_designation(value).casefold().startswith(PREFIX)


def distance_to_center_km(geom):
    # Use projected geometry centroid for ranking, not for property attribution.
    projected = shape(geom)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
    from shapely.ops import transform
    projected = transform(transformer.transform, projected)
    return projected.centroid.distance(Point(CENTER_E, CENTER_N)) / 1000


def sample_points(geometry, limit=MAX_SAMPLES_PER_FEATURE):
    geom = shape(geometry)
    points = []
    components = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    for component in components:
        if len(points) >= limit:
            break
        p = component.representative_point()
        points.append((p.x, p.y, "interior"))
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
    candidates = []
    for feature in all_features:
        if not feature.get("geometry"):
            continue
        props = feature.get("properties", {})
        if str(props.get("Kommunnr", "")) != "2401":
            continue
        distance = distance_to_center_km(feature["geometry"])
        if distance <= RADIUS_KM:
            candidates.append((distance, feature))
    # Prefer spatial relevance to Gräsmyr, then newest notification.
    candidates.sort(key=lambda pair: (pair[0], -feature_date(pair[1]).timestamp()))
    selected = candidates[:MAX_FEATURES]

    session = requests.Session()
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Skog-Grasmyr-monitor/0.4 (limited property pilot)",
        "Referer": "https://minkarta.lantmateriet.se/",
    })
    results = []
    request_count = 0
    for distance_km, feature in selected:
        props = feature.get("properties", {})
        observations = []
        for sample_index, (lon, lat, sample_kind) in enumerate(sample_points(feature["geometry"])):
            east, north = TO_SWEREF.transform(lon, lat)
            try:
                found = lookup(east, north, session)
                status, error = "ok", None
            except Exception as exc:
                found, status, error = [], "error", str(exc)
            request_count += 1
            observations.append({
                "sample_kind": sample_kind,
                "wgs84": {"lon": lon, "lat": lat},
                "sweref99tm": {"east": east, "north": north},
                "properties": found,
                "grasmyr_matches": [x for x in found if is_target_tract(x["designation"])],
                "status": status,
                **({"error": error} if error else {}),
            })
            if request_count < len(selected) * MAX_SAMPLES_PER_FEATURE:
                time.sleep(DELAY_SECONDS)

        unique = {}
        for obs in observations:
            for item in obs["properties"]:
                unique[item["designation"]] = item
        target = [item for item in unique.values() if is_target_tract(item["designation"])]
        results.append({
            "notification_id": props.get("Beteckn") or feature.get("id"),
            "objectid": feature.get("id"),
            "municipality": props.get("Kommun"),
            "notification_date": feature_date(feature).isoformat(),
            "reported_area_ha": props.get("AnmaldHa"),
            "geometry_type": feature["geometry"].get("type"),
            "distance_from_grasmyr_center_km": round(distance_km, 3),
            "sample_count": len(observations),
            "successful_samples": sum(o["status"] == "ok" for o in observations),
            "unique_properties_observed": sorted(unique),
            "unique_property_count": len(unique),
            "target_tract_matches": sorted(x["designation"] for x in target),
            "target_tract_match_count": len(target),
            "observations": observations,
            "interpretation": (
                "Gräsmyr candidate observed in sample(s); full polygon-to-property intersection is unverified."
                if target else
                "No Gräsmyr candidate observed in samples; this does not rule out polygon intersection."
            ),
        })

    # Link notifications using independent signals. Shared sample lookups are weak
    # evidence because the queried endpoint uses a buffer and may return neighbours.
    from shapely.ops import transform as shapely_transform

    feature_by_id = {str(feature.get("id")): feature for _, feature in selected}
    projected_geometries = {}
    for result in results:
        source_feature = feature_by_id.get(str(result["objectid"]))
        if source_feature and source_feature.get("geometry"):
            projected_geometries[str(result["objectid"])] = shapely_transform(
                TO_SWEREF.transform, shape(source_feature["geometry"])
            )

    notification_links = []
    for i, left in enumerate(results):
        for right in results[i + 1:]:
            left_geom = projected_geometries.get(str(left["objectid"]))
            right_geom = projected_geometries.get(str(right["objectid"]))
            if left_geom is None or right_geom is None:
                continue
            polygon_distance_m = float(left_geom.distance(right_geom))
            intersects = bool(left_geom.intersects(right_geom))
            shared_properties = sorted(
                set(left["target_tract_matches"]) & set(right["target_tract_matches"])
            )
            left_dt = datetime.fromisoformat(left["notification_date"])
            right_dt = datetime.fromisoformat(right["notification_date"])
            days_between = abs((left_dt - right_dt).total_seconds()) / 86400
            same_day = left_dt.date() == right_dt.date()

            # Candidate rule: strong geometry/date signal, or shared sampled candidates
            # only when the polygons are also geographically close.
            close_pair = polygon_distance_m <= 250
            same_day_close = same_day and polygon_distance_m <= 1000
            shared_close = bool(shared_properties) and close_pair and days_between <= 180
            if not (intersects or same_day_close or shared_close):
                continue

            signals = []
            if intersects:
                signals.append("notification_polygons_intersect")
            if close_pair:
                signals.append("notification_polygons_within_250m")
            if same_day:
                signals.append("same_notification_date")
            elif days_between <= 30:
                signals.append("notification_dates_within_30_days")
            if shared_properties:
                signals.append("shared_sampled_property_candidates")

            # Confidence only describes how strong the observed link is for review,
            # not probability of a shared operation.
            if intersects and days_between <= 90:
                priority = "high_review_priority"
            elif same_day_close and (shared_properties or close_pair):
                priority = "high_review_priority"
            elif shared_close:
                priority = "review_candidate"
            else:
                priority = "review_candidate"

            notification_links.append({
                "notification_a": left["notification_id"],
                "notification_b": right["notification_id"],
                "days_between_notification_dates": round(days_between, 1),
                "same_notification_date": same_day,
                "polygon_distance_m": round(polygon_distance_m, 1),
                "notification_polygons_intersect": intersects,
                "shared_property_candidates": shared_properties,
                "signals": signals,
                "review_priority": priority,
                "interpretation": "Spatial/temporal link for manual review only. Sampled property candidates are not confirmed parcel intersections and do not prove a shared harvesting operation, ownership, contractor, or cost-sharing.",
            })
    notification_links.sort(
        key=lambda x: (
            0 if x["review_priority"] == "high_review_priority" else 1,
            x["polygon_distance_m"],
            x["days_between_notification_dates"],
        )
    )

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "area_name": CONFIG.get("name"),
        "target_tract_prefix": CONFIG.get("property_tract_prefix"),
        "selection": f"Up to {MAX_FEATURES} Nordmaling notifications within {RADIUS_KM} km, ranked by polygon-centroid distance to configured Gräsmyr point.",
        "method": f"Up to {MAX_SAMPLES_PER_FEATURE} interior/boundary samples per polygon; Min karta results aggregated by designation.",
        "request_count": request_count,
        "delay_seconds_between_requests": DELAY_SECONDS,
        "candidate_notifications_in_radius": len(candidates),
        "features_tested": len(results),
        "target_tract_matches_total": sorted({d for r in results for d in r["target_tract_matches"]}),
        "notification_relationship_links_count": len(notification_links),
        "notification_relationship_links": notification_links,
        "limitations": [
            "Centroid distance is only used to rank notifications; it does not establish cadastral ownership.",
            "Sampling does not calculate exact polygon-to-cadastral-parcel intersections and may miss properties.",
            "A boundary sample can return a neighbouring property; results are candidate matches only.",
            "The Min karta endpoint is an observed internal web-app endpoint, not a documented public API; continued use should be checked against applicable terms.",
        ],
        "results": results,
    }
    out = ROOT / "data" / "property_lookup_pilot.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "checked_at": report["checked_at"],
        "candidate_notifications_in_radius": len(candidates),
        "features_tested": len(results),
        "request_count": request_count,
        "target_tract_matches_total": report["target_tract_matches_total"],
        "notification_relationship_links_count": len(notification_links),
        "high_review_priority_links_count": sum(x["review_priority"] == "high_review_priority" for x in notification_links),
        "sample_relationship_examples": notification_links[:10],
        "results": [{
            "notification_id": r["notification_id"],
            "distance_from_grasmyr_center_km": r["distance_from_grasmyr_center_km"],
            "unique_property_count": r["unique_property_count"],
            "unique_properties_observed": r["unique_properties_observed"],
            "target_tract_matches": r["target_tract_matches"],
            "successful_samples": r["successful_samples"],
        } for r in results],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
