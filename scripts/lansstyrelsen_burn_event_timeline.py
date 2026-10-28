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
EVENT_DATE_KEYS = ("brann", "bränn", "burn", "genomfor", "genomför", "utford", "utförd", "planerad", "atgardsdatum", "åtgärdsdatum", "insatsdatum", "startdatum", "slutdatum", "event_date", "burn_date")
RECORD_DATE_KEYS = ("inkomdatum", "in/upp-datum", "registreringsdatum", "source_date", "created_date", "created_at", "last_edited_date", "updated_at", "diariedatum")
COMPLETED = ("genomförd bränning", "genomförda bränningar", "utförd bränning", "utförda bränningar", "completed burn", "burn completed", "burning completed")
CANCELLED_OR_POSTPONED = ("inställd bränning", "inställd naturvårdsbränning", "inställt på grund av", "bränningen ställs in", "bränningen skjuts upp", "uppskjuten bränning", "avblåst bränning", "cancelled burn", "postponed burn")
POST_BURN = ("efterbevakning", "efterbevakning av naturvårdsbränning", "uppföljning efter bränning", "uppfoljning efter branning", "tillsyn efter utförd naturvårdsbränning", "uppföljning av naturvårdsbränning")
PRE_BURN_SPECIES = ("varglav", "fridlysningsbestämmelser", "fridlysningsbestammelser", "artinventering inför", "inventering inför bränning", "inventering infor branning", "plocka ", "flytta arter", "artskydd inför", "artskydd infor", "dispens från fridlysningsbestämmelserna")
PRE_BURN_WORK = ("byggnation av spång inför", "byggande av spång inför", "röjning inför bränning", "rojning infor branning", "anläggning inför bränning", "anlaggning infor branning", "förberedande arbete inför bränning", "forberedande arbete infor branning", "brandgata inför bränning", "brandgata infor branning")
AGREEMENT = ("avtal om naturvårdsbränning", "avtal om naturvardsbranning", "avtalsförlängning naturvårdsbränning", "avtalsforlangning naturvardsbranning", "contract for prescribed burn")
PROCUREMENT = ("upphandling av naturvårdsbränning", "upphandling av naturvardsbranning", "direktupphandling av naturvårdsbränning", "direktupphandling av naturvardsbranning", "inköp av entreprenad för naturvårdsbränning")
PREP_WORK = ("beställning av trycktjänst", "beställning av distribution av samhällsinfo", "trafikskyltar för naturvårdsbränning", "trafikskyltar for naturvardsbranning", "informationsbrev om naturvårdsbränning")
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
    # Classify the most specific process step before generic words such as
    # "ansökan" or "naturvårdsbränning" to avoid flattening preparation into
    # a generic administrative case.
    if any(term in value for term in CANCELLED_OR_POSTPONED):
        return "cancelled_or_postponed", "medium", "Source text indicates cancellation or postponement; verify whether a later record documents rescheduling or completion."
    if any(term in value for term in COMPLETED):
        return "completed_burn", "high", "Source text explicitly describes a completed burn."
    if any(term in value for term in POST_BURN):
        return "post_burn_follow_up", "medium", "Source text refers to follow-up or monitoring after a burn; the wording is not independently proof of the burn date."
    if any(term in value for term in PRE_BURN_SPECIES):
        return "pre_burn_species_protection", "medium", "Source text indicates a species-protection or handling step before a burn; it does not prove that the burn later occurred."
    if any(term in value for term in PRE_BURN_WORK):
        return "pre_burn_site_preparation", "medium", "Source text indicates physical or site preparation before a burn; it does not prove that the burn later occurred."
    if any(term in value for term in PLAN_WORDS):
        return "planning_or_action_plan", "medium", "Source text refers to planning or a burn/action plan; implementation is not implied."
    if any(term in value for term in PREP_WORK):
        return "publicity_or_logistics_preparation", "medium", "Source text indicates information or logistical preparation for a burn; it is not proof that the burn took place."
    if any(term in value for term in PUBLIC_INFO):
        return "public_information", "medium", "Source text indicates information or public notice; burn status is not implied."
    if any(term in value for term in AGREEMENT):
        return "agreement_or_contract", "medium", "Source text indicates an agreement/contract related to a burn; this is a preparatory or administrative step, not proof of implementation."
    if any(term in value for term in PROCUREMENT):
        return "procurement_or_contracting", "medium", "Source text indicates procurement/contracting for a burn; this is not proof that the work was performed."
    if any(term in value for term in APPLICATION):
        return "application_notification_or_consultation", "medium", "Source text indicates an administrative process; it is not proof of a completed burn."
    if any(term in value for term in BURN_WORDS):
        return (("life2taiga_burn_related_geometry" if source_kind == "lifetaiga" else "burn_related_diary"),
                "low", "Burn-related wording found, but the lifecycle stage is not explicit.")
    return "other_or_unclassified", "low", "No lifecycle stage could be safely inferred from the available text."


