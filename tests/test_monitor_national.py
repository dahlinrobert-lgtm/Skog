import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts.monitor_national import (
    apply_delta, create_delta, fetch_nationwide_features, read_archive_rows, write_gzip_json
)


def feature(oid, status="A", x=0):
    return {
        "type": "Feature",
        "id": str(oid),
        "properties": {"OBJECTID": oid, "ArendeStatus": status},
        "geometry": {"type": "Point", "coordinates": [x, 63.7]},
    }


def snapshot(checked_at, features):
    return {
        "checked_at": checked_at,
        "scope": "Sweden",
        "cutting_notifications": {
            "status": "ok",
            "url": "https://example.test/query",
            "count": len(features),
            "features": features,
        },
    }


class NationalArchiveTests(unittest.TestCase):
    def test_delta_round_trip_add_update_remove(self):
        first = snapshot("2026-01-01T05:00:00Z", [feature(1), feature(2)])
        second = snapshot("2026-01-02T05:00:00Z", [feature(1, status="B"), feature(3)])
        delta = create_delta(first, second, "20260101T050000Z.json.gz")
        self.assertEqual(delta["feature_delta"]["added"], ["3"])
        self.assertEqual(delta["feature_delta"]["updated"], ["1"])
        self.assertEqual(delta["feature_delta"]["removed"], ["2"])
        self.assertIn("1", delta["feature_delta"]["geometry_unchanged"])
        self.assertNotIn("geometry", delta["feature_delta"]["features"]["1"])
        rebuilt = apply_delta(first, delta)
        self.assertEqual({f["id"] for f in rebuilt["cutting_notifications"]["features"]}, {"1", "3"})
        by_id = {f["id"]: f for f in rebuilt["cutting_notifications"]["features"]}
        self.assertEqual(by_id["1"]["properties"]["ArendeStatus"], "B")
        self.assertEqual(by_id["1"]["geometry"]["coordinates"], [0, 63.7])

    def test_compressed_archive_reconstructs_delta_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first_name = "20260101T050000Z.json.gz"
            second_name = "20260102T050000Z.json.gz"
            first = snapshot("2026-01-01T05:00:00Z", [feature(1), feature(2)])
            second = snapshot("2026-01-02T05:00:00Z", [feature(1, status="B"), feature(3)])
            write_gzip_json(directory / first_name, first)
            write_gzip_json(directory / second_name, create_delta(first, second, first_name))
            rows = read_archive_rows(directory)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1][1]["cutting_notifications"]["count"], 2)
            self.assertEqual({f["id"] for f in rows[-1][1]["cutting_notifications"]["features"]}, {"1", "3"})

    def test_compressed_json_is_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json.gz"
            expected = snapshot("2026-01-01T05:00:00Z", [feature(1)])
            write_gzip_json(path, expected)
            self.assertTrue(path.stat().st_size > 0)
            self.assertEqual(read_archive_rows(path.parent)[0][1]["checked_at"], expected["checked_at"])


class NationalCollectorTests(unittest.TestCase):
    @patch("scripts.monitor_national.time.sleep", return_value=None)
    @patch("scripts.monitor_national.get_json")
    def test_fetch_uses_batches_and_verifies_second_inventory(self, get_json, _sleep):
        ids = list(range(1, 252))
        get_json.side_effect = [
            {"objectIds": ids},
            {"features": [feature(value) for value in ids[:250]]},
            {"features": [feature(value) for value in ids[250:]]},
            {"objectIds": ids},
        ]

        features, diagnostics = fetch_nationwide_features()

        self.assertEqual(len(features), 251)
        self.assertEqual(diagnostics["batch_count"], 2)
        self.assertEqual(diagnostics["inventory_checks"], 2)
        self.assertTrue(diagnostics["inventory_stable"])
        self.assertEqual(get_json.call_count, 4)
        self.assertEqual(get_json.call_args_list[1].kwargs, {"use_post": True})
        self.assertEqual(get_json.call_args_list[2].kwargs, {"use_post": True})

    @patch("scripts.monitor_national.time.sleep", return_value=None)
    @patch("scripts.monitor_national.get_json")
    def test_missing_id_is_retried_individually_and_recovered(self, get_json, _sleep):
        get_json.side_effect = [
            {"objectIds": [1, 2]},
            {"features": [feature(1)]},
            {"features": []},
            {"features": [feature(2)]},
            {"objectIds": [1, 2]},
        ]

        features, diagnostics = fetch_nationwide_features()

        self.assertEqual({item["id"] for item in features}, {"1", "2"})
        self.assertEqual(diagnostics["missing_id_retry_count"], 1)
        self.assertEqual(
            diagnostics["missing_id_retry_diagnostics"],
            [{"object_id": "2", "attempts": 2, "status": "recovered"}],
        )
        self.assertEqual(get_json.call_count, 5)

    @patch("scripts.monitor_national.time.sleep", return_value=None)
    @patch("scripts.monitor_national.get_json")
    def test_unresolved_id_reports_identifier_and_last_error(self, get_json, _sleep):
        get_json.side_effect = [
            {"objectIds": [11]},
            {"features": []},
            {"features": []},
            {"features": []},
            {"features": []},
        ]

        with self.assertRaisesRegex(RuntimeError, r"11: ArcGIS returned an empty feature list"):
            fetch_nationwide_features()
        self.assertEqual(get_json.call_count, 5)

    @patch("scripts.monitor_national.get_json")
    def test_duplicate_feature_ids_fail_closed(self, get_json):
        get_json.side_effect = [
            {"objectIds": [1]},
            {"features": [feature(1), feature(1)]},
        ]
        with self.assertRaisesRegex(RuntimeError, "duplicate feature IDs"):
            fetch_nationwide_features()
        self.assertEqual(get_json.call_count, 2)

    @patch("scripts.monitor_national.get_json")
    def test_source_inventory_change_during_scan_fails_closed(self, get_json):
        get_json.side_effect = [
            {"objectIds": [1]},
            {"features": [feature(1)]},
            {"objectIds": [1, 2]},
        ]
        with self.assertRaisesRegex(RuntimeError, "inventory changed during the scan"):
            fetch_nationwide_features()
        self.assertEqual(get_json.call_count, 3)

    @patch("scripts.monitor_national.get_json")
    def test_duplicate_ids_in_initial_inventory_fail_closed(self, get_json):
        get_json.return_value = {"objectIds": [1, 1]}
        with self.assertRaisesRegex(RuntimeError, "duplicate object IDs"):
            fetch_nationwide_features()
        self.assertEqual(get_json.call_count, 1)

    @patch("scripts.monitor_national.get_json")
    def test_unexpected_feature_id_fails_closed(self, get_json):
        get_json.side_effect = [
            {"objectIds": [1]},
            {"features": [feature(1), feature(2)]},
        ]
        with self.assertRaisesRegex(RuntimeError, "outside the discovered inventory"):
            fetch_nationwide_features()
        self.assertEqual(get_json.call_count, 2)


if __name__ == "__main__":
    unittest.main()
