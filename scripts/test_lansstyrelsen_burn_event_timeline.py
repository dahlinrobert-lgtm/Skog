"""Tests for the auditable burn-event timeline."""
import unittest

from lansstyrelsen_burn_event_timeline import build_timeline, classify_text


class BurnEventTimelineTests(unittest.TestCase):
    def test_plan_is_not_classified_as_completed(self):
        result = classify_text("Bränningsplan inför naturvårdsbränning i reservatet")
        self.assertEqual(result["stage"], "planning_or_action_plan")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_application_is_not_proof_of_burn(self):
        result = classify_text("Anmälan om naturvårdsbränning")
        self.assertEqual(result["stage"], "application_notification_or_consultation")

    def test_explicit_completed_burn_is_completed(self):
        result = classify_text("Genomförd bränning i naturreservat")
        self.assertEqual(result["stage"], "completed_burn")
        self.assertEqual(result["confidence"], "high")

    def test_agreement_is_a_preparatory_step_not_a_completed_burn(self):
        result = classify_text("Avtal om naturvårdsbränning i Fågelmossen naturreservat/natura 2000 område, Motala kommun")
        self.assertEqual(result["stage"], "agreement_or_contract")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_species_exemption_before_burn_is_species_protection(self):
        result = classify_text("Ansökan om dispens från fridlysningsbestämmelserna - plocka varglav inför naturvårdsbränning i Drevfjällens naturreservat, Dalarnas län")
        self.assertEqual(result["stage"], "pre_burn_species_protection")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_aftercare_is_not_misclassified_as_completed_burn(self):
        result = classify_text("Avtal om efterbevakning av naturvårdsbränning")
        self.assertEqual(result["stage"], "post_burn_follow_up")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_cancelled_burn_is_not_classified_as_completed(self):
        result = classify_text("Naturvårdsbränningen ställs in på grund av olämpligt väder")
        self.assertEqual(result["stage"], "cancelled_or_postponed")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_site_preparation_is_separate_from_burn(self):
        result = classify_text("Byggnation av spång inför naturvårdsbränning i reservatet")
        self.assertEqual(result["stage"], "pre_burn_site_preparation")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_logistics_preparation_is_separate(self):
        result = classify_text("Beställning av distribution av samhällsinfo inför naturvårdsbränning 2026")
        self.assertEqual(result["stage"], "publicity_or_logistics_preparation")
        self.assertNotEqual(result["stage"], "completed_burn")

    def test_candidate_link_uses_place_overlap_but_does_not_link_sources(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om planerad naturvårdsbränning i Fågelmossen naturreservat, Motala kommun",
            "source_url": "https://example.test/diary",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"source_url": "https://example.test/layer", "features": [{
            "id": 9, "properties": {"OBJECTID": 9, "Namn": "Fågelmossen", "Typ": "T2.3 Controlled burning"},
            "geometry": {"type": "Polygon", "coordinates": []}
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 1)
        candidate = report["link_candidates"][0]
        self.assertEqual(candidate["status"], "candidate_for_manual_review")
        self.assertIn("fågelmossen", candidate["shared_place_tokens"])
        self.assertTrue(all(e["link_status"] == "unlinked" for e in report["events"]))

    def test_candidate_links_do_not_form_on_generic_burn_words_alone(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om naturvårdsbränning",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {"OBJECTID": 9, "Typ": "T2.3 Controlled burning"},
            "geometry": {"type": "Polygon", "coordinates": []}
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 0)

    def test_candidate_diagnostics_explain_evidence_and_ambiguity(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om planerad naturvårdsbränning i Fågelmossen naturreservat 2026",
            "source_url": "https://example.test/diary",
            "columns": {"Diarienummer": "123-2026"}
        }, "r2": {
            "record_key": "r2", "diary_number": "124-2026",
            "title": "Uppföljning vid Fågelmossen naturreservat 2026",
            "source_url": "https://example.test/diary2",
            "columns": {"Diarienummer": "124-2026"}
        }}}
        source = {"source_url": "https://example.test/layer", "features": [{
            "id": 9, "properties": {"OBJECTID": 9, "Namn": "Fågelmossen", "Åtgärdsår": 2026, "Typ": "T2.3 Controlled burning"},
            "geometry": {"type": "Polygon", "coordinates": []}
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 2)
        self.assertEqual(report["link_candidate_summary"]["by_ambiguity"], {
            "geometry_matches_multiple_diary_records": 2
        })
        for candidate in report["link_candidates"]:
            self.assertIn("Shared place token(s): fågelmossen", candidate["evidence_summary"])
            self.assertEqual(candidate["ambiguity"], "geometry_matches_multiple_diary_records")
            self.assertTrue(candidate["shared_years"])
        self.assertTrue(all(event["link_status"] == "unlinked" for event in report["events"]))

    def test_build_keeps_sources_separate_and_undated(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Handlingsplan för naturvårdsbränning",
            "source_url": "https://example.test/diary",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"source_url": "https://example.test/layer", "features": [{
            "id": 9, "properties": {"OBJECTID": 9, "Typ": "T2.3 Controlled burning"},
            "geometry": {"type": "Polygon", "coordinates": []}
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["event_count"], 2)
        self.assertEqual({e["source_type"] for e in report["events"]}, {"lansstyrelsen_diary", "lifetaiga_action_polygon"})
        self.assertTrue(all(e["event_date"] is None for e in report["events"]))
        self.assertTrue(all(e["link_status"] == "unlinked" for e in report["events"]))


if __name__ == "__main__":
    unittest.main()
