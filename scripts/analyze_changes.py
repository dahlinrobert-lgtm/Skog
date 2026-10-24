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
from shapely.ops import transform, unary_union
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


def completed_archive_rows():
    """Return valid archived completed-change snapshots in chronological order."""
    rows = []
    for path in sorted(SNAPSHOTS.glob("completed_*.geojson.gz")):
        try:
            value = load_gzip_geojson(path)
            checked_at = value.get("checked_at")
            features_by_id = {}
            for feature in value.get("features", []):
                oid = feature_id(feature)
                if oid:
                    features_by_id[oid] = feature
            rows.append({
                "filename": path.name,
                "checked_at": checked_at,
                "features_by_id": features_by_id,
            })
        except (OSError, EOFError, json.JSONDecodeError):
            continue
    rows.sort(key=lambda row: str(row.get("checked_at") or row["filename"]))
    return rows


def evidence_transition_events(planned_map, planned_history):
    """Compare each current plan with consecutive comparable completed-layer snapshots.

    This records only newly observed or materially changed completed polygons that
    have a meaningful, temporally plausible overlap with a current planned polygon.
    A newly appearing layer feature is evidence to review, not proof of felling.
    """
    archives = completed_archive_rows()
    events = []
    if len(archives) < 2:
        return {
            "snapshot_count": len(archives),
            "comparable_pairs": 0,
            "events": [],
            "note": "At least two completed-layer archives are required to detect transitions.",
        }

    # Only compare archives with the same known query fingerprint. Older archives
    # without scope metadata are deliberately treated as incomparable to avoid
    # converting a search-area change into apparent source additions/removals.
    comparable_pairs = 0
    skipped_scope_pairs = []
    for before, after in zip(archives, archives[1:]):
        if before.get("checked_at") == after.get("checked_at"):
            continue
        before_scope = before.get("query_scope_sha256")
        after_scope = after.get("query_scope_sha256")
        if not before_scope or not after_scope or before_scope != after_scope:
            skipped_scope_pairs.append({
                "before_snapshot": before["filename"],
                "after_snapshot": after["filename"],
                "before_scope_sha256": before_scope,
                "after_scope_sha256": after_scope,
                "reason": "Completed-layer query scope is missing or changed; source differences are not interpreted as evidence transitions.",
            })
            continue
        comparable_pairs += 1
        before_ids = set(before["features_by_id"])
        after_ids = set(after["features_by_id"])
        added_ids = after_ids - before_ids
        changed_ids = {
            oid for oid in before_ids & after_ids
            if canonical_feature_hash(before["features_by_id"][oid]) !=
               canonical_feature_hash(after["features_by_id"][oid])
        }

        if not added_ids and not changed_ids:
            continue

        for planned_id, planned_feature in planned_map.items():
            planned_geom = valid_geometry(planned_feature)
            if planned_geom is None or planned_geom.area <= 0:
                continue
            props = planned_feature.get("properties") or {}
            received_dt = parse_epoch_ms(props.get("Inkomdatum"))
            if received_dt is None:
                continue

            for oid in sorted(added_ids | changed_ids):
                done_feature = after["features_by_id"][oid]
                done_props = done_feature.get("properties") or {}
                done_geom = valid_geometry(done_feature)
                if done_geom is None or not planned_geom.intersects(done_geom):
                    continue
                inter = planned_geom.intersection(done_geom).area
                if inter <= 0:
                    continue
                planned_share = inter / planned_geom.area
                done_share = inter / done_geom.area if done_geom.area > 0 else 0
                meaningful = inter >= 0.02 * 10000 and max(planned_share, done_share) >= 0.15
                completed_dt = parse_epoch_ms(done_props.get("Avvdatum"))
                in_window = bool(
                    completed_dt and received_dt <= completed_dt <= received_dt + timedelta(days=3 * 365 + 1)
                )
                if not meaningful or not in_window:
                    continue

                previous_feature = before["features_by_id"].get(oid)
                event_type = "new_completed_detection_overlap" if oid in added_ids else "completed_detection_changed_overlap"
                events.append({
                    "event_type": event_type,
                    "planned_object_id": planned_id,
                    "case_number": props.get("Beteckn"),
                    "municipality": props.get("Kommun"),
                    "completed_object_id": oid,
                    "before_snapshot": before["filename"],
                    "after_snapshot": after["filename"],
                    "before_checked_at": before.get("checked_at"),
                    "after_checked_at": after.get("checked_at"),
                    "planned_area_ha": props.get("AnmaldHa"),
                    "intersection_ha": round(inter / 10000, 3),
                    "planned_overlap_pct": round(planned_share * 100, 1),
                    "completed_overlap_pct": round(done_share * 100, 1),
                    "completed_date": done_props.get("Avvdatum"),
                    "geometry_changed": bool(
                        previous_feature is not None and
                        canonical_feature_hash(previous_feature.get("geometry")) !=
                        canonical_feature_hash(done_feature.get("geometry"))
                    ),
                    "attributes_changed": bool(
                        previous_feature is not None and
                        canonical_feature_hash(previous_feature.get("properties")) !=
                        canonical_feature_hash(done_feature.get("properties"))
                    ),
                    "meaning": "New or changed satellite-based completed-harvest layer evidence; manually review, not proof of execution.",
                })

    # Identical records can be seen in multiple archives only if they were new or
    # changed each time. Keep one event for each plan/detection/observation transition.
    unique = {}
    for event in events:
        key = (
            event["event_type"], event["planned_object_id"], event["completed_object_id"],
            event["before_snapshot"], event["after_snapshot"],
        )
        unique[key] = event
    ordered = sorted(unique.values(), key=lambda e: (
        str(e.get("after_checked_at") or ""),
        str(e.get("case_number") or ""),
        str(e.get("completed_object_id") or ""),
    ))
    return {
        "snapshot_count": len(archives),
        "comparable_pairs": comparable_pairs,
        "skipped_scope_pairs": skipped_scope_pairs,
        "events": ordered,
        "note": "Only archives with matching, known query-scope fingerprints are compared. Transitions require meaningful spatial overlap and completed date within three years of notification. The source is satellite-based guidance, not ground truth.",
    }


