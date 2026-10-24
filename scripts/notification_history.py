#!/usr/bin/env python3
"""Maintain durable history for cutting notifications.

A feature missing from a later successful query is recorded as "not_returned".
It is never inferred to be felled, cancelled, or deleted from the source.
Attribute and geometry changes are logged only across consecutive successful
snapshots with the same query scope.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
HISTORY_PATH = DATA / "notification_history.json"
EVENTS_PATH = DATA / "notification_history_events.jsonl"

# Keep this allow-list intentionally narrow and human-readable. We record changed
# keys and old/new values, but never infer what the change means operationally.
TRACKED_ATTRIBUTES = (
    "Beteckn",
    "Kommun",
    "Kommunnr",
    "ArendeStatus",
    "Avverktyp",
    "Inkomdatum",
    "AnmaldHa",
    "SkogsodlHa",
    "AvvHa",
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def feature_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    value = feature.get("id") or props.get("OBJECTID")
    return str(value) if value not in (None, "") else ""


def successful(snapshot: dict[str, Any]) -> bool:
    cuts = snapshot.get("cutting_notifications") or {}
    return cuts.get("status") == "ok" and isinstance(cuts.get("features"), list)


def scope_hash(snapshot: dict[str, Any]) -> str:
    cuts = snapshot.get("cutting_notifications") or {}
    area = snapshot.get("area") or {}
    query_url = str(cuts.get("url") or "").split("?")[0]
    scope = {
        "query_url": query_url,
        "latitude": area.get("latitude"),
        "longitude": area.get("longitude"),
        "radius_km": area.get("radius_km"),
    }
    return canonical_hash(scope)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def observed_attributes(feature: dict[str, Any]) -> dict[str, Any]:
    props = feature.get("properties") or {}
    return {key: props.get(key) for key in TRACKED_ATTRIBUTES if key in props}


def change_details(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any] | None:
    """Return a compact, explicit delta without assuming the change's meaning."""
    old_props = previous.get("properties") or {}
    new_props = current.get("properties") or {}
    changed = {}
    for key in TRACKED_ATTRIBUTES:
        if key not in old_props and key not in new_props:
            continue
        old_value = old_props.get(key)
        new_value = new_props.get(key)
        if old_value != new_value:
            changed[key] = {"old": old_value, "new": new_value}

    old_geometry_hash = canonical_hash(previous.get("geometry"))
    new_geometry_hash = canonical_hash(current.get("geometry"))
    geometry_changed = old_geometry_hash != new_geometry_hash
    if not changed and not geometry_changed:
        return None
    return {
        "changed_attributes": changed,
        "geometry_changed": geometry_changed,
        "previous_geometry_sha256": old_geometry_hash,
        "current_geometry_sha256": new_geometry_hash,
        "meaning": "Source record changed between comparable successful observations; operational meaning is not inferred.",
    }


def read_snapshots() -> list[tuple[str, dict[str, Any]]]:
    rows = []
    for path in SNAPSHOTS.glob("*.json"):
        snapshot = read_json(path, None)
        if isinstance(snapshot, dict) and successful(snapshot):
            rows.append((path.name, snapshot))
    rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))
    return rows


