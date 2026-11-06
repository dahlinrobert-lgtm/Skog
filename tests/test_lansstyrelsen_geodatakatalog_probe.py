import importlib.util
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "catalogue_probe", "scripts/probe_lansstyrelsen_geodatakatalog.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogueProbeTests(unittest.TestCase):
    def test_query_uses_public_catalogue_search_api(self):
        query = module.build_query("slåtter")
        self.assertEqual(query["size"], 100)
        self.assertEqual(
            query["query"]["bool"]["must"][0]["query_string"]["query"],
            '+anytext:"slåtter"',
        )
        self.assertEqual(
            query["query"]["bool"]["filter"][0]["term"]["isTemplate"]["value"],
            "n",
        )

    def test_search_terms_include_completed_action_phrases(self):
        self.assertIn("genomförda åtgärder", module.SEARCH_TERMS)
        self.assertIn("utförda åtgärder", module.SEARCH_TERMS)
        self.assertIn("åtgärdade träd", module.SEARCH_TERMS)

    def test_invalid_search_and_pagination_are_rejected(self):
        with self.assertRaises(ValueError):
            module.build_query(" ")
        with self.assertRaises(ValueError):
            module.build_query("slåtter", offset=-1)
        with self.assertRaises(ValueError):
            module.build_query("slåtter", size=201)

    def test_response_hits_support_both_total_formats(self):
        total, hits = module.response_hits({
            "hits": {"total": {"value": 12}, "hits": [{"_id": "a"}]}
        })
        self.assertEqual(total, 12)
        self.assertEqual(hits, [{"_id": "a"}])
        total, _ = module.response_hits({"hits": {"total": 7, "hits": []}})
        self.assertEqual(total, 7)

    def test_title_extraction_supports_localized_fields(self):
        self.assertEqual(module.hit_title({"resourceTitleObject": {"default": "Ängsskötsel"}}), "Ängsskötsel")
        self.assertEqual(module.hit_title({"title": "Naturvårdsåtgärder"}), "Naturvårdsåtgärder")
        self.assertIsNone(module.hit_title({}))

    def test_retry_wait_uses_retry_after_header(self):
        error = module.urllib.error.HTTPError(
            "https://example.test", 503, "Unavailable", {"Retry-After": "12"}, None
        )
        self.assertEqual(module._retry_wait(error, 1), 12)
        self.assertEqual(module._retry_wait(RuntimeError("temporary"), 2), 4)

    def test_failed_term_does_not_discard_other_results(self):
        good_payload = {"hits": {"total": 1, "hits": [
            {"_id": "record-1", "_source": {"title": "Utförd åtgärd"}}
        ]}}
        with patch.object(module, "SEARCH_TERMS", ("first term", "second term")):
            with patch.object(module, "request_json", side_effect=[
                RuntimeError("HTTP Error 502: Bad Gateway"), good_payload
            ]):
                result = module.run_probe(size=1, max_records_per_term=1, delay=0)
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["complete"])
        self.assertEqual(result["failed_terms"], ["first term"])
        self.assertEqual(result["unique_metadata_records"], 1)
        self.assertEqual(result["term_results"][0]["pages"], 0)
        self.assertIsNotNone(result["term_results"][0]["error"])
        self.assertTrue(result["term_results"][1]["complete"])


if __name__ == "__main__":
    unittest.main()
