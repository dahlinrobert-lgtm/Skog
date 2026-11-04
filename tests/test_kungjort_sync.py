import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.sync_kungjort_api as sync


class FakeApi:
    def __init__(self, pages, details=None):
        self.pages = list(pages)
        self.details = details or {}
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/documents":
            return self.pages.pop(0), "req-list"
        if path.startswith("/documents/"):
            key = path.rsplit("/", 1)[-1]
            return self.details.get(key, {"id": key, "full_text": "sample"}), "req-detail"
        if path == "/changes":
            return self.pages.pop(0), "req-changes"
        raise AssertionError(path)


class KungjortSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "data" / "kungjort"
        self.state_path = self.root / "state.json"
        self.root.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bootstrap_saves_initial_changes_cursor_and_resumes(self):
        pages = [
            {"documents": [{"id": "a"}], "next_cursor": "page-2", "changes_cursor": "change-start"},
            {"documents": [{"id": "b"}], "next_cursor": None},
        ]
        api = FakeApi(pages)
        state = {"schema_version": 1, "bootstrap_complete": False,
                 "bootstrap_cursor": None, "changes_cursor": None}
        with patch.object(sync, "ROOT", self.root), patch.object(sync, "STATE_PATH", self.state_path):
            sync.bootstrap(api, state, 1)
            saved = json.loads(self.state_path.read_text())
            self.assertEqual(saved["changes_cursor"], "change-start")
            self.assertEqual(saved["bootstrap_cursor"], "page-2")
            sync.bootstrap(api, saved, 1)
            saved = json.loads(self.state_path.read_text())
            self.assertTrue(saved["bootstrap_complete"])
            files = sorted((self.root / "bootstrap").glob("*.jsonl.gz"))
            self.assertEqual(len(files), 2)
            self.assertTrue(all(path.stat().st_size > 0 for path in files))
            rows = []
            for file in files:
                with gzip.open(file, "rt", encoding="utf-8") as stream:
                    rows.extend(json.loads(line) for line in stream)
            self.assertEqual([r["document_id"] for r in rows], ["a", "b"])

    def test_bootstrap_refuses_missing_initial_changes_cursor(self):
        api = FakeApi([{"documents": [], "next_cursor": None}])
        state = {"schema_version": 1, "bootstrap_complete": False,
                 "bootstrap_cursor": None, "changes_cursor": None}
        with patch.object(sync, "ROOT", self.root), patch.object(sync, "STATE_PATH", self.state_path):
            with self.assertRaisesRegex(RuntimeError, "changes_cursor"):
                sync.bootstrap(api, state, 1)

    def test_changes_persists_upserts_and_tombstones(self):
        state = {"schema_version": 1, "bootstrap_complete": True,
                 "bootstrap_cursor": None, "changes_cursor": "c1"}
        api = FakeApi([{
            "changes": [
                {"operation": "upsert", "document_id": "a"},
                {"operation": "delete", "document_id": "b"},
            ],
            "next_cursor": "c2",
        }], details={"a": {"id": "a", "revision": 2}})
        with patch.object(sync, "ROOT", self.root), patch.object(sync, "STATE_PATH", self.state_path):
            sync.sync_changes(api, state, 1)
            saved = json.loads(self.state_path.read_text())
            self.assertEqual(saved["changes_cursor"], "c2")
            files = list((self.root / "changes").glob("*.jsonl.gz"))
            with gzip.open(files[0], "rt", encoding="utf-8") as stream:
                rows = [json.loads(line) for line in stream]
            self.assertEqual([r["record_type"] for r in rows], ["document", "tombstone"])

    def test_changes_blocked_until_bootstrap_complete(self):
        state = {"schema_version": 1, "bootstrap_complete": False, "changes_cursor": "c1"}
        with self.assertRaisesRegex(RuntimeError, "bootstrap"):
            sync.sync_changes(FakeApi([]), state, 1)


if __name__ == "__main__":
    unittest.main()
