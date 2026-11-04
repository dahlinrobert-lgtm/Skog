import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "extent", Path(__file__).parents[1] / "scripts/diagnose_sca_mvt_extent_overflow.py"
)
extent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extent)


def test_source_key_parser_preserves_layer_names():
    assert extent.parse_source_key("0:12:2194:1121:Frivilliga_Avsattningar:0") == (
        0, 12, 2194, 1121, "Frivilliga_Avsattningar", 0
    )


def test_directional_overflow_east_west_pair():
    a = {"source_tile_x": 1, "source_tile_y": 2,
         "mvt_east_overshoot_units": 12, "mvt_west_overshoot_units": 0,
         "mvt_south_overshoot_units": 0, "mvt_north_overshoot_units": 0}
    b = {"source_tile_x": 2, "source_tile_y": 2,
         "mvt_east_overshoot_units": 0, "mvt_west_overshoot_units": 8,
         "mvt_south_overshoot_units": 0, "mvt_north_overshoot_units": 0}
    result = extent.directional_overflow(a, b)
    assert result["shared_edge_overflow_pattern"] == "both_features_overflow_toward_each_other"


def test_directional_overflow_south_north_pair():
    a = {"source_tile_x": 1, "source_tile_y": 2,
         "mvt_east_overshoot_units": 0, "mvt_west_overshoot_units": 0,
         "mvt_south_overshoot_units": 4, "mvt_north_overshoot_units": 0}
    b = {"source_tile_x": 1, "source_tile_y": 3,
         "mvt_east_overshoot_units": 0, "mvt_west_overshoot_units": 0,
         "mvt_south_overshoot_units": 0, "mvt_north_overshoot_units": 6}
    result = extent.directional_overflow(a, b)
    assert result["shared_edge_overflow_pattern"] == "both_features_overflow_toward_each_other"


def test_non_adjacent_pair_not_classified_as_buffer_copy():
    a = {"source_tile_x": 1, "source_tile_y": 2,
         "mvt_east_overshoot_units": 10, "mvt_west_overshoot_units": 0,
         "mvt_south_overshoot_units": 0, "mvt_north_overshoot_units": 0}
    b = {"source_tile_x": 3, "source_tile_y": 2,
         "mvt_east_overshoot_units": 0, "mvt_west_overshoot_units": 10,
         "mvt_south_overshoot_units": 0, "mvt_north_overshoot_units": 0}
    result = extent.directional_overflow(a, b)
    assert result["shared_edge_overflow_pattern"] == "not_adjacent"
