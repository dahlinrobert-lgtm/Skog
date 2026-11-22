import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.completed_snapshot_store import read_completed_archives, write_completed_archive


def feature(oid, status="A", x=0):
    return {
        "type": "Feature",
        "id": str(oid),
        "properties": {"OBJECTID": oid, "ArendeStatus": status},
        "geometry": {"type": "Polygon", "coordinates": [[
            [x, 63.7], [x + 0.01, 63.7], [x + 0.01, 63.71],
            [x, 63.71], [x, 63.7]
        ]]},
    }


def collection(checked_at, features, scope="scope-A"):
    return {
        "type": "FeatureCollection",
        "name": "test",
        "checked_at": checked_at,
        "source": "https://example.test/layer",
        "query_scope_sha256": scope,
        "query_scope": {"radius_m": 10000},
        "features": features,
    }


class CompletedSnapshotStoreTests(unittest.TestCase):
    def test_round_trip_add_update_remove_and_geometry_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = collection("2026-01-01T05:00:00Z", [feature(1), feature(2)])
            first_result = write_completed_archive(first, directory)
            self.assertEqual(first_result["format"], "full")

            second = collection(
                "2026-01-02T05:00:00Z",
                [feature(1, status="B"), feature(3, x=0.02)],
            )
            result = write_completed_archive(
                second, directory,
                previous_collection=first, previous_filename=first_result["filename"],
                prefer_delta=True,
            )
            self.assertEqual(result["format"], "delta")
            self.assertEqual(result["added"], 1)
            self.assertEqual(result["updated"], 1)
            self.assertEqual(result["removed"], 1)
            self.assertEqual(result["geometry_omitted"], 1)

            raw_path = directory / result["filename"]
            with gzip.open(raw_path, "rt", encoding="utf-8") as handle:
                raw = json.load(handle)
            self.assertIn("1", raw["feature_delta"]["geometry_unchanged"])
            self.assertNotIn("geometry", raw["feature_delta"]["features"]["1"])

            rows = read_completed_archives(directory)
            self.assertEqual(len(rows), 2)
            reconstructed = rows[-1][1]
            by_id = {item["id"]: item for item in reconstructed["features"]}
            self.assertEqual(set(by_id), {"1", "3"})
            self.assertEqual(by_id["1"]["properties"]["ArendeStatus"], "B")
            self.assertEqual(by_id["1"]["geometry"], feature(1)["geometry"])


    def test_streamed_transitions_only_yield_added_and_updated_features(self):
        from scripts.completed_snapshot_store import iter_completed_archive_transitions

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = collection("2026-01-01T05:00:00Z", [feature(1), feature(2)])
            first_result = write_completed_archive(first, directory)
            second = collection(
                "2026-01-02T05:00:00Z",
                [feature(1, status="B"), feature(3, x=0.02)],
            )
            second_result = write_completed_archive(
                second, directory,
                previous_collection=first, previous_filename=first_result["filename"],
                prefer_delta=True,
            )
            transitions = list(iter_completed_archive_transitions(directory))
            self.assertEqual(len(transitions), 2)
            self.assertFalse(transitions[0]["comparable"])  # first archive is baseline
            transition = transitions[1]
            self.assertTrue(transition["comparable"])
            self.assertEqual(transition["before_snapshot"], first_result["filename"])
            self.assertEqual(transition["after_snapshot"], second_result["filename"])
            self.assertEqual(set(transition["after_features"]), {"1", "3"})
            self.assertEqual(set(transition["before_features"]), {"1"})
            self.assertEqual(
                transition["after_features"]["1"]["geometry"],
                feature(1)["geometry"],
            )

    def test_latest_archive_stream_reconstructs_delta_chain(self):
        from scripts.completed_snapshot_store import read_latest_completed_archive

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = collection("2026-01-01T05:00:00Z", [feature(1), feature(2)])
            first_result = write_completed_archive(first, directory)
            second = collection(
                "2026-01-02T05:00:00Z",
                [feature(1, status="B"), feature(3, x=0.02)],
            )
            second_result = write_completed_archive(
                second, directory,
                previous_collection=first, previous_filename=first_result["filename"],
                prefer_delta=True,
            )
            latest = read_latest_completed_archive(directory)
            self.assertEqual(latest[0], second_result["filename"])
            by_id = {item["id"]: item for item in latest[1]["features"]}
            self.assertEqual(set(by_id), {"1", "3"})
            self.assertEqual(by_id["1"]["properties"]["ArendeStatus"], "B")

    def test_streamed_transitions_follow_declared_base_not_previous_filename(self):
        from scripts.completed_snapshot_store import iter_completed_archive_transitions

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = collection("2026-01-01T05:00:00Z", [feature(1)], "scope-A")
            first_result = write_completed_archive(first, directory)

            # A later full archive is a separate checkpoint. The following delta
            # explicitly references the earlier checkpoint, not the preceding file.
            unrelated = collection("2026-01-02T05:00:00Z", [feature(9)], "scope-A")
            write_completed_archive(unrelated, directory)

            target = collection("2026-01-03T05:00:00Z", [feature(1, status="B")], "scope-A")
            delta = write_completed_archive(
                target, directory,
                previous_collection=first, previous_filename=first_result["filename"],
                prefer_delta=True,
            )
            transitions = list(iter_completed_archive_transitions(directory))
            match = next(item for item in transitions if item["after_snapshot"] == delta["filename"])
            self.assertTrue(match["comparable"])
            self.assertEqual(match["before_snapshot"], first_result["filename"])
            self.assertEqual(set(match["before_features"]), {"1"})
            self.assertEqual(set(match["after_features"]), {"1"})
            self.assertEqual(match["after_features"]["1"]["properties"]["ArendeStatus"], "B")

            from scripts.completed_snapshot_store import read_latest_completed_archive
            latest = read_latest_completed_archive(directory)
            self.assertEqual(latest[0], delta["filename"])
            by_id = {item["id"]: item for item in latest[1]["features"]}
            self.assertEqual(set(by_id), {"1"})
            self.assertEqual(by_id["1"]["properties"]["ArendeStatus"], "B")

    def test_scope_change_forces_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = collection("2026-01-01T05:00:00Z", [feature(1)], "scope-A")
            first_result = write_completed_archive(first, directory)
            second = collection("2026-01-02T05:00:00Z", [feature(2)], "scope-B")
            result = write_completed_archive(
                second, directory,
                previous_collection=first, previous_filename=first_result["filename"],
                prefer_delta=True,
            )
            self.assertEqual(result["format"], "full")
            rows = read_completed_archives(directory)
            self.assertEqual(rows[-1][1]["features"][0]["id"], "2")

    def test_delta_with_missing_or_wrong_scope_base_is_not_reconstructed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = collection("2026-01-01T05:00:00Z", [feature(1)], "scope-A")
            first_result = write_completed_archive(first, directory)
            second = collection("2026-01-02T05:00:00Z", [feature(1, status="B")], "scope-A")
            second_result = write_completed_archive(
                second, directory,
                previous_collection=first, previous_filename=first_result["filename"],
                prefer_delta=True,
            )
            # If the declared base goes missing, the delta must be skipped.
            (directory / first_result["filename"]).unlink()
            self.assertEqual(read_completed_archives(directory), [])


if __name__ == "__main__":
    unittest.main()
