#!/usr/bin/env python3
"""Audit consistency between Länsstyrelsen diary state and append-only events."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def audit_history(state_path: Path, events_path: Path) -> dict[str, Any]:
    state = load_json(state_path, {"records": {}})
    records = state.get("records", {})
    events = []
    if events_path.exists():
        for line_number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                return {
                    "ok": False, "error": "invalid_event_json",
                    "line": line_number, "detail": str(exc),
                }
            if not isinstance(event, dict):
                return {
                    "ok": False, "error": "invalid_event_shape",
                    "line": line_number, "detail": "Each JSONL event must be a JSON object.",
                }
            event["_line_number"] = line_number
            events.append(event)

    event_ids = [e.get("event_id") for e in events if e.get("event_id")]
    duplicate_event_ids = sorted(k for k, n in Counter(event_ids).items() if n > 1)
    events_by_key: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        key = event.get("record_key")
        if key:
            events_by_key.setdefault(str(key), []).append(event)

    event_keys_without_state = sorted(str(key) for key in events_by_key if str(key) not in records)
    first_seen_without_state = sorted(
        str(key) for key in events_by_key
        if str(key) not in records and any(e.get("event_type") == "first_seen" for e in events_by_key[str(key)])
    )
    allowed_event_types = {"first_seen", "observed", "record_changed"}
    unknown_event_types = sorted({
        str(e.get("event_type") or "unknown") for e in events
        if e.get("event_type") not in allowed_event_types
    })
    missing_first_seen = []
    count_mismatches = []
    for key, record in records.items():
        record_events = events_by_key.get(key, [])
        first_seen = sum(e.get("event_type") == "first_seen" for e in record_events)
        observed = sum(e.get("event_type") == "observed" for e in record_events)
        changed = sum(e.get("event_type") == "record_changed" for e in record_events)
        event_total = first_seen + observed + changed
        if first_seen == 0:
            missing_first_seen.append(key)
        # Existing state may predate observation-event logging. Report the gap without
        # manufacturing retroactive events or rewriting historical counts.
        if event_total != int(record.get("observation_count", 0) or 0):
            count_mismatches.append({
                "record_key": key,
                "diary_number": record.get("diary_number"),
                "diary": record.get("diary"),
                "observation_count": int(record.get("observation_count", 0) or 0),
                "event_count": event_total,
                "unexplained_observations": int(record.get("observation_count", 0) or 0) - event_total,
                "first_observed_at": record.get("first_observed_at"),
                "last_observed_at": record.get("last_observed_at"),
            })

    invalid_record_keys = sorted(
        key for key, record in records.items()
        if key != record.get("record_key")
        or not str(record.get("diary_number") or "").strip()
        or not str(record.get("diary") or "").strip()
    )
    report = {
        "schema_version": 1,
        "state_record_count": len(records),
        "event_row_count": len(events),
        "event_types": dict(Counter(e.get("event_type", "unknown") for e in events)),
        "duplicate_event_ids": duplicate_event_ids,
        "event_keys_without_state_record": event_keys_without_state,
        "first_seen_events_without_state_record": first_seen_without_state,
        "unknown_event_types": unknown_event_types,
        "records_missing_first_seen_event": sorted(missing_first_seen),
        "records_with_observation_count_mismatch": count_mismatches,
        "invalid_record_keys": invalid_record_keys,
        "absent_ids_interpreted_as_removed": False,
    }
    report["ok"] = not (
        duplicate_event_ids or event_keys_without_state or unknown_event_types or first_seen_without_state or missing_first_seen or invalid_record_keys
    )
    report["legacy_observation_count_mismatches"] = len(count_mismatches)
    report["note"] = (
        "Observation-count mismatches can be legacy gaps from before repeated observations "
        "were written to events.jsonl; do not invent retroactive events to conceal the gap."
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit_history(args.state, args.events)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if report.get("error"):
        raise SystemExit(2)
    if not report.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
