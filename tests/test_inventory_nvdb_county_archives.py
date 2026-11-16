import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.inventory_nvdb_county_archives import (
    ROAD_FIELDS,
    build_report,
    inspect_archive,
)


class NvdbCountyArchiveInventoryTests(unittest.TestCase):
    def make_archive(self, directory: Path, name: str = "Norrbotten_GeoPackage.zip"):
        path = directory / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("Norrbotten.gpkg", b"metadata-probe-fixture")
        return path

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.list_layers")
    def test_compatible_archive_is_inspected_without_extraction(
        self, list_layers, read_info
    ):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            list_layers.return_value = [["NVDB_DK_O_111_Vagnummer", "Line String"]]
            read_info.return_value = {
                "fields": list(ROAD_FIELDS),
                "features": 123,
                "geometry_type": "Line String",
                "crs": "EPSG:3006",
            }

            result = inspect_archive(archive)

        self.assertEqual(result["status"], "compatible")
        self.assertTrue(result["road_layer_found"])
        self.assertEqual(result["layers"][0]["feature_count"], 123)
        self.assertTrue(archive.exists())
        list_layers.assert_called_once()
        self.assertTrue(list_layers.call_args.args[0].startswith("/vsizip/"))

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.list_layers")
    def test_missing_road_layer_is_not_reported_as_compatible(
        self, list_layers, read_info
    ):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            list_layers.return_value = [["Some_Other_Layer", "Point"]]
            read_info.return_value = {
                "fields": ["id"], "features": 1,
                "geometry_type": "Point", "crs": "EPSG:3006",
            }
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "road_layer_missing")
        self.assertFalse(result["road_layer_found"])

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.list_layers")
    def test_missing_required_fields_is_schema_mismatch(
        self, list_layers, read_info
    ):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            list_layers.return_value = [["NVDB_DK_O_111_Vagnummer", "Line String"]]
            read_info.return_value = {
                "fields": ["ELEMENT_ID", "Huvudnummer"],
                "features": 2,
                "geometry_type": "Line String",
                "crs": "EPSG:3006",
            }
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "schema_mismatch")
        self.assertEqual(
            result["road_layer_missing_fields"], ["Europavag", "Lankroll"]
        )

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.list_layers",
           side_effect=RuntimeError("GDAL read failed"))
    def test_unreadable_layer_is_partial(self, _list_layers):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "partial")
        self.assertIn("GDAL read failed", result["errors"][0])

    def test_expected_archive_count_mismatch_makes_report_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_archive(directory)
            with patch(
                "scripts.inventory_nvdb_county_archives.inspect_archive",
                return_value={"archive_bytes": 10, "status": "compatible"},
            ):
                report = build_report(directory, "*_GeoPackage.zip", 21)

        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["archive_count"], 1)
        self.assertFalse(report["source_archives_modified"])
        self.assertFalse(report["feature_geometries_scanned"])


if __name__ == "__main__":
    unittest.main()
