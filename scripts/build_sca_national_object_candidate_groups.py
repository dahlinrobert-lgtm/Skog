#!/usr/bin/env python3
"""Build conservative cross-tile object-candidate groups from topology audit edges.

Only exact-geometry and very-high-overlap near-duplicate edges are grouped.
All source observations remain immutable and are emitted one row per source key.
Lower-confidence overlap/boundary relations remain separate review edges.
"""
from __future__ import annotations
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("input")
OUT = Path("output")
HIGH_CONFIDENCE = {"exact_geometry_duplicate", "near_duplicate_candidate"}


def stable_id(keys):
    payload = "\n".join(sorted(keys)).encode("utf-8")
    return "sca-cand-" + hashlib.sha256(payload).hexdigest()[:16]


def build_candidate_groups(data):
    edges = data.get("candidate_pairs", [])
    source_record_count = int((data.get("summary") or {}).get("source_feature_records", 0))
    if source_record_count < 0:
        raise ValueError("Invalid negative source_feature_records count in topology summary")

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra > rb:
                ra, rb = rb, ra
            parent[rb] = ra

    # A source key can occur in several pair records. Select its observation
    # metadata deterministically, independent of candidate-pair input order.
    observation_candidates = defaultdict(list)
    for edge in edges:
        a, b = edge["source_key_a"], edge["source_key_b"]
        observation_candidates[a].append({
            "source_key": a, "source_batch": edge["batch_a"], "source_tile": edge["tile_a"],
            "class": edge["class_a"], "motive": edge["motive_a"], "geometry_hash": edge["geometry_hash_a"]
        })
        observation_candidates[b].append({
            "source_key": b, "source_batch": edge["batch_b"], "source_tile": edge["tile_b"],
            "class": edge["class_b"], "motive": edge["motive_b"], "geometry_hash": edge["geometry_hash_b"]
        })
        if edge["category"] in HIGH_CONFIDENCE:
            union(a, b)

    def observation_sort_key(item):
        return tuple("" if value is None else str(value) for value in (
            item["source_batch"], item["source_tile"], item["class"],
            item["motive"], item["geometry_hash"]
        ))

    observations = {
        key: min(candidates, key=observation_sort_key)
        for key, candidates in observation_candidates.items()
    }

    if source_record_count < len(observations):
        raise ValueError(
            "Topology summary source_feature_records is smaller than the unique "
            "source keys represented in candidate_pairs"
        )

    components = defaultdict(set)
    for key in parent:
        components[find(key)].add(key)

    group_edges = defaultdict(list)
    for edge in edges:
        if edge["category"] in HIGH_CONFIDENCE:
            group_edges[find(edge["source_key_a"])].append(edge)

    group_rows, member_rows = [], []
    for root, keys in sorted(components.items()):
        if len(keys) < 2:
            continue
        edge_rows = group_edges[root]
        categories = Counter(edge["category"] for edge in edge_rows)
        classes = sorted({observations[key]["class"] for key in keys if observations[key]["class"]})
        motives = sorted({observations[key]["motive"] for key in keys if observations[key]["motive"]})
        missing_motive_count = sum(not observations[key]["motive"] for key in keys)
        hashes = sorted({observations[key]["geometry_hash"] for key in keys})
        group_id = stable_id(keys)
        has_near = categories["near_duplicate_candidate"] > 0
        group_rows.append({
            "candidate_group_id": group_id,
            "confidence_tier": "high_exact_and_near" if has_near else "high_exact_only",
            "source_observation_count": len(keys),
            "source_tile_count": len({observations[key]["source_tile"] for key in keys}),
            "exact_edge_count": categories["exact_geometry_duplicate"],
            "near_edge_count": categories["near_duplicate_candidate"],
            "class_conflict": len(classes) > 1,
            "motive_conflict": len(motives) > 1,
            "missing_motive_observation_count": missing_motive_count,
            "resolved_classes": " | ".join(classes),
            "resolved_motives": " | ".join(motives),
            "distinct_geometry_hashes": len(hashes),
            "review_status": "candidate_only_not_merged"
        })
        for key in sorted(keys):
            observation = observations[key]
            member_rows.append({
                "candidate_group_id": group_id, "source_key": key,
                "source_batch": observation["source_batch"], "source_tile": observation["source_tile"],
                "class": observation["class"], "motive": observation["motive"],
                "geometry_hash": observation["geometry_hash"],
                "review_status": "retain_source_observation"
            })

    category_counts = Counter(edge["category"] for edge in edges)
    high_confidence_edge_count = sum(category_counts[category] for category in HIGH_CONFIDENCE)
    summary = {
        "input_topology_review": "input/sca-national-topology-review.json",
        "topology_candidate_edges": len(edges),
        "unique_source_observations_in_topology_edges": len(observations),
        "high_confidence_edges_grouped": high_confidence_edge_count,
        "candidate_groups": len(group_rows),
        "source_observations_in_groups": len(member_rows),
        "observations_not_in_candidate_groups_but_seen_in_edges": len(observations) - len(member_rows),
        "source_feature_records_total": source_record_count,
        "source_records_without_any_candidate_edge": source_record_count - len(observations),
        "source_records_not_grouped_total": source_record_count - len(member_rows),
        "group_observation_count_distribution": dict(sorted(Counter(
            str(group["source_observation_count"]) for group in group_rows
        ).items())),
        "groups_with_class_conflict": sum(group["class_conflict"] for group in group_rows),
        "groups_with_motive_conflict": sum(group["motive_conflict"] for group in group_rows),
        "groups_with_missing_motive": sum(group["missing_motive_observation_count"] > 0 for group in group_rows),
        "groups_with_all_motives_missing": sum(
            group["missing_motive_observation_count"] == group["source_observation_count"]
            for group in group_rows
        ),
        "missing_motive_observations_in_groups": sum(
            group["missing_motive_observation_count"] for group in group_rows
        ),
        "all_review_edges_by_category": dict(category_counts),
        "policy": [
            "Only exact geometry and >=95% IoU/area-ratio same-class edges are grouped.",
            "Grouping is a candidate relation, not a confirmed SCA object identity.",
            "No source observation is deleted, dissolved, or geometrically merged.",
            "Contained, partial-overlap and nearby-boundary edges remain ungrouped for manual or later model review.",
            "Transitive connected components can still over-group; inspect group size and attribute conflicts before promoting any group.",
            "Missing motive attributes are reported separately from conflicting non-empty motive values."
        ]
    }
    if summary["source_observations_in_groups"] > summary["unique_source_observations_in_topology_edges"]:
        raise ValueError("Grouped observation count exceeds the topology edge observation universe")
    if min(summary["source_records_without_any_candidate_edge"],
           summary["source_records_not_grouped_total"]) < 0:
        raise ValueError("Derived source-record counts must not be negative")
    return summary, group_rows, member_rows


def main():
    files = sorted(INPUT.rglob("sca-national-topology-review.json"))
    if len(files) != 1:
        raise SystemExit(f"Expected one topology review JSON, found {len(files)}")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    summary, group_rows, member_rows = build_candidate_groups(data)
    summary["input_topology_review"] = str(files[0])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sca-national-object-candidate-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name, rows in [
        ("sca-national-object-candidate-groups.csv", group_rows),
        ("sca-national-object-candidate-members.csv", member_rows),
    ]:
        fields = list(rows[0]) if rows else ["candidate_group_id"]
        with (OUT / name).open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
