import unittest

from scripts.kungjort_document_selection import classify_plan_scope, searchable_text


class KungjortDocumentSelectionTests(unittest.TestCase):
    def test_explicit_detailed_plan_is_core(self):
        result = classify_plan_scope({"metadata": {"title": "Samråd om detaljplan för centrum"}})
        self.assertEqual(result["selection_class"], "core_plan")
        self.assertTrue(result["include_in_core_plan_set"])
        self.assertIn("explicit_plan_term:detaljplan", result["reasons"])

    def test_plan_instrument_without_phase_is_core(self):
        result = classify_plan_scope({"doc_type": "Översiktsplan"})
        self.assertEqual(result["priority"], "P1")

    def test_generic_consultation_is_candidate_not_automatic_include(self):
        result = classify_plan_scope({"title": "Samråd om ny verksamhet"})
        self.assertEqual(result["selection_class"], "process_candidate")
        self.assertFalse(result["include_in_core_plan_set"])

    def test_adjacent_infrastructure_is_separate(self):
        result = classify_plan_scope({"title": "Järnvägsplan för ny sträckning"})
        self.assertEqual(result["selection_class"], "adjacent_geography")
        self.assertFalse(result["include_in_core_plan_set"])

    def test_adjacent_process_notice_stays_in_adjacent_track(self):
        result = classify_plan_scope({"title": "Samråd om järnvägsplan"})
        self.assertEqual(result["selection_class"], "adjacent_geography")

    def test_generic_word_plan_is_not_a_trigger(self):
        result = classify_plan_scope({"title": "Plan för sammanträdet"})
        self.assertEqual(result["selection_class"], "other")

    def test_opaque_ids_and_urls_are_not_searched(self):
        result = classify_plan_scope({
            "id": "detaljplan-123",
            "document_url": "https://example.test/detaljplan",
            "metadata": {"title": "Kommunstyrelsens protokoll"},
        })
        self.assertEqual(result["selection_class"], "other")

    def test_nested_section_heading_is_searched(self):
        result = classify_plan_scope({
            "detail": {"sections": [{"rubrik": "Antagande av detaljplan"}]}
        })
        self.assertEqual(result["selection_class"], "core_plan")

    def test_matching_is_case_and_accent_insensitive(self):
        result = classify_plan_scope({"title": "ÄNDRING AV DETALJPLAN"})
        self.assertEqual(result["selection_class"], "core_plan")

    def test_searchable_text_uses_allowlisted_fields_only(self):
        text = searchable_text({
            "metadata": {"title": "Samråd", "document_url": "detaljplan"},
            "random_field": "översiktsplan",
        })
        self.assertIn("samrad", text)
        self.assertNotIn("detaljplan", text)
        self.assertNotIn("oversiktsplan", text)


if __name__ == "__main__":
    unittest.main()
