"""Analytical ground-truth tests using a uniform synthetic raster."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from scripts.compare_polygon_pixel_methods import compare_one


class UniformControlRasterTests(unittest.TestCase):
    def make_raster(self, path, values):
        values = np.asarray(values, dtype=np.int16)
        with rasterio.open(
            path, "w", driver="GTiff", height=values.shape[0], width=values.shape[1],
            count=1, dtype="int16", crs="EPSG:3006",
            transform=from_origin(500000, 7000020, 10, 10), nodata=-1
        ) as dst:
            dst.write(values, 1)

    def test_one_full_cell_has_exact_known_area_and_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "uniform.tif"
            self.make_raster(path, [[100, 100], [100, 100]])
            # Top-left 10 m x 10 m cell: 100 m² = 0.01 ha.
            with rasterio.open(path) as ds:
                result = compare_one(ds, box(500000, 7000010, 500010, 7000020), -1)
            self.assertEqual(result["status"], "ok")
            self.assertAlmostEqual(result["polygon_area_ha"], 0.01)
            self.assertAlmostEqual(result["fractional_coverage_ha"], 0.01)
            self.assertAlmostEqual(result["fractional_estimated_volume_m3sk"], 1.0)
            self.assertAlmostEqual(result["fractional_mean_m3sk_ha"], 100.0)
            self.assertAlmostEqual(result["center_estimated_volume_m3sk"], 1.0)

    def test_half_cell_has_exact_fractional_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "uniform.tif"
            self.make_raster(path, [[100, 100], [100, 100]])
            # Exactly half of the top-left cell: 50 m² = 0.005 ha.
            with rasterio.open(path) as ds:
                result = compare_one(ds, box(500000, 7000015, 500010, 7000020), -1)
            self.assertAlmostEqual(result["polygon_area_ha"], 0.005)
            self.assertAlmostEqual(result["fractional_coverage_ha"], 0.005)
            self.assertAlmostEqual(result["fractional_estimated_volume_m3sk"], 0.5)

    def test_nodata_is_separated_from_valid_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.tif"
            self.make_raster(path, [[100, -1], [100, -1]])
            # Covers one valid cell and one NoData cell, each 0.01 ha.
            with rasterio.open(path) as ds:
                result = compare_one(ds, box(500000, 7000010, 500020, 7000020), -1)
            self.assertEqual(result["status"], "ok")
            self.assertAlmostEqual(result["fractional_raster_intersection_ha"], 0.02)
            self.assertAlmostEqual(result["fractional_nodata_coverage_ha"], 0.01)
            self.assertAlmostEqual(result["fractional_valid_coverage_ha"], 0.01)
            self.assertAlmostEqual(result["fractional_estimated_volume_m3sk"], 1.0)


if __name__ == "__main__":
    unittest.main()
