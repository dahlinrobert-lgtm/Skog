import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_volume_for_polygon import load_features


class PolygonInputTests(unittest.TestCase):
    def test_polygon_geometry_is_wrapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "poly.json"
            path.write_text(json.dumps({
                "type": "Polygon",
                "coordinates": [[[19.0, 63.0], [19.01, 63.0], [19.01, 63.01], [19.0, 63.01], [19.0, 63.0]]]
            }), encoding="utf-8")
            features, crs = load_features(path)
            self.assertEqual(len(features), 1)
            self.assertEqual(crs.to_epsg(), 4326)
            self.assertTrue(features[0]["geometry"].is_valid)

    def test_feature_collection_ignores_non_polygon_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "poly.json"
            path.write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"id": "a"}, "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[19, 63], [19.01, 63], [19.01, 63.01], [19, 63.01], [19, 63]]]
                    }},
                    {"type": "Feature", "properties": {}, "geometry": {
                        "type": "Point", "coordinates": [19, 63]
                    }}
                ]
            }), encoding="utf-8")
            features, _ = load_features(path)
            self.assertEqual(len(features), 1)
            self.assertEqual(features[0]["feature_id"], "a")


if __name__ == "__main__":
    unittest.main()
