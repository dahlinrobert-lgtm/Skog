import importlib.util, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"match_police_nvr_temporal.py"
SPEC=importlib.util.spec_from_file_location("match_police_nvr_temporal",SCRIPT)
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class MatchAuditReportTests(unittest.TestCase):
    def test_audit_report_counts_zero_one_and_multiple_candidates(self):
        police = [
            {"parent_event_id":"p1","occurrence_index":"1","occurrence_date":"2026-08-31"},
            {"parent_event_id":"p2","occurrence_index":"1","occurrence_date":"2026-08-31"},
            {"parent_event_id":"p3","occurrence_index":"1","occurrence_date":""},
        ]
        nvr = [
            {"accident_key":"2026-501"},
            {"accident_key":"2026-502"},
            {"accident_key":"2026-503"},
        ]
        candidates = [
            {"police_candidate_id":"p1:1","nvr_accident_key":"2026-501","candidate_status":"temporal_candidate_review"},
            {"police_candidate_id":"p1:1","nvr_accident_key":"2026-502","candidate_status":"date_only_weak_candidate"},
            {"police_candidate_id":"p2:1","nvr_accident_key":"2026-502","candidate_status":"temporal_candidate_review"},
        ]
        report = M.build_audit_report(police, nvr, candidates)
        self.assertEqual(report["police_candidate_distribution"], {"zero_candidates":1,"one_candidate":1,"multiple_candidates":1})
        self.assertEqual(report["nvr_event_candidate_distribution"], {"zero_candidates":1,"one_candidate":1,"multiple_candidates":1})
        self.assertEqual(report["police_statements_without_valid_occurrence_date"],1)
        self.assertEqual(report["candidate_pair_count"],3)

if __name__=="__main__":unittest.main()
