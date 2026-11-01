import importlib.util
import unittest

spec = importlib.util.spec_from_file_location("analysis", "scripts/analyze_lansstyrelsen_handlings.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)

class ClassificationTests(unittest.TestCase):
    def test_procurement_is_not_execution(self):
        result = analysis.classify_case({
            "case": {"diary_number": "1-2026", "title": "Upphandling av naturvårdsbränning"},
            "handlings": [{"handling_number": "1", "title": "Förfrågningsunderlag upphandling av naturvårdsbränning"}]
        })
        self.assertNotEqual(result["priority"], "strong_execution_lead")
        self.assertEqual(result["evidence_score"], 0)

    def test_bare_branningsprotokoll_is_not_execution(self):
        result = analysis.classify_case({
            "case": {"diary_number": "2-2026", "title": "Upphandling av naturvårdsbränningar"},
            "handlings": [{"handling_number": "1", "title": "Bilaga 24 Bränningsprotokoll"}]
        })
        self.assertNotEqual(result["priority"], "strong_execution_lead")
        self.assertTrue(any("inte verifierat" in x for x in result["reasons"]))

    def test_filled_protocol_is_strong_lead(self):
        result = analysis.classify_case({
            "case": {"diary_number": "3-2026", "title": "Naturvårdsbränning"},
            "handlings": [{"handling_number": "1", "title": "Ifyllt bränningsprotokoll"}]
        })
        self.assertEqual(result["priority"], "strong_execution_lead")

    def test_aftercare_is_follow_up_lead_not_proof(self):
        result = analysis.classify_case({
            "case": {"diary_number": "4-2026", "title": "Eftersläckning efter naturvårdsbränning"},
            "handlings": [{"handling_number": "1", "title": "Avropsförfrågan eftersläckning"}]
        })
        self.assertNotEqual(result["priority"], "strong_execution_lead")

if __name__ == "__main__":
    unittest.main()
