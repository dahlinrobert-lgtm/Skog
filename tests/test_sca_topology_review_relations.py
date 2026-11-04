from scripts.analyze_sca_topology_review_relations import (
    build_relation_review,
    diagnostic_bucket,
)


def edge(a="a", b="b", category="partial_overlap_review", **overrides):
    row = {
        "source_key_a": a, "source_key_b": b,
        "batch_a": 1, "batch_b": 1,
        "tile_a": "10/10", "tile_b": "11/10",
        "class_a": "51 NO", "class_b": "51 NO",
        "motive_a": "A", "motive_b": "A",
        "geometry_hash_a": "ha", "geometry_hash_b": "hb",
        "same_class": True, "same_motive": True,
        "category": category,
        "area_a_m2_epsg3006": 100.0, "area_b_m2_epsg3006": 10.0,
        "intersection_m2_epsg3006": 9.9,
        "iou_epsg3006": 0.09, "overlap_smaller_epsg3006": 0.99,
        "area_ratio": 0.1, "distance_m_epsg3006": 0.0,
        "hausdorff_m_epsg3006": 50.0,
        "source_geometry_exact_hash_match": False,
    }
    row.update(overrides)
    return row


def test_partial_and_contained_relations_are_preserved_separately():
    data = {"summary": {"source_feature_records": 3}, "candidate_pairs": [
        edge(), edge("b", "c", "contained_or_nested_review"),
        edge("a", "c", "nearby_boundary_review"),
    ]}
    summary, relations, metadata = build_relation_review(data)
    assert len(relations) == 2
    assert summary["overlap_relation_categories"] == {
        "contained_or_nested_review": 1, "partial_overlap_review": 1
    }
    assert summary["nearby_boundary_relations_kept_separate"] == 1
    assert len(metadata) == 3


def test_partial_diagnostic_bucket_is_not_identity_claim():
    row = edge()
    assert diagnostic_bucket(row) == "partial_near_full_smaller_low_area_ratio"
    summary, relations, _ = build_relation_review({
        "summary": {"source_feature_records": 2}, "candidate_pairs": [row]
    })
    assert relations[0]["review_status"] == "relation_review_only_no_identity_resolution"


def test_cross_class_partial_is_separate_bucket():
    row = edge(same_class=False, class_b="60 SK")
    assert diagnostic_bucket(row) == "partial_cross_class_review"


def test_metadata_conflicts_are_counted_instead_of_overwritten():
    data = {"summary": {"source_feature_records": 3}, "candidate_pairs": [
        edge("a", "b", batch_a=1, tile_a="10/10", class_a="51 NO"),
        edge("a", "c", batch_a=2, tile_a="10/11", class_a="60 SK"),
    ]}
    summary, _, metadata = build_relation_review(data)
    by_key = {row["source_key"]: row for row in metadata}
    assert by_key["a"]["has_metadata_conflict"] is True
    assert by_key["a"]["batch_distinct_value_count"] == 2
    assert by_key["a"]["tile_distinct_value_count"] == 2
    assert summary["source_keys_with_any_metadata_conflict"] == 1


def test_output_is_deterministic_when_edges_reverse():
    edges = [edge("a", "b"), edge("b", "c", "contained_or_nested_review")]
    one = build_relation_review({"summary": {"source_feature_records": 3}, "candidate_pairs": edges})
    two = build_relation_review({"summary": {"source_feature_records": 3}, "candidate_pairs": list(reversed(edges))})
    assert one == two
