#!/usr/bin/env python3
"""Quality-check and classify Länsstyrelsen case/handling metadata.

The outputs are descriptive leads, not proof that a prescribed burn took place.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

VERSION = "1.0.0"

RULES = [
    ("burn_execution", re.compile(r"\b(if[iy]llt|genomförd|genomfördes|utförd|utfördes|bränningen har genomförts|eldningsrapport|bränningsrapport|bränningsprotokoll\s*(?:ifyllt|signerat|ifylld))\b", re.I)),
    ("aftercare", re.compile(r"efterbevak|eftersläck|efterkontroll|släckningsrapport", re.I)),
    ("invoice_compensation", re.compile(r"faktura|ersättning|utbetalning|betalningsunderlag", re.I)),
    ("follow_up", re.compile(r"uppföljning|slutrapport|redovisning|resultatrapport|besiktning|utvärdering av insats", re.I)),
    ("award", re.compile(r"tilldelningsbeslut|tilldelning", re.I)),
    ("contract", re.compile(r"\bavtal\b|kontrakt|undertecknat avtal", re.I)),
    ("procurement", re.compile(r"upphandling|anskaff|förfrågningsunderlag|\bffu\b|öppningsprotokoll|anbud|jävsdeklaration|utvärderingsprotokoll", re.I)),
    ("permit", re.compile(r"dispens|tillstånd", re.I)),
    ("notification", re.compile(r"anmälan|föranmälan|bränningsanmälan", re.I)),
    ("opinion", re.compile(r"yttrande|synpunkter", re.I)),
    ("administrative", re.compile(r"start av ärende|uppstart|tjänsteanteckning|avslutande av ärende|avslut av ärende|meddelande om start", re.I)),
]
EXECUTION_STRONG = re.compile(r"ifyllt bränningsprotokoll|genomförd(?:es)? naturvårdsbränning|bränningen har genomförts|eldningsrapport|bränningsrapport|rapport om genomförd bränning", re.I)
PLACE_RE = re.compile(r"(?:i|vid|för)\s+([A-ZÅÄÖ][\wÅÄÖåäö-]+(?:[ -][A-ZÅÄÖa-zåäö]+){0,4})")

def classes(title: str) -> list[str]:
    return [name for name, pattern in RULES if pattern.search(title or "")] or ["other"]

def valid_date(value: str) -> bool:
    if not value:
        return True
    try:
        date.fromisoformat(value[:10])
        return True
    except ValueError:
        return False

def classify_case(record: dict) -> dict:
    case = record.get("case") or {}
    handlings = record.get("handlings") or []
    classified = []
    all_text = (case.get("title") or "") + " " + " ".join(h.get("title") or "" for h in handlings)
    score, reasons = 0, []
    for h in handlings:
        title = h.get("title") or ""
        tags = classes(title)
        classified.append({
            "handling_number": h.get("handling_number", ""),
            "title": title,
            "date": h.get("date", ""),
            "sender_recipient": h.get("sender_recipient", ""),
            "classes": tags,
            "matched_rules": [x for x in tags if x != "other"],
            "classification_version": VERSION,
        })
        # Only explicit result/report language is strong execution evidence.
        if EXECUTION_STRONG.search(title):
            score += 10
            reasons.append("Handlingstitel indikerar dokumenterat genomförande: " + title)
        if "aftercare" in tags:
            score += 3
            reasons.append("Efterbevakning/eftersläckning nämns: " + title)
        if "invoice_compensation" in tags:
            score += 3
            reasons.append("Faktura/ersättning nämns: " + title)
        if "follow_up" in tags:
            score += 3
            reasons.append("Uppföljning/redovisning nämns: " + title)
        if "award" in tags:
            score += 1
        if "contract" in tags:
            score += 1
        if "notification" in tags:
            score += 1
    # A blank template named Bränningsprotokoll in procurement material is not execution evidence.
    if re.search(r"bränningsprotokoll", all_text, re.I) and not EXECUTION_STRONG.search(all_text):
        reasons.append("Bränningsprotokoll nämns, men ifyllt protokoll är inte verifierat.")
    status = "strong_execution_lead" if score >= 10 else "follow_up_lead" if score >= 5 else "planning_or_procurement" if score else "low_signal"
    return {
        "diary": case.get("diary", ""),
        "diary_number": case.get("diary_number", ""),
        "title": case.get("title", ""),
        "status": case.get("status", ""),
        "registered_date": case.get("registered_date", ""),
        "decision_date": case.get("decision_date", ""),
        "municipality": case.get("municipality", ""),
        "source_url": record.get("source_url", ""),
        "handling_count": len(handlings),
        "evidence_score": score,
        "priority": status,
        "reasons": list(dict.fromkeys(reasons)),
        "handlings": classified,
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/lansstyrelsen-diary/case-details.json"))
    p.add_argument("--output-dir", type=Path, default=Path("data/lansstyrelsen-diary/analysis"))
    a = p.parse_args()
    doc = json.loads(a.input.read_text(encoding="utf-8"))
    cases = list((doc.get("cases") or {}).values())
    county_cases, missing_case, missing_handling = Counter(), Counter(), Counter()
    class_counts, date_errors = Counter(), []
    seen_case, seen_handling = set(), set()
    duplicate_cases, duplicate_handlings = [], []
    classified_cases = []
    total_handlings = 0
    for record in cases:
        c = record.get("case") or {}
        county = c.get("diary") or "UNKNOWN"
        county_cases[county] += 1
        key = (county.casefold(), c.get("diary_number", ""))
        if key in seen_case: duplicate_cases.append(list(key))
        seen_case.add(key)
        for field in ("diary", "diary_number", "registered_date", "title", "status", "decision_date", "municipality"):
            if not str(c.get(field) or "").strip(): missing_case[field] += 1
        if c.get("registered_date") and not valid_date(c["registered_date"]): date_errors.append({"case": c.get("diary_number"), "field": "registered_date", "value": c["registered_date"]})
        if c.get("decision_date") and not valid_date(c["decision_date"]): date_errors.append({"case": c.get("diary_number"), "field": "decision_date", "value": c["decision_date"]})
        for h in record.get("handlings") or []:
            total_handlings += 1
            for field in ("handling_number", "title", "date", "sender_recipient"):
                if not str(h.get(field) or "").strip(): missing_handling[field] += 1
            if h.get("date") and not valid_date(h["date"]): date_errors.append({"case": c.get("diary_number"), "handling": h.get("handling_number"), "field": "date", "value": h["date"]})
            hkey = h.get("handling_key") or f"{key}::{h.get('handling_number','')}"
            if hkey in seen_handling: duplicate_handlings.append(hkey)
            seen_handling.add(hkey)
            for tag in classes(h.get("title", "")): class_counts[tag] += 1
        classified_cases.append(classify_case(record))
    a.output_dir.mkdir(parents=True, exist_ok=True)
    classified_handlings = [{"diary_number": c["diary_number"], "diary": c["diary"], **h} for c in classified_cases for h in c["handlings"]]
    priority = sorted(classified_cases, key=lambda x: (-x["evidence_score"], x["diary"], x["diary_number"]))
    report = {
        "schema_version": 1, "classification_version": VERSION,
        "source_updated_at": doc.get("updated_at"),
        "case_count": len(cases), "handling_count": total_handlings,
        "county_case_counts": dict(sorted(county_cases.items())),
        "missing_case_fields": dict(missing_case), "missing_handling_fields": dict(missing_handling),
        "handling_class_counts": dict(class_counts),
        "duplicate_case_keys": duplicate_cases, "duplicate_handling_keys": duplicate_handlings,
        "invalid_dates": date_errors,
        "notes": ["Missing optional fields are data-quality observations, not automatically parser failures.",
                  "Execution priority is a lead for human review; metadata alone does not establish that a burn occurred.",
                  "A bare Bränningsprotokoll attachment title is not treated as proof of execution."]
    }
    (a.output_dir / "quality-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (a.output_dir / "classified-handlings.json").write_text(json.dumps(classified_handlings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (a.output_dir / "priority-review.json").write_text(json.dumps(priority, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (a.output_dir / "priority-review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["diary", "diary_number", "title", "priority", "evidence_score", "registered_date", "decision_date", "municipality", "handling_count", "source_url", "reasons"]
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for item in priority:
            writer.writerow({**{k: item.get(k, "") for k in fields}, "reasons": " | ".join(item["reasons"])})
    print(json.dumps({"case_count": len(cases), "handling_count": total_handlings, "counties": len(county_cases), "output_dir": str(a.output_dir)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
