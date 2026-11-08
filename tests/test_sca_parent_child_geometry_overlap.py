from shapely.geometry import Point, box
from scripts.audit_sca_parent_child_geometry_overlap import tile_bounds, mvt_to_world, intersect_child

def test_parent_point_projects_inside_expected_z9_child():
    px,py=136,70
    b=tile_bounds(9,273,140)
    x=(b[0]+b[2])/2; y=(b[1]+b[3])/2
    pb=tile_bounds(8,px,py); extent=4096
    lx=(x-pb[0])/(pb[2]-pb[0])*extent
    ly=(y-pb[1])/(pb[3]-pb[1])*extent
    geom=mvt_to_world({"type":"Point","coordinates":[lx,ly]},extent,8,px,py)
    hit=intersect_child(geom,b)
    assert hit and hit["intersection_type"]=="Point"

def test_geometry_outside_child_core_is_not_a_hit():
    b=tile_bounds(9,273,140)
    assert intersect_child(Point(b[2]+10,(b[1]+b[3])/2),b) is None

def test_polygon_is_clipped_to_child_core():
    b=tile_bounds(9,273,140)
    poly=box(b[0]-10,b[1]+10,b[0]+10,b[3]-10)
    hit=intersect_child(poly,b)
    assert hit and hit["area_m2_epsg3857"]>0


def test_decoded_y_up_origin_maps_to_tile_southwest_corner():
    z, x, y, extent = 8, 136, 70, 4096
    geom = mvt_to_world({"type": "Point", "coordinates": [0, 0]}, extent, z, x, y)
    bounds = tile_bounds(z, x, y)
    assert abs(geom.x - bounds[0]) < 1e-6
    assert abs(geom.y - bounds[1]) < 1e-6


def test_decoded_y_up_top_right_maps_to_tile_northeast_corner():
    z, x, y, extent = 8, 136, 70, 4096
    geom = mvt_to_world({"type": "Point", "coordinates": [extent, extent]}, extent, z, x, y)
    bounds = tile_bounds(z, x, y)
    assert abs(geom.x - bounds[2]) < 1e-6
    assert abs(geom.y - bounds[3]) < 1e-6


def test_decoded_y_up_places_northern_and_southern_z9_children_correctly():
    parent_z, parent_x, parent_y, extent = 8, 136, 70, 4096
    # XYZ child rows increase southward: the parent's northern half is y=140,
    # and its southern half is y=141. Decoded MVT local y increases northward.
    north_child = tile_bounds(9, 273, 140)
    south_child = tile_bounds(9, 273, 141)
    north_point = mvt_to_world(
        {"type": "Point", "coordinates": [extent / 2, extent * 0.75]},
        extent, parent_z, parent_x, parent_y
    )
    south_point = mvt_to_world(
        {"type": "Point", "coordinates": [extent / 2, extent * 0.25]},
        extent, parent_z, parent_x, parent_y
    )
    assert north_point.y > south_point.y
    assert intersect_child(north_point, north_child) is not None
    assert intersect_child(north_point, south_child) is None
    assert intersect_child(south_point, south_child) is not None
    assert intersect_child(south_point, north_child) is None
