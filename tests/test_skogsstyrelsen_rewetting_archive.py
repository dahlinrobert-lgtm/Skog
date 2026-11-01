import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "rewetting_archive", "scripts/collect_skogsstyrelsen_rewetting.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RewettingArchiveTests(unittest.TestCase):
    def test_required_fields_match_public_layer_schema(self):
        self.assertIn("Uuid", module.REQUIRED_FIELDS)
        self.assertIn("AvtalatDatum", module.REQUIRED_FIELDS)
        self.assertIn("KartaHektar", module.REQUIRED_FIELDS)

    def test_snapshot_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "current.json.gz"
            payload = {"features": [{"attributes": {"OBJECTID": 12}}]}
            module.write_snapshot(path, payload)
            self.assertEqual(module.read_snapshot(path), payload)

    def test_change_detection_add_update_and_remove(self):
        old = {"features": [
            {"attributes": {"OBJECTID": 1, "value": "old"}, "geometry": {"rings": []}},
            {"attributes": {"OBJECTID": 2, "value": "same"}, "geometry": {"rings": []}},
        ]}
        current = [
            {"attributes": {"OBJECTID": 1, "value": "new"}, "geometry": {"rings": []}},
            {"attributes": {"OBJECTID": 2, "value": "same"}, "geometry": {"rings": []}},
            {"attributes": {"OBJECTID": 3, "value": "added"}, "geometry": {"rings": []}},
        ]
        changes = module.detect_changes(old, current, "2026-11-01T00:00:00+00:00")
        self.assertEqual(
            [(item["change"], item["object_id"]) for item in changes],
            [("updated", 1), ("added", 3), ("removed_from_source", 2)],
        )

    def test_endpoint_points_to_skogsstyrelsen_rewetting_layer(self):
        self.assertIn("GeodataportalVisaAtervatningavtal/MapServer/0", module.LAYER_URL)


if __name__ == "__main__":
    unittest.main()
