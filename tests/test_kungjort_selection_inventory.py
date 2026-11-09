import gzip
import json
import unittest
from unittest.mock import MagicMock

from scripts.kungjort_selection_inventory import (
    _detail_has_case_reference,
    _document_id,
    _metadata,
    build_inventory,
    encode_jsonl_gzip,
    read_jsonl_gzip,
)


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

    def test_build_inventory_deduplicates_and_uses_reclassified_metadata(self):
        service = MagicMock()
        service.get_container_client.return_value.list_blobs.side_effect = [
            [MagicMock(name="ignored")],
        ]
        # Supply concrete blob names; list_blobs items expose .name.
        blob_item = MagicMock()
        blob_item.name = "kungjort/index/reclassified-v2/page.jsonl.gz"
        service.get_container_client.return_value.list_blobs.return_value = [blob_item]
        payload = encode_jsonl_gzip([
            {
                "record_type": "document_index",
                "document_id": "doc-1",
                "metadata": {"title": "Samråd om detaljplan"},
            },
            {
                "record_type": "document_index",
                "document_id": "doc-2",
                "metadata": {"title": "Samråd om vägplan"},
            },
        ])
        service.get_blob_client.return_value.download_blob.return_value.readall.return_value = payload

        # Remaining three sources have no blobs.
        empty_container = MagicMock()
        empty_container.list_blobs.return_value = []
        service.get_container_client.side_effect = [
            MagicMock(list_blobs=MagicMock(return_value=[blob_item])),
            empty_container,
            empty_container,
            empty_container,
        ]
        result, aggregate = build_inventory(service, 20, "20261109T000000Z")
        self.assertEqual(aggregate["unique_documents"], 2)
        self.assertEqual(aggregate["priority_counts"]["P1"], 1)
        self.assertEqual(aggregate["priority_counts"]["P3"], 1)
        self.assertEqual(len(result["records"]), 2)


if __name__ == "__main__":
    unittest.main()
