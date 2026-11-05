from scripts.monitor_sca_voluntary_tiles import apply_result, compare_features, digest, extend_tile_plan, feature_record, write_state

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


def test_persisted_state_keeps_hashes_and_metadata_without_repeating_geometry(tmp_path):
    import gzip, json
    a=feat([[[0,0]]],{"class":"NO"})
    state={"schema_version":1,"tile_count":1,"tiles":{"12/10/20":old_tile([a])}}
    path=tmp_path/"tile-state.json.gz"
    write_state(path,state)
    with gzip.open(path,"rt",encoding="utf-8") as handle:
        saved=json.load(handle)
    feature=saved["tiles"]["12/10/20"]["features"][0]
    assert "geometry" not in feature
    assert feature["geometry_sha256"]==a["geometry_sha256"]
    assert feature["properties"]=={"class":"NO"}


def test_new_positive_z9_seed_expands_plan_without_removing_old_tiles(tmp_path):
    import json
    existing=old_tile([])
    state={"tile_count":1,"tiles":{"12/800/1600":existing}}
    census={"summary":{"tiles_in_bbox":2,"tiles_completed":2,"voluntary_states":{"valid_mvt_with_features":1,"valid_mvt_empty":1}},
            "tile_results":[
                {"x":100,"y":200,"voluntary":{"state":"valid_mvt_with_features"},"ownership":{"state":"valid_mvt_with_features"}},
                {"x":101,"y":200,"voluntary":{"state":"valid_mvt_empty"},"ownership":{"state":"valid_mvt_empty"}}
            ]}
    path=tmp_path/"census.json"
    path.write_text(json.dumps(census),encoding="utf-8")
    added,positive=extend_tile_plan(state,path)
    assert positive==1
    assert added>0
    assert "12/800/1600" in state["tiles"]
    assert state["tile_count"]==len(state["tiles"])
    assert state["latest_seed_census"]["positive_voluntary_z9_tiles"]==1


def test_unchanged_tile_hash_skips_vector_tile_decode(monkeypatch):
    import hashlib
    import scripts.monitor_sca_voluntary_tiles as monitor

    class Response:
        status_code=200
        content=b"same tile payload"

    class Session:
        def get(self, url, timeout):
            return Response()

    monkeypatch.setattr(monitor, "get_session", lambda: Session())
    def unexpected_decode(raw):
        raise AssertionError("unchanged tile should not be decoded")
    monkeypatch.setattr(monitor.mapbox_vector_tile, "decode", unexpected_decode)
    sha=hashlib.sha256(Response.content).hexdigest()
    result=monitor.fetch(12,10,20,sha,"valid_mvt_with_features")
    assert result["state"]=="unchanged"
    assert result["sha256"]==sha


def test_incomplete_z9_census_cannot_expand_or_shrink_tile_plan(tmp_path):
    import json, pytest
    from scripts.monitor_sca_voluntary_tiles import extend_tile_plan
    state={"tile_count":1,"tiles":{"12/800/1600":old_tile([])}}
    census={"summary":{"tiles_in_bbox":4,"voluntary_states":{"valid_mvt_with_features":1}},
            "tile_results":[{"x":100,"y":200,"voluntary":{"state":"valid_mvt_with_features"}}]}
    path=tmp_path/"partial-census.json"
    path.write_text(json.dumps(census),encoding="utf-8")
    with pytest.raises(ValueError,match="incomplete"):
        extend_tile_plan(state,path)
    assert state["tile_count"]==1
    assert list(state["tiles"])==["12/800/1600"]


def test_sparse_404_tiles_are_unknown_but_complete_census_can_expand(tmp_path):
    import json
    from scripts.monitor_sca_voluntary_tiles import extend_tile_plan
    state={"tile_count":1,"tiles":{"12/800/1600":old_tile([])}}
    census={
        "summary":{"tiles_in_bbox":3,"tiles_completed":3},
        "tile_results":[
            {"x":100,"y":200,"voluntary":{"state":"valid_mvt_with_features"},
             "ownership":{"state":"valid_mvt_with_features"}},
            {"x":101,"y":200,"voluntary":{"state":"not_found_404"},
             "ownership":{"state":"not_found_404"}},
            {"x":102,"y":200,"voluntary":{"state":"valid_mvt_empty"},
             "ownership":{"state":"request_error"}}
        ]
    }
    path=tmp_path/"sparse-census.json"
    path.write_text(json.dumps(census),encoding="utf-8")
    added,positive=extend_tile_plan(state,path)
    assert positive==1 and added>0
    latest=state["latest_seed_census"]
    assert latest["voluntary_unknown_tiles"]==1
    assert latest["ownership_unknown_tiles"]==2
    assert "12/800/1600" in state["tiles"]


