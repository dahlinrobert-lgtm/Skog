#!/usr/bin/env python3
"""Build a deterministic, review-only quality report from NVDB road-match CSV output.

Uses only the Python standard library. It never changes the match output or
makes an automatic road confirmation. Flagged records are all retained in the
review queue; additional records are selected deterministically per source file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def number(value):
    try:
        result = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def json_list(value):
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return round(ordered[low], 2)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (index - low), 2)


def stable_key(row, row_number, id_field):
    identifier = (row.get(id_field) or "").strip() if id_field else ""
    if identifier:
        return identifier
    material = "|".join([
        str(row_number),
        row.get("nvr_latitude_wgs84", ""),
        row.get("nvr_longitude_wgs84", ""),
        row.get("geo_nvdb_nearest_road_element_id", ""),
    ])
    return material


def analyze(rows, *, id_field="", far_m=100, very_far_m=500,
            ambiguity_gap_m=25, sample_per_source=20, seed="nvdb-review-v1"):
    statuses = Counter()
    distances = []
    candidate_counts = []
    flagged = []
    eligible_by_source = defaultdict(list)
    source_coverage = Counter()
    source_failures = 0

    for index, row in enumerate(rows, start=1):
        status = row.get("geo_nvdb_search_status", "missing_status")
        statuses[status] += 1
        distance = number(row.get("geo_nvdb_nearest_road_distance_m"))
        candidates = json_list(row.get("geo_nvdb_candidates"))
        candidate_count = number(row.get("geo_nvdb_candidate_count"))
        candidate_counts.append(int(candidate_count or 0))
        if distance is not None:
            distances.append(distance)

        sources = sorted({
            str(item.get("source_file", "")).strip()
            for item in candidates if isinstance(item, dict) and item.get("source_file")
        })
        for source in sources:
            source_coverage[source] += 1
        try:
            source_failures += int(row.get("geo_nvdb_sources_failed") or 0)
        except (TypeError, ValueError):
            source_failures += 1

        flags = []
        if status not in {"completed_with_candidates"}:
            flags.append("nonstandard_search_status")
        if distance is not None and distance >= very_far_m:
            flags.append("very_far_from_road")
        elif distance is not None and distance >= far_m:
            flags.append("far_from_road")

        valid_distances = sorted(
            number(item.get("distance_m")) for item in candidates
            if isinstance(item, dict) and number(item.get("distance_m")) is not None
        )
        if len(valid_distances) >= 2 and valid_distances[1] - valid_distances[0] <= ambiguity_gap_m:
            flags.append("close_alternative_candidates")
        if len(candidates) > 1:
            candidate_counts[-1] = max(candidate_counts[-1], len(candidates))

        record = {
            "row_number": index,
            "event_id": row.get(id_field, "") if id_field else "",
            "latitude": row.get("nvr_latitude_wgs84", ""),
            "longitude": row.get("nvr_longitude_wgs84", ""),
            "search_status": status,
            "nearest_road_number": row.get("geo_nvdb_nearest_road_number", ""),
            "nearest_element_id": row.get("geo_nvdb_nearest_road_element_id", ""),
            "nearest_distance_m": distance,
            "candidate_count": int(candidate_count or len(candidates)),
            "source_files": ";".join(sources),
            "review_flags": ";".join(flags),
            "review_status": "pending",
        }
        if flags:
            flagged.append(record)
        else:
            group = sources[0] if sources else "no_source_attributed"
            digest = hashlib.sha256(f"{seed}|{group}|{stable_key(row, index, id_field)}".encode()).hexdigest()
            eligible_by_source[group].append((digest, record))

    sampled = []
    for source, items in sorted(eligible_by_source.items()):
        sampled.extend(record for _, record in sorted(items, key=lambda item: item[0])[:sample_per_source])

    queue = sorted(flagged + sampled, key=lambda item: item["row_number"])
    valid_source_rows = sum(statuses[s] for s in ("completed_with_candidates", "completed_no_candidate_in_search_window"))
    summary = {
        "schema_version": "nvdb_validation_report_v1",
        "review_only": True,
        "input_rows": len(rows),
        "search_status_counts": dict(sorted(statuses.items())),
        "rows_with_candidates": statuses["completed_with_candidates"],
        "rows_without_candidate_in_search_window": statuses["completed_no_candidate_in_search_window"],
        "rows_with_nonstandard_status": len(rows) - valid_source_rows,
        "source_read_failures_total": source_failures,
        "distance_m": {
            "count": len(distances),
            "min": round(min(distances), 2) if distances else None,
            "median": round(statistics.median(distances), 2) if distances else None,
            "p90": percentile(distances, 0.90),
            "p95": percentile(distances, 0.95),
            "max": round(max(distances), 2) if distances else None,
        },
        "candidate_count": {
            "mean": round(statistics.mean(candidate_counts), 2) if candidate_counts else None,
            "max": max(candidate_counts) if candidate_counts else 0,
        },
        "source_file_event_counts": dict(sorted(source_coverage.items())),
        "review_queue": {
            "flagged_rows": len(flagged),
            "deterministic_sample_rows": len(sampled),
            "total_rows": len(queue),
            "sample_per_source": sample_per_source,
            "seed": seed,
        },
        "thresholds": {
            "far_m": far_m,
            "very_far_m": very_far_m,
            "ambiguity_gap_m": ambiguity_gap_m,
        },
        "limitations": [
            "Nearest-road distance is not proof that the event occurred on that road.",
            "Source-file counts describe candidate provenance, not geographic coverage.",
            "A no-candidate result is limited to the configured search window and readable sources.",
            "This report does not alter temporal matching or confirm any road.",
        ],
    }
    return summary, queue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="NVDB-enriched match CSV.")
    parser.add_argument("--report", type=Path, required=True, help="Output JSON quality report.")
    parser.add_argument("--review-queue", type=Path, required=True, help="Output CSV for manual review.")
    parser.add_argument("--event-id-field", default="", help="Optional stable event ID column.")
    parser.add_argument("--far-m", type=float, default=100.0)
    parser.add_argument("--very-far-m", type=float, default=500.0)
    parser.add_argument("--ambiguity-gap-m", type=float, default=25.0)
    parser.add_argument("--sample-per-source", type=int, default=20)
    parser.add_argument("--seed", default="nvdb-review-v1")
    args = parser.parse_args()
    if args.far_m < 0 or args.very_far_m < args.far_m or args.ambiguity_gap_m < 0 or args.sample_per_source < 0:
        parser.error("Trösklar måste vara icke-negativa och very-far-m minst far-m.")

    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            parser.error("Indata saknar CSV-rubrik.")
        rows = list(reader)
    summary, queue = analyze(
        rows, id_field=args.event_id_field, far_m=args.far_m,
        very_far_m=args.very_far_m, ambiguity_gap_m=args.ambiguity_gap_m,
        sample_per_source=args.sample_per_source, seed=args.seed,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.review_queue.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["row_number", "event_id", "latitude", "longitude", "search_status",
              "nearest_road_number", "nearest_element_id", "nearest_distance_m",
              "candidate_count", "source_files", "review_flags", "review_status"]
    with args.review_queue.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(queue)
    print(json.dumps({
        "status": "completed",
        "input_rows": len(rows),
        "review_queue_rows": len(queue),
        "flagged_rows": summary["review_queue"]["flagged_rows"],
        "sample_rows": summary["review_queue"]["deterministic_sample_rows"],
        "report": str(args.report),
        "review_queue": str(args.review_queue),
        "review_only": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
