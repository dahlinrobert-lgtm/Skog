#!/usr/bin/env python3
"""Extract reproducible event- and road-candidate features from NVDB match CSV.

This is descriptive analysis only. It does not infer a correct road, train a
classifier, change temporal matching, or modify the input file.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


def clean(value):
    if value is None:
        return ""
    value = str(value).strip()
    return "" if value.casefold() in {"", "none", "nan", "<na>"} else value


def number(value):
    try:
        result = float(clean(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def parse_candidates(value):
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def extract(rows, *, id_field=""):
    event_rows = []
    candidate_rows = []
    status_counts = Counter()
    role_counts = Counter()
    road_counts = Counter()
    for row_number, row in enumerate(rows, 1):
        event_id = clean(row.get(id_field)) if id_field else ""
        lat = number(row.get("nvr_latitude_wgs84"))
        lon = number(row.get("nvr_longitude_wgs84"))
        status = clean(row.get("geo_nvdb_search_status")) or "missing_status"
        candidates = parse_candidates(row.get("geo_nvdb_candidates"))
        candidates.sort(key=lambda c: (
            number(c.get("distance_m")) if number(c.get("distance_m")) is not None else math.inf,
            clean(c.get("road_number")), clean(c.get("element_id")),
        ))
        distances = [number(c.get("distance_m")) for c in candidates]
        valid_distances = [d for d in distances if d is not None]
        nearest = valid_distances[0] if valid_distances else number(row.get("geo_nvdb_nearest_road_distance_m"))
        second = valid_distances[1] if len(valid_distances) > 1 else None
        gap = round(second - nearest, 2) if nearest is not None and second is not None else None
        ratio = round(second / nearest, 3) if nearest is not None and second is not None and nearest > 0 else None
        sources = sorted({clean(c.get("source_file")) for c in candidates if clean(c.get("source_file"))})
        event_rows.append({
            "row_number": row_number, "event_id": event_id,
            "latitude": lat, "longitude": lon,
            "search_status": status,
            "candidate_count_reported": number(row.get("geo_nvdb_candidate_count")),
            "candidate_count_in_payload": len(candidates),
            "nearest_distance_m": nearest,
            "second_distance_m": second,
            "nearest_second_gap_m": gap,
            "nearest_second_ratio": ratio,
            "source_files_in_candidates": ";".join(sources),
            "source_file_count_in_candidates": len(sources),
            "sources_queried": number(row.get("geo_nvdb_sources_queried")),
            "sources_failed": number(row.get("geo_nvdb_sources_failed")),
            "search_radius_m": number(row.get("geo_nvdb_search_radius_m")),
        })
        status_counts[status] += 1
        for rank, candidate in enumerate(candidates, 1):
            distance = number(candidate.get("distance_m"))
            role = clean(candidate.get("road_role"))
            road = clean(candidate.get("road_number"))
            source = clean(candidate.get("source_file"))
            role_counts[role or "missing"] += 1
            road_counts[road or "missing"] += 1
            candidate_rows.append({
                "row_number": row_number, "event_id": event_id,
                "latitude": lat, "longitude": lon,
                "candidate_rank_by_distance": rank,
                "distance_m": distance,
                "gap_from_nearest_m": round(distance - nearest, 2) if distance is not None and nearest is not None else None,
                "road_number": road, "road_role": role,
                "element_id": clean(candidate.get("element_id")),
                "source_file": source,
                "search_status": status,
                "candidate_count_in_payload": len(candidates),
                "nearest_second_gap_m": gap,
                "nearest_second_ratio": ratio,
            })
    summary = {
        "schema_version": "nvdb_candidate_feature_analysis_v1",
        "review_only": True,
        "input_events": len(rows),
        "candidate_rows": len(candidate_rows),
        "search_status_counts": dict(sorted(status_counts.items())),
        "road_role_candidate_counts": dict(sorted(role_counts.items())),
        "road_number_candidate_counts": dict(sorted(road_counts.items())),
        "limitations": [
            "Candidate rank and distance are descriptive, not correctness labels.",
            "Only candidates retained in the input CSV are analyzed; candidates beyond its cap are unavailable.",
            "Source-file presence is provenance, not proof of geographic coverage.",
            "No temporal matching fields are changed and no road is automatically confirmed.",
        ],
    }
    return event_rows, candidate_rows, summary


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--events-output", type=Path, required=True)
    parser.add_argument("--candidates-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--event-id-field", default="")
    args = parser.parse_args()
    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            parser.error("Indata saknar CSV-rubrik.")
        if args.event_id_field and args.event_id_field not in reader.fieldnames:
            parser.error(f"Händelse-ID-fältet saknas: {args.event_id_field}")
        rows = list(reader)
    events, candidates, summary = extract(rows, id_field=args.event_id_field)
    write_csv(args.events_output, events)
    write_csv(args.candidates_output, candidates)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "completed", "review_only": True,
        "input_events": len(events), "candidate_rows": len(candidates),
        "events_output": str(args.events_output),
        "candidates_output": str(args.candidates_output),
        "summary_output": str(args.summary_output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
