#!/usr/bin/env python3
"""Classify Länsstyrelsen diary cases as candidate physical works or water actions.

A title/handling match is a discovery lead only. It is never a legal finding,
permit decision, geometry, or proof that the activity was carried out.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERSION = "1.0.0"

RULES = [
    ("A", "road_or_track", re.compile(r"\b(?:skogsbilväg|skogsbilvägar|vägbyggnad|väganläggning|vägbygge|vägdragning|väg|vägar|brobyggnad|bro)\b", re.I)),
    ("A", "line_or_cable", re.compile(r"\b(?:ledningsgata|ledningsdragning|kraftledning|elledning|kabel|rörledning|ledning|ledningar)\b", re.I)),
    ("A", "excavation_or_groundwork", re.compile(r"\b(?:schaktning|schakt|grävning|grävarbeten|markarbete|markarbeten|avbaning|sprängning|utfyllnad|fyllnad|masshantering|massupplag|upplag)\b", re.I)),
    ("A", "construction_or_facility", re.compile(r"\b(?:byggnation|byggnadsarbete|anläggningsarbete|anläggning|mast|torn|vindkraftverk|solcellsanläggning|rennäringsanläggning|husbehovstäkt|prospektering)\b", re.I)),
    ("A", "trail_or_recreation", re.compile(r"\b(?:vandringsled|skoterled|ridled|motionsspår|friluftsanläggning)\b", re.I)),
    ("B", "water_activity_general", re.compile(r"\b(?:vattenverksamhet|arbete i vatten|åtgärd i vatten|vattenområde)\b", re.I)),
    ("B", "drainage_or_ditch", re.compile(r"\b(?:markavvattning|dikning|dikesrensning|dikesrens|rensning av dike|nyd dikning|dike|diken|dränering)\b", re.I)),
    ("B", "culvert_or_crossing", re.compile(r"\b(?:trumma|trummor|kulvert|kulvertering|vägpassage|vattendrags passage|bro över vattendrag)\b", re.I)),
    ("B", "watercourse_modification", re.compile(r"\b(?:omgrävning|omledning|omledning av vatten|gräva om vattendrag|muddring|muddr[a-zåäö]*|rensning av vattendrag|schaktning i vatten|fyllning i vatten)\b", re.I)),
    ("B", "wetland_or_restoration", re.compile(r"\b(?:våtmark|våtmarksanläggning|våtmarksrestaurering|hydrologisk restaurering|återvätning|dikespluggning|igenläggning av dike|restaurering av vattendrag|fiskväg|vandringshinder)\b", re.I)),
]

STAGES = [
    ("application_or_notification", re.compile(r"\b(?:anmälan|föranmälan|ansökan|samråd|underrättelse)\b", re.I)),
    ("request_for_complement", re.compile(r"\b(?:komplettering|komplettera|begäran om uppgifter|föreläggande om komplettering)\b", re.I)),
    ("opinion_or_consultation", re.compile(r"\b(?:yttrande|remiss|synpunkter|remissvar)\b", re.I)),
    ("decision_or_conditions", re.compile(r"\b(?:beslut|föreläggande|försiktighetsmått|villkor|medgivande|tillstånd)\b", re.I)),
    ("prohibition_or_rejection", re.compile(r"\b(?:förbud|avslag|avvisning|avskrivning)\b", re.I)),
    ("implementation_or_inspection", re.compile(r"\b(?:utförd|genomförd|arbetsrapport|kontrollrapport|besiktningsprotokoll|slutbesiktning)\b", re.I)),
    ("follow_up_or_aftercare", re.compile(r"\b(?:uppföljning|efterkontroll|återställning|slutrapport|redovisning|eftersläckning)\b", re.I)),
]

def classify_case(record: dict[str, Any]) -> dict[str, Any]:
    case = record.get("case") or {}
    handlings = record.get("handlings") or []
    texts = [{"kind": "case_title", "date": case.get("registered_date") or "", "text": case.get("title") or ""}]
    texts.extend({"kind": "handling_title", "date": h.get("date") or "", "text": h.get("title") or ""} for h in handlings)
    evidence = []
    category_set = set()
    for item in texts:
        value = item["text"]
        for category, action_type, pattern in RULES:
            if pattern.search(value):
                category_set.add(category)
                evidence.append({
                    "category": category,
                    "action_type": action_type,
                    "text_kind": item["kind"],
                    "date": item["date"],
                    "matched_text": value,
                    "rule_version": VERSION,
                })
    stage_evidence = []
    for item in texts:
        for stage, pattern in STAGES:
            if pattern.search(item["text"]):
                stage_evidence.append({
                    "stage": stage,
                    "text_kind": item["kind"],
                    "date": item["date"],
                    "matched_text": item["text"],
                })
    # Keep A and B independently: an access road may be a physical work and
    # include a culvert/water operation in the same administrative case.
    categories = [c for c in ("A", "B") if c in category_set]
    return {
        "schema_version": 1,
        "classification_version": VERSION,
        "diary": case.get("diary", ""),
        "diary_number": case.get("diary_number", ""),
        "title": case.get("title", ""),
        "status": case.get("status", ""),
        "registered_date": case.get("registered_date", ""),
        "decision_date": case.get("decision_date", ""),
        "municipality": case.get("municipality", ""),
        "source_url": record.get("source_url", ""),
        "categories": categories,
        "action_types": sorted({e["action_type"] for e in evidence}),
        "evidence": evidence,
        "administrative_stages": stage_evidence,
        "evidence_level": "title_and_handling_metadata_only" if evidence else "no_match",
        "interpretation": (
            "Discovery lead only. A keyword match does not establish legal applicability, "
            "a granted permit, a precise location, or completed physical work."
        ),
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/lansstyrelsen-diary/case-details.json"))
    parser.add_argument("--output", type=Path, default=Path("data/lansstyrelsen-diary/analysis/action-leads.json"))
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    cases = list((payload.get("cases") or {}).values())
    classified = [classify_case(x) for x in cases]
    leads = [x for x in classified if x["categories"]]
    summary = {
        "schema_version": 1,
        "generated_from": str(args.input),
        "case_count": len(cases),
        "lead_count": len(leads),
        "category_counts": {c: sum(c in x["categories"] for x in leads) for c in ("A", "B")},
        "action_type_counts": {},
        "leads": leads,
        "limitations": [
            "The current detail sample reflects the search terms used to collect it; it is not a representative sample of all Länsstyrelsen cases.",
            "Only case titles and handling metadata are classified; document contents and attachments are not interpreted.",
            "Keyword hits are discovery candidates, not legal classifications or proof of implementation.",
        ],
    }
    for lead in leads:
        for action_type in lead["action_types"]:
            summary["action_type_counts"][action_type] = summary["action_type_counts"].get(action_type, 0) + 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("case_count", "lead_count", "category_counts", "action_type_counts")}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
