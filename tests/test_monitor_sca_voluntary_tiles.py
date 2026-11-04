from scripts.monitor_sca_voluntary_tiles import apply_result, compare_features, digest, feature_record

def feat(coords, props):
    return feature_record("Frivilliga_Avsattningar", {
        "id": 0, "geometry":{"type":"Polygon","coordinates":coords}, "properties":props})

def old_tile(features, sha="old"):
    return {"z":12,"x":10,"y":20,"sha256":sha,"state":"valid_mvt_with_features",
            "features":features,"pending_missing":[],"not_found_streak":0}

def fetched(features, sha="new", state="valid_mvt_with_features"):
    return {"z":12,"x":10,"y":20,"sha256":sha,"state":state,"features":features}

def test_added_geometry_emits_full_geometry_and_metadata():
    a=feat([[[0,0]]],{"class":"NO"}); b=feat([[[1,1]]],{"class":"NS"})
    updated,events=apply_result(old_tile([a]),fetched([a,b]),"2026-11-05T00:00:00Z")
    assert len(updated["features"])==2
    assert events[0]["event_type"]=="geometry_added"
    assert events[0]["geometry"]==b["geometry"]

def test_metadata_change_is_not_geometry_change():
    a=feat([[[0,0]]],{"class":"NO"}); b=feat([[[0,0]]],{"class":"NS"})
    events,active,pending=compare_features("12/10/20",old_tile([a]),{"features":[b]},"now")
    assert events[0]["event_type"]=="metadata_changed"
    assert events[0]["old_properties"]=={"class":"NO"}

def test_geometry_change_is_candidate_not_identity():
    a=feat([[[0,0]]],{"class":"NO"}); b=feat([[[0,1]]],{"class":"NO"})
    events,_,_=compare_features("12/10/20",old_tile([a]),{"features":[b]},"now")
    assert events[0]["event_type"]=="geometry_changed_candidate"
    assert events[0]["identity_resolved"] is False

def test_first_missing_is_candidate_only():
    a=feat([[[0,0]]],{"class":"NO"})
    updated,events=apply_result(old_tile([a]),fetched([],state="valid_mvt_empty"),"now")
    assert updated["pending_missing"][0]["missing_count"]==1
    assert events[0]["event_type"]=="geometry_missing_candidate"

def test_second_valid_empty_observation_confirms_missing():
    a=feat([[[0,0]]],{"class":"NO"})
    old=old_tile([],"empty"); old["pending_missing"]=[{"feature":a,"missing_count":1,"first_missing_at":"then"}]
    updated,events=apply_result(old,fetched([],"empty","valid_mvt_empty"),"now")
    assert updated["pending_missing"]==[]
    assert events[0]["event_type"]=="geometry_removed_confirmed"

def test_404_and_errors_preserve_previous_features():
    a=feat([[[0,0]]],{"class":"NO"})
    old=old_tile([a])
    updated,events=apply_result(old,fetched([],"404","not_found_404"),"now")
    assert len(updated["features"])==1 and updated["not_found_streak"]==1
    failed=fetched([],"err","request_error")
    updated,events=apply_result(old,failed,"now")
    assert len(updated["features"])==1 and events[0]["event_type"]=="tile_poll_error"
