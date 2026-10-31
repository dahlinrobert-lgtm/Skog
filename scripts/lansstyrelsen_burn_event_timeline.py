#!/usr/bin/env python3
"""Build an auditable, source-separated event timeline for prescribed-burn monitoring.

This deliberately keeps diary records and Life2Taiga geometries as separate events
until a defensible link is established. A diary title is evidence of a case/action,
not proof that a burn happened.
"""
from __future__ import annotations

import argparse
import csv
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
    # County names and common inflections are administrative context, not site names.
    for county in COUNTY_NAMES:
        generic.add(county)
        generic.add(county + "s")
    # Frequent connective, directional and area-description words found in the
    # real review queue (for example "Dalarnas ... samt södra ... området").
    generic.update({
        "samt", "området", "omrade", "område", "södra", "sodra", "norra",
        "östra", "ostra", "västra", "vastra", "mellersta", "inre", "yttre",
        "nordöstra", "nordvastra", "sydöstra", "sydvästra", "sydvastra",
        "nordvästra", "nordvastra", "övre", "ovre", "nedre",
        # Common Swedish function words and diary/procurement language.
        "inför", "från", "till", "för", "vid", "på", "inom", "under",
        "mellan", "genom", "efter", "före", "av", "om", "i", "på",
        "eventuellt", "gäller", "giltighetstid", "ansökan", "dispens",
        "upphandling", "upphandlingar", "tjänst", "tjänster", "avrop",
        "entreprenad", "entreprenören", "avtal", "avtalade", "ersättning",
        "skada", "kontraktsbrott", "beställning", "distribution",
        "skog", "skogs", "nationalpark", "nationalparken", "sveaskog",
    })
    return {t for t in _normalized_place(value).split() if len(t) >= 4 and not t.isdigit() and t not in generic}


def _event_year_clues(title: str, event_date: str | None, props: dict[str, Any] | None = None) -> list[str]:
    """Return years supported by event text/date fields, excluding administrative dates."""
    years = set(YEAR_RE.findall(title or ""))
    if event_date:
        years.add(event_date[:4])
    if props:
        for key, value in props.items():
            key_norm = str(key).casefold()
            # Only explicitly action-related year attributes are admitted. Generic
            # created/updated/edited/registration years must not boost a match.
            action_key = any(term in key_norm for term in (
                "åtgärd", "atgard", "bränn", "brann", "burn", "genomför",
                "genomfor", "utförd", "utford", "insats", "action",
            ))
            year_key = "år" in key_norm or "ar" == key_norm or "year" in key_norm
            administrative_key = any(term in key_norm for term in (
                "created", "updated", "edited", "registr", "diarie", "source",
                "uppdater", "ändrad", "andrad", "last_edit",
            ))
            if action_key and year_key and not administrative_key:
                years.update(YEAR_RE.findall(_normal(value)))
    return sorted(years)


COUNTY_NAMES = (
    "blekinge", "dalarna", "gotland", "gavleborg", "gävleborg", "halland",
    "jämtland", "jamtland", "jönköping", "jonkoping", "kalmar", "kronoberg",
    "norrbotten", "skåne", "skane", "stockholm", "södermanland", "sodermanland",
    "uppsala", "värmland", "varmland", "västerbotten", "vasterbotten",
    "västernorrland", "vasternorrland", "västmanland", "vastmanland",
    "västra götaland", "vastra gotaland", "östergötland", "ostergotland",
)


# Broad landscape/protected-area names found to cause cross-site matches in the
# current review queue. These remain useful context, but are not treated as
# evidence that two records refer to the same burn site.
BROAD_PLACE_TOKENS = {
    "gotska", "sandön", "sandon",       # island context; individual sites differ
    "allgunnen",                         # reserve/landscape context; subareas differ
    "skattlösberg", "skattlosberg",     # mire/reserve context; subareas differ
    "stormosse",                         # broad mire context; named sites differ
    "kölarna", "kolarna",               # Natura 2000/landscape context
}


def _place_token_groups(value: str) -> tuple[set[str], set[str]]:
    tokens = _name_tokens(value)
    context = tokens & BROAD_PLACE_TOKENS
    return tokens - context, context


def _county_clues(text: str) -> set[str]:
    value = _normal(text).casefold()
    return {name for name in COUNTY_NAMES if name in value}


