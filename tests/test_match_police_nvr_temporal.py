import importlib.util, json, tempfile, unittest
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
        self.assertEqual(rows[0]["date_offset_days"],0)
    def test_next_day_same_clock_time_uses_full_elapsed_time(self):
        self.nvr[0]["event_datetime_values"]="2026-09-01 00:18"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["date_offset_days"],1)
        self.assertEqual(rows[0]["date_relation"],"nvr_next_day")
        self.assertEqual(rows[0]["time_delta_minutes"],1445.0)
        self.assertEqual(rows[0]["absolute_datetime_delta_minutes"],1445.0)
        self.assertEqual(rows[0]["clock_time_delta_minutes"],5.0)
        self.assertEqual(rows[0]["candidate_status"],"next_day_time_conflict_review")
    def test_midnight_crossing_uses_elapsed_not_wall_clock_delta(self):
        self.police[0]["occurrence_date"]="2026-09-09"
        self.police[0]["occurrence_time"]="22:48"
        self.nvr[0]["event_datetime_values"]="2026-09-10 03:27"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["time_delta_minutes"],279.0)
        self.assertEqual(rows[0]["absolute_datetime_delta_minutes"],279.0)
        self.assertEqual(rows[0]["clock_time_delta_minutes"],1161.0)
        self.assertEqual(rows[0]["candidate_status"],"next_day_time_conflict_review")
    def test_next_day_event_within_three_elapsed_hours_is_rollover_review(self):
        self.police[0]["occurrence_date"]="2026-09-09"
        self.police[0]["occurrence_time"]="23:30"
        self.nvr[0]["event_datetime_values"]="2026-09-10 00:45"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(rows[0]["time_delta_minutes"],75.0)
        self.assertEqual(rows[0]["candidate_status"],"next_day_rollover_review")
    def test_next_day_large_elapsed_conflict_remains_flagged(self):
        self.nvr[0]["event_datetime_values"]="2026-09-01 12:00"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(len(rows),1)
                self.assertEqual(rows[0]["candidate_status"],"next_day_time_conflict_review")
    def test_same_date_only_is_kept_as_weak_candidate(self):
        self.police[0]["occurrence_time"]=""
        self.police[0]["description"]="Viltolycka på länsväg 383, Smedsbyn"
        self.nvr[0]["event_datetime_values"]="2026-08-31 23:50"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["time_band"],"time_unavailable")
        self.assertEqual(rows[0]["candidate_status"],"date_only_weak_candidate")
        self.assertTrue(rows[0]["species_match"])
        self.assertEqual(rows[0]["time_delta_minutes"],"")
    def test_audit_report_is_valid_utf8_json_with_real_newline(self):
        report={"scope":"Luleå","candidate_pair_count":0}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"audit.json"
            M.write_audit_report(report,path)
            raw=path.read_bytes()
            self.assertTrue(raw.startswith(b"\\xef\\xbb\\xbf"))
            decoded=raw.decode("utf-8-sig")
            self.assertTrue(decoded.endswith("}\\n"))
            self.assertNotIn("\\\\n",decoded)
            self.assertEqual(json.loads(decoded),report)
    def test_wrong_date_beyond_window_does_not_match(self):
        self.nvr[0]["event_datetime_values"]="2026-09-02 00:18"
        self.assertEqual(M.build_candidates(self.police,self.nvr),[])
    def test_other_municipality_is_not_candidate(self):
        self.nvr[0]["source_municipalities"]="Boden"
        self.assertEqual(M.build_candidates(self.police,self.nvr),[])
    def test_time_conflict_remains_visible_but_flagged(self):
        self.nvr[0]["event_datetime_values"]="2026-08-31 12:00"
        rows=M.build_candidates(self.police,self.nvr)
        self.assertEqual(rows[0]["candidate_status"],"same_date_time_conflict_review")

if __name__=="__main__":unittest.main()
