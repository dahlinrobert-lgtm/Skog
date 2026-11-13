import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from viltdata_kill_statistics_diff import (
    classify, compare_runs, extract_observations,
)


class ViltdataKillStatisticsDiffTests(unittest.TestCase):
    def test_classifies_null_zero_and_value_changes(self):
        self.assertEqual(classify(None, 12), "new_value")
        self.assertEqual(classify(None, 0), "new_zero")
        self.assertEqual(classify(12, 15), "value_changed")
        self.assertEqual(classify(12, None), "became_missing")
        self.assertEqual(classify(None, None), "unchanged")
        self.assertEqual(classify(0, 0), "unchanged")
        self.assertEqual(classify(12, 12), "unchanged")

    def write_snapshot(self, root, run_id, values, complete=True):
        root.mkdir()
        (root / "raw" / "statistics").mkdir(parents=True)
        payload = {
            "labels": ["2024", "2025"],
            "dataSets": [
                {"label": "Älg", "data": values},
                {"label": "Rådjur", "data": [0, None]},
            ],
        }
        raw_rel = "raw/statistics/national-batch-001.json"
        (root / raw_rel).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        manifest = {
            "run_id": run_id,
            "report_type": "kill",
            "status": "complete" if complete else "partial",
            "complete": complete,
            "species": [{"id": 1, "name": "Älg"}, {"id": 2, "name": "Rådjur"}],
            "statistics_requests_expected": 1,
            "requests": [{
                "kind": "statistics",
                "scope": "national",
                "species_ids": [1, 2],
                "file": raw_rel,
                "status": "ok",
            }],
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )

    def test_compares_two_complete_snapshots(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / "base"
            current = pathlib.Path(temp) / "current"
            self.write_snapshot(base, "base-run", [100, None])
            self.write_snapshot(current, "current-run", [125, 8])

            summary, changes = compare_runs(base, current)

            self.assertEqual(summary["baseline_observations"], 4)
            self.assertEqual(summary["changed_observations"], 2)
            self.assertEqual(summary["counts"]["value_changed"], 1)
            self.assertEqual(summary["counts"]["new_value"], 1)
            self.assertEqual(
                {(item["species_id"], item["year"], item["change"]) for item in changes},
                {(1, 2024, "value_changed"), (1, 2025, "new_value")},
            )

    def test_rejects_incomplete_current_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / "base"
            current = pathlib.Path(temp) / "current"
            self.write_snapshot(base, "base-run", [100, None])
            self.write_snapshot(current, "current-run", [125, 8], complete=False)

            with self.assertRaisesRegex(ValueError, "not complete"):
                compare_runs(base, current)

    def test_rejects_missing_species_dataset_even_if_manifest_says_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / "snapshot"
            self.write_snapshot(root, "run", [100, None])
            raw = root / "raw" / "statistics" / "national-batch-001.json"
            payload = json.loads(raw.read_text(encoding="utf-8"))
            payload["dataSets"].pop()
            raw.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Missing species datasets"):
                extract_observations(root)

    def test_rejects_different_observation_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            base = pathlib.Path(temp) / "base"
            current = pathlib.Path(temp) / "current"
            self.write_snapshot(base, "base-run", [100, None])
            self.write_snapshot(current, "current-run", [100, None])
            raw = current / "raw" / "statistics" / "national-batch-001.json"
            payload = json.loads(raw.read_text(encoding="utf-8"))
            payload["labels"] = ["2024"]
            for dataset in payload["dataSets"]:
                dataset["data"] = dataset["data"][:1]
            raw.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "coverage differs"):
                compare_runs(base, current)


if __name__ == "__main__":
    unittest.main()
