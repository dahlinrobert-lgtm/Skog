import unittest
from unittest.mock import Mock

from scripts.snapshot_harvest_notifications_pilot import (
    BATCH_SIZE,
    fetch_complete_features,
    query_scope,
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


if __name__ == "__main__":
    unittest.main()
