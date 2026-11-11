import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_police_wildlife_incidents.py"
SPEC = importlib.util.spec_from_file_location("extract_police_wildlife_incidents", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WildlifeExtractionTests(unittest.TestCase):
    def row(self, content):
        return {
            "event_id": "event-1",
            "date": "2026-11-10",
            "content": content,
            "description": "",
            "headline": "",
            "external_source_link": "https://example.invalid/event-1",
        }

    def test_publication_date_is_not_assumed_to_be_occurrence_date(self):
        rows = MODULE.extract(self.row("Kl. 07:15: En viltolycka inträffade vid Luleå."))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["publication_date"], "2026-11-10")
        self.assertEqual(rows[0]["occurrence_date"], "2026-11-10")
        self.assertEqual(rows[0]["occurrence_time"], "07:15")

    def test_explicit_count_is_kept_as_low_confidence_candidates(self):
        rows = MODULE.extract(self.row("Två viltolyckor har rapporterats."))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["confidence"] == "low" for row in rows if row["extraction_method"] == "explicit_count_v1"))
        self.assertTrue(all(row["extraction_method"] == "explicit_count_v1" for row in rows if row["confidence"] == "low"))
        self.assertTrue(all(row["extraction_method"] == "explicit_count_v1" for row in rows if row["confidence"] == "low"))
        self.assertTrue(any(row["extraction_method"] == "explicit_count_v1" for row in rows))
        self.assertTrue(all(row["occurrence_date"] == "" for row in rows))


    def test_night_summary_assigns_after_midnight_to_publication_date(self):
        row = self.row("00:35 Viltolycka, Luleå: En ren har blivit påkörd.")
        row["date"] = "2021-05-13"
        row["type_original"] = "Sammanfattning natt"
        row["is_summary"] = "true"
        rows = MODULE.extract(row)
        self.assertEqual(rows[0]["occurrence_date"], "2021-05-13")
        self.assertEqual(rows[0]["occurrence_date_basis"], "night_summary_after_midnight")

    def test_night_summary_assigns_late_evening_to_previous_date(self):
        row = self.row("22:45 Viltolycka, Boden: En älg har blivit påkörd.")
        row["date"] = "2021-05-13"
        row["type_original"] = "Sammanfattning natt"
        row["is_summary"] = "true"
        rows = MODULE.extract(row)
        self.assertEqual(rows[0]["occurrence_date"], "2021-05-12")
        self.assertEqual(rows[0]["occurrence_date_basis"], "night_summary_previous_evening")

    def test_source_event_id_is_preserved(self):
        rows = MODULE.extract(self.row("En älgolycka rapporterades vid Boden."))
        self.assertTrue(rows)
        self.assertTrue(all(row["parent_event_id"] == "event-1" for row in rows))


if __name__ == "__main__":
    unittest.main()
