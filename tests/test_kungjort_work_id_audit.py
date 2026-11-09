import unittest

from scripts.kungjort_work_id_audit import (
    build_audit,
    encode_jsonl_gzip,
    protocol_references,
    read_jsonl_gzip,
    work_id_matches,
)


class FakeItem:
    def __init__(self, name):
        self.name = name


class FakeContainer:
    def __init__(self, names):
        self.names = names

    def list_blobs(self, name_starts_with):
        return [FakeItem(n) for n in self.names if n.startswith(name_starts_with)]


class FakeDownloader:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


class FakeBlob:
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
        return FakeBlob(self.blobs[(container, blob)])


class WorkIdAuditTests(unittest.TestCase):
    def test_extracts_work_id_without_rewriting_identifier(self):
        self.assertEqual(work_id_matches("Hertsöfältet, KLF2023/1308"), ["KLF2023/1308"])
        self.assertEqual(work_id_matches("klf 2023 / 1308"), ["KLF2023/1308"])

    def test_does_not_match_numeric_suffix_alone(self):
        self.assertEqual(work_id_matches("1308 eller 2023/1308"), [])

    def test_does_not_treat_common_swedish_words_as_authority_prefixes(self):
        self.assertEqual(work_id_matches("planen eller 2023/1308"), [])

    def test_extracts_protocol_date_and_paragraph(self):
        refs = protocol_references("beslutat 2023-10-23 (§ 21)")
        self.assertEqual(refs[0]["decision_date"], "2023-10-23")
        self.assertEqual(refs[0]["protocol_paragraph"], "21")

    def test_gzip_roundtrip(self):
        rows = [{"document_id": "a"}]
        self.assertEqual(read_jsonl_gzip(encode_jsonl_gzip(rows)), rows)

    def test_builds_private_candidate_group_and_aggregate_only_report(self):
        selection_path = "kungjort/selection/v2/test/document-selection.jsonl.gz"
        detail_path = "bootstrap-live/batch.jsonl.gz"
        blobs = {
            ("metadata", selection_path): encode_jsonl_gzip([
                {"document_id": "a", "municipality": "Luleå", "organizational_identity": {"committee": {"status": "resolved", "name": "Samma nämnd"}}, "selection": {"priority": "P1"}},
                {"document_id": "b", "municipality": "Luleå", "selection": {"priority": "P1"}},
                {"document_id": "c", "municipality": "Umeå", "selection": {"priority": "P1"}},
            ]),
            ("kungjort-raw", detail_path): encode_jsonl_gzip([
                {"document_id": "a", "detail": {"sections": [{"rubrik": "Plan KLF2023/1308"}]}},
                {"document_id": "b", "detail": {"sections": [{"sammanfattning": "Beslut 2023-10-23 (§ 21), KLF2023/1308"}]}},
                {"document_id": "c", "detail": {"sections": [{"rubrik": "Plan KLF2023/1308"}]}},
            ]),
        }
        rows, report = build_audit(FakeService(blobs), 20, "test", "audit")
        groups = [r for r in rows if r["record_type"] == "kungjort_work_id_candidate_group"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["document_ids"], ["a", "b"])
        self.assertEqual(report["candidate_groups_same_committee_and_work_id"], 1)
        self.assertNotIn("KLF2023/1308", str(report))
        self.assertNotIn("document_ids", report)

    def test_missing_municipality_never_creates_candidate_group(self):
        selection_path = "kungjort/selection/v2/test/document-selection.jsonl.gz"
        detail_path = "bootstrap-live/batch.jsonl.gz"
        blobs = {
            ("metadata", selection_path): encode_jsonl_gzip([
                {"document_id": "a", "selection": {"priority": "P1"}},
                {"document_id": "b", "selection": {"priority": "P1"}},
            ]),
            ("kungjort-raw", detail_path): encode_jsonl_gzip([
                {"document_id": "a", "detail": {"rubrik": "KLF2023/1308"}},
                {"document_id": "b", "detail": {"rubrik": "KLF2023/1308"}},
            ]),
        }
        rows, report = build_audit(FakeService(blobs), 20, "test", "audit")
        groups = [r for r in rows if r["record_type"] == "kungjort_work_id_candidate_group"]
        self.assertEqual(groups, [])
        self.assertEqual(report["candidate_groups_same_committee_and_work_id"], 0)



    def test_groups_using_resolved_authority_when_explicit_municipality_field_is_missing(self):
        selection_path = "kungjort/selection/v2/test/document-selection.jsonl.gz"
        detail_path = "bootstrap-live/batch.jsonl.gz"
        blobs = {
            ("metadata", selection_path): encode_jsonl_gzip([
                {"document_id": "a", "organizational_identity": {"committee": {"status": "resolved", "name": "Samma nämnd"}}},
                {"document_id": "b", "authority_resolution": {"status": "resolved", "name": "Luleå", "method": "municipal_organ", "evidence": []}},
            ]),
            ("kungjort-raw", detail_path): encode_jsonl_gzip([
                {"document_id": "a", "detail": {"sections": [{"rubrik": "KLF2023/1308"}]}},
                {"document_id": "b", "detail": {"sections": [{"rubrik": "KLF2023/1308"}]}},
            ]),
        }
        rows, report = build_audit(FakeService(blobs), 20, "test", "audit")
        groups = [row for row in rows if row["record_type"] == "kungjort_work_id_candidate_group"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(report["documents_with_resolved_authority"], 2)

    def test_conflicting_authority_does_not_create_candidate_group(self):
        selection_path = "kungjort/selection/v2/test/document-selection.jsonl.gz"
        detail_path = "bootstrap-live/batch.jsonl.gz"
        blobs = {
            ("metadata", selection_path): encode_jsonl_gzip([
                {"document_id": "a", "organizational_identity": {"committee": {"status": "conflict", "name": None}}},
                {"document_id": "b", "authority_resolution": {"status": "conflict", "name": None}},
            ]),
            ("kungjort-raw", detail_path): encode_jsonl_gzip([
                {"document_id": "a", "detail": {"rubrik": "KLF2023/1308"}},
                {"document_id": "b", "detail": {"rubrik": "KLF2023/1308"}},
            ]),
        }
        rows, report = build_audit(FakeService(blobs), 20, "test", "audit")
        self.assertFalse(any(row["record_type"] == "kungjort_work_id_candidate_group" for row in rows))
        self.assertEqual(report["documents_with_conflicting_authority"], 2)


if __name__ == "__main__":
    unittest.main()