def build_history(snapshots: list[tuple[str, dict[str, Any]]],
                  previous: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cases: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    previous = previous or {}
    for key, value in (previous.get("cases") or {}).items():
        if isinstance(value, dict):
            cases[str(key)] = value

    prior_ids: set[str] | None = None
    prior_features: dict[str, dict[str, Any]] = {}
    prior_scope = None
    prior_time = None
    for filename, snapshot in snapshots:
        if not successful(snapshot):
            continue
        checked_at = str(snapshot.get("checked_at") or filename)
        scope = scope_hash(snapshot)
        current_features = {}
        for feature in (snapshot.get("cutting_notifications") or {}).get("features", []):
            key = feature_id(feature)
            if key:
                current_features[key] = feature
        ids = set(current_features)
        comparable = prior_ids is not None and scope == prior_scope

        if prior_ids is not None and not comparable:
            events.append({
                "event_type": "comparison_skipped_scope_changed",
                "observed_at": checked_at,
                "previous_observed_at": prior_time,
                "snapshot": filename,
                "meaning": "Query scope changed; presence/absence and record-change differences were not interpreted.",
            })

        if comparable:
            for key in sorted(ids - (prior_ids or set())):
                events.append({
                    "event_type": "reappeared_or_newly_observed",
                    "notification_id": key,
                    "observed_at": checked_at,
                    "previous_observed_at": prior_time,
                    "snapshot": filename,
                    "meaning": "Returned after a previous comparable successful query; application date is not inferred.",
                })
            for key in sorted((prior_ids or set()) - ids):
                events.append({
                    "event_type": "not_returned",
                    "notification_id": key,
                    "observed_at": checked_at,
                    "previous_observed_at": prior_time,
                    "snapshot": filename,
                    "meaning": "Absent from this successful query only; not evidence of felling, cancellation, deletion, or expiry.",
                })
            for key in sorted(ids & (prior_ids or set())):
                delta = change_details(prior_features[key], current_features[key])
                if delta:
                    events.append({
                        "event_type": "record_changed",
                        "notification_id": key,
                        "observed_at": checked_at,
                        "previous_observed_at": prior_time,
                        "previous_snapshot": None,
                        "snapshot": filename,
                        **delta,
                    })

        for key, feature in current_features.items():
            props = feature.get("properties") or {}
            record = cases.get(key, {})
            was_missing = record.get("observation_status") == "not_returned"
            old_hash = record.get("attribute_sha256")
            current_hash = canonical_hash(props)
            record.update({
                "notification_id": key,
                "first_seen_at": record.get("first_seen_at") or checked_at,
                "last_seen_at": checked_at,
                "observation_status": "observed",
                "last_query_scope_hash": scope,
                "last_snapshot": filename,
                "attributes": props,
                "tracked_attributes": observed_attributes(feature),
                "geometry_sha256": canonical_hash(feature.get("geometry")),
                "attribute_sha256": current_hash,
                "status_interpretation": "current_source_observation_only",
            })
            if was_missing:
                record["last_reappeared_at"] = checked_at
            if old_hash and old_hash != current_hash:
                record["last_attributes_changed_at"] = checked_at
            cases[key] = record

        if comparable:
            for key in sorted((prior_ids or set()) - ids):
                record = cases.get(key)
                if record is None:
                    continue
                if record.get("observation_status") != "not_returned":
                    record["first_not_returned_at"] = checked_at
                record["observation_status"] = "not_returned"
                record["last_not_returned_at"] = checked_at
                record["last_snapshot"] = filename

        prior_ids, prior_features, prior_scope, prior_time = ids, current_features, scope, checked_at

    for key, record in cases.items():
        record.setdefault("notification_id", key)
        record.setdefault("observation_status", "not_returned")
        record.setdefault("status_interpretation", "not_returned_is_not_felling_or_cancellation")

    result = {
        "generated_at": iso(now_utc()),
        "schema_version": 2,
        "snapshot_count_compared": len(snapshots),
        "case_count": len(cases),
        "source_status_semantics": {
            "observed": "Returned by a successful query in the configured search area.",
            "not_returned": "Previously observed but absent from a later comparable successful query.",
            "record_changed": "Selected source attributes or geometry changed between comparable successful observations; cause is not inferred.",
            "absence_never_means": ["felled", "cancelled", "deleted", "expired"],
        },
        "cases": dict(sorted(cases.items())),
        "events": events,
    }
    return result, events


def append_events(events: list[dict[str, Any]]) -> int:
    known = set()
    if EVENTS_PATH.exists():
        with EVENTS_PATH.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    known.add(canonical_hash(json.loads(line)))
                except json.JSONDecodeError:
                    continue
    added = 0
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        for event in events:
            digest = canonical_hash(event)
            if digest not in known:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                known.add(digest)
                added += 1
    return added


def main() -> None:
    DATA.mkdir(exist_ok=True)
    SNAPSHOTS.mkdir(exist_ok=True)
    previous = read_json(HISTORY_PATH, {})
    snapshots = read_snapshots()
    history, events = build_history(snapshots, previous)
    added = append_events(events)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(HISTORY_PATH.relative_to(ROOT)),
        "event_log": str(EVENTS_PATH.relative_to(ROOT)),
        "successful_snapshots": len(snapshots),
        "known_notifications": history["case_count"],
        "currently_observed": sum(x.get("observation_status") == "observed" for x in history["cases"].values()),
        "not_returned": sum(x.get("observation_status") == "not_returned" for x in history["cases"].values()),
        "changed_records_in_this_rebuild": sum(e.get("event_type") == "record_changed" for e in events),
        "new_events_appended": added,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
