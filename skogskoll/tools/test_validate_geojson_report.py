import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("validate-geojson-report.py")
SPEC = importlib.util.spec_from_file_location("geojson_report", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GeoJSONValidationReportTests(unittest.TestCase):
    def polygon_feature(self):
        return {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [[[
                    [19.0, 63.0], [19.1, 63.0], [19.1, 63.1],
                    [19.0, 63.0]
                ]]]
            },
            "properties": {
                "objektidentitet": "test-id",
                "omradesnummer": 1,
                "source_crs": "EPSG:3006",
                "target_crs": "EPSG:4326",
            }
        }

    def test_valid_feature_reports_ring_closure_and_preserves_crs_uncertainty(self):
        report = MODULE.make_report({
            "type": "FeatureCollection",
            "features": [self.polygon_feature()]
        })
        self.assertEqual(report["valid_feature_count"], 1)
        self.assertEqual(report["invalid_feature_count"], 0)
        feature = report["features"][0]
        self.assertEqual(feature["ring_count"], 1)
        self.assertEqual(feature["closed_rings"], 1)
        self.assertEqual(feature["bounds_wgs84"], [19.0, 63.0, 19.1, 63.1])
        self.assertFalse(report["source_crs_verified"])
        self.assertFalse(report["authoritative_boundary_verified"])

    def test_invalid_polygon_is_flagged(self):
        feature = self.polygon_feature()
        feature["geometry"]["coordinates"] = [[[
            [19.0, 63.0], [19.1, 63.1], [19.0, 63.1],
            [19.1, 63.0], [19.0, 63.0]
        ]]]
        report = MODULE.make_report({
            "type": "FeatureCollection",
            "features": [feature]
        })
        self.assertEqual(report["invalid_feature_count"], 1)
        self.assertFalse(report["features"][0]["valid"])

    def test_out_of_bounds_coordinates_generate_warning(self):
        feature = self.polygon_feature()
        feature["geometry"]["coordinates"] = [[[
            [732218.989, 7078525.562], [732226.0, 7078519.0],
            [732218.989, 7078525.562]
        ]]]
        report = MODULE.make_report({
            "type": "FeatureCollection",
            "features": [feature]
        })
        self.assertTrue(any("outside WGS84" in warning for warning in report["features"][0]["warnings"]))

    def test_requires_feature_collection(self):
        with self.assertRaises(ValueError):
            MODULE.make_report({"type": "Feature", "features": []})


if __name__ == "__main__":
    unittest.main()
