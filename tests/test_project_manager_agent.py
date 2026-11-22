import json, sys, unittest
from pathlib import Path
from email.message import Message
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from project_manager_agent import GitHubAPIError, GitHubClient, build_report, collect_inventory

class FakeResponse:
    def __init__(self, payload, link=""):
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = Message()
        if link: self.headers["Link"] = link
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.payload

class PaginationTests(unittest.TestCase):
    def client_for(self, pages):
        calls = []
        def opener(req, timeout=30):
            calls.append(req.full_url)
            page = int(req.full_url.rsplit("page=", 1)[1])
            payload, link = pages[page-1]
            return FakeResponse(payload, link)
        return GitHubClient("token", "acme/skog", opener=opener), calls

    def test_zero_pages_is_complete_empty_list(self):
        client, calls = self.client_for([([], "")])
        rows, coverage = client.paged_with_coverage("/items")
        self.assertEqual(rows, [])
        self.assertEqual(coverage["status"], "complete")
        self.assertEqual(coverage["pages_fetched"], 1)
        self.assertFalse(coverage["truncated"])
        self.assertEqual(len(calls), 1)

    def test_one_page_is_complete(self):
        client, _ = self.client_for([([{"id": 1}], "")])
        rows, coverage = client.paged_with_coverage("/items")
        self.assertEqual([x["id"] for x in rows], [1])
        self.assertEqual(coverage["status"], "complete")
        self.assertEqual(coverage["items_fetched"], 1)

    def test_multiple_pages_follow_link_header_until_last_page(self):
        client, calls = self.client_for([
            ([{"id": 1}], '<https://api.github.com/items?page=2>; rel="next"'),
            ([{"id": 2}], '<https://api.github.com/items?page=3>; rel="next"'),
            ([{"id": 3}], '<https://api.github.com/items?page=3>; rel="last"'),
        ])
        rows, coverage = client.paged_with_coverage("/items")
        self.assertEqual([x["id"] for x in rows], [1, 2, 3])
        self.assertEqual(coverage["pages_fetched"], 3)
        self.assertEqual(coverage["status"], "complete")
        self.assertFalse(coverage["next_page_available"])
        self.assertEqual(len(calls), 3)

    def test_exact_safety_cap_with_next_page_is_truncated(self):
        next_link = '<https://api.github.com/items?page=3>; rel="next"'
        client, calls = self.client_for([([{"id": 1}], next_link), ([{"id": 2}], next_link)])
        rows, coverage = client.paged_with_coverage("/items", max_pages=2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(coverage["status"], "truncated")
        self.assertTrue(coverage["truncated"])
        self.assertEqual(coverage["max_items"], 200)
        self.assertEqual(len(calls), 2)

    def test_non_list_response_fails_closed(self):
        client, _ = self.client_for([({"message": "bad"}, "")])
        with self.assertRaises(GitHubAPIError):
            client.paged_with_coverage("/items")

class FakeClient:
    repository = "acme/skog"
    def get_json(self, path):
        if path == "/repos/acme/skog":
            return {"full_name":"acme/skog","default_branch":"main","html_url":"https://github.com/acme/skog","private":True}
        if path == "/repos/acme/skog/actions/workflows?per_page=100":
            return {"workflows":[{"id":7,"name":"CI","path":".github/workflows/ci.yml","state":"active"}]}
        if path == "/repos/acme/skog/actions/runs?per_page=50":
            return {"workflow_runs":[
                {"id":100,"name":"CI","workflow_id":7,"status":"completed","conclusion":"failure","updated_at":"2026-11-18","html_url":"https://github.com/acme/skog/actions/runs/100"},
                {"id":101,"name":"Success","workflow_id":7,"status":"completed","conclusion":"success"}]}
        raise AssertionError(path)
    def paged_with_coverage(self, endpoint, max_pages=10):
        if "/issues?" in endpoint:
            return ([
                {"number":1,"title":"Open task","state":"open","updated_at":"2026-11-18","html_url":"https://github.com/acme/skog/issues/1","labels":[{"name":"P1"}]},
                {"number":2,"title":"Closed task","state":"closed","updated_at":"2026-11-17","html_url":"https://github.com/acme/skog/issues/2","labels":[]},
                {"number":3,"title":"PR is not an issue","state":"open","pull_request":{"url":"x"},"labels":[]}],
                {"status":"complete","pages_fetched":1,"items_fetched":3,"page_size":100,"max_pages":10,"max_items":1000,"truncated":False})
        if "/pulls?" in endpoint:
            return [{"number":9,"title":"Merged work","state":"closed","merged_at":"2026-11-18","updated_at":"2026-11-18","html_url":"https://github.com/acme/skog/pull/9","base":{"ref":"main"},"head":{"ref":"feature"}}], \
                {"status":"complete","pages_fetched":1,"items_fetched":1,"page_size":100,"max_pages":10,"max_items":1000,"truncated":False}
        if "/commits" in endpoint:
            return [{"sha":"abc","commit":{"message":"A commit\\nbody","committer":{"date":"2026-11-18"}},"html_url":"https://github.com/acme/skog/commit/abc"}], {}
        raise AssertionError(endpoint)
    def paged(self, endpoint, max_pages=3):
        return self.paged_with_coverage(endpoint, max_pages)[0]
    def file_metadata(self, path):
        return {"path":path,"sha":"blob123","size":42,"exists":True}

class ProjectManagerAgentTests(unittest.TestCase):
    def test_inventory_separates_issues_and_prs_and_records_coverage(self):
        result=collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z")
        self.assertEqual([x["number"] for x in result["issues"]],[1,2])
        self.assertEqual([x["number"] for x in result["pull_requests"]],[9])
        self.assertEqual(result["repository"]["default_branch"],"main")
        self.assertEqual(len(result["documents"]),9)
        self.assertEqual(result["schema_version"],2)
        self.assertEqual(result["collection_limits"]["issues"]["status"],"complete")
    def test_report_flags_failed_runs_as_review_signal(self):
        report=build_report(collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z"))
        self.assertIn("Misslyckade/avbrutna senaste körningar: 1",report)
        self.assertIn("granskningssignal",report)
        self.assertIn("Open task",report)
        self.assertNotIn("PR is not an issue",report)
    def test_report_discloses_coverage_limits_and_no_llm(self):
        data=collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z")
        report=build_report(data)
        self.assertIn("Täckning och fullständighet",report)
        self.assertIn("Link-pagination",report)
        self.assertIn("Ingen språkmodell används",report)
    def test_truncated_inventory_is_explicit_in_report(self):
        data=collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z")
        data["collection_limits"]["issues"].update(status="truncated",truncated=True)
        report=build_report(data)
        self.assertIn("trunkerat",report)
        self.assertIn("frånvarobaserade slutsatser",report)
    def test_report_requires_architecture_reuse_review_before_new_solution(self):
        report=build_report(collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z"))
        self.assertIn("Arkitekturpassning", report)
        self.assertIn("återanvänd", report)
        self.assertIn("ny parallell lösning", report)
        self.assertIn("utför inte självständig arkitekturgranskning", report)

    def test_inventory_does_not_export_issue_bodies_or_token(self):
        data=collect_inventory(FakeClient(),generated_at="2026-11-18T12:00:00Z")
        serialized=json.dumps(data)
        self.assertNotIn('"body"',serialized)
        self.assertNotIn("GITHUB_TOKEN",serialized)

if __name__ == "__main__": unittest.main()
