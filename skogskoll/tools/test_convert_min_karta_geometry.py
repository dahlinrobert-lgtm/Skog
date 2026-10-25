import importlib.util
import unittest
from pathlib import Path

from pyproj import Transformer

MODULE_PATH = Path(__file__).with_name("convert-min-karta-geometry.py")
SPEC = importlib.util.spec_from_file_location("geometry_converter", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
transform_nested = MODULE.transform_nested


class GeometryConverterTests(unittest.TestCase):
    def setUp(self):
        self.transformer = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True)

    def test_known_sweref_point_transforms_to_grasmyr_region(self):
        # Diagnostic control point in the Gräsmyr area; this tests math, not CRS provenance.
        lon, lat = self.transformer.transform(732218.989, 7078525.562)
        self.assertAlmostEqual(lon, 19.710105, places=5)
        self.assertAlmostEqual(lat, 63.757190, places=5)
        self.assertTrue(-180 <= lon <= 180)
        self.assertTrue(-90 <= lat <= 90)

    def test_nested_polygon_ring_is_preserved_and_closed(self):
        ring = [[732218.989, 7078525.562], [732226.815, 7078519.838], [732218.989, 7078525.562]]
        converted = transform_nested([ring], self.transformer)
        self.assertEqual(len(converted), 1)
        self.assertEqual(converted[0][0], converted[0][-1])
        self.assertEqual(len(converted[0]), 3)
        for lon, lat in converted[0]:
            self.assertTrue(-180 <= lon <= 180)
            self.assertTrue(-90 <= lat <= 90)

    def test_polygon_holes_and_multiple_rings_keep_structure(self):
        rings = [
            [[732218.989, 7078525.562], [732226.815, 7078519.838], [732218.989, 7078525.562]],
            [[732220.0, 7078524.0], [732221.0, 7078523.0], [732220.0, 7078524.0]],
        ]
        converted = transform_nested(rings, self.transformer)
        self.assertEqual(len(converted), 2)
        self.assertTrue(all(ring[0] == ring[-1] for ring in converted))


if __name__ == "__main__":
    unittest.main()
