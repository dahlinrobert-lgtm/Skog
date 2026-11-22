import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.snapshot_harvest_notifications_pilot import (
    BATCH_SIZE,
    fetch_complete_features,
    query_scope,
    atomic_write_text,
    write_snapshot_atomic,
)


class CompleteHarvestPilotTests(unittest.TestCase):
    def test_scope_is_fixed_grasmyr_10km(self):
        scope = query_scope()
        self.assertEqual(scope["distance"], "10000")
        self.assertEqual(scope["geometryType"], "esriGeometryPoint")
        self.assertEqual(scope["spatialRel"], "esriSpatialRelIntersects")
        self.assertIn("19.66455", scope["geometry"])

    def test_fetches_id_batches_and_verifies_exact_ids(self):
        ids = list(range(1, BATCH_SIZE + 2))
        session = Mock()
        def get(url, params, timeout):
            requested = [int(v) for v in params["objectIds"].split(",")]
            return Mock(
                raise_for_status=lambda: None,
                json=lambda: {"features": [
                    {"id": value, "properties": {"OBJECTID": value}, "geometry": None}
                    for value in requested
                ]},
            )
        session.get.side_effect = get
        features = fetch_complete_features(session, "OBJECTID", ids)
        self.assertEqual(len(features), len(ids))
        self.assertEqual([feature["id"] for feature in features], ids)
        self.assertEqual(session.get.call_count, 2)

    def test_missing_id_in_batch_fails_closed(self):
        session = Mock()
        session.get.return_value = Mock(
            raise_for_status=lambda: None,
            json=lambda: {"features": [
                {"id": 1, "properties": {"OBJECTID": 1}, "geometry": None}
            ]},
        )
        with self.assertRaisesRegex(RuntimeError, "batch mismatch"):
            fetch_complete_features(session, "OBJECTID", [1, 2])

    def test_transfer_limit_fails_closed(self):
        session = Mock()
        session.get.return_value = Mock(
            raise_for_status=lambda: None,
            json=lambda: {
                "features": [{"id": 1, "properties": {"OBJECTID": 1}}],
                "exceededTransferLimit": True,
            },
        )
        with self.assertRaisesRegex(RuntimeError, "transfer-limited"):
            fetch_complete_features(session, "OBJECTID", [1])

    def test_snapshot_is_published_as_complete_gzip_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.geojson.gz"
            raw = b'{"type":"FeatureCollection","features":[]}'
            write_snapshot_atomic(path, raw)
            with gzip.open(path, "rb") as source:
                self.assertEqual(source.read(), raw)
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_failed_snapshot_publish_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.geojson.gz"
            path.write_bytes(b"previous-complete-snapshot")
            with patch("scripts.snapshot_harvest_notifications_pilot.os.replace", side_effect=OSError("simulated publish failure")):
                with self.assertRaises(OSError):
                    write_snapshot_atomic(path, b"new-snapshot")
            self.assertEqual(path.read_bytes(), b"previous-complete-snapshot")
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_manifest_replace_preserves_previous_file_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.json"
            path.write_text('{"status":"previous"}', encoding="utf-8")
            with patch("scripts.snapshot_harvest_notifications_pilot.os.replace", side_effect=OSError("simulated publish failure")):
                with self.assertRaises(OSError):
                    atomic_write_text(path, '{"status":"success"}')
            self.assertEqual(path.read_text(encoding="utf-8"), '{"status":"previous"}')
            self.assertFalse(path.with_name(path.name + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
