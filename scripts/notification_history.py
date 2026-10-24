#!/usr/bin/env python3
"""Maintain durable history for cutting notifications.

A feature missing from a later successful query is recorded as "not_returned"
only when consecutive successful queries have the same spatial/query scope. If
the scope changes, IDs omitted by the new query become "scope_changed", not
"not_returned". Attribute and geometry changes are logged only across comparable
snapshots. The event JSONL is derived from saved snapshots and rewritten on each
run so obsolete events from earlier faulty comparability logic can be corrected.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from snapshot_store import read_snapshot_rows

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
HISTORY_PATH = DATA / "notification_history.json"
EVENTS_PATH = DATA / "notification_history_events.jsonl"

# Query parameters that can change which features are returned or which parts
# of a source record are comparable. Tracking these prevents bbox/radius (or
# other query) transitions from being mistaken for source-register changes.
SCOPE_QUERY_KEYS = (
    "where",
    "geometry",
    "geometryType",
    "inSR",
    "spatialRel",
    "distance",
    "units",
    "relation",
    "time",
    "objectIds",
    "historicMoment",
    "outFields",
    "returnGeometry",
)

# Keep the attribute change log intentionally narrow and human-readable.
TRACKED_ATTRIBUTES = (
    "Beteckn",
    "Kommun",
    "Kommunnr",
    "ArendeStatus",
    "Avverktyp",
    "Inkomdatum",
    "AnmaldHa",
    "SkogsodlHa",
    "NatforHa",
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


def _normalized_query_parameters(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    parsed_values = parse_qs(parsed.query, keep_blank_values=True)
    normalized: dict[str, Any] = {}
    for key in SCOPE_QUERY_KEYS:
        if key not in parsed_values:
            continue
        values: list[Any] = []
        for value in parsed_values[key]:
            if key == "geometry":
                try:
                    values.append(json.loads(value))
                    continue
                except (ValueError, TypeError):
                    pass
            values.append(value)
        normalized[key] = values[0] if len(values) == 1 else values
    return {"endpoint": f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}", "parameters": normalized}


def scope_hash(snapshot: dict[str, Any]) -> str:
    """Fingerprint configured area plus query filters/geometry, not query ordering."""
    cuts = snapshot.get("cutting_notifications") or {}
    area = snapshot.get("area") or {}
    scope = {
        "query": _normalized_query_parameters(str(cuts.get("url") or "")),
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
    # Reconstruct both legacy full snapshots and new delta snapshots.
    return [
        (filename, snapshot)
        for filename, snapshot in read_snapshot_rows(SNAPSHOTS)
        if successful(snapshot)
    ]


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
    prior_filename = None
    seen_in_scope_run: set[str] = set()

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
            seen_in_scope_run = set(ids)
            missing_due_to_scope = sorted((prior_ids or set()) - ids)
            events.append({
                "event_type": "comparison_skipped_scope_changed",
                "observed_at": checked_at,
                "previous_observed_at": prior_time,
                "previous_snapshot": prior_filename,
                "snapshot": filename,
                "previous_scope_sha256": prior_scope,
                "current_scope_sha256": scope,
                "omitted_previous_ids_count": len(missing_due_to_scope),
                "meaning": "Query filters or spatial scope changed; omitted IDs are not treated as source-register changes.",
            })
            # These IDs were present in the old query but not the new one. Record
            # the scope transition explicitly instead of leaving a stale 'observed'
            # state or falsely labelling them as not_returned.
            for key in missing_due_to_scope:
                record = cases.get(key)
                if record is not None:
                    record["observation_status"] = "scope_changed"
                    record["scope_changed_at"] = checked_at
                    record["current_query_scope_hash"] = scope
                    record["status_interpretation"] = "search_scope_changed_not_source_absence"
                events.append({
                    "event_type": "scope_changed",
                    "notification_id": key,
                    "observed_at": checked_at,
                    "previous_observed_at": prior_time,
                    "previous_snapshot": prior_filename,
                    "snapshot": filename,
                    "meaning": "ID was omitted after a query-scope change; this is not evidence of source disappearance or felling.",
                })

        if comparable:
            for key in sorted(ids - (prior_ids or set())):
                previously_seen_in_run = key in seen_in_scope_run
                if previously_seen_in_run:
                    record = cases.get(key)
                    if record is not None:
                        record["last_reappeared_at"] = checked_at
                events.append({
                    "event_type": "reappeared_or_newly_observed",
                    "notification_id": key,
                    "observed_at": checked_at,
                    "previous_observed_at": prior_time,
                    "previous_snapshot": prior_filename,
                    "snapshot": filename,
                    "previously_seen_in_scope_run": previously_seen_in_run,
                    "meaning": "Returned in the current query after being absent from the prior comparable query; application date is not inferred.",
                })
            for key in sorted((prior_ids or set()) - ids):
                events.append({
                    "event_type": "not_returned",
                    "notification_id": key,
                    "observed_at": checked_at,
                    "previous_observed_at": prior_time,
                    "previous_snapshot": prior_filename,
                    "snapshot": filename,
                    "meaning": "Absent from this successful comparable query only; not evidence of felling, cancellation, deletion, or expiry.",
                })
            for key in sorted(ids & (prior_ids or set())):
                delta = change_details(prior_features[key], current_features[key])
                if delta:
                    events.append({
                        "event_type": "record_changed",
                        "notification_id": key,
                        "observed_at": checked_at,
                        "previous_observed_at": prior_time,
                        "previous_snapshot": prior_filename,
                        "snapshot": filename,
                        **delta,
                    })

        for key, feature in current_features.items():
            props = feature.get("properties") or {}
            record = cases.get(key, {})
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
                record["last_query_scope_hash"] = scope
                record["status_interpretation"] = "not_returned_is_not_felling_or_cancellation"

        seen_in_scope_run.update(ids)
        prior_ids, prior_features, prior_scope, prior_time, prior_filename = ids, current_features, scope, checked_at, filename

    for key, record in cases.items():
        record.setdefault("notification_id", key)
        record.setdefault("observation_status", "not_returned")
        record.setdefault("status_interpretation", "not_returned_is_not_felling_or_cancellation")

    result = {
        "generated_at": iso(now_utc()),
        "schema_version": 3,
        "snapshot_count_compared": len(snapshots),
        "case_count": len(cases),
        "event_log_semantics": "Derived from successful saved snapshots and rewritten on each run; saved snapshots are the source of truth.",
        "source_status_semantics": {
            "observed": "Returned by the latest processed successful query.",
            "not_returned": "Absent from a later comparable successful query; not proof of source deletion or felling.",
            "scope_changed": "Absent after a query-scope change; not comparable as a source-register disappearance.",
            "record_changed": "Selected source attributes or geometry changed between comparable successful observations; cause is not inferred.",
            "absence_never_means": ["felled", "cancelled", "deleted", "expired"],
        },
        "cases": dict(sorted(cases.items())),
        "events": events,
    }
    return result, events


def write_event_log(events: list[dict[str, Any]], path: Path = EVENTS_PATH) -> int:
    """Write a complete event ledger derived from snapshots, removing obsolete derived events."""
    serialized = "".join(
        json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        for event in events
    )
    old_content = None
    try:
        old_content = path.read_text(encoding="utf-8")
    except OSError:
        pass
    if old_content != serialized:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    return len(events)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    SNAPSHOTS.mkdir(exist_ok=True)
    previous = read_json(HISTORY_PATH, {})
    snapshots = read_snapshots()
    history, events = build_history(snapshots, previous)
    written = write_event_log(events)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(HISTORY_PATH.relative_to(ROOT)),
        "event_log": str(EVENTS_PATH.relative_to(ROOT)),
        "successful_snapshots": len(snapshots),
        "known_notifications": history["case_count"],
        "currently_observed": sum(x.get("observation_status") == "observed" for x in history["cases"].values()),
        "scope_changed": sum(x.get("observation_status") == "scope_changed" for x in history["cases"].values()),
        "not_returned": sum(x.get("observation_status") == "not_returned" for x in history["cases"].values()),
        "record_changed_events": sum(e.get("event_type") == "record_changed" for e in events),
        "derived_events_written": written,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