def test_census_with_pending_or_unknown_states_is_rejected(tmp_path):
    import json, pytest
    from scripts.monitor_sca_voluntary_tiles import extend_tile_plan
    state={"tile_count":1,"tiles":{"12/800/1600":old_tile([])}}
    census={"summary":{"tiles_in_bbox":1,"tiles_completed":1},
            "tile_results":[{"x":100,"y":200,"voluntary":{"state":"pending"},
                             "ownership":{"state":"valid_mvt_empty"}}]}
    path=tmp_path/"pending-census.json"
    path.write_text(json.dumps(census),encoding="utf-8")
    with pytest.raises(ValueError,match="pending or unknown"):
        extend_tile_plan(state,path)
    assert state["tile_count"]==1


def test_404_diagnostics_are_preserved_without_overwriting_last_valid_hash():
    a=feat([[[0,0]]],{"class":"NO"})
    old=old_tile([a],"last-valid-hash")
    new=fetched([],"body-hash","not_found_404")
    new.update({"http_status":404,"bytes":150,"content_type":"text/plain","body_preview":"tile not found"})
    updated,events=apply_result(old,new,"now")
    assert updated["sha256"]=="last-valid-hash"
    assert updated["last_attempt_sha256"]=="body-hash"
    assert updated["last_attempt_http_status"]==404
    assert updated["last_attempt_content_type"]=="text/plain"
    assert updated["last_attempt_body_preview"]=="tile not found"
    assert len(updated["features"])==1


def test_multizoom_audit_positive_z10_expands_z12_plan(tmp_path):
    import json
    from scripts.monitor_sca_voluntary_tiles import extend_tile_plan
    state={"tile_count":1,"tiles":{"12/800/1600":old_tile([])}}
    census={"summary":{"tiles_in_bbox":1,"tiles_completed":1},
            "tile_results":[{"x":100,"y":200,
                "voluntary":{"state":"not_found_404"},
                "ownership":{"state":"not_found_404"}}]}
    audit={"schema_version":1,"samples_per_class_requested":1,"unique_probe_tiles":5,
           "probe_requests":5,"states_by_zoom":{"10":{"valid_mvt_with_features":1}},
           "probe_results":[{"z":10,"x":100,"y":200,"state":"valid_mvt_with_features"}]}
    cp=tmp_path/"census.json"; ap=tmp_path/"audit.json"
    cp.write_text(json.dumps(census),encoding="utf-8")
    ap.write_text(json.dumps(audit),encoding="utf-8")
    added,positive=extend_tile_plan(state,cp,ap)
    assert positive==1
    assert added>0
    assert "12/400/800" in state["tiles"]
    assert any(s["source"]=="multizoom_audit" for s in state["tiles"]["12/400/800"]["discovery_sources"])


def test_normalize_event_adds_stable_source_and_notification_envelope():
    from scripts.monitor_sca_voluntary_tiles import normalize_event
    raw={"event_type":"geometry_added","tile":"12/10/20","layer":"Frivilliga_Avsattningar",
         "geometry_sha256":"abc","properties_sha256":"def","observed_at":"2026-11-05T00:00:00+00:00"}
    first=normalize_event(raw)
    second=normalize_event(raw)
    assert first["event_schema_version"]==1
    assert first["event_id"]==second["event_id"]
    assert first["source_system"]=="sca_olga_mvt"
    assert first["source_tile"]=={"z":12,"x":10,"y":20}
    assert first["source_url"].endswith("/12/10/20.pbf")
    assert first["event_category"]=="geometry"
    assert first["notification_candidate"] is True
    assert first["identity_resolved"] is False


def test_candidate_events_are_not_notification_eligible():
    from scripts.monitor_sca_voluntary_tiles import normalize_event
    item=normalize_event({"event_type":"geometry_changed_candidate","tile":"12/10/20",
                          "layer":"Frivilliga_Avsattningar","observed_at":"now"})
    assert item["event_category"]=="geometry_candidate"
    assert item["notification_candidate"] is False
