import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_nvdb_candidate_features import extract


class CandidateFeatureTests(unittest.TestCase):
    def test_extracts_event_and_candidate_features_without_labels(self):
        rows = [{
            "event_id": "evt-1",
            "nvr_latitude_wgs84": "65.5",
            "nvr_longitude_wgs84": "22.1",
            "geo_nvdb_search_status": "completed_with_candidates",
            "geo_nvdb_candidate_count": "3",
            "geo_nvdb_sources_queried": "21",
            "geo_nvdb_sources_failed": "0",
            "geo_nvdb_search_radius_m": "1000",
            "geo_nvdb_candidates": json.dumps([
                {"distance_m": 12, "road_number": "E4", "road_role": "Europaväg", "element_id": "a", "source_file": "north.zip"},
                {"distance_m": 20, "road_number": "95", "road_role": "Riksväg", "element_id": "b", "source_file": "north.zip"},
            ]),
        }]
        events, candidates, summary = extract(rows, id_field="event_id")
        self.assertEqual(len(events), 1)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(events[0]["event_id"], "evt-1")
        self.assertEqual(events[0]["nearest_second_gap_m"], 8)
        self.assertEqual(events[0]["nearest_second_ratio"], 1.667)
        self.assertEqual(candidates[1]["candidate_rank_by_distance"], 2)
        self.assertEqual(summary["candidate_rows"], 2)
        self.assertTrue(summary["review_only"])
        self.assertNotIn("correct_road", candidates[0])

    def test_invalid_candidate_json_is_empty_not_fatal(self):
        events, candidates, summary = extract([{
            "geo_nvdb_candidates": "{bad",
            "geo_nvdb_search_status": "partial_source_read",
        }])
        self.assertEqual(candidates, [])
        self.assertEqual(events[0]["candidate_count_in_payload"], 0)
        self.assertEqual(summary["search_status_counts"]["partial_source_read"], 1)

    def test_zero_nearest_distance_has_no_infinite_ratio(self):
        events, _, _ = extract([{
            "geo_nvdb_candidates": json.dumps([
                {"distance_m": 0, "road_number": "E4"},
                {"distance_m": 10, "road_number": "95"},
            ])
        }])
        self.assertIsNone(events[0]["nearest_second_ratio"])


if __name__ == "__main__":
    unittest.main()
