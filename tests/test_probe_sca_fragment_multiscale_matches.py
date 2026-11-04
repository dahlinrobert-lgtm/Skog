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
