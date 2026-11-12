import importlib.util, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"match_police_nvr_temporal.py"
SPEC=importlib.util.spec_from_file_location("match_police_nvr_temporal",SCRIPT)
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class TemporalMatchTests(unittest.TestCase):
    def setUp(self):
        self.police=[{"parent_event_id":"p1","occurrence_date":"2026-08-31","occurrence_date_basis":"explicit_time_in_summary","occurrence_time":"00:13","municipality":"Luleå","species":"älg","description":"00.13 Viltolycka på länsväg 383, Smedsbyn"}]
        self.nvr=[{"accident_key":"2026-507","OlycksID":"507","event_datetime_values":"2026-08-31 00:18","source_municipalities":"Luleå","species":"Älg"}]
    def test_same_date_close_time_and_species_produce_candidate(self):
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["time_delta_minutes"],5.0)
        self.assertTrue(rows[0]["species_match"]);self.assertEqual(rows[0]["candidate_status"],"temporal_candidate_review")
        self.assertFalse(rows[0]["geographic_match_used"])
    def test_same_date_only_is_kept_as_weak_candidate(self):
        self.police[0]["occurrence_time"]=""
        self.nvr[0]["event_datetime_values"]="2026-08-31 23:50"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["time_band"],"same_date_time_unavailable")
        self.assertEqual(rows[0]["candidate_status"],"date_only_weak_candidate")
        self.assertEqual(rows[0]["time_delta_minutes"],"")
    def test_wrong_date_does_not_match(self):
        self.nvr[0]["event_datetime_values"]="2026-09-01 00:18"
        self.assertEqual(M.build_candidates(self.police,self.nvr),[])
    def test_other_municipality_is_not_candidate(self):
        self.nvr[0]["source_municipalities"]="Boden"
        self.assertEqual(M.build_candidates(self.police,self.nvr),[])
    def test_time_conflict_remains_visible_but_flagged(self):
        self.nvr[0]["event_datetime_values"]="2026-08-31 12:00"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(rows[0]["candidate_status"],"same_date_time_conflict_review")

if __name__=="__main__":unittest.main()
