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
