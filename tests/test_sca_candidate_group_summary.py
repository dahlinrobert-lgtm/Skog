from scripts.build_sca_national_object_candidate_groups import build_candidate_groups


def edge(a, b, category="near_duplicate_candidate", motive_a="", motive_b=""):
    return {
        "source_key_a": a, "source_key_b": b,
        "batch_a": 0, "batch_b": 1,
        "tile_a": "10/10", "tile_b": "11/10",
        "class_a": "51 NO", "class_b": "51 NO",
        "motive_a": motive_a, "motive_b": motive_b,
        "geometry_hash_a": f"h-{a}", "geometry_hash_b": f"h-{b}",
        "category": category,
    }


def test_source_counts_are_separate_from_edge_universe():
    data = {
        "summary": {"source_feature_records": 10},
        "candidate_pairs": [edge("a", "b")],
    }
    summary, groups, members = build_candidate_groups(data)
    assert summary["source_feature_records_total"] == 10
    assert summary["unique_source_observations_in_topology_edges"] == 2
    assert summary["source_records_without_any_candidate_edge"] == 8
    assert summary["source_records_not_grouped_total"] == 8
    assert len(groups) == 1
    assert len(members) == 2


def test_missing_motives_are_not_reported_as_conflicts():
    data = {
        "summary": {"source_feature_records": 2},
        "candidate_pairs": [edge("a", "b", motive_a="", motive_b="")],
    }
    summary, groups, _ = build_candidate_groups(data)
    assert groups[0]["motive_conflict"] is False
    assert groups[0]["missing_motive_observation_count"] == 2
    assert summary["groups_with_motive_conflict"] == 0
    assert summary["groups_with_missing_motive"] == 1
    assert summary["groups_with_all_motives_missing"] == 1


def test_different_nonempty_motives_are_a_real_conflict():
    data = {
        "summary": {"source_feature_records": 2},
        "candidate_pairs": [
            edge("a", "b", motive_a="Motive A", motive_b="Motive B")
        ],
    }
    summary, groups, _ = build_candidate_groups(data)
    assert groups[0]["motive_conflict"] is True
    assert groups[0]["missing_motive_observation_count"] == 0
    assert summary["groups_with_motive_conflict"] == 1
    assert summary["groups_with_missing_motive"] == 0


def test_low_confidence_edges_do_not_form_groups():
    data = {
        "summary": {"source_feature_records": 2},
        "candidate_pairs": [
            edge("a", "b", category="partial_overlap_review")
        ],
    }
    summary, groups, members = build_candidate_groups(data)
    assert summary["candidate_groups"] == 0
    assert groups == []
    assert members == []


def test_source_total_smaller_than_edge_universe_is_rejected():
    data = {
        "summary": {"source_feature_records": 1},
        "candidate_pairs": [edge("a", "b")],
    }
    try:
        build_candidate_groups(data)
    except ValueError as exc:
        assert "smaller than the unique source keys" in str(exc)
    else:
        raise AssertionError("Expected source-count invariant to reject invalid input")


def test_grouping_is_deterministic_and_preserves_all_members():
    first = {
        "summary": {"source_feature_records": 3},
        "candidate_pairs": [edge("a", "b"), edge("b", "c")],
    }
    second = {
        "summary": {"source_feature_records": 3},
        "candidate_pairs": list(reversed(first["candidate_pairs"])),
    }
    summary_a, groups_a, members_a = build_candidate_groups(first)
    summary_b, groups_b, members_b = build_candidate_groups(second)
    assert groups_a == groups_b
    assert members_a == members_b
    assert summary_a["source_observations_in_groups"] == 3
    assert summary_b["source_observations_in_groups"] == 3
    assert groups_a[0]["source_observation_count"] == 3
