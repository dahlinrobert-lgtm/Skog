import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "lifetaiga_archive", "scripts/archive_lifetaiga_naturvardsatgarder.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def feature(oid, gid, value="same"):
    return {
        "attributes": {"objectid": oid, "globalid": "{" + gid + "}", "symbology": value},
        "geometry": {"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    }


class Life2TaigaArchiveTests(unittest.TestCase):
    def test_globalid_is_stable_when_objectid_changes(self):
        self.assertEqual(module.stable_key(feature(1, "ABC")), module.stable_key(feature(99, "abc")))

    def test_arcgis_attribute_lookup_is_case_insensitive(self):
        self.assertEqual(module.attribute_value({"OBJECTID": 512}, "objectid"), 512)

    def test_detects_add_update_and_removal(self):
        previous = {"features": [feature(1, "a"), feature(2, "b")]}
        current = [feature(10, "a", "changed"), feature(2, "b"), feature(3, "c")]
        changes = module.detect_changes(previous, current, "2026-11-01T00:00:00+00:00")
        self.assertEqual(
            [(item["change"], item["source_globalid"]) for item in changes],
            [("updated", "a"), ("added", "c")],
        )

    def test_duplicate_globalids_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate GlobalID"):
            module.detect_changes({"features": []}, [feature(1, "a"), feature(2, "A")], "now")

    def test_snapshot_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "current.json.gz"
            payload = {"features": [feature(1, "a")]}
            module.write_snapshot(path, payload)
            self.assertEqual(module.read_snapshot(path), payload)

    def test_source_is_lifetaiga_restoration_measure_layer(self):
        self.assertTrue(module.LAYER_URL.endswith("/FeatureServer/13"))
        self.assertIn("globalid", module.REQUIRED_FIELDS)


if __name__ == "__main__":
    unittest.main()
