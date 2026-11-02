#!/usr/bin/env python3
"""Build deterministic canonical events from the current planned-harvest register.

This first vertical slice deliberately excludes the completed-harvest polygon layer:
its Forebild/Efterbild metadata identifies it as satellite-derived evidence. Satellite
indications remain a later, lower-priority input and are not promoted to completed
harvest events by this builder.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LATEST = DATA / "latest.json"
HISTORY = DATA / "notification_history.json"
OUT = DATA / "harvest_event_bundle.json"
SOURCE_ID = "skogsstyrelsen.harvest_notifications"
INTERPRETATION_VERSION = "planned-harvest-event-v1"


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError):
        return None


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def build_bundle(latest: dict[str, Any], history: dict[str, Any] | None = None) -> dict[str, Any]:
    checked_at = timestamp(latest.get("checked_at"))
    cuts = latest.get("cutting_notifications") or {}
    features = cuts.get("features")
    if not checked_at or cuts.get("status") != "ok" or not isinstance(features, list):
        raise ValueError("Latest planned-harvest source snapshot is not a successful, timestamped result.")

    area = latest.get("area") or {}
    scope = {
        "source_url": cuts.get("url"),
        "area": {
            "latitude": area.get("latitude"),
            "longitude": area.get("longitude"),
            "radius_km": area.get("radius_km"),
        },
    }
    scope_hash = canonical_hash(scope)
    run_id = f"{SOURCE_ID}:{checked_at}:{scope_hash[:12]}"
    cases = (history or {}).get("cases") or {}

    source_run = {
        "run_id": run_id,
        "source_id": SOURCE_ID,
        "started_at": checked_at,
        "finished_at": checked_at,
        "status": "success",
        "scope_hash": scope_hash,
        "source_snapshot_at": None,
        "records_seen": len(features),
        "records_valid": len(features),
        "records_rejected": 0,
        "snapshot_ref": "data/latest.json#/cutting_notifications",
        "checksum": canonical_hash(features),
        "diagnostics": {
            "area": area.get("name"),
            "query_url": cuts.get("url"),
            "note": "Successful current source result. This local area snapshot is not the national archive.",
        },
    }

    observations = []
    events = []
    evidence = []
    chains = []
    seen_source_ids: set[str] = set()

    for feature in sorted(features, key=lambda item: str(item.get("id") or (item.get("properties") or {}).get("OBJECTID") or "")):
        props = feature.get("properties") or {}
        source_record_id = str(feature.get("id") or props.get("OBJECTID") or "")
        if not source_record_id:
            continue
        if source_record_id in seen_source_ids:
            raise ValueError(f"Duplicate source record ID in current snapshot: {source_record_id}")
        seen_source_ids.add(source_record_id)

        feature_hash = canonical_hash(feature)
        observation_id = f"obs:{SOURCE_ID}:{source_record_id}:{feature_hash[:16]}"
        event_id = f"planned-harvest:{source_record_id}"
        chain_id = f"harvest-chain:{source_record_id}"
        case = cases.get(source_record_id) or {}
        first_seen = timestamp(case.get("first_seen_at")) or checked_at
        last_seen = timestamp(case.get("last_seen_at")) or checked_at
        received = timestamp(props.get("Inkomdatum"))

        observations.append({
            "observation_id": observation_id,
            "source_id": SOURCE_ID,
            "source_record_id": source_record_id,
            "run_id": run_id,
            "observed_at": checked_at,
            "source_created_at": received,
            "source_updated_at": None,
            "valid_time": received,
            "content_hash": f"sha256:{feature_hash}",
            "raw_ref": f"data/latest.json#/cutting_notifications/features/{source_record_id}",
            "geometry_ref": f"data/latest.json#/cutting_notifications/features/{source_record_id}/geometry" if feature.get("geometry") else None,
            "geometry_crs": "EPSG:4326" if feature.get("geometry") else None,
            "quality_status": "valid",
            "attributes": props,
        })

        case_number = props.get("Beteckn") or source_record_id
        municipality = props.get("Kommun") or "kommun ej angiven"
        source_status = props.get("ArendeStatus") or "status ej angiven"
        area_ha = props.get("AnmaldHa")
        summary = (
            f"Skogsstyrelsen redovisar avverkningsanmälan {case_number} i {municipality}. "
            f"Källstatus: {source_status}. Detta är en registrerad anmälan, inte belägg för att avverkning har utförts."
        )
        events.append({
            "event_id": event_id,
            "event_type": "planned_harvest_notification",
            "event_status": "registered_in_source",
            "title": f"Avverkningsanmälan {case_number}",
            "summary": summary,
            "event_time_start": received,
            "event_time_end": None,
            "first_observed_at": first_seen,
            "last_observed_at": last_seen,
            "geometry_ref": f"data/latest.json#/cutting_notifications/features/{source_record_id}/geometry" if feature.get("geometry") else None,
            "confidence_class": "verified",
            "interpretation_version": INTERPRETATION_VERSION,
        })
        evidence.append({
            "event_id": event_id,
            "observation_id": observation_id,
            "evidence_role": "primary",
            "match_method": "same_source_record_id",
            "match_score": 100,
            "confidence_class": "verified",
            "reason_codes": ["source_record_exists", "same_source_record_id"],
            "review_status": "unreviewed",
        })
        chains.append({
            "chain_id": chain_id,
            "chain_type": "planned_harvest_follow_up",
            "primary_area_ref": f"observation:{observation_id}",
            "started_at": first_seen,
            "last_activity_at": last_seen,
            "chain_status": "open",
            "summary": f"Uppföljningskedja för avverkningsanmälan {case_number}. Fler oberoende källor kopplas på i nästa steg.",
            "confidence_class": "verified",
            "event_ids": [event_id],
        })

    if not observations:
        raise ValueError("No valid source records found; refusing to publish an empty event bundle.")
    source_run["records_valid"] = len(observations)
    source_run["records_rejected"] = len(features) - len(observations)

    return {
        "schema_version": 1,
        "generated_at": checked_at,
        "source_runs": [source_run],
        "observations": observations,
        "events": events,
        "evidence": evidence,
        "relationships": [],
        "chains": chains,
    }


def main() -> int:
    latest = load_json(LATEST)
    if not isinstance(latest, dict):
        print(f"ERROR: missing or invalid {LATEST}", file=sys.stderr)
        return 1
    history = load_json(HISTORY, {})
    try:
        bundle = build_bundle(latest, history if isinstance(history, dict) else {})
        sys.path.insert(0, str(ROOT / "data-platform" / "scripts"))
        from validate_event_bundle import SCHEMA, validate_bundle
        schema = load_json(SCHEMA)
        errors = validate_bundle(bundle, schema)
        if errors:
            raise ValueError("Event bundle validation failed: " + "; ".join(errors[:10]))
    except (ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(OUT.suffix + ".tmp")
    temporary.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUT)
    print(json.dumps({
        "output": str(OUT.relative_to(ROOT)),
        "source_records": bundle["source_runs"][0]["records_seen"],
        "canonical_events": len(bundle["events"]),
        "event_chains": len(bundle["chains"]),
        "relationships": len(bundle["relationships"]),
        "satellite_indications_included": False,
        "schema_validation": "passed",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
