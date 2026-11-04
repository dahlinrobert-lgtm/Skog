import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "trace", Path(__file__).parents[1] / "scripts/trace_sca_overlap_sources.py"
)
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)


def test_parse_source_key():
    assert trace.parse_source_key("10:12:2247:1088:Frivilliga_Avsattningar:0") == (
        10, 12, 2247, 1088, "Frivilliga_Avsattningar", 0
    )


def test_parse_source_key_layer_with_separator():
    assert trace.parse_source_key("2:12:1:2:layer:sub:7") == (
        2, 12, 1, 2, "layer:sub", 7
    )


def test_choose_sample_is_deterministic_and_unique():
    rows = [
        {"source_key_a": "a", "source_key_b": "b", "review_priority": "1",
         "review_bucket": "partial_same_class_fragment_signal", "motive_relation": "same"},
        {"source_key_a": "c", "source_key_b": "d", "review_priority": "1",
         "review_bucket": "partial_cross_class", "motive_relation": "different"},
        {"source_key_a": "e", "source_key_b": "f", "review_priority": "2",
         "review_bucket": "nested_same_class", "motive_relation": "same"},
    ]
    first = trace.choose_sample(rows, 3)
    second = trace.choose_sample(list(reversed(rows)), 3)
    assert [(r["source_key_a"], r["source_key_b"]) for r in first] == [
        (r["source_key_a"], r["source_key_b"]) for r in second
    ]
    assert len(first) == 3


def test_tile_to_3857_keeps_polygon_valid():
    from shapely.geometry import box
    geom = trace.tile_to_3857(box(0, 0, 4096, 4096), 2048, 2048, 4096)
    assert geom.is_valid
    assert not geom.is_empty
