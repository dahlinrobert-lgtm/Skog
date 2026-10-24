import tempfile
import unittest
from pathlib import Path

from scripts.monitor_national import (
    apply_delta, create_delta, read_archive_rows, write_gzip_json
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


if __name__ == "__main__":
    unittest.main()
