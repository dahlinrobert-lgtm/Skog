from __future__ import annotations
import argparse, csv, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "police_events"
INDIVIDUAL_METHODS = {"wildlife_text_line_v1", "wildlife_time_segment_v2"}
COUNT_METHOD = "explicit_count_v1"

def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def classify_geography(text):
    value = (text or "").casefold()
    if any(token in value for token in ("e4", "e10", "e45", "riksväg ", "länsväg ", "väg ")):
        return "possible_road_reference"
    if any(token in value for token in ("mellan ", "på ", "vid ", "i luleå", "luleå")):
        return "place_or_route_text_needs_review"
    return "unclassified_place_text"

def build_review(rows):
    lulea = [r for r in rows if (r.get("municipality") or "").strip().casefold() == "luleå"]
    individual = [dict(r) for r in lulea if r.get("extraction_method") in INDIVIDUAL_METHODS]
    count_only = [r for r in lulea if r.get("extraction_method") == COUNT_METHOD]
    for row in individual:
        has_time = bool((row.get("occurrence_time") or "").strip())
        has_date = bool((row.get("occurrence_date") or "").strip())
        row["review_priority"] = "time_and_date_available" if has_time and has_date else ("time_only" if has_time else "missing_occurrence_time")
        row["geographic_evidence_type"] = classify_geography((row.get("description") or "") + " " + (row.get("place_text") or ""))
    individual.sort(key=lambda r: (not bool(r.get("occurrence_date")), not bool(r.get("occurrence_time")), r.get("occurrence_date") or r.get("publication_date") or "", r.get("occurrence_time") or "", r.get("parent_event_id") or ""))
    report = {
        "schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Luleå municipality", "source_file": "wildlife_incidents.csv",
        "interpretation": "Review subset only. Individual extracted time-segment candidates are not verified collisions. Count-only rows are excluded and reported separately. Expanded child rows retain parent event IDs and occurrence indices. No geocoding or NVR matching is performed.",
        "input_row_count": len(rows), "lulea_candidate_row_count": len(lulea),
        "individual_text_candidate_count": len(individual), "count_only_candidate_row_count": len(count_only),
        "individual_with_occurrence_date_count": sum(bool(r.get("occurrence_date")) for r in individual),
        "individual_with_occurrence_time_count": sum(bool(r.get("occurrence_time")) for r in individual),
        "unique_parent_event_count": len({r.get("parent_event_id") for r in individual if r.get("parent_event_id")}),
        "review_priority_counts": dict(sorted(Counter(r["review_priority"] for r in individual).items())),
        "geographic_evidence_type_counts": dict(sorted(Counter(r["geographic_evidence_type"] for r in individual).items())),
    }
    return individual, report

def main():
    parser = argparse.ArgumentParser(description="Build a conservative review subset of individual Luleå wildlife statements.")
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA / "wildlife_incidents.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA / "lulea_review_candidates.csv")
    parser.add_argument("--report", type=Path, default=DEFAULT_DATA / "lulea_review_report.json")
    args = parser.parse_args()
    rows = read_rows(args.input)
    candidates, report = build_review(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(candidates[0]) if candidates else ["parent_event_id","publication_date","occurrence_date","occurrence_date_basis","occurrence_time","municipality","species","place_text","description","source_link","extraction_method","confidence","occurrence_index","review_priority","geographic_evidence_type"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(candidates)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Review CSV: {args.output}"); print(f"Report: {args.report}")

if __name__ == "__main__":
    main()
