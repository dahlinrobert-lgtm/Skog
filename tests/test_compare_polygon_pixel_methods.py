import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box
from scripts.compare_polygon_pixel_methods import compare_one

class FractionalCoverageTests(unittest.TestCase):
    def test_half_cell_polygon_fractionally_weights_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grid.tif"
            with rasterio.open(path, "w", driver="GTiff", height=1, width=2, count=1,
                               dtype="int16", crs="EPSG:3006",
                               transform=from_origin(500000, 7000010, 10, 10), nodata=-1) as dst:
                dst.write(np.array([[100, 200]], dtype=np.int16), 1)
            with rasterio.open(path) as ds:
                result = compare_one(ds, box(500005, 7000000, 500015, 7000010), -1)
            self.assertAlmostEqual(result["fractional_equivalent_cells"], 0.5)
            self.assertAlmostEqual(result["fractional_coverage_ha"], 0.005)
            self.assertAlmostEqual(result["fractional_estimated_volume_m3sk"], 0.5)
            self.assertEqual(result["valid_center_cells"], 0)


    def test_slanted_polygon_area_and_fractional_volume(self):
        from shapely.geometry import Polygon
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "grid.tif"
            with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1,
                               dtype="int16", crs="EPSG:3006",
                               transform=from_origin(500000, 7000020, 10, 10), nodata=-1) as dst:
                dst.write(np.array([[100, 200], [300, 400]], dtype=np.int16), 1)
            triangle = Polygon([
                (500000, 7000020), (500020, 7000020),
                (500000, 7000005), (500000, 7000020)
            ])
            with rasterio.open(path) as ds:
                result = compare_one(ds, triangle, -1)
            self.assertAlmostEqual(result["polygon_area_ha"], 0.015)
            self.assertAlmostEqual(result["fractional_coverage_ha"], 0.015)
            self.assertAlmostEqual(result["fractional_estimated_volume_m3sk"], 2.208, places=3)

if __name__ == "__main__":
    unittest.main()
