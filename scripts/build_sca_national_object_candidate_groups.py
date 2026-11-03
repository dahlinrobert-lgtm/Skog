#!/usr/bin/env python3
"""Build conservative cross-tile object-candidate groups from topology audit edges.

Only exact-geometry and very-high-overlap near-duplicate edges are grouped.
All source observations remain immutable and are emitted one row per source key.
Lower-confidence overlap/boundary relations remain separate review edges.
"""
from __future__ import annotations
import csv, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("input")
OUT = Path("output")
HIGH_CONFIDENCE = {"exact_geometry_duplicate", "near_duplicate_candidate"}

def stable_id(keys):
    payload = "\n".join(sorted(keys)).encode("utf-8")
    return "sca-cand-" + hashlib.sha256(payload).hexdigest()[:16]

def main():
    files = sorted(INPUT.rglob("sca-national-topology-review.json"))
    if len(files) != 1:
        raise SystemExit(f"Expected one topology review JSON, found {len(files)}")
    data = json.loads(files[0].read_text(encoding="utf-8"))
    edges = data.get("candidate_pairs", [])
    parent, members = {}, {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            # deterministic root
            if ra > rb: ra, rb = rb, ra
            parent[rb] = ra
    observations = {}
    for e in edges:
        a, b = e["source_key_a"], e["source_key_b"]
        observations[a] = {
            "source_key": a, "source_batch": e["batch_a"], "source_tile": e["tile_a"],
            "class": e["class_a"], "motive": e["motive_a"], "geometry_hash": e["geometry_hash_a"]
        }
        observations[b] = {
            "source_key": b, "source_batch": e["batch_b"], "source_tile": e["tile_b"],
            "class": e["class_b"], "motive": e["motive_b"], "geometry_hash": e["geometry_hash_b"]
        }
        if e["category"] in HIGH_CONFIDENCE:
            union(a, b)
    components = defaultdict(set)
    for key in parent:
        components[find(key)].add(key)
    group_edges = defaultdict(list)
    for e in edges:
        if e["category"] in HIGH_CONFIDENCE:
            group_edges[find(e["source_key_a"])].append(e)
    group_rows, member_rows = [], []
    for root, keys in sorted(components.items()):
        if len(keys) < 2:
            continue
        es = group_edges[root]
        categories = Counter(e["category"] for e in es)
        classes = sorted({observations[k]["class"] for k in keys if observations[k]["class"]})
        motives = sorted({observations[k]["motive"] for k in keys if observations[k]["motive"]})
        hashes = sorted({observations[k]["geometry_hash"] for k in keys})
        group_id = stable_id(keys)
        has_near = categories["near_duplicate_candidate"] > 0
        group_rows.append({
            "candidate_group_id": group_id,
            "confidence_tier": "high_exact_and_near" if has_near else "high_exact_only",
            "source_observation_count": len(keys),
            "source_tile_count": len({observations[k]["source_tile"] for k in keys}),
            "exact_edge_count": categories["exact_geometry_duplicate"],
            "near_edge_count": categories["near_duplicate_candidate"],
            "class_conflict": len(classes) > 1,
            "motive_conflict_or_missing_variation": len(motives) > 1 or any(not observations[k]["motive"] for k in keys),
            "resolved_classes": " | ".join(classes),
            "resolved_motives": " | ".join(motives),
            "distinct_geometry_hashes": len(hashes),
            "review_status": "candidate_only_not_merged"
        })
        for key in sorted(keys):
            o = observations[key]
            member_rows.append({
                "candidate_group_id": group_id, "source_key": key,
                "source_batch": o["source_batch"], "source_tile": o["source_tile"],
                "class": o["class"], "motive": o["motive"],
                "geometry_hash": o["geometry_hash"],
                "review_status": "retain_source_observation"
            })
    category_counts = Counter(e["category"] for e in edges)
    summary = {
        "input_topology_review": str(files[0]),
        "topology_candidate_edges": len(edges),
        "high_confidence_edges_grouped": sum(category_counts[c] for c in HIGH_CONFIDENCE),
        "candidate_groups": len(group_rows),
        "source_observations_in_groups": len(member_rows),
        "observations_in_topology_edges": len(observations),\n        "source_feature_records_total": source_record_count,\n        "observations_not_in_candidate_groups_but_seen_in_edges": len(observations) - len(member_rows),\n        "source_records_without_any_candidate_edge": source_record_count - len(observations),\n        "source_records_not_grouped_total": source_record_count - len(member_rows),
        "group_observation_count_distribution": dict(sorted(Counter(str(g["source_observation_count"]) for g in group_rows).items())),
        "groups_with_class_conflict": sum(g["class_conflict"] for g in group_rows),
        "groups_with_motive_conflict_or_missing_variation": sum(g["motive_conflict_or_missing_variation"] for g in group_rows),
        "all_review_edges_by_category": dict(category_counts),
        "policy": [
            "Only exact geometry and >=95% IoU/area-ratio same-class edges are grouped.",
            "Grouping is a candidate relation, not a confirmed SCA object identity.",
            "No source observation is deleted, dissolved, or geometrically merged.",
            "Contained, partial-overlap and nearby-boundary edges remain ungrouped for manual or later model review.",
            "Transitive connected components can still over-group; inspect group size and attribute conflicts before promoting any group."
        ]
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sca-national-object-candidate-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for name, rows in [("sca-national-object-candidate-groups.csv", group_rows), ("sca-national-object-candidate-members.csv", member_rows)]:
        fields = list(rows[0]) if rows else ["candidate_group_id"]
        with (OUT/name).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
