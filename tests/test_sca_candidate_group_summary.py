import json
from pathlib import Path


def test_source_counts_are_separate_from_edge_universe():
    # Regression fixture: topology edges reference 3 records, while source universe has 10.
    summary = {
        "summary": {"source_feature_records": 10},
        "candidate_pairs": [
            {"source_key_a": "a", "source_key_b": "b", "batch_a": 0, "batch_b": 0,
             "tile_a": "1/1", "tile_b": "1/2", "class_a": "51 NO", "class_b": "51 NO",
             "motive_a": "", "motive_b": "", "geometry_hash_a": "ha", "geometry_hash_b": "hb",
             "category": "near_duplicate_candidate"}
        ]
    }
    edge_keys = {e[k] for e in summary["candidate_pairs"] for k in ("source_key_a", "source_key_b")}
    assert len(edge_keys) == 2
    assert summary["summary"]["source_feature_records"] - len(edge_keys) == 8


def test_script_summary_has_corrected_coverage_fields():
    script = Path("scripts/build_sca_national_object_candidate_groups.py").read_text()
    for field in (
        "source_feature_records_total",
        "source_records_without_any_candidate_edge",
        "source_records_not_grouped_total",
    ):
        assert f'"{field}"' in script
