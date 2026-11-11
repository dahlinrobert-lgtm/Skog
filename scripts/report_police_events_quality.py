#!/usr/bin/env python3
"""Write a compact, auditable quality report for the Police events archive."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "police_events"
EVENTS = DATA / "events.csv"
CANDIDATES = DATA / "wildlife_candidates.csv"
INCIDENTS = DATA / "wildlife_incidents.csv"
OUT = DATA / "run_quality_report.json"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def count_by(rows: list[dict], field: str) -> dict[str, int]:
    counter = Counter((row.get(field) or "(missing)") for row in rows)
    return dict(sorted(counter.items()))


def build_report(events: list[dict], candidates: list[dict], incidents: list[dict]) -> dict:
    dated = [row.get("date", "") for row in events if row.get("date")]
    years = Counter(value[:4] for value in dated if len(value) >= 4)
    years_missing = sum(1 for row in events if not row.get("date"))
    occurrences = [row.get("occurrence_date", "") for row in incidents if row.get("occurrence_date")]
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Norrbottens län",
        "source": "Brottsplatskartan API; public Police event material",
        "interpretation": "Successful workflow and counts do not attest complete historical API coverage. Extracted wildlife rows are candidates, not confirmed collisions.",
        "archive": {
            "event_count": len(events),
            "unique_event_ids": len({row.get("event_id", "") for row in events if row.get("event_id")}),
            "missing_publication_date_count": years_missing,
            "publication_year_counts": dict(sorted(years.items())),
            "oldest_publication_date": min(dated) if dated else None,
            "newest_publication_date": max(dated) if dated else None,
            "event_type_counts": count_by(events, "type_original"),
        },
        "wildlife_text": {
            "broad_candidate_count": len(candidates),
            "individual_incident_candidate_count": len(incidents),
            "candidate_year_counts": dict(sorted(Counter(value[:4] for value in occurrences if len(value) >= 4).items())),
            "candidate_missing_occurrence_date_count": sum(1 for row in incidents if not row.get("occurrence_date")),
            "extraction_method_counts": count_by(incidents, "extraction_method"),
            "confidence_counts": count_by(incidents, "confidence"),
            "species_mentions": count_by(incidents, "species"),
        },
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, default=EVENTS)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--incidents", type=Path, default=INCIDENTS)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    events = read_csv(args.events)
    candidates = read_csv(args.candidates)
    incidents = read_csv(args.incidents)
    report = build_report(events, candidates, incidents)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
