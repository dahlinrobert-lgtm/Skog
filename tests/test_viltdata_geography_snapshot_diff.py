import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from viltdata_geography_snapshot_diff import compare_runs


def write_run(root, name, complete, counties, afos, parts, areas):
    run = root / name
    requests = []
    relationships = []
    def write(level, parent_id, rows, parent_level=None):
        rel = f"raw/{level}/{'root' if parent_id is None else parent_id}.json"
        path = run / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows), encoding="utf-8")
        requests.append({"level": level, "parent_id": parent_id, "file": rel, "status": "ok"})
        if parent_level:
            for row in rows:
                relationships.append({
                    "parent_level": parent_level, "parent_id": parent_id,
                    "child_level": level, "child_id": row["id"],
                })
    write("counties", None, counties)
    write("afos", 1, afos, "counties")
    write("parts", 10, parts, "afos")
    write("areas", 20, areas, "parts")
    (run / "manifest.json").write_text(json.dumps({
        "complete": complete, "requests": requests, "relationships": relationships
    }), encoding="utf-8")
    return run


class ViltdataGeographySnapshotDiffTests(unittest.TestCase):
    def test_detects_add_change_remove_and_parent_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            old = write_run(root, "old", True,
                [{"id": 1, "name": "County"}],
                [{"id": 10, "title": "AFO"}],
                [{"id": 20, "title": "Part"}],
                [{"id": 30, "parentId": 20, "title": "Old name"},
                 {"id": 31, "parentId": 20, "title": "Removed"}])
            new = write_run(root, "new", True,
                [{"id": 1, "name": "County"}],
                [{"id": 10, "title": "AFO renamed"}],
                [{"id": 20, "title": "Part"}],
                [{"id": 30, "parentId": 20, "title": "New name"},
                 {"id": 32, "parentId": 20, "title": "Added"}])
            result = compare_runs(old, new)
            self.assertEqual(result["counts"]["added"], 1)
            self.assertEqual(result["counts"]["removed"], 1)
            self.assertEqual(result["counts"]["changed"], 2)
            self.assertTrue(result["deletions_enabled"])

    def test_incomplete_snapshot_suppresses_removals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            old = write_run(root, "old", True,
                [{"id": 1, "name": "County"}], [], [], [])
            new = write_run(root, "new", False, [], [], [], [])
            result = compare_runs(old, new)
            self.assertEqual(result["counts"]["removed"], 0)
            self.assertEqual(result["counts"]["unconfirmed_missing"], 1)
            self.assertFalse(result["deletions_enabled"])


if __name__ == "__main__":
    unittest.main()