def classify_text(text: str, source_kind: str = "diary") -> dict[str, str]:
    stage, confidence, explanation = _classify(text, source_kind)
    return {"stage": stage, "confidence": confidence, "explanation": explanation}


def _record_dates(record: dict[str, Any], props: dict[str, Any] | None = None) -> dict[str, str | None]:
    values = []
    # The diary collector stores the source's In/Upp-datum both as a top-level
    # source_date and as a column. These are record/registration dates, not burn dates.
    for key in ("source_date", "created_at", "updated_at"):
        if record.get(key) is not None:
            values.append((key, record[key]))
    if props:
        values.extend((key, value) for key, value in props.items())
    columns = record.get("columns") or {}
    values.extend((key, value) for key, value in columns.items())
    result = {"event_date": None, "event_date_source_field": None,
              "record_date": None, "record_date_source_field": None}
    for key, value in values:
        key_norm = str(key).casefold()
        found = _date_from_value(value)
        if not found:
            continue
        if result["event_date"] is None and any(term in key_norm for term in EVENT_DATE_KEYS):
            if not any(term in key_norm for term in ("last_edited", "updated", "created")):
                result["event_date"] = found
                result["event_date_source_field"] = str(key)
        if result["record_date"] is None and any(term in key_norm for term in RECORD_DATE_KEYS):
            result["record_date"] = found
            result["record_date_source_field"] = str(key)
    return result

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



