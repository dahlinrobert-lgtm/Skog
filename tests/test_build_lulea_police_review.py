import importlib.util, unittest
from pathlib import Path
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_lulea_police_review.py"
SPEC = importlib.util.spec_from_file_location("build_lulea_police_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

class LuleaPoliceReviewTests(unittest.TestCase):
    def test_only_lulea_individual_candidates_are_exported(self):
        rows = [
            {"municipality":"Luleå","extraction_method":"wildlife_text_line_v1","parent_event_id":"1","occurrence_date":"2026-07-20","occurrence_time":"00:25","description":"Viltolycka på riksväg 97 vid Luleå"},
            {"municipality":"Luleå","extraction_method":"explicit_count_v1","parent_event_id":"1","description":"Två viltolyckor"},
            {"municipality":"Boden","extraction_method":"wildlife_text_line_v1","parent_event_id":"2","description":"Viltolycka vid Boden"}]
        candidates, report = MODULE.build_review(rows)
        self.assertEqual(len(candidates),1); self.assertEqual(candidates[0]["parent_event_id"],"1")
        self.assertEqual(candidates[0]["review_priority"],"time_and_date_available")
        self.assertEqual(candidates[0]["geographic_evidence_type"],"possible_road_reference")
        self.assertEqual(report["count_only_candidate_row_count"],1)
    def test_expanded_time_segment_method_is_included(self):
        rows = [
            {"municipality":"Luleå","extraction_method":"wildlife_time_segment_v2","parent_event_id":"summary-1","occurrence_index":"2","occurrence_date":"2026-11-10","occurrence_time":"03:10","description":"03:10 Viltolycka vid Måttsund"}
        ]
        candidates, report = MODULE.build_review(rows)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["occurrence_index"], "2")
        self.assertEqual(report["individual_text_candidate_count"], 1)

    def test_lansvag_reference_is_classified_as_road_reference(self):
        self.assertEqual(MODULE.classify_geography("Olycka på länsväg 383, Smedsbyn"), "possible_road_reference")
        self.assertEqual(MODULE.classify_geography("Olycka på länsväg 596 vid Sinksundet"), "possible_road_reference")
    def test_missing_time_is_retained_and_flagged(self):
        rows=[{"municipality":"Luleå","extraction_method":"wildlife_text_line_v1","parent_event_id":"3","description":"Viltolycka, Luleå"}]
        candidates, report=MODULE.build_review(rows)
        self.assertEqual(len(candidates),1); self.assertEqual(candidates[0]["review_priority"],"missing_occurrence_time")
        self.assertEqual(report["individual_with_occurrence_time_count"],0)
    def test_count_only_rows_are_not_individual_candidates(self):
        rows=[{"municipality":"Luleå","extraction_method":"explicit_count_v1","parent_event_id":"4","description":"Tre viltolyckor"}]
        candidates, report=MODULE.build_review(rows)
        self.assertEqual(candidates,[]); self.assertEqual(report["count_only_candidate_row_count"],1)

if __name__ == "__main__": unittest.main()
