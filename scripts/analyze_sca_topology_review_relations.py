#!/usr/bin/env python3
"""Create a review-only diagnostic extract for SCA partial/contained overlaps.

This script never resolves identity and never alters source geometries.
It preserves every selected relation and reports source-key metadata variation.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("input")
OUT = Path("output")
REVIEW_CATEGORIES = {"partial_overlap_review", "contained_or_nested_review"}
NEARBY_CATEGORY = "nearby_boundary_review"
METADATA_FIELDS = {
    "batch": ("batch_a", "batch_b"),
    "tile": ("tile_a", "tile_b"),
    "class": ("class_a", "class_b"),
    "motive": ("motive_a", "motive_b"),
    "geometry_hash": ("geometry_hash_a", "geometry_hash_b"),
}


def _norm(value):
    return "" if value is None else str(value)


def _finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def diagnostic_bucket(edge):
    """Descriptive review priority, not a same-object classifier."""
    category = edge.get("category")
    same_class = edge.get("same_class") is True
    smaller = _finite_number(edge.get("overlap_smaller_epsg3006"))
    ratio = _finite_number(edge.get("area_ratio"))

    if category == "contained_or_nested_review":
        return "contained_nested_review"
    if category != "partial_overlap_review":
        return "other_relation_not_in_overlap_extract"
    if not same_class:
        return "partial_cross_class_review"
    if smaller is not None and smaller >= 0.95 and ratio is not None and ratio <= 0.20:
        return "partial_near_full_smaller_low_area_ratio"
    if smaller is not None and smaller >= 0.95:
        return "partial_near_full_smaller"
    return "partial_general_review"


def build_relation_review(data):
    edges = data.get("candidate_pairs", [])
    source_count = int((data.get("summary") or {}).get("source_feature_records", 0))
    relation_rows = []
    metadata_values = defaultdict(lambda: defaultdict(set))
    category_counts = Counter()
    all_category_counts = Counter()
    bucket_counts = Counter()
    class_match_counts = Counter()
    motive_match_counts = Counter()
    missing_motive_relation_count = 0

    for edge in edges:
        category = edge.get("category", "")
        all_category_counts[category] += 1
        a, b = edge.get("source_key_a"), edge.get("source_key_b")
        if not a or not b:
            raise ValueError("Every candidate relation must contain both source keys")

        for field, (field_a, field_b) in METADATA_FIELDS.items():
            metadata_values[a][field].add(_norm(edge.get(field_a)))
            metadata_values[b][field].add(_norm(edge.get(field_b)))

        if category not in REVIEW_CATEGORIES:
            continue

        row = dict(edge)
        row["diagnostic_bucket"] = diagnostic_bucket(edge)
        row["review_status"] = "relation_review_only_no_identity_resolution"
        relation_rows.append(row)
        category_counts[category] += 1
        bucket_counts[row["diagnostic_bucket"]] += 1
        class_match_counts[str(edge.get("same_class"))] += 1

        motive_a, motive_b = _norm(edge.get("motive_a")), _norm(edge.get("motive_b"))
        both_motives_present = bool(motive_a and motive_b)
        row["both_motives_present"] = both_motives_present
        motive_match_counts["both_present_same" if both_motives_present and motive_a == motive_b
                            else "both_present_different" if both_motives_present
                            else "one_or_both_missing"] += 1
        if not both_motives_present:
            missing_motive_relation_count += 1

    metadata_rows = []
    metadata_conflict_counts = Counter()
    for source_key in sorted(metadata_values):
        values = metadata_values[source_key]
        row = {"source_key": source_key}
        conflict_fields = []
        for field in METADATA_FIELDS:
            distinct = sorted(values[field])
            row[f"{field}_distinct_value_count"] = len(distinct)
            row[f"{field}_values_json"] = json.dumps(distinct, ensure_ascii=False)
            if len(distinct) > 1:
                conflict_fields.append(field)
                metadata_conflict_counts[field] += 1
        row["metadata_conflict_fields"] = "|".join(conflict_fields)
        row["has_metadata_conflict"] = bool(conflict_fields)
        metadata_rows.append(row)

    relation_rows.sort(key=lambda row: (
        _norm(row.get("category")), _norm(row.get("source_key_a")),
        _norm(row.get("source_key_b"))
    ))
    metadata_rows.sort(key=lambda row: row["source_key"])

    summary = {
        "source_feature_records_total": source_count,
        "candidate_pairs_total": len(edges),
        "all_relation_categories": dict(sorted(all_category_counts.items())),
        "nearby_boundary_relations_kept_separate": all_category_counts[NEARBY_CATEGORY],
        "overlap_review_relations": len(relation_rows),
        "overlap_relation_categories": dict(sorted(category_counts.items())),
        "diagnostic_buckets": dict(sorted(bucket_counts.items())),
        "overlap_relations_same_class": class_match_counts["True"],
        "overlap_relations_different_or_unknown_class": len(relation_rows) - class_match_counts["True"],
        "overlap_relations_both_motives_present_and_same": motive_match_counts["both_present_same"],
        "overlap_relations_both_motives_present_and_different": motive_match_counts["both_present_different"],
        "overlap_relations_one_or_both_motives_missing": missing_motive_relation_count,
        "source_keys_seen_in_candidate_pairs": len(metadata_rows),
        "source_keys_with_any_metadata_conflict": sum(bool(r["has_metadata_conflict"]) for r in metadata_rows),
        "source_key_metadata_conflicts_by_field": dict(sorted(metadata_conflict_counts.items())),
        "policy": [
            "Every overlap/containment relation is a review relation, not an object identity.",
            "No source geometry or source observation is merged, dissolved, or deleted.",
            "Partial overlap and contained/nested relations are reported separately.",
            "Nearby-boundary relations are counted but excluded from the overlap relation extract.",
            "Metadata conflicts are counted per source key and field; no representative value is silently selected here.",
            "Possible clipping or fragmentation patterns are diagnostic buckets only and require source-level verification."
        ]
    }

    if sum(category_counts.values()) != len(relation_rows):
        raise ValueError("Overlap category totals do not match relation row count")
    if summary["source_keys_with_any_metadata_conflict"] > summary["source_keys_seen_in_candidate_pairs"]:
        raise ValueError("Metadata conflict count exceeds source-key universe")
    return summary, relation_rows, metadata_rows


def _write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    files = sorted(INPUT.rglob("sca-national-topology-review.json"))
    if len(files) != 1:
        raise SystemExit(f"Expected one topology review JSON, found {len(files)}")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    summary, relations, metadata = build_relation_review(data)
    summary["input_topology_review"] = str(files[0])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sca-national-overlap-review-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(OUT / "sca-national-overlap-review-relations.csv", relations)
    _write_csv(OUT / "sca-national-source-key-metadata-audit.csv", metadata)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
