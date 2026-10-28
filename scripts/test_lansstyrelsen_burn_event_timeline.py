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
        self.assertEqual(report["link_candidate_summary"]["by_evidence_tier"], {"place_and_event_year": 2})
        self.assertEqual(report["link_candidate_summary"]["by_review_priority"], {"normal": 2})

    def test_record_date_does_not_create_shared_event_year_evidence(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om planerad naturvårdsbränning vid Fågelmossen",
            "source_date": "2026-04-02",
            "columns": {"Diarienummer": "123-2026", "In/Upp-datum": "2026-04-02"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Namn": "Fågelmossen", "Åtgärdsår": 2026,
                "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 1)
        candidate = report["link_candidates"][0]
        self.assertEqual(candidate["shared_years"], [])
        self.assertEqual(candidate["evidence_tier"], "place_only")
        self.assertEqual(candidate["review_priority"], "normal")

    def test_higher_priority_requires_place_and_year_and_multiple_place_tokens(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Planerad naturvårdsbränning vid Fågelmossen i Motala 2026",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Namn": "Fågelmossen i Motala", "Åtgärdsår": 2026,
                "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 1)
        candidate = report["link_candidates"][0]
        self.assertEqual(candidate["evidence_tier"], "place_and_event_year")
        self.assertEqual(candidate["review_priority"], "higher")

    def test_admin_geometry_date_does_not_create_event_year_match(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om planerad naturvårdsbränning vid Fågelmossen",
            "source_date": "2026-04-02",
            "columns": {"Diarienummer": "123-2026", "In/Upp-datum": "2026-04-02"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Namn": "Fågelmossen",
                "last_edited_date": "2026-11-01T00:00:00Z",
                "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 1)
        candidate = report["link_candidates"][0]
        self.assertEqual(candidate["shared_years"], [])
        self.assertEqual(candidate["evidence_tier"], "place_only")

    def test_action_year_attribute_can_support_event_year_candidate(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Planerad naturvårdsbränning vid Fågelmossen 2026",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Namn": "Fågelmossen", "Åtgärdsår": 2026,
                "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 1)
        self.assertIn("2026", report["link_candidates"][0]["shared_years"])

    def test_review_csv_contains_joined_titles_and_review_priority(self):
        from pathlib import Path
        import csv
        import tempfile
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om planerad naturvårdsbränning i Fågelmossen i Motala 2026",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {"OBJECTID": 9, "Namn": "Fågelmossen i Motala", "Åtgärdsår": 2026},
            "geometry": {"type": "Polygon", "coordinates": []}
        }]}
        report = build_timeline(state, source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.csv"
            from lansstyrelsen_burn_event_timeline import write_review_csv
            count = write_review_csv(report, path)
            self.assertEqual(count, 1)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertIn("Fågelmossen", rows[0]["diary_title"])
            self.assertIn("Fågelmossen", rows[0]["geometry_title"])
            self.assertEqual(rows[0]["review_priority"], "higher")

    def test_diary_source_date_is_record_date_not_burn_date(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om planerad naturvårdsbränning i reservatet",
            "source_date": "2026-04-02",
            "columns": {"Diarienummer": "123-2026", "In/Upp-datum": "2026-04-02", "date": "2026-04-02"}
        }}}
        report = build_timeline(state, {"features": []})
        event = report["events"][0]
        self.assertIsNone(event["event_date"])
        self.assertEqual(event["record_date"], "2026-04-02")
        self.assertEqual(event["record_date_source_field"], "source_date")

    def test_in_up_date_column_is_used_when_top_level_source_date_missing(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "124-2026",
            "title": "Anmälan om naturvårdsbränning",
            "columns": {"Diarienummer": "124-2026", "In/Upp-datum": "2026-04-03"}
        }}}
        report = build_timeline(state, {"features": []})
        event = report["events"][0]
        self.assertIsNone(event["event_date"])
        self.assertEqual(event["record_date"], "2026-04-03")
        self.assertEqual(event["record_date_source_field"], "In/Upp-datum")

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
