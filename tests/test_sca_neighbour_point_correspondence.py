from shapely.geometry import Point
from scripts.audit_sca_neighbour_point_correspondence import tile_to_world

def test_tile_point_transforms_to_world_coordinate():
    z,x,y,extent=9,278,143,4096
    geom=tile_to_world({"type":"Point","coordinates":[extent/2,extent/2]},extent,z,x,y)
    assert geom.geom_type=="Point"
    assert geom.x > 0 and geom.y > 0

def test_tile_point_distance_can_be_measured_against_parent_coordinate():
    geom=tile_to_world({"type":"Point","coordinates":[2048,2048]},4096,9,278,143)
    assert geom.distance(Point(geom.x,geom.y))==0


def test_unique_tile_keys_are_valid_fetch_decode_inputs():
    from scripts.audit_sca_neighbour_point_correspondence import tile_fetch_args
    assert tile_fetch_args((9, 278, 143)) == {"z": 9, "x": 278, "y": 143}


def test_decoded_y_up_tile_corners_map_to_epsg3857_bounds():
    from scripts.audit_sca_neighbour_point_correspondence import tile_to_world
    from scripts.audit_sca_parent_child_geometry_overlap import tile_bounds
    z, x, y, extent = 9, 278, 143, 4096
    bounds = tile_bounds(z, x, y)
    southwest = tile_to_world({"type": "Point", "coordinates": [0, 0]}, extent, z, x, y)
    northeast = tile_to_world({"type": "Point", "coordinates": [extent, extent]}, extent, z, x, y)
    assert abs(southwest.x - bounds[0]) < 1e-6
    assert abs(southwest.y - bounds[1]) < 1e-6
    assert abs(northeast.x - bounds[2]) < 1e-6
    assert abs(northeast.y - bounds[3]) < 1e-6
