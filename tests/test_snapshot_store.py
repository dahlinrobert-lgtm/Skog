import json
import tempfile
import unittest
from pathlib import Path

from scripts.snapshot_store import read_snapshot_rows, write_snapshot


def feature(oid, status="A", x=0):
    return {
        "type": "Feature",
        "id": str(oid),
        "properties": {"OBJECTID": oid, "ArendeStatus": status},
        "geometry": {"type": "Point", "coordinates": [x, 63.7]},
    }


def snapshot(checked_at, features, url="https://example.test/query?distance=10000"):
    return {
        "checked_at": checked_at,
        "area": {"latitude": 63.7, "longitude": 19.6, "radius_km": 10},
        "cutting_notifications": {
            "status": "ok",
            "url": url,
            "count": len(features),
            "features": features,
        },
    }


class SnapshotStoreTests(unittest.TestCase):
    def test_round_trip_add_update_remove_and_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = snapshot("2026-01-01T05:00:00Z", [feature(1), feature(2)])
            first_result = write_snapshot(first, directory)
            self.assertEqual(first_result["format"], "full")

            second = snapshot(
                "2026-01-02T05:00:00Z",
                [feature(1, status="B"), feature(3)],
            )
            second_result = write_snapshot(
                second, directory, previous_snapshot=first,
                previous_filename=first_result["filename"],
            )
            self.assertEqual(second_result["format"], "delta")
            self.assertEqual(second_result["added"], 1)
            self.assertEqual(second_result["updated"], 1)
            self.assertEqual(second_result["removed"], 1)

            rows = read_snapshot_rows(directory)
            self.assertEqual(len(rows), 2)
            reconstructed = rows[-1][1]
            self.assertEqual(
                {item["id"] for item in reconstructed["cutting_notifications"]["features"]},
                {"1", "3"},
            )
            by_id = {item["id"]: item for item in reconstructed["cutting_notifications"]["features"]}
            self.assertEqual(by_id["1"]["properties"]["ArendeStatus"], "B")
            self.assertEqual(reconstructed["cutting_notifications"]["count"], 2)

    def test_unchanged_features_are_not_repeated_in_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = snapshot("2026-01-01T05:00:00Z", [feature(i) for i in range(1, 6)])
            first_result = write_snapshot(first, directory)
            second = snapshot("2026-01-02T05:00:00Z", [feature(i) for i in range(1, 6)])
            result = write_snapshot(
                second, directory, previous_snapshot=first,
                previous_filename=first_result["filename"],
            )
            raw = json.loads((directory / result["filename"]).read_text(encoding="utf-8"))
            self.assertEqual(raw["feature_delta"]["added"], [])
            self.assertEqual(raw["feature_delta"]["updated"], [])
            self.assertEqual(raw["feature_delta"]["removed"], [])
            self.assertEqual(raw["feature_delta"]["features"], {})
            self.assertNotIn("features", raw["cutting_notifications"])

    def test_scope_change_forces_full_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = snapshot("2026-01-01T05:00:00Z", [feature(1)])
            first_result = write_snapshot(first, directory)
            second = snapshot(
                "2026-01-02T05:00:00Z", [feature(2)],
                url="https://example.test/query?distance=20000",
            )
            result = write_snapshot(
                second, directory, previous_snapshot=first,
                previous_filename=first_result["filename"],
            )
            self.assertEqual(result["format"], "full")
            rows = read_snapshot_rows(directory)
            self.assertEqual(rows[-1][1]["cutting_notifications"]["features"][0]["id"], "2")

    def test_failed_query_is_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = snapshot("2026-01-01T05:00:00Z", [])
            bad["cutting_notifications"]["status"] = "error"
            with self.assertRaises(ValueError):
                write_snapshot(bad, Path(tmp))
            self.assertEqual(list(Path(tmp).glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
