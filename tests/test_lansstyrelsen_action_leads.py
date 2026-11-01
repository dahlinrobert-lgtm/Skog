import importlib.util
import unittest

spec = importlib.util.spec_from_file_location(
    "action_leads", "scripts/classify_lansstyrelsen_action_leads.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def record(title, handlings=None):
    return {
        "case": {
            "diary": "Länsstyrelsen i Västerbottens län",
            "diary_number": "1234-2026",
            "title": title,
            "status": "Handläggning",
            "registered_date": "2026-10-01",
        },
        "handlings": handlings or [],
        "source_url": "https://diarium.lansstyrelsen.se/example",
    }

class ActionLeadTests(unittest.TestCase):
    def test_road_case_is_physical_work_lead(self):
        result = module.classify_case(record("Anmälan om byggande av skogsbilväg"))
        self.assertIn("A", result["categories"])
        self.assertIn("road_or_track", result["action_types"])
        self.assertEqual(result["evidence_level"], "title_and_handling_metadata_only")

    def test_culvert_case_is_water_lead(self):
        result = module.classify_case(record("Anmälan om att byta trumma i vattendrag"))
        self.assertIn("B", result["categories"])
        self.assertIn("culvert_or_crossing", result["action_types"])

    def test_ditch_cleaning_is_water_and_not_automatically_forest_road(self):
        result = module.classify_case(record("Dikesrensning i skogsmark"))
        self.assertEqual(result["categories"], ["B"])
        self.assertIn("drainage_or_ditch", result["action_types"])

    def test_road_with_culvert_can_be_both_a_and_b(self):
        result = module.classify_case(record(
            "Anläggning av skogsbilväg",
            [{"title": "Anmälan om trumma i vattendrag", "date": "2026-10-02"}],
        ))
        self.assertEqual(result["categories"], ["A", "B"])

    def test_complement_and_decision_are_separate_stages(self):
        result = module.classify_case(record(
            "Anmälan om vägbyggnad",
            [
                {"title": "Begäran om komplettering", "date": "2026-10-02"},
                {"title": "Beslut med försiktighetsmått", "date": "2026-10-10"},
            ],
        ))
        stages = {x["stage"] for x in result["administrative_stages"]}
        self.assertIn("request_for_complement", stages)
        self.assertIn("decision_or_conditions", stages)

    def test_keyword_does_not_assert_implementation(self):
        result = module.classify_case(record("Ansökan om våtmarksanläggning"))
        self.assertNotIn("implementation_or_inspection", {x["stage"] for x in result["administrative_stages"]})
        self.assertIn("does not establish", result["interpretation"])

    def test_nonmatching_case_is_ignored(self):
        result = module.classify_case(record("Allmän information om ett möte"))
        self.assertEqual(result["categories"], [])
        self.assertEqual(result["evidence"], [])

if __name__ == "__main__":
    unittest.main()
