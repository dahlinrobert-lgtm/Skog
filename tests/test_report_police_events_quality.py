import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "report_police_events_quality.py"
SPEC = importlib.util.spec_from_file_location("report_police_events_quality", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PoliceEventsQualityReportTests(unittest.TestCase):
    def test_report_counts_dates_years_and_candidate_status_separately(self):
        events = [
            {"event_id": "1", "date": "2020-01-02", "type_original": "Trafikolycka"},
            {"event_id": "2", "date": "2026-02-03", "type_original": "Viltolycka"},
            {"event_id": "3", "date": "", "type_original": ""},
        ]
        candidates = [{"event_id": "2"}, {"event_id": "3"}]
        incidents = [
            {"occurrence_date": "2026-02-03", "extraction_method": "wildlife_text_line_v1", "confidence": "review", "species": "älg"},
            {"occurrence_date": "", "extraction_method": "explicit_count_v1", "confidence": "low", "species": ""},
        ]
        report = MODULE.build_report(events, candidates, incidents)
        self.assertEqual(report["archive"]["event_count"], 3)
        self.assertEqual(report["archive"]["unique_event_ids"], 3)
        self.assertEqual(report["archive"]["oldest_publication_date"], "2020-01-02")
        self.assertEqual(report["archive"]["newest_publication_date"], "2026-02-03")
        self.assertEqual(report["archive"]["missing_publication_date_count"], 1)
        self.assertEqual(report["archive"]["publication_year_counts"], {"2020": 1, "2026": 1})
        self.assertEqual(report["wildlife_text"]["broad_candidate_count"], 2)
        self.assertEqual(report["wildlife_text"]["individual_incident_candidate_count"], 2)
        self.assertEqual(report["wildlife_text"]["candidate_missing_occurrence_date_count"], 1)
        self.assertEqual(report["wildlife_text"]["confidence_counts"], {"low": 1, "review": 1})
        self.assertIn("not confirmed collisions", report["interpretation"])


if __name__ == "__main__":
    unittest.main()
