import importlib.util
from pathlib import Path
from shapely.geometry import box

SPEC = importlib.util.spec_from_file_location(
    "edge", Path(__file__).parents[1] / "scripts/diagnose_sca_mvt_tile_edge_effects.py"
)
edge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(edge)


def test_tile_bounds_are_adjacent():
    a = edge.tile_bounds(2000, 1000)
    b = edge.tile_bounds(2001, 1000)
    assert abs(a[2] - b[0]) < 1e-8
    assert a[1] == b[1]
    assert a[3] == b[3]


def test_geometry_on_tile_edge_is_detected():
    xmin, ymin, xmax, ymax = edge.tile_bounds(2000, 1000)
    geom = box(xmin - 5, ymin + 100, xmin + 20, ymin + 200)
    m = edge.edge_metrics(geom, 2000, 1000)
    assert m["min_distance_to_tile_edge_m"] == 0
    assert m["outside_tile_area_fraction"] > 0


def test_geometry_inside_tile_has_no_outside_area():
    xmin, ymin, xmax, ymax = edge.tile_bounds(2000, 1000)
    geom = box(xmin + 100, ymin + 100, xmin + 200, ymin + 200)
    m = edge.edge_metrics(geom, 2000, 1000)
    assert m["outside_tile_area_fraction"] == 0
    assert m["inside_tile_area_fraction"] == 1


def test_pair_metrics_identity_not_inferred():
    from shapely.geometry import box
    m = edge.pair_metrics(box(0, 0, 10, 10), box(5, 0, 15, 10))
    assert m["overlap_smaller_fraction"] == 0.5
    assert m["area_ratio"] == 1
    assert m["iou"] == 1 / 3
