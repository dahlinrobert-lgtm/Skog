import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "data-platform" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from inspect_lansstyrelsen_fire_ban_service import inspect_service, layer_refs


class FireBanConnectorTests(unittest.TestCase):
    def test_discovers_layers_and_tables_without_feature_queries(self):
        calls = []

        def fake_fetch(url, timeout):
            calls.append(url)
            if url.endswith("FeatureServer"):
                return {
                    "currentVersion": 11.2,
                    "layers": [{"id": 3, "name": "Fire bans"}],
                    "tables": [{"id": 7, "name": "Decisions"}],
                }
            return {
                "name": "metadata only",
                "objectIdField": "OBJECTID",
                "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID"}],
            }

        result = inspect_service(
            fetcher=fake_fetch, service_url="https://example.test/FeatureServer"
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["safety"]["request_count"], 3)
        self.assertFalse(result["safety"]["feature_records_requested"])
        self.assertFalse(result["safety"]["geometry_requested"])
        self.assertFalse(result["safety"]["snapshot_created"])
        self.assertEqual([item["id"] for item in result["layers"]], [3, 7])

    def test_rejects_layer_list_over_safety_cap(self):
        service = {"layers": [{"id": n} for n in range(3)], "tables": []}
        with self.assertRaises(RuntimeError):
            layer_refs(service, max_layers=2)

    def test_rejects_invalid_layer_id(self):
        with self.assertRaises(RuntimeError):
            layer_refs({"layers": [{"id": "0"}]}, max_layers=5)

    def test_rejects_duplicate_layer_ids(self):
        with self.assertRaises(RuntimeError):
            layer_refs({"layers": [{"id": 0}, {"id": 0}]}, max_layers=5)

    def test_rejects_unsafe_max_layers(self):
        with self.assertRaises(ValueError):
            inspect_service(fetcher=lambda *_: {}, max_layers=0)


if __name__ == "__main__":
    unittest.main()
