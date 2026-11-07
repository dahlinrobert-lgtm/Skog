from scripts.audit_sca_cluster_point_targeted_probes import (
    WORLD, point_candidates, tile_neighbourhood, world_to_tile,
)


def test_world_to_tile_maps_parent_overlap_point_to_expected_z9_child():
    # Point reported in run #11 overlap: inside z9 x=278, y=143.
    x, y = 1753045.025206376, 8771454.743837116
    assert world_to_tile(x, y, 9) == (278, 143)


def test_neighbourhood_contains_center_and_eight_adjacent_tiles():
    tiles = tile_neighbourhood(9, 278, 143)
    assert len(tiles) == 9
    assert (9, 278, 143) in tiles
    assert (9, 277, 142) in tiles
    assert (9, 279, 144) in tiles


def test_neighbourhood_clamps_at_world_edge():
    tiles = tile_neighbourhood(9, 0, 0)
    assert len(tiles) == 4
    assert all(0 <= x < 512 and 0 <= y < 512 for _, x, y in tiles)


def test_point_candidates_preserve_source_provenance_and_deduplicate():
    hit = {
        "parent_geometry_type": "Point", "bounds_epsg3857": [100.0, 200.0, 100.0, 200.0],
        "layer": "Frivilliga_Avsattningar_punkt", "feature_index": 2, "mvt_id": 0,
        "properties": {"point_count": 3}
    }
    report = {"rows": [{"child_z9": {"x": 278, "y": 143}, "intersections": [hit, hit]}]}
    points = point_candidates(report)
    assert len(points) == 1
    assert points[0]["source_child_z9"] == {"x": 278, "y": 143}
    assert points[0]["source_properties"]["point_count"] == 3
