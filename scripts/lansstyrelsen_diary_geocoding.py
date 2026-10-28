#!/usr/bin/env python3
"""Extract auditable geographic clues from Länsstyrelsen diary records.

This stage intentionally does not invent coordinates. Candidate points/circles are
created only after a clue has been matched to an authoritative geographic feature.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

AREA_TERMS = (
    "naturreservat", "nationalpark", "naturvårdsområde", "Natura 2000",
    "naturvårdsbränning", "naturvårdsområde", "naturminne",
)
AREA_PATTERN = re.compile(
    r"(?i)\b([\wÅÄÖåäöÉéÜüÖöÄäÅå'’\-]+(?:\s+[\wÅÄÖåäöÉéÜü'’\-]+){0,5})\s+"
    r"(naturreservatet|naturreservat|nationalparken|nationalpark|Natura\s+2000-?område)\b"
)
# Recognize named Natura 2000 sites even when the title doesn't call them a reserve.
NATURA_PATTERN = re.compile(
    r"(?i)\b(?:Natura\s*2000[- ]?(?:området|område))\s+([\wÅÄÖåäöÉéÜü'’\-]+(?:\s+(?:och|i|på|av|den|det|de|[A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*)){0,5})"
)
IN_NATURA_PATTERN = re.compile(
    r"(?i)\b(?:i|inom|på)\s+([\wÅÄÖåäöÉéÜü'’\-]+(?:\s+[\wÅÄÖåäöÉéÜü'’\-]+){0,5})\s+Natura\s*2000[- ]?(?:området|område)\b"
)
DIRECT_PLACE_PATTERN = re.compile(
    r"(?i)\b(?:vid|på|för)\s+([A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*(?:\s+(?:och|i|på|av|den|det|de|[A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*)){0,4})"
)
PREPOSITION_PATTERN = re.compile(
    r"(?i)\b(?:i|på|vid|inom|kring|nära)\s+"
    r"([A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*(?:\s+(?:och|i|på|av|den|det|de|[A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*)){0,5})"
)
MUNICIPALITY_PATTERN = re.compile(
    r"(?i)\b([A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*(?:\s+[A-ZÅÄÖÉÜ][\wÅÄÖåäöÉéÜü'’\-]*){0,2})\s+kommun\b"
)
STOP_WORDS = {
    "information", "ansökan", "anmälan", "föranmälan", "avropsförfrågan",
    "naturvårdsbränning", "planerad", "genomförande", "stöd", "byggnation",
    "inför", "samråd", "beslut", "uppföljning", "tillstånd", "om",
}


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for item in items:
        item = re.sub(r"\s+", " ", item).strip(" .,:;–-")
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            output.append(item)
    return output


def extract_geographic_clues(record: dict[str, Any]) -> dict[str, Any]:
    columns = record.get("columns") or {}
    title = str(record.get("title") or columns.get("Ärenderubrik") or "").strip()
    municipality_column = str(columns.get("Kommun") or "").strip()
    postort = str(columns.get("Postort") or "").strip()
    diary = str(record.get("diary") or "")
    municipality_mentions = _unique(MUNICIPALITY_PATTERN.findall(title))
    area_names = _unique([m.group(1) for m in AREA_PATTERN.finditer(title)])
    area_names.extend(NATURA_PATTERN.findall(title))
    area_names.extend(IN_NATURA_PATTERN.findall(title))
    area_names = _unique(area_names)
    place_names = []
    # Explicit place clauses catch names such as "för Krångdalen" and "vid Knappåsen".
    for match in DIRECT_PLACE_PATTERN.finditer(title):
        candidate = match.group(1).strip()
        if candidate.split()[0].casefold() not in STOP_WORDS:
            place_names.append(candidate)
    for match in PREPOSITION_PATTERN.finditer(title):
        candidate = match.group(1).strip()
        first = candidate.split()[0].casefold()
        if first in STOP_WORDS or candidate.casefold() in {x.casefold() for x in area_names}:
            continue
        place_names.append(candidate)
    place_names = _unique(place_names)

    clues = []
    for name in area_names:
        clues.append({"type": "protected_area_name", "value": name, "source": "title"})
    for name in municipality_mentions:
        clues.append({"type": "municipality", "value": name, "source": "title"})
    if municipality_column:
        clues.append({"type": "municipality", "value": municipality_column, "source": "Kommun column"})
    for name in place_names:
        clues.append({"type": "place_name_candidate", "value": name, "source": "title"})
    if postort:
        clues.append({"type": "postort", "value": postort, "source": "Postort column"})
    if diary:
        clues.append({"type": "county_context", "value": diary, "source": "diary"})

    if area_names:
        confidence = "medium"
        reason = "Named protected area in title; must be matched to an authoritative polygon."
    elif municipality_mentions or municipality_column or place_names:
        confidence = "low"
        reason = "Geographic text clue found, but exact burn location is not yet verified."
    elif postort:
        confidence = "very_low"
        reason = "Only postort metadata is available; it may describe a sender, not the burn site."
    else:
        confidence = "unresolved"
        reason = "No reliable geographic clue extracted from the title or metadata."

    return {
        "record_key": record.get("record_key") or record.get("diary_number") or "",
        "diary_number": record.get("diary_number") or columns.get("Diarienummer") or "",
        "diary": diary,
        "title": title,
        "source_url": record.get("source_url") or "",
        "geocoding": {
            "status": "needs_authoritative_match",
            "confidence": confidence,
            "confidence_reason": reason,
            "coordinates": None,
            "circle_radius_m": None,
            "geometry": None,
            "clues": clues,
            "popup": {
                "title": title,
                "diary_number": record.get("diary_number") or columns.get("Diarienummer") or "",
                "confidence": confidence,
                "confidence_reason": reason,
                "clues": clues,
            },
        },
    }


def build_report(state: dict[str, Any]) -> dict[str, Any]:
    records = state.get("records") or {}
    features = [extract_geographic_clues(record) for record in records.values()]
    counts = Counter(item["geocoding"]["confidence"] for item in features)
    return {
        "schema_version": 1,
        "generated_from_schema_version": state.get("schema_version"),
        "record_count": len(features),
        "coordinate_policy": "No coordinates or circles are emitted until matched to an authoritative geographic feature.",
        "summary": dict(sorted(counts.items())),
        "features": features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/lansstyrelsen-diary/state.json"))
    parser.add_argument("--output", type=Path, default=Path("data/lansstyrelsen-diary/geocoding-candidates.json"))
    args = parser.parse_args()
    state = json.loads(args.input.read_text(encoding="utf-8"))
    report = build_report(state)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "record_count": report["record_count"], "summary": report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
