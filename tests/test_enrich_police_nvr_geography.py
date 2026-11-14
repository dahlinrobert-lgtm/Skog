import unittest

import pandas as pd

from scripts.enrich_police_nvr_geography import (
    clean_text,
    extract_place_reference,
    find_named_place_matches,
    parse_road_number,
    place_search_term,
)


class GeographyEvidenceTests(unittest.TestCase):
    def test_parse_european_road(self):
        self.assertEqual(parse_road_number("E4"), ("european", 4))

    def test_parse_riksvag(self):
        self.assertEqual(parse_road_number("riksväg 97"), ("national", 97))

    def test_parse_lansvag(self):
        self.assertEqual(parse_road_number("länsväg 383"), ("national", 383))

    def test_between_text_extracts_second_endpoint(self):
        row = {
            "police_text": (
                "Olycka på riksväg 97 mellan Södra Sunderbyn "
                "och Notviken. Inga personskador."
            )
        }
        self.assertEqual(extract_place_reference(row), "Notviken")

    def test_explicit_place_takes_precedence(self):
        row = {
            "police_place_reference": "Norra Rutvik",
            "police_text": "på E4 mellan två orter"
        }
        self.assertEqual(extract_place_reference(row), "Norra Rutvik")

    def test_compass_prefix_is_removed_for_search_only(self):
        self.assertEqual(place_search_term("Norra Rutvik"), "Rutvik")

    def test_missing_place_is_empty(self):
        self.assertEqual(extract_place_reference({"police_text": ""}), "")

    def test_pandas_nan_does_not_leak_into_output(self):
        self.assertEqual(clean_text(float("nan")), "")


    def test_named_place_search_matches_crossing_and_traffic_place_names(self):
        crossings = pd.DataFrame({
            "Namn": ["Rutvik", None, "Notviken"],
            "Trafikplatsnamn": [None, "Rutvik", "Notviken"],
        })
        term, matches = find_named_place_matches(crossings, "Norra Rutvik")
        self.assertEqual(term, "Rutvik")
        self.assertEqual(len(matches), 2)

    def test_named_place_search_does_not_match_missing_names(self):
        crossings = pd.DataFrame({
            "Namn": [None, ""],
            "Trafikplatsnamn": [None, ""],
        })
        term, matches = find_named_place_matches(crossings, "Smedsbyn")
        self.assertEqual(term, "Smedsbyn")
        self.assertTrue(matches.empty)

    def test_empty_place_reference_returns_no_matches(self):
        crossings = pd.DataFrame({
            "Namn": ["Rutvik"],
            "Trafikplatsnamn": [None],
        })
        term, matches = find_named_place_matches(crossings, "")
        self.assertEqual(term, "")
        self.assertTrue(matches.empty)

if __name__ == "__main__":
    unittest.main()