def _normalized_place(value: str) -> str:
    """Normalize place text conservatively for candidate comparisons."""
    value = value.casefold().replace("naturreservatet", "").replace("naturreservat", "")
    value = value.replace("natura 2000-område", "").replace("natura 2000 område", "")
    value = re.sub(r"[^0-9a-zåäöéü]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _name_tokens(value: str) -> set[str]:
    # Drop generic administrative words: they create false matches by themselves.
    generic = {"lansstyrelsen", "länsstyrelsen", "kommun", "län", "naturreservat",
               "naturreservatet", "naturvårdsbränning", "naturvardsbranning",
               "bränning", "branning", "information", "planerad", "planering"}
    return {t for t in _normalized_place(value).split() if len(t) >= 4 and t not in generic}


def _candidate_links(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit review-only links; do not mutate event.link_status or claim verified links."""
    diary_events = [e for e in events if e["source_type"] == "lansstyrelsen_diary"]
    geometry_events = [e for e in events if e["source_type"] == "lifetaiga_action_polygon"]
    candidates = []
    for diary in diary_events:
        diary_text = _normal(diary.get("title", ""))
        diary_tokens = _name_tokens(diary_text + " " + " ".join(diary.get("place_candidates") or []))
        # Avoid using record/created dates as event dates. They may only add weak temporal context.
        diary_years = set(YEAR_RE.findall(diary_text))
        if diary.get("event_date"):
            diary_years.add(diary["event_date"][:4])
        for geometry in geometry_events:
            geo_tokens = _name_tokens(geometry.get("title", "") + " " + " ".join(geometry.get("place_candidates") or []))
            overlap = sorted(diary_tokens & geo_tokens)
            if not overlap:
                continue
            geom_years = set(YEAR_RE.findall(geometry.get("evidence_text", "")))
            if geometry.get("event_date"):
                geom_years.add(geometry["event_date"][:4])
            year_overlap = sorted(diary_years & geom_years)
            # A shared descriptive token is a candidate clue, not sufficient identity evidence.
            score = min(0.65, 0.35 + 0.10 * (len(overlap) - 1))
            if year_overlap:
                score = min(0.85, score + 0.20)
            # Keep the heuristic score, but explicitly expose evidence strength.
            # A shared year is only supportive when present in event-specific text/date
            # evidence; record/registration dates are deliberately excluded.
            candidates.append({
                "candidate_id": f'{diary["event_id"]}~{geometry["event_id"]}',
                "diary_event_id": diary["event_id"],
                "geometry_event_id": geometry["event_id"],
                "score": round(score, 2),
                "confidence": "medium" if score >= 0.55 else "low",
                "shared_place_tokens": overlap,
                "shared_years": year_overlap,
                "evidence_tier": (
                    "place_and_event_year" if overlap and year_overlap else
                    "place_only"
                ),
                "review_priority": (
                    "higher" if overlap and year_overlap and len(overlap) >= 2 else
                    "normal"
                ),
                "status": "candidate_for_manual_review",
                "evidence_policy": "Text overlap suggests a review candidate only. A shared event-year clue is supportive, not proof. No source records are linked and no burn is inferred."
            })
    candidates.sort(key=lambda c: (-c["score"], c["diary_event_id"], c["geometry_event_id"]))
    # Quantify ambiguity so reviewers can spot one-to-many and many-to-one cases.
    diary_counts = Counter(c["diary_event_id"] for c in candidates)
    geometry_counts = Counter(c["geometry_event_id"] for c in candidates)
    for candidate in candidates:
        diary_count = diary_counts[candidate["diary_event_id"]]
        geometry_count = geometry_counts[candidate["geometry_event_id"]]
        candidate["diary_candidate_count"] = diary_count
        candidate["geometry_candidate_count"] = geometry_count
        candidate["ambiguity"] = (
            "many_to_many" if diary_count > 1 and geometry_count > 1 else
            "diary_matches_multiple_geometries" if diary_count > 1 else
            "geometry_matches_multiple_diary_records" if geometry_count > 1 else
            "single_candidate_pair"
        )
        candidate["evidence_summary"] = (
            "Shared place token(s): " + ", ".join(candidate["shared_place_tokens"]) +
            ("; shared year(s): " + ", ".join(candidate["shared_years"]) if candidate["shared_years"] else
             "; no shared year clue")
        )
    return candidates


def build_timeline(diary_state: dict[str, Any], lifetaiga: dict[str, Any]) -> dict[str, Any]:
    events = []
    for key, record in (diary_state.get("records") or {}).items():
        if not isinstance(record, dict):
            continue
        title = _normal(record.get("title") or (record.get("columns") or {}).get("Ärenderubrik"))
        searchable = " ".join([title] + [_normal(v) for v in (record.get("columns") or {}).values() if not isinstance(v, (dict, list))])
        classification = classify_text(searchable, "diary")
        dates = _record_dates(record)
        diary_number = _normal(record.get("diary_number") or (record.get("columns") or {}).get("Diarienummer"))
        events.append({
            "event_id": "diary:" + _normal(record.get("record_key") or diary_number or key),
            "source_type": "lansstyrelsen_diary",
            "source_record_id": diary_number or _normal(key),
            "title": title or "Diariepost utan rubrik",
            **dates,
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
        dates = _record_dates({}, props)
        oid = props.get("OBJECTID") or props.get("ObjectId") or feature.get("id")
        geometry = feature.get("geometry")
        events.append({
            "event_id": "lifetaiga:" + _normal(oid or len(events)),
            "source_type": "lifetaiga_action_polygon",
            "source_record_id": _normal(oid),
            "title": _normal(props.get("title") or props.get("Namn") or props.get("namn") or "Life2Taiga naturvårdsåtgärd"),
            **dates,
            **classification,
            "place_candidates": _place_candidates(props),
            "geometry": geometry if isinstance(geometry, dict) else None,
            "link_status": "unlinked",
            "source_url": lifetaiga.get("source_url") or "",
            "evidence_text": searchable[:1600],
        })

    # Dates first; undated items remain visible at the end and are not assigned a fake date.
    events.sort(key=lambda event: ((event["event_date"] or event["record_date"]) is None, event["event_date"] or event["record_date"] or "", event["source_type"], event["event_id"]))
    stage_counts = Counter(event["stage"] for event in events)
    source_counts = Counter(event["source_type"] for event in events)
    link_candidates = _candidate_links(events)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_policy": "Diary and Life2Taiga records remain separate unless linked by verified evidence. Diary presence is not proof that a burn occurred. Missing dates remain null.",
        "event_count": len(events),
        "link_candidate_count": len(link_candidates),
        "link_candidate_summary": {
            "by_confidence": dict(sorted(Counter(c["confidence"] for c in link_candidates).items())),
            "by_ambiguity": dict(sorted(Counter(c["ambiguity"] for c in link_candidates).items())),
            "by_evidence_tier": dict(sorted(Counter(c["evidence_tier"] for c in link_candidates).items())),
            "by_review_priority": dict(sorted(Counter(c["review_priority"] for c in link_candidates).items())),
            "diary_events_with_candidates": len({c["diary_event_id"] for c in link_candidates}),
            "geometry_events_with_candidates": len({c["geometry_event_id"] for c in link_candidates}),
            "policy": "Candidate metrics are triage indicators, not calibrated probabilities. Shared event-year clues exclude record/registration dates. Ambiguous matches require manual review; original events remain unlinked."
        },
        "link_candidates": link_candidates,
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