def canonical_feature_hash(feature):
    """Deterministic representation used to detect any archived feature change."""
    return json.dumps(feature, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


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
    evidence_transitions = evidence_transition_events(planned_map, planned_history)
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
        # Match score ranks candidates; it is a transparent heuristic, not a probability.
        for candidate in candidates:
            score = 0
            if candidate["meaningful"]:
                score += 25
                score += min(30, candidate["completed_overlap_pct"] * 0.30)
                score += min(20, candidate["planned_overlap_pct"] * 0.20)
            if candidate["within_3_year_window"]:
                score += 15
            if props.get("Kommun") and candidate.get("completed_municipality") and str(props.get("Kommun")).casefold() == str(candidate["completed_municipality"]).casefold():
                score += 10
            candidate["match_score"] = round(min(100, score), 1)
        candidates.sort(key=lambda x: (x["match_score"], x["intersection_ha"]), reverse=True)
        strong_candidates = [c for c in candidates if c["meaningful"] and c["within_3_year_window"] and c["match_score"] >= 65]
        best = strong_candidates[0] if strong_candidates else (candidates[0] if candidates else None)

        # Do not add pairwise intersection areas: completed polygons may overlap.
        # Compute unique coverage by unioning eligible polygons and clipping to plan.
        # Use only confident candidates for coverage so weak spatial coincidences
        # don't count as completed felling. Union prevents overlapping detections
        # from double-counting the same ground area.
        eligible_ids = {
            c["completed_object_id"] for c in strong_candidates
        }
        eligible_geometries = [
            done["geometry"] for done in completed_index
            if done["id"] in eligible_ids and done["geometry"].intersects(planned_geom)
        ]
        if eligible_geometries:
            covered_geometry = unary_union(eligible_geometries).intersection(planned_geom)
            unique_covered_ha = covered_geometry.area / 10000
            unique_covered_pct = min(100.0, unique_covered_ha / (planned_geom.area / 10000) * 100)
        else:
            unique_covered_ha = 0.0
            unique_covered_pct = 0.0
        age_days = max(0, (datetime.now(timezone.utc) - received_dt).days) if received_dt else None
        strong_ids = {c["completed_object_id"] for c in strong_candidates}
        if strong_candidates:
            total_overlap_ha = sum(c["intersection_ha"] for c in strong_candidates)
            covered_pct = min(100.0, sum(c["planned_overlap_pct"] for c in strong_candidates))
            if len(strong_candidates) > 1:
                follow_status = "likely_multiple_or_partial"
            elif best and best["planned_overlap_pct"] < 80:
                follow_status = "likely_partial"
            else:
                follow_status = "likely_completed"
        elif age_days is not None and age_days >= 730:
            follow_status = "old_no_detection"
            total_overlap_ha = 0
            covered_pct = 0
        elif age_days is not None and age_days >= 365:
            follow_status = "follow_up_no_detection"
            total_overlap_ha = 0
            covered_pct = 0
        else:
            follow_status = "awaiting_evidence"
            total_overlap_ha = 0
            covered_pct = 0
        first_seen = None
        for snap_name, snap_data, snap_map in planned_history:
            if object_id in snap_map:
                first_seen = snap_data.get("checked_at")
                break
        planned_checks.append({
            "planned_object_id": object_id,
            "case_number": props.get("Beteckn"),
            "municipality": props.get("Kommun"),
            "received_date": date_value,
            "planned_area_ha": props.get("AnmaldHa"),
            "status": status,
            "follow_up_status": follow_status,
            "match_score": best["match_score"] if best else 0,
            "best_match_id": best["completed_object_id"] if best and strong_candidates else None,
            "strong_match_count": len(strong_candidates),
            "age_days": age_days,
            "first_seen_at": first_seen,
            "last_checked_at": current.get("checked_at"),
            "completed_overlap_ha_sum": round(total_overlap_ha, 3),
            "estimated_plan_coverage_pct": round(covered_pct, 1),
            "unique_union_covered_ha": round(unique_covered_ha, 3),
            "unique_union_plan_coverage_pct": round(unique_covered_pct, 1),
            "union_candidate_count": len(eligible_geometries),
            "completed_candidate_count": len(candidates),
            "best_candidates": candidates[:5],
        })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "area": current.get("area"),
        "method": {
            "projection": "EPSG:3006",
            "spatial_test": "polygon intersection; unique coverage uses union of eligible completed polygons clipped to each planned polygon",
            "area_accounting": "Pairwise overlap sums are diagnostic only. unique_union_covered_ha and unique_union_plan_coverage_pct are the deduplicated union measures. Only meaningful spatial candidates within the three-year window contribute.",
            "time_window": "A completed polygon is temporally plausible when its Avvdatum is between the planned Inkomdatum and three years after it. Missing/unparseable dates are not counted as time-window matches.",
            "meaningful_overlap_threshold": "intersection >= 0.02 ha and overlap share >= 15% of at least one polygon",
            "completed_layer_warning": "Satellite-based change-detection layer. Spatial overlaps are candidates for manual review, not proof that a planned case was executed.",
            "missing_planned_id_warning": "An ID missing from a later query is only not returned by the current query; it does not prove deletion, expiry, or felling.",
            "follow_up_status_method": "Follow-up status is a heuristic: strong match requires meaningful overlap, date within 3 years and score >=65; no-detection labels depend on age since notification, not proof that felling did not occur. Candidate score is a ranking aid, not a probability.",
            "match_score_formula": "0-100 heuristic: meaningful overlap +25, completed polygon coverage up to +30, planned polygon coverage up to +20, plausible timing +15, same municipality +10."
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
            "likely_completed": sum(r["follow_up_status"] == "likely_completed" for r in planned_checks),
            "likely_partial": sum(r["follow_up_status"] == "likely_partial" for r in planned_checks),
            "likely_multiple_or_partial": sum(r["follow_up_status"] == "likely_multiple_or_partial" for r in planned_checks),
            "follow_up_no_detection": sum(r["follow_up_status"] == "follow_up_no_detection" for r in planned_checks),
            "old_no_detection": sum(r["follow_up_status"] == "old_no_detection" for r in planned_checks),
            "awaiting_evidence": sum(r["follow_up_status"] == "awaiting_evidence" for r in planned_checks),
            "completed_geometries_loaded": len(completed_geometries),
            **dict(counts),
        },
        "planned_persistence_events": persistence_events,
        "incomparable_snapshot_pairs": incomparable_snapshot_pairs,
        "completed_evidence_transitions": evidence_transitions,
        "planned_vs_completed": sorted(planned_checks, key=lambda row: (
            {"likely_completed": 0, "likely_partial": 1, "likely_multiple_or_partial": 2, "follow_up_no_detection": 3, "old_no_detection": 4, "awaiting_evidence": 5}.get(row.get("follow_up_status"), 6),
            -row.get("match_score", 0),
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
        "planned_with_meaningful_overlap_within_3_years": counts["planned_with_meaningful_overlap_within_3_years"],
        "planned_with_meaningful_overlap_outside_3_years": counts["planned_with_meaningful_overlap_outside_3_years"],
        "planned_with_only_weak_overlap": counts["planned_with_only_weak_overlap"],
        "planned_without_current_overlap": counts["planned_without_current_overlap"],
        "follow_up_status_counts": {key: sum(r["follow_up_status"] == key for r in planned_checks) for key in ["likely_completed", "likely_partial", "likely_multiple_or_partial", "follow_up_no_detection", "old_no_detection", "awaiting_evidence"]},
        "persistence_change_events": len(persistence_events),
        "completed_evidence_transition_events": len(evidence_transitions["events"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
