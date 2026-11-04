from scripts.prioritize_sca_overlap_review import (
    build_prioritized_review,
    classify_relation,
)


def edge(category="partial_overlap_review", **overrides):
    row = {
        "source_key_a": "a", "source_key_b": "b",
        "tile_a": "100/200", "tile_b": "101/200",
        "class_a": "51 NO", "class_b": "51 NO",
        "motive_a": "A", "motive_b": "A",
        "same_class": True, "same_motive": True,
        "category": category,
        "overlap_smaller_epsg3006": 0.99, "area_ratio": 0.10,
        "iou_epsg3006": 0.09, "distance_m_epsg3006": 0.0,
    }
    row.update(overrides)
    return row


def test_same_class_high_smaller_coverage_low_ratio_is_only_a_signal():
    bucket, priority, motive = classify_relation(edge())
    assert bucket == "partial_same_class_fragment_signal"
    assert priority == 1
    assert motive == "same"


def test_cross_class_partial_is_thematic_review():
    bucket, priority, _ = classify_relation(edge(
        class_b="60 Skötsel", same_class=False, same_motive=False,
        motive_a="A", motive_b="B"
    ))
    assert bucket == "partial_cross_class"
    assert priority == 1


def test_nested_and_partial_are_separate():
    assert classify_relation(edge("contained_or_nested_review"))[0] == "nested_same_class"
    assert classify_relation(edge("partial_overlap_review"))[0] != "nested_same_class"


def test_invalid_non_neighbor_tiles_are_rejected():
    data = {"summary": {"source_feature_records": 2}, "candidate_pairs": [
        edge(tile_b="103/200")
    ]}
    try:
        build_prioritized_review(data)
    except ValueError as exc:
        assert "tile-neighbor rule" in str(exc)
    else:
        raise AssertionError("Expected non-neighbor relation to be rejected")


def test_all_relations_retained_and_no_identity_resolved():
    data = {"summary": {"source_feature_records": 3}, "candidate_pairs": [
        edge(), edge("contained_or_nested_review"),
        edge("nearby_boundary_review"),
    ]}
    summary, rows = build_prioritized_review(data)
    assert len(rows) == 2
    assert summary["overlap_review_relations_total"] == 2
    assert summary["identity_resolved_relations"] == 0
    assert all(row["identity_resolved"] is False for row in rows)


def test_output_order_is_deterministic():
    edges = [edge(), edge("contained_or_nested_review", source_key_a="c", source_key_b="d")]
    a = build_prioritized_review({"summary": {"source_feature_records": 4}, "candidate_pairs": edges})
    b = build_prioritized_review({"summary": {"source_feature_records": 4}, "candidate_pairs": list(reversed(edges))})
    assert a == b