def _lifecycle_compatibility(diary_stage: str, geometry_stage: str) -> tuple[int, str]:
    """Score whether a diary lifecycle step plausibly relates to a mapped burn action."""
    compatible = {
        "planning_or_action_plan", "publicity_or_logistics_preparation",
        "public_information", "agreement_or_contract", "procurement_or_contracting",
        "application_notification_or_consultation", "pre_burn_species_protection",
        "pre_burn_site_preparation", "completed_burn", "post_burn_follow_up",
        "cancelled_or_postponed", "burn_related_diary",
    }
    if diary_stage in compatible and geometry_stage == "life2taiga_burn_related_geometry":
        return 15, "diary_lifecycle_step_is_consistent_with_burn_action_layer"
    return 0, "lifecycle_relation_not_specific_enough"


def _candidate_links(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score review candidates using explainable clues; never auto-link source events."""
    diary_events = [e for e in events if e["source_type"] == "lansstyrelsen_diary"]
    geometry_events = [e for e in events if e["source_type"] == "lifetaiga_action_polygon"]
    candidates = []
    for diary in diary_events:
        diary_text = _normal(diary.get("title", "")) + " " + _normal(diary.get("evidence_text", ""))
        diary_place_text = diary_text + " " + " ".join(diary.get("place_candidates") or [])
        diary_tokens, diary_context_tokens = _place_token_groups(diary_place_text)
        diary_years = set(diary.get("event_year_clues") or [])
        diary_counties = _county_clues(diary_text)
        for geometry in geometry_events:
            geo_text = _normal(geometry.get("title", "")) + " " + _normal(geometry.get("evidence_text", ""))
            geo_place_text = geo_text + " " + " ".join(geometry.get("place_candidates") or [])
            geo_tokens, geo_context_tokens = _place_token_groups(geo_place_text)
            overlap = sorted(diary_tokens & geo_tokens)
            context_overlap = sorted(
                (diary_context_tokens & (geo_context_tokens | geo_tokens)) |
                (geo_context_tokens & diary_tokens)
            )
            geo_years = set(geometry.get("event_year_clues") or [])
            geo_counties = _county_clues(geo_text)
            shared_counties = sorted(diary_counties & geo_counties)
            # Candidate discovery is deliberately permissive within a named county,
            # while generic burn wording alone still cannot create a candidate.
            if not overlap and not context_overlap and not shared_counties:
                continue

            # Five transparent components, each capped at its published weight.
            place_points = min(40, 20 * len(overlap))
            county_points = 15 if shared_counties else 0
            year_overlap = sorted(diary_years & geo_years)
            time_points = 20 if year_overlap else 0
            lifecycle_points, lifecycle_reason = _lifecycle_compatibility(
                diary.get("stage", ""), geometry.get("stage", "")
            )
            raw_score = place_points + county_points + time_points + lifecycle_points
            evidence_dimensions = sum((
                bool(overlap), bool(diary_counties and geo_counties),
                bool(diary_years and geo_years), bool(lifecycle_points),
            ))
            candidates.append({
                "candidate_id": f'{diary["event_id"]}~{geometry["event_id"]}',
                "diary_event_id": diary["event_id"],
                "geometry_event_id": geometry["event_id"],
                "score": raw_score,  # uniqueness is added after alternatives are counted
                "confidence": "unassessed",
                "place_points": place_points,
                "county_points": county_points,
                "time_points": time_points,
                "lifecycle_points": lifecycle_points,
                "uniqueness_points": 0,
                "shared_place_tokens": overlap,
                "shared_context_place_tokens": context_overlap,
                "shared_counties": shared_counties,
                "shared_years": year_overlap,
                "evidence_tier": (
                    "place_county_and_year" if overlap and shared_counties and year_overlap else
                    "place_and_year" if overlap and year_overlap else
                    "county_and_year" if shared_counties and year_overlap else
                    "place_and_county" if overlap and shared_counties else
                    "place_only" if overlap else
                    "context_only" if context_overlap else "county_only"
                ),
                "data_coverage": round(evidence_dimensions / 4, 2),
                "data_coverage_note": (
                    "Coverage measures available comparison dimensions, not truth probability. "
                    "Missing source details are not treated as contradictory evidence."
                ),
                "lifecycle_reason": lifecycle_reason,
                "status": "candidate_for_manual_review",
                "evidence_policy": (
                    "Weighted clue score is a triage aid, not a calibrated probability. "
                    "County-level candidates may have sparse site details. Source events remain "
                    "unlinked until independently verified."
                ),
            })

    # Geographic uniqueness is assessed among candidates for the same diary event.
    # It is not awarded when there is no shared county context.
    diary_counts = Counter(c["diary_event_id"] for c in candidates)
    geometry_counts = Counter(c["geometry_event_id"] for c in candidates)
    for candidate in candidates:
        diary_count = diary_counts[candidate["diary_event_id"]]
        geometry_count = geometry_counts[candidate["geometry_event_id"]]
        # Award uniqueness only for a genuinely one-to-one candidate pair.
        # A diary record matching one polygon is not unique if that polygon also
        # matches other diary records, and vice versa.
        if candidate["shared_counties"] and diary_count == 1 and geometry_count == 1:
            candidate["uniqueness_points"] = 10
        candidate["score"] = min(100, candidate["score"] + candidate["uniqueness_points"])
        candidate["confidence"] = (
            "high" if candidate["score"] >= 80 and candidate["data_coverage"] >= 0.75 else
            "medium" if candidate["score"] >= 55 and candidate["data_coverage"] >= 0.5 else
            "low"
        )
        candidate["diary_candidate_count"] = diary_count
        candidate["geometry_candidate_count"] = geometry_count
        candidate["ambiguity"] = (
            "many_to_many" if diary_count > 1 and geometry_count > 1 else
            "diary_matches_multiple_geometries" if diary_count > 1 else
            "geometry_matches_multiple_diary_records" if geometry_count > 1 else
            "single_candidate_pair"
        )
        candidate["review_priority"] = (
            "higher" if candidate["score"] >= 60 and candidate["data_coverage"] >= 0.5 else
            "normal"
        )
        candidate["evidence_summary"] = (
            f'Plats {candidate["place_points"]}/40; län {candidate["county_points"]}/15; '
            f'tid {candidate["time_points"]}/20; händelseförlopp {candidate["lifecycle_points"]}/15; '
            f'unikhet {candidate["uniqueness_points"]}/10. '
            + ("Gemensamma platsindicier: " + ", ".join(candidate["shared_place_tokens"]) + ". "
               if candidate["shared_place_tokens"] else "Inget gemensamt specifikt platsnamn. ")
            + ("Gemensamt län: " + ", ".join(candidate["shared_counties"]) + ". "
               if candidate["shared_counties"] else "Inget gemensamt län identifierat. ")
            + ("Gemensamt händelseår: " + ", ".join(candidate["shared_years"]) + "."
               if candidate["shared_years"] else "Inget gemensamt händelseår.")
        )
    candidates.sort(key=lambda c: (-c["score"], c["diary_event_id"], c["geometry_event_id"]))
    return candidates


def build_field_inventory(lifetaiga: dict[str, Any]) -> dict[str, Any]:
    """Summarize real Life2Taiga property names and values to guide safe date mapping."""
    features = [f for f in (lifetaiga.get("features") or []) if isinstance(f, dict)]
    stats: dict[str, dict[str, Any]] = {}
    for feature in features:
        props = feature.get("properties") or {}
        if not isinstance(props, dict):
            continue
        for key, value in props.items():
            name = str(key)
            item = stats.setdefault(name, {
                "field": name,
                "non_null_count": 0,
                "value_types": {},
                "examples": [],
            })
            if value is None or value == "":
                continue
            item["non_null_count"] += 1
            value_type = type(value).__name__
            item["value_types"][value_type] = item["value_types"].get(value_type, 0) + 1
            example = _normal(value)
            if example and len(example) <= 120 and example not in item["examples"] and len(item["examples"]) < 3:
                item["examples"].append(example)
    entries = []
    for name, item in stats.items():
        key_norm = name.casefold()
        date_related = any(term in key_norm for term in (
            "date", "datum", "time", "år", "ar", "year", "bränn", "brann",
            "burn", "åtgärd", "atgard", "genomför", "genomfor", "utförd", "utford",
        ))
        item["date_or_action_field_candidate"] = date_related
        entries.append(item)
    entries.sort(key=lambda item: (
        not item["date_or_action_field_candidate"],
        item["field"].casefold(),
    ))
    return {
        "schema_version": 1,
        "source_url": lifetaiga.get("source_url") or "",
        "source_layer_id": lifetaiga.get("source_layer_id"),
        "source_layer_name": lifetaiga.get("source_layer_name") or lifetaiga.get("name") or "",
        "generated_at": lifetaiga.get("generated_at") or "",
        "feature_count": len(features),
        "field_count": len(entries),
        "date_or_action_field_candidates": [
            item["field"] for item in entries if item["date_or_action_field_candidate"]
        ],
        "fields": entries,
        "interpretation_policy": (
            "Field-name matching is only a discovery aid. A field is not treated as an event date or "
            "completion indicator until its meaning and values have been verified."
        ),
    }


def write_field_inventory(lifetaiga: dict[str, Any], output_path: Path) -> dict[str, Any]:
    inventory = build_field_inventory(lifetaiga)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + ".tmp")
    temp.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(output_path)
    return inventory


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
            "event_year_clues": _event_year_clues(title, dates.get("event_date")),
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
            "event_year_clues": _event_year_clues(_normal(props.get("title") or props.get("Namn") or props.get("namn") or ""), dates.get("event_date"), props),
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


def write_review_csv(report: dict[str, Any], output_path: Path) -> int:
    """Write a spreadsheet-friendly, evidence-focused review queue for candidate pairs."""
    events = {event["event_id"]: event for event in report.get("events", [])}
    candidates = list(report.get("link_candidates", []))
    candidates.sort(key=lambda c: (
        c.get("review_priority") != "higher",
        -float(c.get("score") or 0),
        c.get("diary_event_id", ""),
        c.get("geometry_event_id", ""),
    ))
    columns = [
        "review_priority", "score", "confidence", "evidence_tier",
        "shared_place_tokens", "shared_counties", "shared_years", "ambiguity",
        "place_points", "county_points", "time_points", "lifecycle_points", "uniqueness_points", "data_coverage",
        "diary_candidate_count", "geometry_candidate_count",
        "diary_event_id", "diary_number", "diary_title",
        "diary_event_date", "diary_record_date", "diary_source_url",
        "geometry_event_id", "geometry_record_id", "geometry_title",
        "geometry_event_date", "geometry_record_date", "geometry_source_url",
        "status", "evidence_summary",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for candidate in candidates:
            diary = events.get(candidate.get("diary_event_id"), {})
            geometry = events.get(candidate.get("geometry_event_id"), {})
            writer.writerow({
                **candidate,
                "shared_place_tokens": " | ".join(candidate.get("shared_place_tokens") or []),
                "shared_counties": " | ".join(candidate.get("shared_counties") or []),
                "shared_years": " | ".join(candidate.get("shared_years") or []),
                "diary_number": diary.get("source_record_id", ""),
                "diary_title": diary.get("title", ""),
                "diary_event_date": diary.get("event_date") or "",
                "diary_record_date": diary.get("record_date") or "",
                "diary_source_url": diary.get("source_url", ""),
                "geometry_record_id": geometry.get("source_record_id", ""),
                "geometry_title": geometry.get("title", ""),
                "geometry_event_date": geometry.get("event_date") or "",
                "geometry_record_date": geometry.get("record_date") or "",
                "geometry_source_url": geometry.get("source_url", ""),
            })
    temp.replace(output_path)
    return len(candidates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diary-state", type=Path, default=Path("data/lansstyrelsen-diary/state.json"))
    parser.add_argument("--lifetaiga", type=Path, default=Path("docs/data/lifetaiga-naturvardsatgarder.geojson"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/burn-event-timeline.json"))
    parser.add_argument("--review-csv", type=Path, default=Path("docs/data/burn-event-link-review.csv"))
    parser.add_argument("--field-inventory", type=Path, default=Path("docs/data/lifetaiga-field-inventory.json"))
    args = parser.parse_args()
    diary_state = json.loads(args.diary_state.read_text(encoding="utf-8"))
    lifetaiga = json.loads(args.lifetaiga.read_text(encoding="utf-8"))
    report = build_timeline(diary_state, lifetaiga)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(args.output)
    review_count = write_review_csv(report, args.review_csv)
    inventory = write_field_inventory(lifetaiga, args.field_inventory)
    print(json.dumps({
        "output": str(args.output),
        "event_count": report["event_count"],
        "stage_counts": report["stage_counts"],
        "source_counts": report["source_counts"],
        "review_csv": str(args.review_csv),
        "review_candidate_count": review_count,
        "link_candidate_summary": report["link_candidate_summary"],
        "field_inventory": str(args.field_inventory),
        "field_count": inventory["field_count"],
        "date_or_action_field_candidates": inventory["date_or_action_field_candidates"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
