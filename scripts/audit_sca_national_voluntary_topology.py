#!/usr/bin/env python3
"""National cross-tile topology review for SCA voluntary-set-aside MVT features.

Reads all 25 projected batch GeoJSONs, retains source observations, and emits
candidate pairs only. It never dissolves or merges features and never reports
candidate counts as unique SCA objects.
"""
from __future__ import annotations
import csv, hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree

INPUT = Path("input")
OUT = Path("output")
NEAR_DISTANCE_M = 25.0
AREA_EPS = 1e-6

TO_3006 = Transformer.from_crs("EPSG:3857", "EPSG:3006", always_xy=True).transform


def load_features():
    items = []
    files = sorted(INPUT.rglob("sca-voluntary-batch-epsg3857.geojson"))
    if len(files) != 25:
        raise SystemExit(f"Expected 25 geometry batch GeoJSON files, found {len(files)}")
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for index, feature in enumerate(data.get("features", [])):
            props = feature.get("properties") or {}
            geom = shape(feature["geometry"])
            if geom.is_empty or not geom.is_valid:
                raise SystemExit(f"Invalid geometry in {path} feature {index}")
            tile = (int(props["source_tile_x"]), int(props["source_tile_y"]))
            batch = int(props["source_batch"])
            source_key = str(feature.get("id") or f"{batch}:{tile}:{index}")
            geom_hash = hashlib.sha256(geom.normalize().wkb).hexdigest()
            items.append({
                "source_key": source_key,
                "batch": batch,
                "tile_x": tile[0],
                "tile_y": tile[1],
                "tile": tile,
                "class": str(props.get("SKOTSEL_KL_resolved") or ""),
                "motive": str(props.get("MOTIV_resolved") or ""),
                "geometry": geom,
                "geometry_hash": geom_hash,
            })
    return items, files


