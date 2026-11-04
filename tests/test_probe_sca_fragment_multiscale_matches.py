import importlib.util
from pathlib import Path
from shapely.geometry import box, Polygon

SPEC = importlib.util.spec_from_file_location(
    "multiscale", Path(__file__).parents[1] / "scripts/probe_sca_fragment_multiscale_matches.py"
)
multi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(multi)


def test_xyz_tile_for_web_mercator_origin():
    assert multi.tile_xy_from_3857(0, 0, 1) == (1, 1)


def test_tile_to_3857_maps_full_extent_to_tile_bounds():
    from shapely.geometry import box
    geom = multi.tile_to_3857(box(0, 0, 4096, 4096), 1, 1, 1, 4096)
    xmin = 0
    xmax = 20037508.342789244
    ymin = -20037508.342789244
    ymax = 0
    assert abs(geom.bounds[0] - xmin) < 1e-6
    assert abs(geom.bounds[2] - xmax) < 1e-6
    assert abs(geom.bounds[1] - ymin) < 1e-6
    assert abs(geom.bounds[3] - ymax) < 1e-6


def test_property_lookup_prefers_resolved_class_and_motive():
    props = {"SKOTSEL_KL": "raw", "SKOTSEL_KL_resolved": "51 NO",
             "MOTIV_resolved": "1 Eget värde"}
    assert multi.get_property(props, "skotsel_kl") == "51 NO"
    assert multi.get_property(props, "motiv") == "1 Eget värde"


def test_normalize_is_case_and_whitespace_insensitive():
    assert multi.normalize("  51 Naturvård   NO ") == "51 naturvård no"


def test_build_tile_plan_is_deterministic_and_deduplicated():
    points = {
        "1": {"a": box(-10, -10, 10, 10), "b": box(-10, -10, 10, 10)},
    }
    plan = multi.build_tile_plan(points, zooms=(9, 11))
    assert plan == sorted(set(plan))
    assert len(plan) == 2


def test_similarity_detects_identical_geometry():
    geom = box(1000000, 7000000, 1000100, 7000100)
    m = multi.similarity(geom, geom)
    assert abs(m["source_coverage"] - 1.0) < 1e-9
    assert abs(m["candidate_coverage"] - 1.0) < 1e-9
    assert abs(m["iou"] - 1.0) < 1e-9



def _candidate(locator, a_intersection, b_intersection, a_coverage, b_coverage):
    return {
        "locator": locator,
        "sim_a": {"intersection_m2_epsg3006": a_intersection,
                  "source_coverage": a_coverage, "distance_m_epsg3006": 0.0},
        "sim_b": {"intersection_m2_epsg3006": b_intersection,
                  "source_coverage": b_coverage, "distance_m_epsg3006": 0.0},
    }


def test_common_candidate_must_intersect_both_source_fragments():
    one_sided = _candidate("one-sided", 100.0, 0.0, 1.0, 0.0)
    best_a, best_b, best_common = multi.select_best_candidates([one_sided])
    assert best_a is one_sided
    assert best_b is None
    assert best_common is None


def test_common_candidate_prefers_highest_minimum_coverage():
    one = _candidate("common-low", 100.0, 100.0, 0.4, 0.3)
    two = _candidate("common-high", 100.0, 100.0, 0.8, 0.7)
    best_a, best_b, best_common = multi.select_best_candidates([one, two])
    assert best_a is two
    assert best_b is two
    assert best_common is two


def test_summarize_cross_zoom_uses_pair_level_coverage_and_motive_not_tile_ids():
    rows = [
        {"relation_sample_id": "1", "zoom": 13, "best_single_candidate_min_source_coverage": 0.95, "best_candidate_motive": "1 Eget värde", "best_candidate_locator": "13/1/1/layer/0"},
        {"relation_sample_id": "1", "zoom": 15, "best_single_candidate_min_source_coverage": 0.92, "best_candidate_motive": "1 Eget värde", "best_candidate_locator": "15/2/2/layer/0"},
        {"relation_sample_id": "2", "zoom": 13, "best_single_candidate_min_source_coverage": 0.80, "best_candidate_motive": "1 Eget värde", "best_candidate_locator": "13/3/3/layer/0"},
        {"relation_sample_id": "2", "zoom": 15, "best_single_candidate_min_source_coverage": 0.40, "best_candidate_motive": "2 Annat", "best_candidate_locator": "15/4/4/layer/0"},
    ]
    output, counts = multi.summarize_cross_zoom(rows)
    assert len(output) == 2
    assert output[0]["both_zooms_ge_90pct"] is True
    assert output[0]["motive_consistent_nonempty"] is True
    assert output[0]["identity_resolved"] is False
    assert output[1]["both_zooms_ge_50pct"] is False
    assert output[1]["motive_consistent_nonempty"] is False
    assert counts["pairs_with_common_candidate_min_coverage_ge_90pct_at_both_z13_z15"] == 1
    assert counts["identity_resolved_relations"] == 0


def test_build_source_pair_dedup_groups_exact_geometry_pairs_direction_independently():
    pairs = {
        "11": {
            "a": {"mvt_decoded_geometry_sha256_epsg3857": "hash-A", "source_key": "tile-a"},
            "b": {"mvt_decoded_geometry_sha256_epsg3857": "hash-B", "source_key": "tile-b"},
        },
        "12": {
            "a": {"mvt_decoded_geometry_sha256_epsg3857": "hash-A", "source_key": "tile-a"},
            "b": {"mvt_decoded_geometry_sha256_epsg3857": "hash-B", "source_key": "tile-c"},
        },
        "13": {
            "a": {"mvt_decoded_geometry_sha256_epsg3857": "hash-B", "source_key": "tile-b"},
            "b": {"mvt_decoded_geometry_sha256_epsg3857": "hash-A", "source_key": "tile-a"},
        },
    }
    pair_rows, group_rows, summary = multi.build_source_pair_dedup(pairs)
    assert len(pair_rows) == 3
    assert len(group_rows) == 1
    assert group_rows[0]["relation_sample_ids"] == "11;12;13"
    assert summary["unique_exact_geometry_pair_count"] == 1
    assert summary["redundant_relation_rows_beyond_one_per_group"] == 2
    assert summary["identity_resolved_relations"] == 0


def test_build_source_pair_dedup_keeps_nearby_but_different_hash_pairs_separate():
    pairs = {
        "1": {"a": {"mvt_decoded_geometry_sha256_epsg3857": "A"}, "b": {"mvt_decoded_geometry_sha256_epsg3857": "B"}},
        "2": {"a": {"mvt_decoded_geometry_sha256_epsg3857": "A"}, "b": {"mvt_decoded_geometry_sha256_epsg3857": "C"}},
    }
    _, group_rows, summary = multi.build_source_pair_dedup(pairs)
    assert len(group_rows) == 2
    assert summary["unique_exact_geometry_pair_count"] == 2