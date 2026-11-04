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



def test_exclusive_partition_covers_polygon_without_double_count():
    from shapely.geometry import box
    # A and B are adjacent, so this partition should be exact in one CRS.
    intersection = box(9, 2, 11, 8)
    tile_a = box(0, 0, 10, 10)
    tile_b = box(10, 0, 20, 10)
    zone_a = intersection.intersection(tile_a)
    zone_b_only = intersection.intersection(tile_b).difference(tile_a)
    zone_outside = intersection.difference(tile_a.union(tile_b))
    assert abs(zone_a.area + zone_b_only.area + zone_outside.area - intersection.area) < 1e-12
    assert zone_a.area == 6
    assert zone_b_only.area == 6
    assert zone_outside.area == 0


def test_diagonal_tile_partition_uses_exclusive_accounting():
    from shapely.geometry import box
    intersection = box(9, 9, 11, 11)
    tile_a = box(0, 0, 10, 10)
    tile_b = box(10, 10, 20, 20)
    zone_a = intersection.intersection(tile_a)
    zone_b_only = intersection.intersection(tile_b).difference(tile_a)
    zone_outside = intersection.difference(tile_a.union(tile_b))
    assert abs(zone_a.area + zone_b_only.area + zone_outside.area - intersection.area) < 1e-12