def pair_metrics(a, b):
    ga, gb = a["geometry"], b["geometry"]
    inter = ga.intersection(gb)
    ia = inter.area
    aa, ab = ga.area, gb.area
    union = aa + ab - ia
    iou = ia / union if union > 0 else 0.0
    smaller = min(aa, ab)
    overlap_smaller = ia / smaller if smaller > 0 else 0.0
    ratio = min(aa, ab) / max(aa, ab) if max(aa, ab) > 0 else 0.0
    distance = ga.distance(gb)
    # Use EPSG:3006 for area and distance diagnostics, not Web Mercator.
    ga_m = transform(TO_3006, ga)
    gb_m = transform(TO_3006, gb)
    inter_m = ga_m.intersection(gb_m)
    ia_m = inter_m.area
    aa_m, ab_m = ga_m.area, gb_m.area
    union_m = aa_m + ab_m - ia_m
    iou_m = ia_m / union_m if union_m > 0 else 0.0
    smaller_m = min(aa_m, ab_m)
    overlap_smaller_m = ia_m / smaller_m if smaller_m > 0 else 0.0
    distance_m = ga_m.distance(gb_m)
    hausdorff_m = ga_m.hausdorff_distance(gb_m)
    exact = a["geometry_hash"] == b["geometry_hash"]
    same_class = bool(a["class"] and a["class"] == b["class"])
    same_motive = bool(a["motive"] and a["motive"] == b["motive"])
    contained = ga_m.buffer(0.01).covers(gb_m) or gb_m.buffer(0.01).covers(ga_m)
    if exact:
        category = "exact_geometry_duplicate"
    elif iou_m >= 0.95 and ratio >= 0.95 and same_class:
        category = "near_duplicate_candidate"
    elif contained and overlap_smaller_m >= 0.98:
        category = "contained_or_nested_review"
    elif ia_m > 1.0:
        category = "partial_overlap_review"
    elif distance_m <= NEAR_DISTANCE_M:
        category = "nearby_boundary_review"
    else:
        category = "no_material_overlap"
    return {
        "source_key_a": a["source_key"], "source_key_b": b["source_key"],
        "batch_a": a["batch"], "batch_b": b["batch"],
        "tile_a": f'{a["tile_x"]}/{a["tile_y"]}',
        "tile_b": f'{b["tile_x"]}/{b["tile_y"]}',
        "class_a": a["class"], "class_b": b["class"],
        "motive_a": a["motive"], "motive_b": b["motive"],
        "same_class": same_class, "same_motive": same_motive,
        "geometry_hash_a": a["geometry_hash"],
        "geometry_hash_b": b["geometry_hash"],
        "category": category,
        "area_a_m2_epsg3006": aa_m, "area_b_m2_epsg3006": ab_m,
        "intersection_m2_epsg3006": ia_m,
        "iou_epsg3006": iou_m,
        "overlap_smaller_epsg3006": overlap_smaller_m,
        "area_ratio": ratio,
        "distance_m_epsg3006": distance_m,
        "hausdorff_m_epsg3006": hausdorff_m,
        "source_geometry_exact_hash_match": exact,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, files = load_features()
    hash_groups = defaultdict(list)
    for i, item in enumerate(items):
        hash_groups[item["geometry_hash"]].append(i)
    pairs = set()
    # Exact hashes across the entire national run, including non-neighbor tiles.
    for indexes in hash_groups.values():
        if len(indexes) > 1:
            for pos, i in enumerate(indexes):
                for j in indexes[pos + 1:]:
                    if items[i]["tile"] != items[j]["tile"]:
                        pairs.add((min(i, j), max(i, j)))
    # Spatial candidate search restricted to distinct adjacent XYZ tiles.
    geoms = [x["geometry"] for x in items]
    tree = STRtree(geoms)
    for i, item in enumerate(items):
        query_geom = item["geometry"].buffer(NEAR_DISTANCE_M)
        for j in tree.query(query_geom):
            j = int(j)
            if j <= i:
                continue
            other = items[j]
            if item["tile"] == other["tile"]:
                continue
            if max(abs(item["tile_x"] - other["tile_x"]),
                   abs(item["tile_y"] - other["tile_y"])) > 1:
                continue
            pairs.add((i, j))
    reviews = []
    for i, j in sorted(pairs):
        row = pair_metrics(items[i], items[j])
        if row["category"] != "no_material_overlap":
            reviews.append(row)
    counts = Counter(x["category"] for x in reviews)
    exact_groups = sum(1 for group in hash_groups.values() if len(group) > 1)
    exact_extra = sum(len(group) - 1 for group in hash_groups.values() if len(group) > 1)
    summary = {
        "input_geometry_batches": len(files),
        "source_feature_records": len(items),
        "globally_unique_exact_geometry_hashes": len(hash_groups),
        "global_exact_duplicate_hash_groups": exact_groups,
        "global_exact_duplicate_extra_records": exact_extra,
        "candidate_pairs_evaluated": len(pairs),
        "review_candidate_pairs": len(reviews),
        "candidate_categories": dict(counts),
        "source_tiles": len({x["tile"] for x in items}),
        "area_crs": "EPSG:3006",
        "near_distance_threshold_m": NEAR_DISTANCE_M,
        "limitations": [
            "Candidates are not confirmed object identities.",
            "No source records are deleted, dissolved, or merged.",
            "MVT clipping, buffers and generalization can make the same object appear as partial geometries.",
            "Spatial adjacency is limited to distinct tiles at Chebyshev distance <= 1.",
            "The z12 collection itself is derived from positive z9 seeds and a neighbor ring; it is not proof of complete national source coverage."
        ]
    }
    (OUT / "sca-national-topology-review.json").write_text(
        json.dumps({"summary": summary, "candidate_pairs": reviews},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(reviews[0].keys()) if reviews else [
        "source_key_a", "source_key_b", "category", "tile_a", "tile_b"
    ]
    with (OUT / "sca-national-topology-candidates.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(reviews)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
