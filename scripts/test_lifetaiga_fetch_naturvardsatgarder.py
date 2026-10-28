"""Tests for the Life2Taiga ArcGIS FeatureServer collector."""
import unittest
from unittest.mock import patch

from lifetaiga_fetch_naturvardsatgarder import fetch_layer


class Life2TaigaFetchTests(unittest.TestCase):
    def test_fetches_and_deduplicates_paginated_features(self):
        metadata = {
            "type": "Feature Layer", "name": "Life2Taiga Naturvårdsåtgärder",
            "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID"}],
            "objectIdField": "OBJECTID", "maxRecordCount": 2,
            "geometryType": "esriGeometryPolygon",
        }
        page1 = {"features": [
            {"id": 1, "type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}, "properties": {"OBJECTID": 1}},
            {"id": 2, "type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}, "properties": {"OBJECTID": 2}},
        ]}
        page2 = {"features": [
            {"id": 2, "type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}, "properties": {"OBJECTID": 2}},
            {"id": 3, "type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}, "properties": {"OBJECTID": 3}},
        ]}
        page3 = {"features": []}
        with patch("lifetaiga_fetch_naturvardsatgarder.get_json", side_effect=[metadata, page1, page2, page3]):
            result = fetch_layer("https://example.test/FeatureServer/13", pause_seconds=0)
        self.assertEqual(result["feature_count"], 3)
        self.assertEqual(result["source_layer_id"], 13)
        self.assertEqual([f["properties"]["OBJECTID"] for f in result["features"]], [1, 2, 3])

    def test_refuses_empty_data(self):
        metadata = {"type": "Feature Layer", "fields": [{"name": "OBJECTID"}], "objectIdField": "OBJECTID"}
        with patch("lifetaiga_fetch_naturvardsatgarder.get_json", side_effect=[metadata, {"features": []}]):
            with self.assertRaisesRegex(RuntimeError, "zero geometries"):
                fetch_layer("https://example.test/FeatureServer/13", pause_seconds=0)

    def test_rejects_non_feature_layer(self):
        with patch("lifetaiga_fetch_naturvardsatgarder.get_json", return_value={"type": "Map Service"}):
            with self.assertRaisesRegex(RuntimeError, "Feature Layer"):
                fetch_layer("https://example.test/FeatureServer/13", pause_seconds=0)


if __name__ == "__main__":
    unittest.main()
