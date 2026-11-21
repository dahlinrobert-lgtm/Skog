import unittest

from scripts.kungjort_organization_value_audit import (
    build_private_audit,
    classify_organization,
    normalize_organization,
)


class KungjortOrganizationValueAuditTests(unittest.TestCase):
    def test_normalization_is_case_and_accent_insensitive(self):
        self.assertEqual(normalize_organization("  MILJÖ- OCH BYGGNÄMNDEN "), "miljo och byggnamnden")

    def test_classification_is_conservative_and_separates_entity_types(self):
        self.assertEqual(classify_organization("Miljö- och byggnadsnämnden"), "committee_or_board_candidate")
        self.assertEqual(classify_organization("Kommunstyrelsen"), "committee_or_board_candidate")
        self.assertEqual(classify_organization("Stadsbyggnadsförvaltningen"), "administration_candidate")
        self.assertEqual(classify_organization("Kommunfullmäktige"), "municipal_assembly_candidate")
        self.assertEqual(classify_organization("Luleå kommun"), "municipality_level_publisher")
        self.assertEqual(classify_organization("Länsstyrelsen i Västerbotten"), "other_public_authority")
        self.assertEqual(classify_organization("Okänt organ"), "unclassified_organ")

    def test_private_audit_groups_values_but_aggregate_never_exposes_them(self):
        records = [
            {
                "document_id": "private-doc-1",
                "has_detail_record": True,
                "organizational_identity": {
                    "issuing_organ": {
                        "evidence": [{"source": "organ", "value": "Miljö- och byggnadsnämnden"}]
                    }
                },
            },
            {
                "document_id": "private-doc-2",
                "has_detail_record": False,
                "organizational_identity": {
                    "issuing_organ": {
                        "evidence": [{"source": "organ", "value": "Miljö- och byggnadsnämnden"}]
                    }
                },
            },
        ]
        rows, aggregate = build_private_audit(records, "test-run")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["document_count"], 2)
        self.assertIn("Miljö- och byggnadsnämnden", rows[0]["source_value"])
        self.assertEqual(aggregate["unique_organ_values_by_category"]["committee_or_board_candidate"], 1)
        self.assertNotIn("Miljö- och byggnadsnämnden", str(aggregate))
        self.assertNotIn("private-doc-1", str(aggregate))
        self.assertNotIn(rows[0]["normalized_value_sha256"], str(aggregate))
        self.assertEqual(aggregate["documents_with_detail"], 1)
        self.assertEqual(aggregate["documents_without_detail"], 1)

    def test_only_approved_organization_source_fields_are_included(self):
        records = [{
            "document_id": "doc",
            "organizational_identity": {
                "issuing_organ": {
                    "evidence": [
                        {"source": "organ_name", "value": "Luleå kommun"},
                        {"source": "sender", "value": "Should not be included"},
                        {"source": "title", "value": "Not an organ"},
                    ]
                }
            },
        }]
        rows, aggregate = build_private_audit(records, "test-run")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_field"], "organ_name")
        self.assertNotIn("Should not be included", str(rows))

    def test_duplicate_source_evidence_is_counted_once_per_document_category(self):
        records = [{
            "document_id": "doc",
            "organizational_identity": {
                "issuing_organ": {
                    "evidence": [
                        {"source": "organ", "value": "Kommunstyrelsen"},
                        {"source": "organ", "value": "Kommunstyrelsen"},
                    ]
                }
            },
        }]
        rows, aggregate = build_private_audit(records, "test-run")
        self.assertEqual(rows[0]["document_count"], 1)
        self.assertEqual(aggregate["documents_with_organ_value_by_category"]["committee_or_board_candidate"], 1)

    def test_empty_normalized_values_are_ignored(self):
        rows, aggregate = build_private_audit([{
            "document_id": "doc",
            "organizational_identity": {
                "issuing_organ": {"evidence": [{"source": "organ", "value": "!!!"}]}
            },
        }], "test-run")
        self.assertEqual(rows, [])
        self.assertEqual(aggregate["unique_organ_value_groups"], 0)


if __name__ == "__main__":
    unittest.main()
