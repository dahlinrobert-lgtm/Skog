import unittest

import geopandas as gpd
from shapely.geometry import Point

from scripts.export_ortnamn_municipality_reference import export_municipality


class OrtnamnMunicipalityExportTests(unittest.TestCase):
    def setUp(self):
        self.frame = gpd.GeoDataFrame(
            [
                {"kommunkod": "2580", "ortnamn": "Notviken", "detaljtyp": "TRAKTTX", "lopnummer": 12, "geometry": Point(825884, 7295728)},
                {"kommunkod": "2580", "ortnamn": "Södra Sunderbyn", "detaljtyp": "BEBTÄTTX", "lopnummer": 13, "geometry": Point(818186, 7299407)},
                {"kommunkod": "2480", "ortnamn": "Notviken", "detaljtyp": "TRAKTTX", "lopnummer": 14, "geometry": Point(700000, 7300000)},
            ],
            geometry="geometry",
            crs="EPSG:3006",
        )

    def test_exports_only_requested_municipality(self):
        rows, summary = export_municipality(self.frame, "2580")
        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["exported_feature_count"], 2)
        self.assertTrue(all(row["municipality_code"] == "2580" for row in rows))

    def test_preserves_detail_type_and_source_attributes(self):
        rows, _ = export_municipality(self.frame, "2580")
        self.assertEqual({row["detaljtyp"] for row in rows}, {"TRAKTTX", "BEBTÄTTX"})
        self.assertTrue(all(row["attributes_json"] for row in rows))

    def test_keeps_point_coordinates_and_crs(self):
        rows, summary = export_municipality(self.frame, "2580")
        self.assertEqual(rows[0]["source_geometry_x"], 825884.0)
        self.assertEqual(rows[0]["source_geometry_y"], 7295728.0)
        self.assertEqual(summary["crs"], "EPSG:3006")

    def test_reports_no_false_stable_identity_claim(self):
        _, summary = export_municipality(self.frame, "2580")
        self.assertIn("not a persistent", summary["source_row_index_note"])
        self.assertIn("not assume it is unique or stable", summary["lopnummer_note"])


if __name__ == "__main__":
    unittest.main()
