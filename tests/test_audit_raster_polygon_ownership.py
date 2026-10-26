import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

from scripts.audit_raster_polygon_ownership import audit_cell_ownership


class RasterPolygonOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "grid.tif"
        with rasterio.open(
            self.path, "w", driver="GTiff", height=2, width=4, count=1,
            dtype="uint8", crs="EPSG:3006",
            transform=from_origin(500000, 7000020, 10, 10),
        ) as dst:
            dst.write(np.ones((2, 4), dtype=np.uint8), 1)

    def test_edge_adjacent_polygons_have_no_double_count(self):
        features = [
            {"feature_id": "left", "properties": {}, "geometry": box(500000, 7000000, 500020, 7000020)},
            {"feature_id": "right", "properties": {}, "geometry": box(500020, 7000000, 500040, 7000020)},
        ]
        with rasterio.open(self.path) as ds:
            report = audit_cell_ownership(ds, features, ds.crs)
        self.assertEqual([f["cell_assignments"] for f in report["polygon_cell_counts"]], [4, 4])
        self.assertEqual(report["cells_selected_by_multiple_polygons"], 0)
        self.assertEqual(report["double_count_excess"], 0)
        self.assertEqual(report["unique_cells_selected"], 8)

    def test_overlapping_polygons_report_double_count(self):
        features = [
            {"feature_id": "a", "properties": {}, "geometry": box(500000, 7000000, 500030, 7000020)},
            {"feature_id": "b", "properties": {}, "geometry": box(500020, 7000000, 500040, 7000020)},
        ]
        with rasterio.open(self.path) as ds:
            report = audit_cell_ownership(ds, features, ds.crs)
        self.assertEqual(report["cells_selected_by_multiple_polygons"], 2)
        self.assertEqual(report["sum_polygon_cell_assignments"], 10)
        self.assertEqual(report["unique_cells_selected"], 8)
        self.assertEqual(report["double_count_excess"], 2)


if __name__ == "__main__":
    unittest.main()
