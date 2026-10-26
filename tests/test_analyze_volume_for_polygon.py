import json
import tempfile
import unittest

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box
from pathlib import Path

from scripts.analyze_volume_for_polygon import load_features, summarize_feature


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


    def test_polygon_statistics_keep_zero_and_exclude_nodata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.tif"
            values = np.array([[0, 10], [20, -1]], dtype=np.int16)
            with rasterio.open(
                path, "w", driver="GTiff", height=2, width=2, count=1,
                dtype="int16", crs="EPSG:3006",
                transform=from_origin(500000, 7000000, 10, 10), nodata=-1,
            ) as dst:
                dst.write(values, 1)
            with rasterio.open(path) as ds:
                polygon = box(500000, 6999980, 500020, 7000000)
                stats = summarize_feature(ds, polygon, -1)
            self.assertEqual(stats["valid_cells"], 3)
            self.assertEqual(stats["zero_cells"], 1)
            self.assertEqual(stats["positive_cells"], 2)
            self.assertEqual(stats["nodata_cells_inside_polygon"], 1)
            self.assertAlmostEqual(stats["mean_volume_m3sk_per_ha_including_zero"], 10.0)
            self.assertAlmostEqual(stats["estimated_volume_m3sk_from_valid_cells"], 0.3)
            self.assertAlmostEqual(stats["valid_coverage_pct"], 75.0)

    def test_polygon_outside_raster_returns_no_coverage_not_zero_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.tif"
            with rasterio.open(
                path, "w", driver="GTiff", height=2, width=2, count=1,
                dtype="int16", crs="EPSG:3006",
                transform=from_origin(500000, 7000000, 10, 10), nodata=-1,
            ) as dst:
                dst.write(np.full((2, 2), -1, dtype=np.int16), 1)
            with rasterio.open(path) as ds:
                stats = summarize_feature(ds, box(510000, 6990000, 510100, 6990100), -1)
            self.assertEqual(stats["status"], "outside_raster_extent")
            self.assertIsNone(stats["mean_volume_m3sk_per_ha_including_zero"])
            self.assertEqual(stats["valid_cells"], 0)


if __name__ == "__main__":
    unittest.main()
