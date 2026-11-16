import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.inventory_nvdb_county_archives import (
    EXPECTED_CRS,
    ROAD_FIELDS,
    ROAD_LAYER,
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
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_dataframe")
    def test_compatible_archive_uses_catalog_and_direct_layer_read(
        self, read_dataframe, read_info
    ):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            read_dataframe.return_value = {"table_name": [ROAD_LAYER]}
            read_info.return_value = {
                "layer_name": ROAD_LAYER,
                "fields": list(ROAD_FIELDS),
                "features": 123,
                "geometry_type": "Unknown",
                "crs": EXPECTED_CRS,
            }

            result = inspect_archive(archive)

            self.assertTrue(archive.exists())
            with zipfile.ZipFile(archive) as source_zip:
                self.assertEqual(source_zip.namelist(), ["Norrbotten.gpkg"])
                self.assertEqual(
                    source_zip.read("Norrbotten.gpkg"), b"metadata-probe-fixture"
                )

        self.assertEqual(result["status"], "compatible")
        self.assertTrue(result["road_layer_found"])
        self.assertEqual(result["layers"][0]["feature_count"], 123)
        self.assertEqual(result["layers"][0]["geometry_type"], "Unknown")
        self.assertTrue(result["road_layer_crs_matches_expected"])
        read_dataframe.assert_called_once()
        self.assertIn("gpkg_contents", read_dataframe.call_args.kwargs["sql"])
        read_info.assert_called_once()
        self.assertEqual(read_info.call_args.kwargs["layer"], ROAD_LAYER)
        self.assertTrue(read_info.call_args.args[0].startswith("/vsizip/"))

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_dataframe")
    def test_missing_road_layer_is_not_reported_as_compatible(
        self, read_dataframe, read_info
    ):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            read_dataframe.return_value = {"table_name": ["Some_Other_Layer"]}
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "road_layer_missing")
        self.assertFalse(result["road_layer_found"])
        read_info.assert_not_called()

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_dataframe")
    def test_missing_required_fields_is_schema_mismatch(
        self, read_dataframe, read_info
    ):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            read_dataframe.return_value = {"table_name": [ROAD_LAYER]}
            read_info.return_value = {
                "fields": ["ELEMENT_ID", "Huvudnummer"],
                "features": 2,
                "geometry_type": "Unknown",
                "crs": EXPECTED_CRS,
            }
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "schema_mismatch")
        self.assertEqual(
            result["road_layer_missing_fields"], ["Europavag", "Lankroll"]
        )

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_dataframe")
    def test_catalog_read_failure_is_partial(self, read_dataframe, _read_info):
        read_dataframe.side_effect = RuntimeError("GDAL catalog read failed")
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "partial")
        self.assertIn("GDAL catalog read failed", result["errors"][0])

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_dataframe")
    def test_road_layer_read_failure_is_partial(self, read_dataframe, read_info):
        read_dataframe.return_value = {"table_name": [ROAD_LAYER]}
        read_info.side_effect = RuntimeError("GDAL road layer read failed")
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["road_layer_found"])
        self.assertIn("GDAL road layer read failed", result["errors"][0])

    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_info")
    @patch("scripts.inventory_nvdb_county_archives.pyogrio.read_dataframe")
    def test_wrong_crs_is_schema_mismatch(self, read_dataframe, read_info):
        read_dataframe.return_value = {"table_name": [ROAD_LAYER]}
        read_info.return_value = {
            "fields": list(ROAD_FIELDS),
            "features": 5,
            "geometry_type": "Unknown",
            "crs": "EPSG:4326",
        }
        with tempfile.TemporaryDirectory() as temp:
            archive = self.make_archive(Path(temp))
            result = inspect_archive(archive)

        self.assertEqual(result["status"], "schema_mismatch")
        self.assertFalse(result["road_layer_crs_matches_expected"])

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
        self.assertEqual(report["schema_version"], 2)
        self.assertFalse(report["source_archives_modified"])
        self.assertFalse(report["feature_geometries_scanned"])


if __name__ == "__main__":
    unittest.main()
