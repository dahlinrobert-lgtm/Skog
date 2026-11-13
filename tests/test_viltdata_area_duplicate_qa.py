import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from viltdata_area_duplicate_qa import inspect_run, normalize_title


class ViltdataAreaDuplicateQaTests(unittest.TestCase):
    def test_normalizes_unicode_whitespace_and_case(self):
        self.assertEqual(normalize_title("  KLOCKESTEN\u00a0 "), "klockesten")

    def test_flags_only_same_part_parent_and_normalized_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = pathlib.Path(tmp)
            areas_dir = run_dir / "raw" / "areas"
            areas_dir.mkdir(parents=True)

            (areas_dir / "26.json").write_text(json.dumps([
                {"id": 101, "parentId": 5244, "title": "Klockesten"},
                {"id": 102, "parentId": 5244, "title": "  KLOCKESTEN "},
                {"id": 103, "parentId": 9999, "title": "Klockesten"},
                {"id": 104, "parentId": None, "title": "Klockesten"},
            ]), encoding="utf-8")
            (areas_dir / "40.json").write_text(json.dumps([
                {"id": 105, "parentId": 5244, "title": "Klockesten"},
            ]), encoding="utf-8")

            report = inspect_run(run_dir)

            self.assertEqual(report["files_read"], 2)
            self.assertEqual(report["records_read"], 5)
            self.assertEqual(report["candidate_groups"], 1)
            self.assertEqual(report["candidates"][0]["part_id"], 26)
            self.assertEqual(report["candidates"][0]["parent_id"], 5244)
            self.assertEqual(report["candidates"][0]["area_ids"], [101, 102])
            self.assertFalse(report["raw_data_modified"])


if __name__ == "__main__":
    unittest.main()
