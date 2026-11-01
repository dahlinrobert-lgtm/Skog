import importlib.util
import unittest

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


if __name__ == "__main__":
    unittest.main()
