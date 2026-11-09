import unittest

from scripts.kungjort_schema_audit import safe_key, summarize_records


class KungjortSchemaAuditTests(unittest.TestCase):
    def test_summarizes_field_paths_and_types_without_values(self):
        report = summarize_records([
            {
                "record_type": "document",
                "document_id": "PRIVATE-ID-123",
                "detail": {
                    "title": "Secret title",
                    "published_at": "2026-01-02",
                    "active": True,
                    "tags": ["one", "two"],
                },
            },
            {
                "record_type": "document",
                "document_id": "ANOTHER-PRIVATE-ID",
                "detail": {"title": "Another secret", "active": False},
            },
        ], "test")
        self.assertEqual(report["records_reviewed"], 2)
        paths = {field["path"]: field for field in report["fields"]}
        self.assertEqual(paths["detail.title"]["observed_types"], {"string": 2})
        self.assertEqual(paths["detail.active"]["observed_types"], {"boolean": 2})
        self.assertIn("detail.tags[]", paths)
        serialized = str(report)
        self.assertNotIn("PRIVATE-ID", serialized)
        self.assertNotIn("Secret title", serialized)
        self.assertNotIn("Another secret", serialized)

    def test_dynamic_property_names_are_redacted(self):
        self.assertEqual(safe_key("normal_field_1"), "normal_field_1")
        self.assertEqual(safe_key("case/12345"), "<dynamic-key>")
        self.assertEqual(safe_key("x" * 100), "<dynamic-key>")


if __name__ == "__main__":
    unittest.main()
