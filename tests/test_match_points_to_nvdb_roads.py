import unittest
import json
from pathlib import Path, PureWindowsPath
import tempfile
import zipfile
from unittest.mock import patch

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import LineString

from scripts.match_points_to_nvdb_roads import (
    prepare_sources, resolve_dataset_path, road_number, search_event,
)


class NationalRoadProximityTests(unittest.TestCase):
    def setUp(self):
        self.transformer = Transformer.from_crs(
            "EPSG:4326", "EPSG:3006", always_xy=True
        )
        self.sources = [{
            "path": Path("county-a.gpkg"),
            "crs": None,
            "transformer": self.transformer,
            "to_wgs84": Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True),
        }]

    def frame(self, rows):
        return gpd.GeoDataFrame(
            rows,
            geometry=[
                LineString([(x, y), (x + 20, y)])
                for x, y in [(500000, 7000000), (500000, 7000010)]
            ][:len(rows)],
            crs="EPSG:3006",
        )

    def test_returns_nearest_and_alternative_road_candidates(self):
        point_x, point_y = self.transformer.transform(20.0, 63.0)
        frame = gpd.GeoDataFrame(
            {
                "ELEMENT_ID": ["road-near", "road-far"],
                "Europavag": ["Nej", "Ja"],
                "Huvudnummer": [97, 4],
                "Lankroll": ["Normal", "Gren"],
            },
            geometry=[
                LineString([(point_x - 10, point_y + 5), (point_x + 10, point_y + 5)]),
                LineString([(point_x - 10, point_y + 30), (point_x + 10, point_y + 30)]),
            ],
            crs="EPSG:3006",
        )
        with patch(
            "scripts.match_points_to_nvdb_roads.pyogrio.read_dataframe",
            return_value=frame,
        ) as read:
            result = search_event(63.0, 20.0, self.sources, 100, 5)

        self.assertEqual(result["geo_nvdb_search_status"], "completed_with_candidates")
        self.assertEqual(result["geo_nvdb_nearest_road_number"], "97")
        self.assertEqual(result["geo_nvdb_nearest_road_element_id"], "road-near")
        self.assertEqual(result["geo_nvdb_nearest_road_distance_m"], "5.0")
        self.assertEqual(result["geo_nvdb_candidate_count"], "2")
        self.assertEqual(result["geo_review_status"], "review_only_not_confirmed")
        self.assertEqual(read.call_args.kwargs["bbox"], (
            point_x - 100, point_y - 100, point_x + 100, point_y + 100
        ))

    def test_invalid_coordinates_do_not_query_sources(self):
        with patch("scripts.match_points_to_nvdb_roads.pyogrio.read_dataframe") as read:
            result = search_event(999, 20, self.sources, 100, 5)
        self.assertEqual(
            result["geo_nvdb_search_status"],
            "missing_or_invalid_coordinates",
        )
        read.assert_not_called()

    def test_source_read_failure_is_partial_not_negative_evidence(self):
        with patch(
            "scripts.match_points_to_nvdb_roads.pyogrio.read_dataframe",
            side_effect=RuntimeError("read failed"),
        ):
            result = search_event(63.0, 20.0, self.sources, 100, 5)
        self.assertEqual(result["geo_nvdb_search_status"], "partial_source_read")
        self.assertEqual(result["geo_nvdb_sources_failed"], "1")
        self.assertEqual(result["geo_nvdb_candidate_count"], "0")

    def test_no_candidate_is_explicitly_limited_to_search_window(self):
        with patch(
            "scripts.match_points_to_nvdb_roads.pyogrio.read_dataframe",
            return_value=gpd.GeoDataFrame(
                {"ELEMENT_ID": [], "Europavag": [], "Huvudnummer": [], "Lankroll": []},
                geometry=[],
                crs="EPSG:3006",
            ),
        ):
            result = search_event(63.0, 20.0, self.sources, 100, 5)
        self.assertEqual(
            result["geo_nvdb_search_status"],
            "completed_no_candidate_in_search_window",
        )
        self.assertNotIn("no_road_exists", result["geo_nvdb_search_status"])

    def test_european_road_number_is_formatted(self):
        self.assertEqual(
            road_number({"Europavag": "Ja", "Huvudnummer": 4}),
            "E4",
        )


    def test_resolves_zip_with_one_gpkg_without_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "county.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("nested/county.gpkg", b"fixture")
            resolved = resolve_dataset_path(archive)
            self.assertEqual(
                resolved,
                f"/vsizip/{archive.resolve().as_posix()}/nested/county.gpkg",
            )
            self.assertEqual(archive.read_bytes()[:2], b"PK")

    def test_zip_without_gpkg_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "empty.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("readme.txt", "not a geopackage")
            with self.assertRaisesRegex(ValueError, "ingen .gpkg"):
                resolve_dataset_path(archive)

    def test_zip_with_multiple_gpkg_members_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "multiple.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("one.gpkg", b"one")
                zipped.writestr("two.gpkg", b"two")
            with self.assertRaisesRegex(ValueError, "exakt en"):
                resolve_dataset_path(archive)

    def test_prepare_sources_reads_metadata_from_vsi_path(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "county.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("county.gpkg", b"fixture")
            expected_path = resolve_dataset_path(archive)
            info = {
                "crs": "EPSG:3006",
                "fields": ["ELEMENT_ID", "Europavag", "Huvudnummer", "Lankroll"],
            }
            with patch(
                "scripts.match_points_to_nvdb_roads.pyogrio.read_info",
                return_value=info,
            ) as read_info:
                sources, errors = prepare_sources([archive])
            self.assertEqual(errors, [])
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]["dataset_path"], expected_path)
            read_info.assert_called_once_with(expected_path, layer="NVDB_DK_O_111_Vagnummer")


    def test_resolves_zip_with_windows_drive_path(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "county.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("nested/county.gpkg", b"fixture")
            with patch(
                "scripts.match_points_to_nvdb_roads.Path.resolve",
                return_value=PureWindowsPath(r"C:\GIS\county.zip"),
            ):
                resolved = resolve_dataset_path(archive)
            self.assertEqual(
                resolved,
                "/vsizip/C:/GIS/county.zip/nested/county.gpkg",
            )


    def test_search_event_exports_event_and_candidate_geometry_for_geojson(self):
        point_x, point_y = self.transformer.transform(20.0, 63.0)
        frame = gpd.GeoDataFrame(
            {
                "ELEMENT_ID": ["road-near"],
                "Europavag": ["Nej"],
                "Huvudnummer": [97],
                "Lankroll": ["Normal"],
            },
            geometry=[
                LineString([(point_x - 10, point_y + 5), (point_x + 10, point_y + 5)])
            ],
            crs="EPSG:3006",
        )
        with patch(
            "scripts.match_points_to_nvdb_roads.pyogrio.read_dataframe",
            return_value=frame,
        ):
            result = search_event(63.0, 20.0, self.sources, 100, 5, include_geometry=True)

        self.assertEqual(len(result["_geojson_candidates"]), 1)
        self.assertEqual(result["_geojson_candidates"][0]["geometry"]["type"], "LineString")
        self.assertNotIn("geometry", json.loads(result["geo_nvdb_candidates"])[0])
        coordinates = result["_geojson_candidates"][0]["geometry"]["coordinates"]
        self.assertAlmostEqual(coordinates[0][0], 20.0, places=3)
        self.assertAlmostEqual(coordinates[0][1], 63.0, places=3)


if __name__ == "__main__":
    unittest.main()
