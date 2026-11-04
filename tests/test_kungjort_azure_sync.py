import gzip
import json
import unittest

from scripts.sync_kungjort_azure import canonical_hash, classify_document, cursor_key, encode_jsonl_gzip, initial_state


class AzureSyncHelperTests(unittest.TestCase):
    def test_cursor_key_is_stable_and_does_not_expose_cursor(self):
        self.assertEqual(cursor_key("opaque-cursor"), cursor_key("opaque-cursor"))
        self.assertNotIn("opaque-cursor", cursor_key("opaque-cursor"))
        self.assertNotEqual(cursor_key(None), cursor_key(""))

    def test_canonical_hash_ignores_dictionary_key_order(self):
        self.assertEqual(canonical_hash({"a": 1, "b": 2}), canonical_hash({"b": 2, "a": 1}))

    def test_jsonl_gzip_is_readable_and_deterministic(self):
        records = [{"record_type": "tombstone", "document_id": "x"}]
        first = encode_jsonl_gzip(records)
        second = encode_jsonl_gzip(records)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(gzip.decompress(first).decode().strip()), records[0])


    def test_high_priority_topics_are_classified(self):
        result = classify_document({
            "title": "Avverkning och naturvärdesinventering",
            "organ": "Samhällsbyggnadsnämnden",
            "doc_type": "Tjänsteskrivelse",
        })
        self.assertEqual(result["priority"], "high")
        self.assertIn("skog_och_skogsbruk", result["categories"])
        self.assertIn("naturvard_och_skydd", result["categories"])

    def test_medium_priority_topics_are_classified(self):
        result = classify_document({
            "title": "Ansökan om vindkraftspark och nätkoncession",
            "organ": "Kommunstyrelsen",
        })
        self.assertEqual(result["priority"], "medium")
        self.assertIn("energi_och_infrastruktur", result["categories"])

    def test_irrelevant_document_is_metadata_only(self):
        result = classify_document({
            "title": "Budgetuppföljning för skolan",
            "organ": "Barn- och utbildningsnämnden",
            "doc_type": "Protokoll",
        })
        self.assertEqual(result["priority"], "low")
        self.assertEqual(result["categories"], [])

    def test_initial_state_has_safe_defaults(self):
        state = initial_state()
        self.assertFalse(state["bootstrap_complete"])
        self.assertIsNone(state["bootstrap_cursor"])
        self.assertIsNone(state["changes_cursor"])
        self.assertEqual(state["storage_backend"], "azure-blob")


if __name__ == "__main__":
    unittest.main()
