#!/usr/bin/env python3
"""Build an auditable, source-separated event timeline for prescribed-burn monitoring.

This deliberately keeps diary records and Life2Taiga geometries as separate events
until a defensible link is established. A diary title is evidence of a case/action,
not proof that a burn happened.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
PLACE_KEYS = ("omrade", "område", "reservat", "plats", "objekt", "lokal", "namn", "kommun", "site", "location", "place")
DATE_KEYS = ("datum", "date", "arende", "ärende", "brann", "bränn", "burn", "start", "slut", "genomfor", "genomför", "plan", "created", "edited", "last")
COMPLETED = ("genomförd bränning", "genomförda bränningar", "utförd bränning", "utförda bränningar", "completed burn", "burn completed", "burning completed")
PLAN_WORDS = ("handlingsplan", "bränningsplan", "branningsplan", "planering", "planerad bränning", "planned burn", "burn plan")
PUBLIC_INFO = ("information om", "informationsmöte", "allmänheten", "kungörelse", "public information", "public notice")
APPLICATION = ("ansökan", "anmälan", "dispens", "tillstånd", "samråd", "upphandling", "application", "permit", "consultation")
BURN_WORDS = ("naturvårdsbränning", "naturvardsbranning", "bränning", "branning", "controlled burning", "prescribed burn", "t2.3")


def _normal(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _date_from_value(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = _normal(value)
    match = DATE_RE.search(text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            pass
    # Unix milliseconds/seconds commonly occur in ArcGIS date fields.
    if isinstance(value, (int, float)) and value > 100_000_000_000:
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    return None


def _classify(text: str, source_kind: str) -> tuple[str, str, str]:
    value = text.casefold()
    if any(term in value for term in COMPLETED):
        return "completed_burn", "high", "Source text explicitly describes a completed burn."
    if any(term in value for term in PLAN_WORDS):
        return "planning_or_action_plan", "medium", "Source text refers to planning or a burn/action plan; implementation is not implied."
    if any(term in value for term in PUBLIC_INFO):
        return "public_information", "medium", "Source text indicates information or public notice; burn status is not implied."
    if any(term in value for term in APPLICATION):
        return "application_notification_or_consultation", "medium", "Source text indicates an administrative process; it is not proof of a completed burn."
    if any(term in value for term in BURN_WORDS):
        return ("life2taiga_burn_related_geometry" if source_kind == "lifetaiga" else "burn_related_diary"),
            "low", "Burn-related wording found, but the lifecycle stage is not explicit."
    return "other_or_unclassified", "low", "No lifecycle stage could be safely inferred from the available text."


def classify_text(text: str, source_kind: str = "diary") -> dict[str, str]:
    stage, confidence, explanation = _classify(text, source_kind)
    return {"stage": stage, "confidence": confidence, "explanation": explanation}


def _record_date(record: dict[str, Any], props: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    values = []
    if props:
        values.extend((key, value) for key, value in props.items())
    columns = record.get("columns") or {}
    values.extend((key, value) for key, value in columns.items())
    for key, value in values:
        if any(term in str(key).casefold() for term in DATE_KEYS):
            found = _date_from_value(value)
            if found:
                return found, str(key)
    # Only accept explicit ISO-like dates in titles, not a bare year.
    title = _normal(record.get("title") or (props or {}).get("title"))
    found = _date_from_value(title)
    return (found, "title") if found else (None, None)


def _place_candidates(props: dict[str, Any], title: str = "") -> list[str]:
    candidates = []
    for key, value in props.items():
        if value is None or isinstance(value, (dict, list)):
            continue
        if any(term in str(key).casefold() for term in PLACE_KEYS):
            value = _normal(value)
            if value and len(value) <= 180 and value.casefold() not in {"okänd", "saknas", "visas ej", "null"}:
                candidates.append(value)
    # Keep a title only as raw source text; don't pretend it is a verified place.
    out, seen = [], set()
    for value in candidates:
        if value.casefold() not in seen:
            seen.add(value.casefold())
            out.append(value)
    return out[:20]


def build_timeline(diary_state: dict[str, Any], lifetaiga: dict[str, Any]) -> dict[str, Any]:
    events = []
    for key, record in (diary_state.get("records") or {}).items():
        if not isinstance(record, dict):
            continue
        title = _normal(record.get("title") or (record.get("columns") or {}).get("Ärenderubrik"))
        searchable = " ".join([title] + [_normal(v) for v in (record.get("columns") or {}).values() if not isinstance(v, (dict, list))])
        classification = classify_text(searchable, "diary")
        event_date, date_source = _record_date(record)
        diary_number = _normal(record.get("diary_number") or (record.get("columns") or {}).get("Diarienummer"))
        events.append({
            "event_id": "diary:" + _normal(record.get("record_key") or diary_number or key),
            "source_type": "lansstyrelsen_diary",
            "source_record_id": diary_number or _normal(key),
            "title": title or "Diariepost utan rubrik",
            "event_date": event_date,
            "event_date_source_field": date_source,
            **classification,
            "place_candidates": _place_candidates(record.get("columns") or {}, title),
            "geometry": None,
            "link_status": "unlinked",
            "source_url": _normal(record.get("source_url")),
            "evidence_text": searchable[:1600],
        })

    for feature in lifetaiga.get("features") or []:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        searchable = " ".join([_normal(k) + ": " + _normal(v) for k, v in props.items() if not isinstance(v, (dict, list))])
        classification = classify_text(searchable, "lifetaiga")
        event_date, date_source = _record_date({}, props)
        oid = props.get("OBJECTID") or props.get("ObjectId") or feature.get("id")
        geometry = feature.get("geometry")
        events.append({
            "event_id": "lifetaiga:" + _normal(oid or len(events)),
            "source_type": "lifetaiga_action_polygon",
            "source_record_id": _normal(oid),
            "title": _normal(props.get("title") or props.get("Namn") or props.get("namn") or "Life2Taiga naturvårdsåtgärd"),
            "event_date": event_date,
            "event_date_source_field": date_source,
            **classification,
            "place_candidates": _place_candidates(props),
            "geometry": geometry if isinstance(geometry, dict) else None,
            "link_status": "unlinked",
            "source_url": lifetaiga.get("source_url") or "",
            "evidence_text": searchable[:1600],
        })

    # Dates first; undated items remain visible at the end and are not assigned a fake date.
    events.sort(key=lambda event: (event["event_date"] is None, event["event_date"] or "", event["source_type"], event["event_id"]))
    stage_counts = Counter(event["stage"] for event in events)
    source_counts = Counter(event["source_type"] for event in events)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_policy": "Diary and Life2Taiga records remain separate unless linked by verified evidence. Diary presence is not proof that a burn occurred. Missing dates remain null.",
        "event_count": len(events),
        "stage_counts": dict(sorted(stage_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diary-state", type=Path, default=Path("data/lansstyrelsen-diary/state.json"))
    parser.add_argument("--lifetaiga", type=Path, default=Path("docs/data/lifetaiga-naturvardsatgarder.geojson"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/burn-event-timeline.json"))
    args = parser.parse_args()
    diary_state = json.loads(args.diary_state.read_text(encoding="utf-8"))
    lifetaiga = json.loads(args.lifetaiga.read_text(encoding="utf-8"))
    report = build_timeline(diary_state, lifetaiga)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({"output": str(args.output), "event_count": report["event_count"], "stage_counts": report["stage_counts"], "source_counts": report["source_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
