import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "zones", Path(__file__).parents[1] / "scripts/diagnose_sca_mvt_intersection_zones.py"
)
zones = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(zones)


def test_classify_outside_both():
    assert zones.classify_zone(0.1, 0.1, 0.8) == "mostly_outside_both_nominal_tiles"


def test_classify_dominant_tile_a():
    assert zones.classify_zone(0.9, 0.05, 0.05) == "mostly_in_tile_a_core"


def test_classify_split_across_both_cores():
    assert zones.classify_zone(0.4, 0.4, 0.2) == "spread_across_both_tile_cores"


def test_classify_buffer_only():
    assert zones.classify_zone(0.0, 0.0, 1.0) == "mostly_outside_both_nominal_tiles"
