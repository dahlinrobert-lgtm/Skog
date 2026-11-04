#!/usr/bin/env python3
"""Prioritize SCA overlap relations for manual review; never resolve object identity."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

INPUT = Path("input")
OUT = Path("output")
OVERLAP_CATEGORIES = {"partial_overlap_review", "contained_or_nested_review"}


def number(value):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def tile_xy(value):
    try:
        x, y = str(value).split("/", 1)
        return int(x), int(y)
    except (TypeError, ValueError):
        return None


def classify_relation(edge):
    category = edge.get("category")
    same_class = edge.get("same_class") is True
    same_motive = edge.get("same_motive") is True
    smaller = number(edge.get("overlap_smaller_epsg3006"))
    ratio = number(edge.get("area_ratio"))

    motive_a = str(edge.get("motive_a") or "").strip()
    motive_b = str(edge.get("motive_b") or "").strip()
    motive_status = (
        "missing_one_or_both" if not motive_a or not motive_b
        else "same" if motive_a == motive_b
        else "different"
    )

    if category == "contained_or_nested_review":
        bucket = "nested_same_class" if same_class else "nested_cross_class_or_unknown"
        priority = 2 if not same_class else 3
    elif category == "partial_overlap_review" and not same_class:
        bucket = "partial_cross_class"
        priority = 1
    elif category == "partial_overlap_review" and same_class and smaller is not None and ratio is not None and smaller >= 0.95 and ratio <= 0.20:
        bucket = "partial_same_class_fragment_signal"
        priority = 1
    elif category == "partial_overlap_review" and same_class and smaller is not None and smaller >= 0.95:
        bucket = "partial_same_class_high_smaller_coverage"
        priority = 2
    else:
        bucket = "partial_general"
        priority = 3

    if motive_status == "different":
        priority = min(priority, 1)

    return bucket, priority, motive_status


def build_prioritized_review(data):
    all_edges = data.get("candidate_pairs", [])
    rows = []
    bucket_counts = Counter()
    class_pair_counts = Counter()
    motive_counts = Counter()
    direction_counts = Counter()
    tile_delta_counts = Counter()

    for edge in all_edges:
        if edge.get("category") not in OVERLAP_CATEGORIES:
            continue
        row = dict(edge)
        bucket, priority, motive_status = classify_relation(edge)
        a = tile_xy(edge.get("tile_a"))
        b = tile_xy(edge.get("tile_b"))
        if a is None or b is None:
            raise ValueError("Overlap relation has invalid tile coordinate")
        dx, dy = b[0] - a[0], b[1] - a[1]
        chebyshev = max(abs(dx), abs(dy))
        if chebyshev > 1:
            raise ValueError("Overlap relation exceeds the topology tile-neighbor rule")
        direction = (
            "same_tile" if dx == 0 and dy == 0 else
            "east" if dx == 1 and dy == 0 else
            "west" if dx == -1 and dy == 0 else
            "south" if dx == 0 and dy == 1 else
            "north" if dx == 0 and dy == -1 else
            "south_east" if dx == 1 and dy == 1 else
            "south_west" if dx == -1 and dy == 1 else
            "north_east" if dx == 1 and dy == -1 else
            "north_west"
        )
        class_a = str(edge.get("class_a") or "(missing)")
        class_b = str(edge.get("class_b") or "(missing)")
        pair = " <> ".join(sorted((class_a, class_b)))
        row.update({
            "review_bucket": bucket,
            "review_priority": priority,
            "motive_relation": motive_status,
            "tile_dx": dx,
            "tile_dy": dy,
            "tile_chebyshev_distance": chebyshev,
            "tile_neighbor_direction_b_to_a": direction,
            "canonical_class_pair": pair,
            "possible_fragmentation_signal": bucket == "partial_same_class_fragment_signal",
            "identity_resolved": False,
            "review_status": "manual_review_only_no_identity_resolution"
        })
        rows.append(row)
        bucket_counts[bucket] += 1
        class_pair_counts[pair] += 1
        motive_counts[motive_status] += 1
        direction_counts[direction] += 1
        tile_delta_counts[f"{dx},{dy}"] += 1

    rows.sort(key=lambda r: (
        int(r["review_priority"]), r["review_bucket"],
        r["canonical_class_pair"], str(r.get("source_key_a")),
        str(r.get("source_key_b"))
    ))
    summary = {
        "source_feature_records_total": int((data.get("summary") or {}).get("source_feature_records", 0)),
        "topology_candidate_pairs_total": len(all_edges),
        "overlap_review_relations_total": len(rows),
        "review_bucket_counts": dict(sorted(bucket_counts.items())),
        "canonical_class_pair_counts": dict(sorted(class_pair_counts.items(), key=lambda item: (-item[1], item[0]))),
        "motive_relation_counts": dict(sorted(motive_counts.items())),
        "tile_neighbor_direction_counts": dict(sorted(direction_counts.items())),
        "tile_delta_counts": dict(sorted(tile_delta_counts.items())),
        "priority_1_relations": sum(r["review_priority"] == 1 for r in rows),
        "possible_fragmentation_signal_relations": sum(r["possible_fragmentation_signal"] for r in rows),
        "cross_class_partial_relations": bucket_counts["partial_cross_class"],
        "identity_resolved_relations": sum(r["identity_resolved"] for r in rows),
        "policy": [
            "Priority and buckets are review triage only, not probability or identity classification.",
            "High smaller-geometry coverage with low area ratio is a possible fragment signal, not proof of a shared object.",
            "Cross-class overlap is treated as thematic review, not same-object grouping.",
            "Motive disagreement is an independent review flag.",
            "Tile direction is derived from source tile coordinates and does not infer clipping.",
            "All source keys and original relation metrics are retained; no geometries are merged or modified."
        ]
    }
    if len(rows) != sum(bucket_counts.values()):
        raise ValueError("Review bucket counts do not reconcile to relation count")
    if summary["identity_resolved_relations"] != 0:
        raise ValueError("This workflow must never resolve object identity")
    return summary, rows


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    files = sorted(INPUT.rglob("sca-national-topology-review.json"))
    if len(files) != 1:
        raise SystemExit(f"Expected one topology review JSON, found {len(files)}")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    summary, rows = build_prioritized_review(data)
    summary["input_topology_review"] = str(files[0])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sca-national-overlap-priority-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(OUT / "sca-national-overlap-priority-review.csv", rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
