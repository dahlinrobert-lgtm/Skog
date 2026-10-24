#!/usr/bin/env python3
"""Compare planned-notification snapshots with completed-harvest snapshots.

This is a diagnostic, not a definitive proof of felling or source deletion.
It computes spatial overlap between planned polygons present in the latest
planned layer and the current completed-harvest polygons, and summarizes
planned-object persistence across saved daily snapshots where available.
"""
import gzip
import json
from urllib.parse import unquote
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
OUT = DATA / "change_analysis.json"
# SWEREF99 TM, metres, for area and distance calculations.
TO_TM = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True).transform


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_gzip_geojson(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def feature_id(feature):
    props = feature.get("properties") or {}
    return str(feature.get("id") or props.get("OBJECTID") or "")


def valid_geometry(feature):
    try:
        geometry = shape(feature.get("geometry"))
        if geometry.is_empty or not geometry.is_valid:
            geometry = geometry.buffer(0)
        if geometry.is_empty:
            return None
        return transform(TO_TM, geometry)
    except Exception:
        return None


def parse_epoch_ms(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def query_scope(snapshot):
    url = unquote(str((snapshot.get("cutting_notifications") or {}).get("url") or "")).lower()
    if "geometrytype=esrigeometryenvelope" in url:
        return "bounding_box"
    if "distance=10000" in url and "esrigeometrypoint" in url:
        return "radius_10km"
    return "unknown"


def get_notification_map(snapshot):
    features = (snapshot.get("cutting_notifications") or {}).get("features") or []
    return {feature_id(feature): feature for feature in features if feature_id(feature)}


def main():
    current_path = DATA / "latest.json"
    completed_path = DATA / "completed_latest.json"
    if not current_path.exists() or not completed_path.exists():
        raise SystemExit("Missing data/latest.json or data/completed_latest.json; run the monitor first.")

    current = load_json(current_path)
    completed = load_json(completed_path)
    planned_map = get_notification_map(current)
    completed_map = completed.get("features_by_id") or {}

    # Read all complete planned snapshots; the initial 09:31 file was an
    # interrupted/incomplete upload in the early project setup, so unreadable
    # files are counted and skipped instead of aborting the report.
    planned_history = []
    unreadable_snapshots = []
    for path in sorted(SNAPSHOTS.glob("*.json")):
        try:
            value = load_json(path)
            if value.get("cutting_notifications", {}).get("status") != "ok":
                continue
            planned_history.append((path.name, value, get_notification_map(value)))
        except (OSError, json.JSONDecodeError):
            unreadable_snapshots.append(path.name)
    planned_history.sort(key=lambda item: item[1].get("checked_at") or "")

    # Consecutive saved history comparisons: new/missing identities in the
    # planned layer. Missing is intentionally called "not returned", not deleted.
    persistence_events = []
    incomparable_snapshot_pairs = []
    for (prev_name, prev_data, prev_map), (next_name, next_data, next_map) in zip(planned_history, planned_history[1:]):
        prev_scope = query_scope(prev_data)
        next_scope = query_scope(next_data)
        if prev_scope != next_scope:
            incomparable_snapshot_pairs.append({
                "from_snapshot": prev_name,
                "to_snapshot": next_name,
                "from_scope": prev_scope,
                "to_scope": next_scope,
                "reason": "The query geometry/scope changed between snapshots; ID differences are not interpreted as source changes.",
            })
            continue
        appeared = sorted(set(next_map) - set(prev_map))
        missing = sorted(set(prev_map) - set(next_map))
        if appeared or missing:
            persistence_events.append({
                "from_snapshot": prev_name,
                "to_snapshot": next_name,
                "scope": next_scope,
                "from_checked_at": prev_data.get("checked_at"),
                "to_checked_at": next_data.get("checked_at"),
                "appeared_count": len(appeared),
                "not_returned_count": len(missing),
                "appeared_ids": appeared[:100],
                "not_returned_ids": missing[:100],
            })

    # Match current planned polygons to current completed polygons using projected
    # geometry. Spatial relation is evidence for review only; there is no assumption
    # that the planned and completed records represent the same case.
    completed_geometries = []
    skipped_completed = 0
    for object_id, item in completed_map.items():
        geometry_hash = item.get("geometry_sha256")
        # Full geometry comes from latest compressed archive, loaded below.
        if not geometry_hash:
            skipped_completed += 1
    archives = sorted(SNAPSHOTS.glob("completed_*.geojson.gz"))
    latest_archive = archives[-1] if archives else None
    if latest_archive:
        archived = load_gzip_geojson(latest_archive)
        for feature in archived.get("features", []):
            oid = feature_id(feature)
            geom = valid_geometry(feature)
            if oid and geom is not None:
                props = feature.get("properties") or {}
                completed_geometries.append({
                    "id": oid, "geometry": geom,
                    "date": props.get("Avvdatum"),
                    "area_ha": props.get("Arealha"),
                    "municipality": props.get("Kommun"),
                    "image_before": props.get("Forebild"),
                    "image_after": props.get("Efterbild"),
                })
    completed_by_id = {entry["id"]: entry for entry in completed_geometries}

    latest_by_id = {entry["id"]: entry for entry in completed_geometries}
    completed_index = list(latest_by_id.values())
    planned_checks = []
    counts = Counter()
    threshold_area_ha = 0.02
    min_overlap_share = 0.15

    for object_id, feature in planned_map.items():
        planned_geom = valid_geometry(feature)
        props = feature.get("properties") or {}
        date_value = props.get("Inkomdatum")
        if planned_geom is None:
            counts["invalid_planned_geometry"] += 1
            continue
        if planned_geom.area <= 0:
            counts["zero_area_planned"] += 1
            continue
        candidates = []
        received_dt = parse_epoch_ms(date_value)
        for done in completed_index:
            if not planned_geom.intersects(done["geometry"]):
                continue
            intersection_area = planned_geom.intersection(done["geometry"]).area
            if intersection_area <= 0:
                continue
            planned_share = intersection_area / planned_geom.area
            done_share = intersection_area / done["geometry"].area if done["geometry"].area > 0 else 0
            meaningful = intersection_area >= threshold_area_ha * 10000 and max(planned_share, done_share) >= min_overlap_share
            completed_dt = parse_epoch_ms(done["date"])
            within_time_window = bool(
                received_dt and completed_dt and
                received_dt <= completed_dt <= received_dt + timedelta(days=3 * 365 + 1)
            )
            candidates.append({
                "completed_object_id": done["id"],
                "intersection_ha": round(intersection_area / 10000, 4),
                "planned_overlap_pct": round(planned_share * 100, 1),
                "completed_overlap_pct": round(done_share * 100, 1),
                "meaningful": meaningful,
                "within_3_year_window": within_time_window,
                "completed_date": done["date"],
                "completed_area_ha": done["area_ha"],
                "completed_municipality": done["municipality"],
                "forebild": done["image_before"],
                "efterbild": done["image_after"],
            })
        candidates.sort(key=lambda x: (x["within_3_year_window"], x["meaningful"], x["intersection_ha"]), reverse=True)
        temporal_good = [candidate for candidate in candidates if candidate["meaningful"] and candidate["within_3_year_window"]]
        good = [candidate for candidate in candidates if candidate["meaningful"]]
        if temporal_good:
            counts["planned_with_meaningful_overlap_within_3_years"] += 1
            status = "meaningful_overlap_within_3_years"
        elif good:
            counts["planned_with_meaningful_overlap_outside_3_years"] += 1
            status = "meaningful_overlap_outside_3_years"
        elif candidates:
            counts["planned_with_only_weak_overlap"] += 1
            status = "weak_overlap_only"
        else:
            counts["planned_without_current_overlap"] += 1
            status = "no_current_geometric_overlap"
        planned_checks.append({
            "planned_object_id": object_id,
            "case_number": props.get("Beteckn"),
            "municipality": props.get("Kommun"),
            "received_date": date_value,
            "planned_area_ha": props.get("AnmaldHa"),
            "status": status,
            "completed_candidate_count": len(candidates),
            "best_candidates": candidates[:5],
        })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "area": current.get("area"),
        "method": {
            "projection": "EPSG:3006",
            "spatial_test": "polygon intersection",
            "time_window": "A completed polygon is temporally plausible when its Avvdatum is between the planned Inkomdatum and three years after it. Missing/unparseable dates are not counted as time-window matches.",
            "meaningful_overlap_threshold": "intersection >= 0.02 ha and overlap share >= 15% of at least one polygon",
            "completed_layer_warning": "Satellite-based change-detection layer. Spatial overlaps are candidates for manual review, not proof that a planned case was executed.",
            "missing_planned_id_warning": "An ID missing from a later query is only not returned by the current query; it does not prove deletion, expiry, or felling.",
        },
        "sources": {
            "latest_planned_checked_at": current.get("checked_at"),
            "latest_completed_checked_at": completed.get("checked_at"),
            "completed_archive": latest_archive.name if latest_archive else None,
            "planned_snapshots_read": len(planned_history),
            "unreadable_snapshots": unreadable_snapshots,
        },
        "counts": {
            "current_planned_features": len(planned_map),
            "current_completed_features": len(completed_map),
            "completed_geometries_loaded": len(completed_geometries),
            **dict(counts),
        },
        "planned_persistence_events": persistence_events,
        "incomparable_snapshot_pairs": incomparable_snapshot_pairs,
        "planned_vs_completed": sorted(planned_checks, key=lambda row: (
            row["status"] != "meaningful_overlap_candidate",
            -(row["best_candidates"][0]["intersection_ha"] if row["best_candidates"] else 0),
            row["case_number"] or "",
        )),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "planned_snapshots_read": len(planned_history),
        "unreadable_snapshots": len(unreadable_snapshots),
        "planned_features": len(planned_map),
        "completed_features": len(completed_map),
        "completed_geometries_loaded": len(completed_geometries),
        "planned_with_meaningful_completed_overlap": counts["planned_with_meaningful_completed_overlap"],
        "planned_with_only_weak_overlap": counts["planned_with_only_weak_overlap"],
        "planned_without_current_overlap": counts["planned_without_current_overlap"],
        "persistence_change_events": len(persistence_events),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
