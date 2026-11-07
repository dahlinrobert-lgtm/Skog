from shapely.geometry import Point, box
from scripts.audit_sca_parent_child_geometry_overlap import tile_bounds, mvt_to_world, intersect_child

def test_decoded_y_up_point_projects_inside_expected_z9_child():
    px,py=136,70
    b=tile_bounds(9,273,140)
    x=(b[0]+b[2])/2; y=(b[1]+b[3])/2
    pb=tile_bounds(8,px,py); extent=4096
    # mapbox_vector_tile.decode() flips MVT y-down coordinates by default.
    # Build the decoded y-up coordinate expected by mvt_to_world().
    lx=(x-pb[0])/(pb[2]-pb[0])*extent
    ly=(y-pb[1])/(pb[3]-pb[1])*extent
    geom=mvt_to_world({"type":"Point","coordinates":[lx,ly]},extent,8,px,py)
    hit=intersect_child(geom,b)
    assert hit and hit["intersection_type"]=="Point"
    assert abs(geom.x-x)<1e-6 and abs(geom.y-y)<1e-6

def test_geometry_outside_child_core_is_not_a_hit():
    b=tile_bounds(9,273,140)
    assert intersect_child(Point(b[2]+10,(b[1]+b[3])/2),b) is None

def test_polygon_is_clipped_to_child_core():
    b=tile_bounds(9,273,140)
    poly=box(b[0]-10,b[1]+10,b[0]+10,b[3]-10)
    hit=intersect_child(poly,b)
    assert hit and hit["area_m2_epsg3857"]>0
