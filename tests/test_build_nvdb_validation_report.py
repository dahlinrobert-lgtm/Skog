import unittest

from scripts.build_nvdb_validation_report import analyze


class NvdbValidationReportTests(unittest.TestCase):
    def row(self, **overrides):
        row = {
            "nvr_latitude_wgs84": "65.6",
            "nvr_longitude_wgs84": "22.1",
            "geo_nvdb_search_status": "completed_with_candidates",
            "geo_nvdb_nearest_road_number": "E4",
            "geo_nvdb_nearest_road_element_id": "road-1",
            "geo_nvdb_nearest_road_distance_m": "3.0",
            "geo_nvdb_candidate_count": "1",
            "geo_nvdb_sources_failed": "0",
            "geo_nvdb_candidates": '[{"source_file":"county.zip","distance_m":3.0,"road_number":"E4","element_id":"road-1"}]',
        }
        row.update(overrides)
        return row

    def test_flags_far_distance_and_keeps_it_in_review_queue(self):
        summary, queue = analyze([self.row(geo_nvdb_nearest_road_distance_m="150")])
        self.assertEqual(summary["review_queue"]["flagged_rows"], 1)
        self.assertEqual(queue[0]["review_flags"], "far_from_road")
        self.assertEqual(queue[0]["review_status"], "pending")

    def test_partial_source_read_is_flagged_not_treated_as_no_candidate(self):
        summary, queue = analyze([self.row(
            geo_nvdb_search_status="partial_source_read",
            geo_nvdb_sources_failed="1",
        )])
        self.assertEqual(summary["rows_with_nonstandard_status"], 1)
        self.assertIn("nonstandard_search_status", queue[0]["review_flags"])

    def test_close_alternative_candidates_are_flagged(self):
        candidates = (
            '[{"source_file":"county.zip","distance_m":4.0},'
            '{"source_file":"county.zip","distance_m":12.0}]'
        )
        _, queue = analyze([self.row(
            geo_nvdb_candidate_count="2",
            geo_nvdb_candidates=candidates,
        )])
        self.assertIn("close_alternative_candidates", queue[0]["review_flags"])

    def test_clean_records_are_sampled_deterministically(self):
        rows = [self.row(geo_nvdb_nearest_road_element_id=f"road-{i}") for i in range(10)]
        summary_a, queue_a = analyze(rows, sample_per_source=3, seed="fixed")
        summary_b, queue_b = analyze(rows, sample_per_source=3, seed="fixed")
        self.assertEqual(summary_a["review_queue"]["total_rows"], 3)
        self.assertEqual(
            [item["row_number"] for item in queue_a],
            [item["row_number"] for item in queue_b],
        )

    def test_flagged_records_are_not_lost_when_sample_limit_is_zero(self):
        rows = [
            self.row(geo_nvdb_nearest_road_distance_m="700"),
            self.row(geo_nvdb_nearest_road_distance_m="5"),
        ]
        summary, queue = analyze(rows, sample_per_source=0)
        self.assertEqual(summary["review_queue"]["flagged_rows"], 1)
        self.assertEqual(len(queue), 1)


if __name__ == "__main__":
    unittest.main()
