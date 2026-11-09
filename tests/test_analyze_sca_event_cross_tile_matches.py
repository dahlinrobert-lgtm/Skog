import gzip
import json

from scripts.analyze_sca_event_cross_tile_matches import (
    build_report, read_events, to_web_mercator
)


def _event(tile, geometry, event_id, properties=None):
    return {
        "event_id": event_id,
        "event_type": "geometry_added",
        "source_tile": {"z": 12, "x": tile[0], "y": tile[1]},
        "layer": "Frivilliga_Avsattningar",
        "geometry": geometry,
        "properties": properties or {"SKOTSEL_KL_resolved": "51 Naturvård orörd (NO)",
                                     "MOTIV_KL_resolved": "1 Eget värde"},
    }


def test_neighboring_tiles_identical_world_geometry_match():
    # Same world-space rectangle represented in two adjacent tile coordinate systems.
    x, y = 100, 200
    # MVT buffer coordinates extend beyond each tile edge. These two local
    # rectangles therefore describe the same world-space rectangle.
    ga = {"type": "Polygon", "coordinates": [[[3900, 1000], [4300, 1000],
          [4300, 2000], [3900, 2000], [3900, 1000]]]}
    gb = {"type": "Polygon", "coordinates": [[[-196, 1000], [204, 1000],
          [204, 2000], [-196, 2000], [-196, 1000]]]}
    report = build_report([_event((x, y), ga, "a"), _event((x + 1, y), gb, "b")],
                          "fixture.jsonl.gz")
    assert report["eligible_geometry_observations"] == 2
    assert report["cross_tile_candidate_pairs"] == 1
    assert report["pairs"][0]["candidate_class"] == "strong_geometry_and_attributes_candidate"
    assert report["pairs"][0]["identity_resolved"] is False


def test_conflicting_attributes_are_review_only():
    geom = {"type": "Polygon", "coordinates": [[
        [3900, 1000], [4300, 1000], [4300, 2000], [3900, 2000], [3900, 1000]
    ]]}
    other = {"type": "Polygon", "coordinates": [[
        [-196, 1000], [204, 1000], [204, 2000], [-196, 2000], [-196, 1000]
    ]]}
    a = _event((100, 200), geom, "a")
    b = _event((101, 200), other, "b", {"SKOTSEL_KL_resolved": "60 annan klass"})
    report = build_report([a, b], "fixture")
    assert report["cross_tile_candidate_pairs"] == 1
    assert report["pairs"][0]["candidate_class"] == "geometry_overlap_attribute_conflict_review"


def test_same_tile_and_non_neighbor_tiles_are_not_compared():
    geom = {"type": "Polygon", "coordinates": [[[10, 10], [100, 10],
             [100, 100], [10, 100], [10, 10]]]}
    events = [_event((100, 200), geom, "a"), _event((100, 200), geom, "b"),
              _event((103, 200), geom, "c")]
    assert build_report(events, "fixture")["cross_tile_candidate_pairs"] == 0


def test_event_reader_supports_gzip_jsonl(tmp_path):
    path = tmp_path / "events.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        stream.write(json.dumps({"event_type": "tile_poll_error"}) + "\n")
    assert read_events(path) == [{"event_type": "tile_poll_error"}]


def test_404_and_technical_events_are_not_geometry_observations():
    events = [{"event_type": "tile_unavailable_candidate"},
              {"event_type": "tile_poll_error"}]
    report = build_report(events, "fixture")
    assert report["eligible_geometry_observations"] == 0
    assert report["cross_tile_candidate_pairs"] == 0



def test_missing_class_and_motive_do_not_count_as_compatible():
    geom_a = {"type": "Polygon", "coordinates": [[[3900, 1000], [4300, 1000],
        [4300, 2000], [3900, 2000], [3900, 1000]]]}
    geom_b = {"type": "Polygon", "coordinates": [[[-196, 1000], [204, 1000],
        [204, 2000], [-196, 2000], [-196, 1000]]]}
    a = _event((100, 200), geom_a, "a", {"other": "old"})
    b = _event((101, 200), geom_b, "b", {"other": "new"})
    report = build_report([a, b], "fixture")
    assert report["cross_tile_candidate_pairs"] == 1
    assert report["pairs"][0]["candidate_class"] == "geometry_overlap_attribute_conflict_review"
