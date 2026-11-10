import unittest

from scripts.kungjort_hierarchy_audit import build_hierarchy_audit
from scripts.kungjort_relationship_audit import encode_jsonl_gzip


class Item:
    def __init__(self, name): self.name = name


class Downloader:
    def __init__(self, payload): self.payload = payload
    def readall(self): return self.payload


class Blob:
    def __init__(self, payload): self.payload = payload
    def download_blob(self): return Downloader(self.payload)


class Container:
    def __init__(self, names): self.names = names
    def list_blobs(self, name_starts_with):
        return [Item(n) for n in self.names if n.startswith(name_starts_with)]


class Service:
    def __init__(self, blobs): self.blobs = blobs
    def get_container_client(self, container):
        return Container([name for (kind, name) in self.blobs if kind == container])
    def get_blob_client(self, container, blob):
        return Blob(self.blobs[(container, blob)])


class HierarchyAuditTests(unittest.TestCase):
    def test_builds_conservative_meeting_and_case_candidates(self):
        selection = "kungjort/selection/v2/test/document-selection.jsonl.gz"
        details = "bootstrap-live/test.jsonl.gz"
        identity = {
            "municipality": {"status": "resolved", "name": "Test kommun"},
            "committee": {"status": "resolved", "name": "Miljönämnden"},
            "administration": {"status": "unknown", "name": None},
        }
        blobs = {
            ("metadata", selection): encode_jsonl_gzip([
                {"document_id": "a", "organizational_identity": identity},
                {"document_id": "b", "organizational_identity": identity},
                {"document_id": "c", "organizational_identity": {
                    "municipality": {"status": "unknown", "name": None}}},
            ]),
            ("kungjort-raw", details): encode_jsonl_gzip([
                {"document_id": "a", "detail": {"organ": "Miljönämnden", "meeting_date": "2025-02-01",
                    "sections": [{"paragraf": "§ 2", "cases": [{"case_id": "case-1"}]}]}},
                {"document_id": "b", "detail": {"organ": "Miljönämnden", "meeting_date": "2025-02-01",
                    "sections": [{"paragraf": "§ 3", "cases": [{"case_id": "case-1"}]}]}},
                {"document_id": "c", "detail": {"organ": "Miljönämnden", "meeting_date": "2025-02-01",
                    "sections": [{"paragraf": "§ 4", "cases": [{"case_id": "case-1"}]}]}},
            ]),
        }
        rows, report = build_hierarchy_audit(Service(blobs), 20, "test", "audit")
        self.assertEqual(report["candidate_groups"]["meeting_groups"], 1)
        self.assertEqual(report["candidate_groups"]["documents_in_meeting_groups"], 2)
        self.assertEqual(report["candidate_groups"]["case_reference_groups"], 1)
        self.assertEqual(report["coverage"]["with_resolved_municipality"], 2)
        self.assertEqual(report["coverage"]["with_resolved_committee"], 2)
        self.assertEqual(report["coverage"]["with_paragraph"], 3)
        self.assertNotIn("case-1", str(report))
        self.assertNotIn("document_ids", report)
        self.assertEqual(sum(row["record_type"] == "kungjort_meeting_candidate_group" for row in rows), 1)

    def test_does_not_link_meetings_without_resolved_municipality(self):
        selection = "kungjort/selection/v2/test/document-selection.jsonl.gz"
        details = "bootstrap-live/test.jsonl.gz"
        blobs = {
            ("metadata", selection): encode_jsonl_gzip([
                {"document_id": "a"}, {"document_id": "b"}]),
            ("kungjort-raw", details): encode_jsonl_gzip([
                {"document_id": doc, "detail": {"organ": "Kommunstyrelsen",
                    "meeting_date": "2025-02-01"}} for doc in ("a", "b")]),
        }
        _, report = build_hierarchy_audit(Service(blobs), 20, "test", "audit")
        self.assertEqual(report["candidate_groups"]["meeting_groups"], 0)


if __name__ == "__main__":
    unittest.main()
