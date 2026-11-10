import unittest

from scripts.kungjort_selection_inventory import (
    _detail_has_case_reference,
    _document_id,
    _metadata,
    build_inventory,
    encode_jsonl_gzip,
    resolve_organizational_identity,
    read_jsonl_gzip,
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
        return FakeContainer([
            name for (container_name, name) in self.blobs if container_name == container
        ])

    def get_blob_client(self, container, blob):
        return FakeBlobClient(self.blobs[(container, blob)])


class KungjortSelectionInventoryTests(unittest.TestCase):
    def test_jsonl_gzip_roundtrip(self):
        rows = [{"document_id": "A", "record_type": "document_index"}]
        self.assertEqual(read_jsonl_gzip(encode_jsonl_gzip(rows)), rows)

    def test_document_id_resolution(self):
        self.assertEqual(_document_id({"document_id": "x"}), "x")
        self.assertEqual(_document_id({"metadata": {"id": 12}}), "12")
        self.assertIsNone(_document_id({"title": "no identifier"}))

    def test_metadata_resolution_for_index_and_detail(self):
        self.assertEqual(
            _metadata({"metadata": {"title": "x"}}, "listing_metadata"),
            {"title": "x"},
        )
        self.assertEqual(
            _metadata({"list_record": {"title": "y"}}, "document_details"),
            {"title": "y"},
        )

    def test_case_reference_detection(self):
        self.assertTrue(_detail_has_case_reference({
            "sections": [{"cases": [{"dnr": "opaque"}]}]
        }))
        self.assertFalse(_detail_has_case_reference({"sections": [{"cases": []}]}))

    def test_build_inventory_deduplicates_and_prioritises_metadata(self):
        index_prefix = "kungjort/index/reclassified-v2/"
        raw_prefix = "bootstrap-live/"
        blobs = {
            ("metadata", index_prefix + "index.jsonl.gz"): encode_jsonl_gzip([
                {
                    "record_type": "document_index",
                    "document_id": "doc-1",
                    "metadata": {"title": "Samråd om detaljplan", "kommunkod": 2580},
                },
                {
                    "record_type": "document_index",
                    "document_id": "doc-2",
                    "metadata": {"title": "Samråd om vägplan"},
                },
            ]),
            ("kungjort-raw", raw_prefix + "details.jsonl.gz"): encode_jsonl_gzip([
                {
                    "record_type": "document",
                    "document_id": "doc-1",
                    "list_record": {"title": "A less specific title"},
                    "detail": {"sections": [{"cases": [{"dnr": "2026-123"}]}]},
                },
            ]),
        }
        result, aggregate = build_inventory(FakeService(blobs), 20, "test-run")
        self.assertEqual(aggregate["unique_documents"], 2)
        self.assertEqual(aggregate["duplicate_source_records"], 1)
        self.assertEqual(aggregate["priority_counts"]["P1"], 1)
        self.assertEqual(aggregate["priority_counts"]["P3"], 1)
        self.assertEqual(aggregate["documents_with_detail"], 1)
        self.assertEqual(aggregate["documents_with_case_reference_in_detail"], 1)
        self.assertEqual(aggregate["municipality_attribution"]["documents_with_municipality_code"], 1)
        self.assertEqual(aggregate["municipality_attribution"]["documents_without_municipality_evidence"], 1)
        self.assertEqual(aggregate["municipality_attribution"]["status_counts"]["resolved"], 1)
        self.assertFalse(any(aggregate["source_scan_truncated"].values()))
        doc1 = next(row for row in result["records"] if row["document_id"] == "doc-1")
        self.assertEqual(doc1["title"], "Samråd om detaljplan")
        self.assertTrue(doc1["has_case_reference_in_detail"])



    def test_resolves_authority_from_explicit_municipality_or_municipal_organ(self):
        from scripts.kungjort_selection_inventory import resolve_authority
        self.assertEqual(resolve_authority({"municipality": "Luleå"})["name"], "Luleå")
        result = resolve_authority({"organ": "Luleå kommun"})
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["name"], "Luleå")

    def test_resolves_municipality_code_and_id_without_name(self):
        from scripts.kungjort_selection_inventory import resolve_authority
        result = resolve_authority({"kommunkod": 2580, "kommun_id": "municipality-2580"})
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["municipality_code"], "2580")
        self.assertEqual(result["municipality_id"], "municipality-2580")
        self.assertIsNone(result["name"])

    def test_publication_organ_can_establish_municipality(self):
        from scripts.kungjort_selection_inventory import resolve_authority
        result = resolve_authority({"publication_organ": "Luleå kommun"})
        self.assertEqual(result["name"], "Luleå")

    def test_conflicting_authority_evidence_is_not_resolved(self):
        from scripts.kungjort_selection_inventory import resolve_authority
        result = resolve_authority({"municipality": "Luleå", "organ": "Umeå kommun"})
        self.assertEqual(result["status"], "conflict")
        self.assertIsNone(result["name"])

    def test_non_municipal_organ_is_not_treated_as_authority(self):
        from scripts.kungjort_selection_inventory import resolve_authority
        result = resolve_authority({"organ": "Länsstyrelsen"})
        self.assertEqual(result["status"], "unknown")


    def test_organizational_identity_keeps_committee_and_administration_separate(self):
        identity = resolve_organizational_identity({
            "municipality": "Luleå",
            "committee_name": "Miljö- och byggnadsnämnden",
            "administration_name": "Stadsbyggnadsförvaltningen",
            "organ": "Luleå kommun",
        })
        self.assertEqual(identity["municipality"]["name"], "Luleå")
        self.assertEqual(identity["committee"]["name"], "Miljö- och byggnadsnämnden")
        self.assertEqual(identity["administration"]["name"], "Stadsbyggnadsförvaltningen")
        self.assertEqual(identity["issuing_organ"]["status"], "resolved")

    def test_generic_organ_is_not_promoted_to_committee(self):
        identity = resolve_organizational_identity({"organ": "Luleå kommun"})
        self.assertEqual(identity["committee"]["status"], "unknown")
        self.assertEqual(identity["administration"]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
