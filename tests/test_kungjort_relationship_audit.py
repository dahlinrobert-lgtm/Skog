import unittest

from scripts.kungjort_relationship_audit import (
    build_reference_audit,
    encode_jsonl_gzip,
    extract_reference_values,
    normalize_reference,
    read_jsonl_gzip,
    _latest_selection_blob,
)


class FakeBlobItem:
    def __init__(self, name):
        self.name = name


class FakeContainer:
    def __init__(self, names):
        self.names = names

    def list_blobs(self, name_starts_with):
        return [FakeBlobItem(name) for name in self.names if name.startswith(name_starts_with)]


class FakeDownloader:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


class FakeBlobClient:
    def __init__(self, payload):
        self.payload = payload

    def download_blob(self):
        return FakeDownloader(self.payload)


class FakeService:
    def __init__(self, blobs):
        self.blobs = blobs

    def get_container_client(self, container):
        return FakeContainer([name for (kind, name) in self.blobs if kind == container])

    def get_blob_client(self, container, blob):
        return FakeBlobClient(self.blobs[(container, blob)])


class KungjortRelationshipAuditTests(unittest.TestCase):
    def test_gzip_roundtrip(self):
        rows = [{"document_id": "x"}]
        self.assertEqual(read_jsonl_gzip(encode_jsonl_gzip(rows)), rows)

    def test_normalize_reference_is_conservative(self):
        self.assertEqual(normalize_reference("  2026/Ä  12 "), "2026/ä 12")
        self.assertIsNone(normalize_reference("  "))

    def test_extracts_only_structured_reference_fields(self):
        values = extract_reference_values({
            "sections": [{
                "cases": [{
                    "case_id": "CASE-1",
                    "dnr": "2026/12",
                    "normalized_dnr": "2026-12",
                    "relation": "successor",
                }],
                "dnr": ["2026/12", "2026/13"],
                "decision_id": "DEC-1",
                "diarieplan_kod": "DP-1",
                "section_id": "SEC-1",
            }]
        })
        self.assertEqual(values["case_id"], {"case-1"})
        self.assertEqual(values["case_dnr"], {"2026/12"})
        self.assertEqual(values["normalized_dnr"], {"2026-12"})
        self.assertEqual(values["case_relation"], {"successor"})
        self.assertEqual(values["section_dnr"], {"2026/12", "2026/13"})
        self.assertEqual(values["decision_id"], {"dec-1"})

    def test_latest_selection_blob_resolves_run_id(self):
        service = FakeService({
            ("metadata", "kungjort/selection/v2/20261109T100000Z/document-selection.jsonl.gz"): b"",
            ("metadata", "kungjort/selection/v2/20261109T110000Z/document-selection.jsonl.gz"): b"",
        })
        run_id, name = _latest_selection_blob(service)
        self.assertEqual(run_id, "20261109T110000Z")
        self.assertTrue(name.endswith("document-selection.jsonl.gz"))

    def test_builds_priority_coverage_and_shared_reference_counts(self):
        run_id = "test-run"
        selection_name = f"kungjort/selection/v2/{run_id}/document-selection.jsonl.gz"
        detail_name = "bootstrap-live/batch.jsonl.gz"
        blobs = {
            ("metadata", selection_name): encode_jsonl_gzip([
                {"document_id": "a", "selection": {"priority": "P1", "selection_class": "core_plan"}},
                {"document_id": "b", "selection": {"priority": "P1", "selection_class": "core_plan"}},
                {"document_id": "c", "selection": {"priority": "P2", "selection_class": "process_candidate"}},
            ]),
            ("kungjort-raw", detail_name): encode_jsonl_gzip([
                {"document_id": "a", "detail": {"sections": [{"cases": [{"dnr": "2026/1"}]}]}},
                {"document_id": "b", "detail": {"sections": [{"cases": [{"dnr": "2026/1"}]}]}},
            ]),
        }
        records, report = build_reference_audit(FakeService(blobs), 20, run_id)
        self.assertEqual(report["coverage_by_priority"]["P1"]["documents"], 2)
        self.assertEqual(report["coverage_by_priority"]["P1"]["documents_with_any_reference"], 2)
        self.assertEqual(report["coverage_by_priority"]["P2"]["documents_with_any_reference"], 0)
        self.assertEqual(report["cross_document_reference_frequency"]["case_dnr"]["reference_values_shared_by_multiple_documents"], 1)
        self.assertEqual(len(records), 4)
        self.assertNotIn("document_id", report)
        groups = [row for row in records if row["record_type"] == "kungjort_relationship_candidate_group"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["reference_field"], "case_dnr")
        self.assertEqual(groups[0]["document_count"], 2)
        self.assertEqual(groups[0]["link_status"], "candidate_only")
        self.assertEqual(report["candidate_relationship_groups"]["total_groups"], 1)
        self.assertIn("diarieplan_kod", report["candidate_relationship_groups"]["excluded_weak_fields"])


if __name__ == "__main__":
    unittest.main()
