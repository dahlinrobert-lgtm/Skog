"""Tests for the public map geocoding export."""
import unittest

from lansstyrelsen_diary_web_export import build_map_data


class WebExportTests(unittest.TestCase):
    def test_exports_unique_and_multiple_locations(self):
        report = {"features": [
            {"record_key": "x", "diary_number": "1-2026", "title": "Bränning i A",
             "geocoding": {"confidence": "medium", "confidence_reason": "Unique match.",
               "clues": [{"type": "protected_area_name", "value": "A"}],
               "locations": [
                 {"candidate_name": "A", "official_name": "A", "coordinates": {"longitude": 15, "latitude": 60},
                  "circle_radius_m": 1200, "match": {"source": "https://example.test/a", "match_method": "exact"}},
                 {"candidate_name": "B", "official_name": "B", "coordinates": {"longitude": 16, "latitude": 61},
                  "circle_radius_m": 2200, "match": {"source": "https://example.test/b", "match_method": "exact"}}]}},
            {"record_key": "y", "diary_number": "2-2026", "title": "Okänd",
             "geocoding": {"status": "no_match", "coordinates": None}},
        ]}
        data = build_map_data(report)
        self.assertEqual(data["source_report_record_count"], 2)
        self.assertEqual(data["map_location_count"], 2)
        self.assertEqual(data["features"][0]["geometry"]["coordinates"], [15.0, 60.0])
        self.assertEqual(data["features"][1]["properties"]["circle_radius_m"], 2200)

    def test_type_mismatch_lowers_confidence(self):
        report = {"features": [
            {"diary_number": "3-2026", "title": "Bränning", "geocoding": {"confidence": "medium",
             "locations": [{"official_name": "A", "coordinates": {"longitude": 15, "latitude": 60},
               "circle_radius_m": 1000, "category_mismatch": True, "match": {"source_dataset": "LBSO"}}]}}
        ]}
        feature = build_map_data(report)["features"][0]
        self.assertEqual(feature["properties"]["confidence"], "low")
        self.assertTrue(feature["properties"]["category_mismatch"])

    def test_invalid_or_zero_radius_location_is_not_published(self):
        report = {"features": [
            {"diary_number": "4-2026", "geocoding": {"locations": [
                {"coordinates": {"longitude": 15, "latitude": 60}, "circle_radius_m": 0},
                {"coordinates": {"longitude": 999, "latitude": 60}, "circle_radius_m": 100},
            ]}}
        ]}
        self.assertEqual(build_map_data(report)["map_location_count"], 0)


if __name__ == "__main__":
    unittest.main()
