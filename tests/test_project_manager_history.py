import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from project_manager_history import (
    ExistingRunConflict,
    HistoryValidationError,
    build_manifest,
    check_append_only,
    restore_run_files,
)

REPOSITORY = "dahlinrobert-lgtm/Skog"
ARCHIVED_AT = "2026-11-19T05:00:00Z"


def fixture_inventory(issue_status="complete", pr_status="complete"):
    return {
        "generated_at": "2026-11-19T04:00:00Z",
        "repository": {"full_name": REPOSITORY},
        "collection_limits": {
            "issues": {"status": issue_status, "pages_fetched": 1, "items_fetched": 3,
                       "page_size": 100, "max_pages": 10, "truncated": issue_status == "truncated"},
            "pull_requests": {"status": pr_status, "pages_fetched": 1, "items_fetched": 2,
                              "page_size": 100, "max_pages": 10, "truncated": pr_status == "truncated"},
        },
    }


def manifest_for(inventory=None, report=b"# Synthetic report\n"):
    return build_manifest(
        json.dumps(inventory or fixture_inventory(), separators=(",", ":")).encode(),
        report,
        run_id="123456789",
        run_attempt=1,
        repository=REPOSITORY,
        source_branch="main",
        source_commit_sha="a" * 40,
        archived_at=ARCHIVED_AT,
    )


class ManifestTests(unittest.TestCase):
    def test_manifest_contains_exact_sha256_and_sizes(self):
        inventory = json.dumps(fixture_inventory(), separators=(",", ":")).encode()
        report = b"# Report\n"
        result = json.loads(build_manifest(
            inventory, report, run_id="123", run_attempt=1, repository=REPOSITORY,
            source_branch="main", source_commit_sha="b" * 40, archived_at=ARCHIVED_AT,
        ))
        self.assertEqual(result["files"]["inventory_json"]["sha256"], hashlib.sha256(inventory).hexdigest())
        self.assertEqual(result["files"]["report_md"]["sha256"], hashlib.sha256(report).hexdigest())
        self.assertEqual(result["files"]["inventory_json"]["size_bytes"], len(inventory))
        self.assertTrue(result["comparison_eligible"])

    def test_manifest_serialization_is_deterministic(self):
        first = manifest_for()
        second = manifest_for()
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))

    def test_truncated_issues_are_not_comparison_eligible(self):
        result = json.loads(manifest_for(fixture_inventory(issue_status="truncated")))
        self.assertFalse(result["comparison_eligible"])
        self.assertEqual(result["coverage"]["issues"]["status"], "truncated")

    def test_truncated_pull_requests_are_not_comparison_eligible(self):
        result = json.loads(manifest_for(fixture_inventory(pr_status="truncated")))
        self.assertFalse(result["comparison_eligible"])

    def test_missing_or_unknown_coverage_fails_closed(self):
        inventory = fixture_inventory()
        del inventory["collection_limits"]["issues"]
        with self.assertRaises(HistoryValidationError):
            manifest_for(inventory)
        inventory = fixture_inventory()
        inventory["collection_limits"]["issues"]["status"] = "unknown"
        with self.assertRaises(HistoryValidationError):
            manifest_for(inventory)

    def test_invalid_json_fails_closed(self):
        with self.assertRaises(HistoryValidationError):
            build_manifest(b"{bad", b"report", run_id="1", run_attempt=1,
                repository=REPOSITORY, source_branch="main",
                source_commit_sha="c" * 40, archived_at=ARCHIVED_AT)

    def test_repository_mismatch_fails_closed(self):
        inventory = fixture_inventory()
        inventory["repository"]["full_name"] = "someone/else"
        with self.assertRaises(HistoryValidationError):
            manifest_for(inventory)

    def test_invalid_run_metadata_fails_closed(self):
        with self.assertRaises(HistoryValidationError):
            build_manifest(b"{}", b"x", run_id="../bad", run_attempt=1,
                repository=REPOSITORY, source_branch="main",
                source_commit_sha="d" * 40, archived_at=ARCHIVED_AT)

    def test_naive_timestamp_fails_closed(self):
        inventory = fixture_inventory()
        inventory["generated_at"] = "2026-11-19T04:00:00"
        with self.assertRaises(HistoryValidationError):
            manifest_for(inventory)


class AppendOnlyTests(unittest.TestCase):
    def test_missing_run_directory_is_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(check_append_only(Path(tmp) / "new-run", {"manifest.json": b"{}"}))

    def test_identical_existing_run_is_idempotent_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            expected = {"inventory.json": b"{}", "report.md": b"report", "manifest.json": b"manifest"}
            for name, content in expected.items():
                (run_dir / name).write_bytes(content)
            self.assertFalse(check_append_only(run_dir, expected))

    def test_existing_run_with_different_bytes_is_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            (run_dir / "inventory.json").write_bytes(b"old")
            with self.assertRaises(ExistingRunConflict):
                check_append_only(run_dir, {"inventory.json": b"new"})

    def test_existing_run_with_missing_or_extra_files_is_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            (run_dir / "inventory.json").write_bytes(b"{}")
            with self.assertRaises(ExistingRunConflict):
                check_append_only(run_dir, {"inventory.json": b"{}", "report.md": b"x"})
            (run_dir / "report.md").write_bytes(b"x")
            (run_dir / "unexpected.txt").write_bytes(b"x")
            with self.assertRaises(ExistingRunConflict):
                check_append_only(run_dir, {"inventory.json": b"{}", "report.md": b"x"})


if __name__ == "__main__":
    unittest.main()
