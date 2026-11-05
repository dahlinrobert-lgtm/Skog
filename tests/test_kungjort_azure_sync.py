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

    def test_swedish_synonyms_match_without_diacritics(self):
        result = classify_document({
            "title": "Ansökan om avverkning, röjning och skogsföryngring",
        })
        self.assertEqual(result["priority"], "high")
        self.assertIn("skog_och_skogsbruk", result["categories"])
        self.assertIn("roejning", [term.replace("ö", "oe") for term in result["matched_terms"]])

    def test_environmental_and_land_use_synonyms(self):
        nature = classify_document({"title": "Dispens från strandskydd och biotopskydd"})
        land = classify_document({"title": "Fastighetsbildning och exploateringsavtal"})
        self.assertEqual(nature["priority"], "high")
        self.assertIn("naturvard_och_skydd", nature["categories"])
        self.assertEqual(land["priority"], "high")
        self.assertIn("mark_och_planering", land["categories"])

    def test_medium_synonyms_cover_water_and_energy(self):
        result = classify_document({
            "title": "Regionnät, transformatorstation och våtmarksrestaurering",
        })
        self.assertEqual(result["priority"], "medium")
        self.assertIn("energi_och_infrastruktur", result["categories"])
        self.assertIn("klimat_och_vatten", result["categories"])

    def test_irrelevant_document_is_metadata_only(self):
        result = classify_document({
            "title": "Budgetuppföljning för skolan",
            "organ": "Barn- och utbildningsnämnden",
            "doc_type": "Protokoll",
        })
        self.assertEqual(result["priority"], "low")
        self.assertEqual(result["categories"], [])

    def test_relevance_rule_version_is_current(self):
        result = classify_document({"title": "Avverkning"})
        self.assertEqual(result["rule_version"], "2026-11-05-v2")

    def test_initial_state_has_safe_defaults(self):
        state = initial_state()
        self.assertFalse(state["bootstrap_complete"])
        self.assertIsNone(state["bootstrap_cursor"])
        self.assertIsNone(state["changes_cursor"])
        self.assertEqual(state["storage_backend"], "azure-blob")


class BootstrapCheckpointTests(unittest.TestCase):
    def test_bootstrap_resume_without_cursor_can_start_initial_page(self):
        from scripts.sync_kungjort_azure import bootstrap
        class FakeArchive:
            def __init__(self): self.state_saves = 0; self.uploaded = []
            def upload_batch(self, container, name, payload, source_hash):
                self.uploaded.append(name); return True
            def exists_with_source_hash(self, container, name, source_hash): return False
            def save_state(self, state): self.state_saves += 1
        class FakeApi:
            def get(self, path, params=None):
                return ({"documents": [], "changes_cursor": "c0", "next_cursor": None}, "req")
        state = initial_state()
        archive = FakeArchive()
        result = bootstrap(FakeApi(), archive, state, 1)
        self.assertTrue(result["bootstrap_complete"])
        self.assertEqual(result["changes_cursor"], "c0")
        self.assertEqual(archive.state_saves, 1)

    def test_bootstrap_resume_with_cursor_requires_original_changes_cursor(self):
        from scripts.sync_kungjort_azure import bootstrap
        class FakeApi:
            def get(self, path, params=None): self.called = True
        api = FakeApi()
        state = initial_state()
        state["bootstrap_cursor"] = "resume-token"
        with self.assertRaisesRegex(RuntimeError, "without the original changes_cursor"):
            bootstrap(api, object(), state, 1)
        self.assertFalse(getattr(api, "called", False))


if __name__ == "__main__":
    unittest.main()
