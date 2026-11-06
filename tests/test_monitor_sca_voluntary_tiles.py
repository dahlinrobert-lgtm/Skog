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
        headers={"Content-Type":"application/x-protobuf","Server":"test"}

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


def test_multizoom_audit_probes_parent_and_descendants():
    from scripts.audit_sca_tile_coverage import probes_for_seed
    probes=probes_for_seed({"x":100,"y":200,"class":"positive_z9"})
    assert (8,50,100,"parent_z8") in probes
    assert len([p for p in probes if p[0]==10])==4
    assert len([p for p in probes if p[0]==11])==16
    assert len([p for p in probes if p[0]==12])==64


def test_multizoom_seed_selection_samples_positive_empty_and_404_classes():
    from scripts.audit_sca_tile_coverage import choose_seeds
    rows=[]
    for i in range(10):
        rows.append({"x":100+i*3,"y":200+i*2,
                     "voluntary":{"state":"valid_mvt_with_features",
                                  "layers":[{"feature_count":i+1}]}})
        rows.append({"x":101+i*3,"y":201+i*2,
                     "voluntary":{"state":"valid_mvt_empty","layers":[]}})
    for i in range(12):
        rows.append({"x":102+i*3,"y":202+i*2,
                     "voluntary":{"state":"not_found_404","layers":[]}})
    seeds=choose_seeds({"tile_results":rows},4)
    assert len(seeds)==12
    assert sum(s["class"]=="positive_z9" for s in seeds)==4
    assert sum(s["class"]=="valid_empty_z9" for s in seeds)==4
    assert sum(s["class"]=="not_found_404_z9" for s in seeds)==4


def test_spatial_state_summary_accounts_for_every_z9_tile():
    from scripts.audit_sca_tile_coverage import spatial_state_summary
    census={"tile_results":[
        {"x":100,"y":200,"voluntary":{"state":"valid_mvt_with_features"}},
        {"x":101,"y":200,"voluntary":{"state":"valid_mvt_empty"}},
        {"x":110,"y":210,"voluntary":{"state":"not_found_404"}},
        {"x":111,"y":211,"voluntary":{"state":"request_error"}},
    ]}
    summary=spatial_state_summary(census,columns=2,rows=2)
    assert sum(cell["tile_count"] for cell in summary["cells"])==4
    assert sum(cell["positive_tiles"] for cell in summary["cells"])==1
    assert sum(cell["valid_empty_tiles"] for cell in summary["cells"])==1
    assert sum(cell["not_found_404_tiles"] for cell in summary["cells"])==1
    assert sum(cell["technical_or_unknown_tiles"] for cell in summary["cells"])==1


def test_response_diagnostics_group_identical_404_bodies():
    from scripts.monitor_sca_voluntary_tiles import summarize_response_diagnostics
    rows=[
        {"state":"not_found_404","http_status":404,"sha256":"same","content_type":"text/html","bytes":150,"body_preview":"not found"},
        {"state":"not_found_404","http_status":404,"sha256":"same","content_type":"text/html","bytes":150,"body_preview":"not found"},
        {"state":"not_found_404","http_status":404,"sha256":"other","content_type":"text/html","bytes":151,"body_preview":"other body"},
        {"state":"unchanged","http_status":200,"sha256":"valid"}
    ]
    groups=summarize_response_diagnostics(rows)
    assert len(groups)==2
    same=next(g for g in groups if g["sha256"]=="same")
    assert same["count"]==2
    assert same["body_preview"]=="not found"


def test_multizoom_probe_jobs_deduplicate_tiles_and_keep_all_seed_provenance():
    from scripts.audit_sca_tile_coverage import build_probe_jobs

    seeds = [
        {"z": 9, "x": 100, "y": 200, "class": "positive_z9"},
        {"z": 9, "x": 101, "y": 200, "class": "not_found_404_z9"},
    ]
    jobs = build_probe_jobs(seeds)
    coords = [(z, x, y) for z, x, y, _ in jobs]

    assert len(coords) == len(set(coords))
    shared = next(refs for z, x, y, refs in jobs if (z, x, y) == (8, 50, 100))
    assert len(shared) == 2
    assert {ref["seed_z9"]["class"] for ref in shared} == {
        "positive_z9", "not_found_404_z9"
    }
    assert all(len(refs) >= 1 for _, _, _, refs in jobs)



def test_multizoom_audit_reuses_http_session_within_worker_thread():
    from scripts.audit_sca_tile_coverage import session

    first = session()
    second = session()
    assert first is second



def test_discovery_coverage_accounting_is_explicit_and_idempotent(tmp_path):
    import json
    from scripts.monitor_sca_voluntary_tiles import extend_tile_plan

    state={"tile_count":0,"tiles":{}}
    census={"summary":{"tiles_in_bbox":1,"tiles_completed":1},
            "tile_results":[{"x":100,"y":200,
                "voluntary":{"state":"valid_mvt_with_features"},
                "ownership":{"state":"valid_mvt_empty"}}]}
    audit={"schema_version":1,"samples_per_class_requested":1,"unique_probe_tiles":1,
           "probe_requests":1,"states_by_zoom":{"10":{"valid_mvt_with_features":1}},
           "probe_results":[{"z":10,"x":200,"y":400,"state":"valid_mvt_with_features"}]}
    cp=tmp_path/"census.json"; ap=tmp_path/"audit.json"
    cp.write_text(json.dumps(census),encoding="utf-8")
    ap.write_text(json.dumps(audit),encoding="utf-8")

    added,positive=extend_tile_plan(state,cp,ap)
    first=state["latest_seed_census"]
    assert positive==2
    assert added==first["z12_discovery_target_tiles_added"]
    assert first["z12_discovery_target_tiles"] > 0
    assert first["z12_discovery_target_tiles_already_monitored"] + added == first["z12_discovery_target_tiles"]
    assert first["positive_discovery_seed_tiles_by_source"] == {
        "z9_census":1,"multizoom_audit":1
    }

    added_again,positive_again=extend_tile_plan(state,cp,ap)
    second=state["latest_seed_census"]
    assert added_again==0
    assert positive_again==positive
    assert second["z12_discovery_target_tiles_already_monitored"] == second["z12_discovery_target_tiles"]
    assert second["z12_discovery_target_tiles_added"] == 0



def test_404_seed_selection_includes_cells_without_positive_z9_tiles():
    from scripts.audit_sca_tile_coverage import choose_seeds, _grid_cell

    rows=[]
    # 4x4 grid extent; positives occupy only the upper-left region.
    for x in range(100,116):
        for y in range(200,216):
            state="not_found_404"
            if x < 104 and y < 204:
                state="valid_mvt_with_features"
            rows.append({"x":x,"y":y,"voluntary":{"state":state,"layers":[]}})
    seeds=choose_seeds({"tile_results":rows},8)
    missing=[s for s in seeds if s["class"].startswith("not_found_404")]
    bounds=(100,115,200,215)
    positive_cells={_grid_cell(r["x"],r["y"],bounds) for r in rows
                    if r["voluntary"]["state"]=="valid_mvt_with_features"}
    no_positive=[s for s in missing
                 if _grid_cell(s["x"],s["y"],bounds) not in positive_cells]
    assert len(missing)==8
    reserved=[s for s in missing if s["sampling_stratum"]=="no_positive_grid_cell"]
    assert len(reserved)>=4
    assert all(_grid_cell(s["x"],s["y"],bounds) not in positive_cells for s in reserved)
