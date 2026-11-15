import unittest

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from scripts.enrich_police_nvr_geography import (
    build_segment_evidence,
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


    def test_named_road_segment_measures_point_between_two_anchors(self):
        roads = gpd.GeoDataFrame({
            "ELEMENT_ID": ["road-97"],
            "Europavag": ["nej"],
            "Huvudnummer": [97],
            "Lankroll": ["Normal"],
        }, geometry=[LineString([(0, 0), (200, 0)])], crs="EPSG:3006")
        crossings = gpd.GeoDataFrame({
            "ELEMENT_ID": ["start", "end"],
            "Generaliseringstyp": ["enkel korsning", "enkel korsning"],
            "Ingar_i_trafikplats": ["nej", "nej"],
            "Namn": ["Södra Sunderbyn", "Notviken"],
            "Trafikplatsnamn": ["", ""],
        }, geometry=[Point(0, 5), Point(200, 5)], crs="EPSG:3006")

        result = build_segment_evidence(
            Point(100, 4), roads, crossings, ("national", 97),
            "Södra Sunderbyn", "Notviken",
            anchor_snap_radius=20, segment_search_radius=10,
        )

        self.assertEqual(result["geo_segment_route_status"], "segment_built")
        self.assertEqual(result["geo_segment_distance_m"], "4.0")
        self.assertEqual(result["geo_segment_within_radius"], "yes")
        self.assertEqual(result["geo_segment_length_m"], "200.0")
        self.assertEqual(result["geo_segment_from_anchor_element_id"], "start")
        self.assertEqual(result["geo_segment_to_anchor_element_id"], "end")

    def test_named_road_segment_does_not_bridge_disconnected_road_parts(self):
        roads = gpd.GeoDataFrame({
            "ELEMENT_ID": ["road-a", "road-b"],
            "Europavag": ["nej", "nej"],
            "Huvudnummer": [97, 97],
            "Lankroll": ["Normal", "Normal"],
        }, geometry=[
            LineString([(0, 0), (50, 0)]),
            LineString([(150, 0), (200, 0)]),
        ], crs="EPSG:3006")
        crossings = gpd.GeoDataFrame({
            "ELEMENT_ID": ["start", "end"],
            "Generaliseringstyp": ["enkel korsning", "enkel korsning"],
            "Ingar_i_trafikplats": ["nej", "nej"],
            "Namn": ["Södra Sunderbyn", "Notviken"],
            "Trafikplatsnamn": ["", ""],
        }, geometry=[Point(0, 5), Point(200, 5)], crs="EPSG:3006")

        result = build_segment_evidence(
            Point(100, 4), roads, crossings, ("national", 97),
            "Södra Sunderbyn", "Notviken",
            anchor_snap_radius=20, segment_search_radius=10,
        )

        self.assertEqual(
            result["geo_segment_route_status"],
            "no_connected_road_component_within_anchor_radius",
        )
        self.assertEqual(result["geo_segment_candidate_count"], "0")

    def test_named_road_segment_requires_both_anchor_references(self):
        result = build_segment_evidence(
            Point(10, 0), pd.DataFrame(), pd.DataFrame(),
            ("national", 97), "Södra Sunderbyn", "",
        )
        self.assertEqual(result["geo_segment_route_status"], "segment_reference_missing")

if __name__ == "__main__":
    unittest.main()
