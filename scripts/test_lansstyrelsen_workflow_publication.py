"""Regression tests for the Länsstyrelsen diary publication workflows."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DAILY = (ROOT / ".github/workflows/lansstyrelsen-diary-search.yml").read_text(encoding="utf-8")
MONTHLY = (ROOT / ".github/workflows/lansstyrelsen-monthly-snapshots.yml").read_text(encoding="utf-8")


class DiaryWorkflowPublicationTests(unittest.TestCase):
    def test_both_writers_use_the_same_serialized_pr_publication_branch(self):
        for workflow in (DAILY, MONTHLY):
            self.assertIn("pull-requests: write", workflow)
            self.assertIn("group: lansstyrelsen-diary-archive", workflow)
            self.assertIn("uses: peter-evans/create-pull-request@v7", workflow)
            self.assertIn("branch: automation/lansstyrelsen-diary-history", workflow)
            self.assertIn("pull_request:", workflow)
            self.assertNotIn("git push origin HEAD:main", workflow)

    def test_daily_writer_rebuilds_against_latest_main_before_pr(self):
        reset = DAILY.index("git reset --hard origin/main")
        persist = DAILY.index("python scripts/persist_lansstyrelsen_diary.py", reset)
        audit = DAILY.index("python scripts/audit_lansstyrelsen_diary_history.py", persist)
        create_pr = DAILY.index("uses: peter-evans/create-pull-request@v7")
        self.assertLess(reset, persist)
        self.assertLess(persist, audit)
        self.assertLess(audit, create_pr)
        self.assertIn("data/lansstyrelsen-diary/", DAILY)

    def test_monthly_writer_publishes_only_snapshots_and_manifest(self):
        self.assertIn("data/lansstyrelsen-diary/snapshots/", MONTHLY)
        self.assertIn("data/lansstyrelsen-diary/snapshot-runs.jsonl", MONTHLY)
        self.assertIn("if: success() && github.ref == 'refs/heads/main' && github.event_name != 'pull_request'", MONTHLY)

    def test_pull_request_validation_does_not_run_browser_collection(self):
        self.assertIn("if: github.event_name != 'pull_request'", DAILY)
        self.assertIn("if: github.event_name != 'pull_request'", MONTHLY)
        self.assertIn("if: github.event_name != 'pull_request'", MONTHLY)


if __name__ == "__main__":
    unittest.main()
