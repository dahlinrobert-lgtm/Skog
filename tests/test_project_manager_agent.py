import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from project_manager_agent import build_report, collect_inventory

class FakeClient:
    def get_json(self, path):
        if path == "/repos/acme/skog":
            return {"full_name":"acme/skog","default_branch":"main","html_url":"https://github.com/acme/skog","private":True}
        if path.startswith("/repos/acme/skog/issues?"):
            return [
                {"number":1,"title":"Open task","state":"open","updated_at":"2026-11-18","html_url":"https://github.com/acme/skog/issues/1","labels":[{"name":"P1"}]},
                {"number":2,"title":"Closed task","state":"closed","updated_at":"2026-11-17","html_url":"https://github.com/acme/skog/issues/2","labels":[]},
                {"number":3,"title":"PR is not an issue","state":"open","pull_request":{"url":"x"},"labels":[]}]
        if path.startswith("/repos/acme/skog/pulls?"):
            return [{"number":9,"title":"Merged work","state":"closed","merged_at":"2026-11-18","updated_at":"2026-11-18","html_url":"https://github.com/acme/skog/pull/9","base":{"ref":"main"},"head":{"ref":"feature"}}]
        if path == "/repos/acme/skog/actions/workflows?per_page=100":
            return {"workflows":[{"id":7,"name":"CI","path":".github/workflows/ci.yml","state":"active"}]}
        if path == "/repos/acme/skog/actions/runs?per_page=50":
            return {"workflow_runs":[
                {"id":100,"name":"CI","workflow_id":7,"status":"completed","conclusion":"failure","updated_at":"2026-11-18","html_url":"https://github.com/acme/skog/actions/runs/100"},
                {"id":101,"name":"Success","workflow_id":7,"status":"completed","conclusion":"success"}]}
        if path.startswith("/repos/acme/skog/commits?"):
            return [{"sha":"abc","commit":{"message":"A commit\nbody","committer":{"date":"2026-11-18"}},"html_url":"https://github.com/acme/skog/commit/abc"}]
        raise AssertionError(path)
    def paged(self, endpoint, max_pages=3):
        return self.get_json(endpoint + "?per_page=100&page=1")
    def file_metadata(self, path):
        return {"path":path,"sha":"blob123","size":42,"exists":True}

class ProjectManagerAgentTests(unittest.TestCase):
    def test_inventory_separates_issues_and_prs(self):
        result=collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z")
        self.assertEqual([x["number"] for x in result["issues"]],[1,2])
        self.assertEqual([x["number"] for x in result["pull_requests"]],[9])
        self.assertEqual(result["repository"]["default_branch"],"main")
        self.assertEqual(len(result["documents"]),9)
    def test_report_flags_failed_runs_as_review_signal(self):
        report=build_report(collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z"))
        self.assertIn("Misslyckade/avbrutna senaste körningar: 1",report)
        self.assertIn("granskningssignal",report)
        self.assertIn("Open task",report)
        self.assertNotIn("PR is not an issue",report)
    def test_report_discloses_limits_and_no_llm(self):
        report=build_report(collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z"))
        self.assertIn("högst tre sidor",report)
        self.assertIn("Ingen språkmodell används",report)
    def test_inventory_does_not_export_issue_bodies(self):
        data=collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z")
        serialized=json.dumps(data)
        self.assertNotIn('"body"',serialized)
        self.assertNotIn("GITHUB_TOKEN",serialized)

if __name__ == "__main__": unittest.main()
