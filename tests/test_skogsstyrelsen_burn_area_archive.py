import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "burn_archive", "scripts/collect_skogsstyrelsen_burn_areas.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BurnAreaArchiveTests(unittest.TestCase):
    def test_hash_is_order_independent_for_json_objects(self):
        self.assertEqual(
            module.canonical_hash({"a": 1, "b": 2}),
            module.canonical_hash({"b": 2, "a": 1}),
        )

    def test_snapshot_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json.gz"
            payload = {"features": [{"attributes": {"OBJECTID": 7}}]}
            module.write_snapshot(path, payload)
            self.assertEqual(module.read_snapshot(path), payload)

    def test_required_schema_includes_actual_rest_fields(self):
        self.assertIn("BrandTyp", module.REQUIRED_FIELDS)
        self.assertIn("DatumBrand", module.REQUIRED_FIELDS)
        self.assertIn("ArealHa", module.REQUIRED_FIELDS)

    def test_query_candidates_include_layer_and_service_routes(self):
        candidates = [
            module.LAYER_URL + "/query",
            module.LAYER_URL.rsplit("/0", 1)[0] + "/query",
        ]
        self.assertTrue(candidates[0].endswith("/MapServer/0/query"))
        self.assertTrue(candidates[1].endswith("/MapServer/query"))


if __name__ == "__main__":
    unittest.main()
