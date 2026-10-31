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

    def test_place_tokens_ignore_county_inflections_and_generic_area_words(self):
        from lansstyrelsen_burn_event_timeline import _name_tokens
        tokens = _name_tokens("Dalarnas län samt södra området vid naturvårdsbränning")
        self.assertEqual(tokens, set())

    def test_specific_site_name_survives_generic_area_filter(self):
        from lansstyrelsen_burn_event_timeline import _name_tokens
        tokens = _name_tokens("Dalarnas län samt södra området vid Hornbobrändan")
        self.assertEqual(tokens, {"hornbobrändan"})

    def test_place_tokens_ignore_diary_and_procurement_vocabulary(self):
        from lansstyrelsen_burn_event_timeline import _name_tokens
        tokens = _name_tokens(
            "Ansökan om dispens från naturvårdsbränning inför upphandling "
            "av tjänst i nationalparken"
        )
        self.assertEqual(tokens, set())

    def test_generic_nationalpark_and_forest_terms_do_not_outvote_site_name(self):
        from lansstyrelsen_burn_event_timeline import _name_tokens
        tokens = _name_tokens("Fulufjällets nationalpark samt skog")
        self.assertEqual(tokens, {"fulufjällets"})

    def test_broad_landscape_names_are_context_not_specific_site_evidence(self):
        from lansstyrelsen_burn_event_timeline import _place_token_groups
        diary_specific, diary_context = _place_token_groups(
            "Bränning vid Gotska Sandön, Slyngdynen"
        )
        geometry_specific, geometry_context = _place_token_groups(
            "Slyngdynen, Gotska Sandön"
        )
        other_specific, other_context = _place_token_groups(
            "Tomtebo, Gotska Sandön"
        )
        self.assertEqual(diary_specific & geometry_specific, {"slyngdynen"})
        self.assertEqual(diary_context & geometry_context, {"gotska", "sandön"})
        self.assertEqual(diary_specific & other_specific, set())
        self.assertEqual(diary_context & other_context, {"gotska", "sandön"})

    def test_allgunnen_context_does_not_count_as_specific_overlap(self):
        from lansstyrelsen_burn_event_timeline import _place_token_groups
        left_specific, left_context = _place_token_groups("Allgunnen Värlekärret")
        right_specific, right_context = _place_token_groups("Allgunnen Brantehallar")
        self.assertEqual(left_specific & right_specific, set())
        self.assertEqual(left_context & right_context, {"allgunnen"})

    def test_skattlosberg_context_does_not_count_as_specific_overlap(self):
        from lansstyrelsen_burn_event_timeline import _place_token_groups
        left_specific, left_context = _place_token_groups("Skattlösbergs stormosse Lövmosstrupen")
        right_specific, right_context = _place_token_groups("Skattlösbergs stormosse Tuppmossheden")
        self.assertEqual(left_specific & right_specific, set())
        self.assertTrue({"skattlösberg", "stormosse"}.issubset(left_context & right_context))

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

    def test_timeline_summary_includes_bounded_context_only_examples(self):
        diary = {"records": {"d1": {"record_key": "d1", "title": "Bränning vid Gotska Sandön", "columns": {"Län": "Gotlands län"}}}}
        lifetaiga = {"features": [{"id": 1, "properties": {"OBJECTID": 1, "title": "Gotska Sandön Slyngdynen", "lansnamn": "Gotlands län"}, "geometry": {"type": "Polygon", "coordinates": []}}]}
        report = build_timeline(diary, lifetaiga)
        examples = report["link_candidate_summary"]["context_only_examples"]
        self.assertLessEqual(len(examples), 20)
        self.assertTrue(all(item["shared_context_place_tokens"] for item in examples))

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
            self.assertIn("Gemensamma platsindicier: fågelmossen", candidate["evidence_summary"])
            self.assertEqual(candidate["ambiguity"], "geometry_matches_multiple_diary_records")
            self.assertTrue(candidate["shared_years"])
        self.assertTrue(all(event["link_status"] == "unlinked" for event in report["events"]))
        self.assertEqual(report["link_candidate_summary"]["by_evidence_tier"], {"place_and_year": 2})
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
        self.assertEqual(candidate["evidence_tier"], "place_and_year")
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

    def test_field_inventory_finds_action_and_date_fields_without_asserting_meaning(self):
        from lansstyrelsen_burn_event_timeline import build_field_inventory
        source = {
            "source_url": "https://example.test/layer",
            "source_layer_id": 13,
            "features": [
                {"properties": {"OBJECTID": 1, "Namn": "Fågelmossen", "Åtgärdsår": 2026, "EditDate": 1790000000000}},
                {"properties": {"OBJECTID": 2, "Namn": "Vändåtberget", "Åtgärdsår": None, "EditDate": 1790000000000}},
            ],
        }
        report = build_field_inventory(source)
        self.assertEqual(report["feature_count"], 2)
        self.assertEqual(report["field_count"], 4)
        self.assertIn("Åtgärdsår", report["date_or_action_field_candidates"])
        action_year = next(field for field in report["fields"] if field["field"] == "Åtgärdsår")
        self.assertEqual(action_year["non_null_count"], 1)
        self.assertEqual(action_year["examples"], ["2026"])
        self.assertIn("EditDate", report["date_or_action_field_candidates"])
        self.assertIn("not treated as an event date", report["interpretation_policy"])

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


    def test_county_context_can_create_candidate_without_exact_site_name(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Information om naturvårdsbränning i Västerbottens län",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Län": "Västerbotten",
                "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 1)
        candidate = report["link_candidates"][0]
        self.assertEqual(candidate["shared_counties"], ["västerbotten"])
        self.assertEqual(candidate["place_points"], 0)
        self.assertEqual(candidate["county_points"], 15)
        self.assertEqual(candidate["status"], "candidate_for_manual_review")
        self.assertTrue(all(event["link_status"] == "unlinked" for event in report["events"]))

    def test_correlation_score_exposes_components_and_data_coverage(self):
        state = {"records": {"r1": {
            "record_key": "r1", "diary_number": "123-2026",
            "title": "Planerad naturvårdsbränning vid Fågelmossen i Västerbotten 2026",
            "columns": {"Diarienummer": "123-2026"}
        }}}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Namn": "Fågelmossen",
                "Län": "Västerbotten", "Åtgärdsår": 2026,
                "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        candidate = report["link_candidates"][0]
        self.assertEqual(candidate["place_points"], 20)
        self.assertEqual(candidate["county_points"], 15)
        self.assertEqual(candidate["time_points"], 20)
        self.assertEqual(candidate["lifecycle_points"], 15)
        self.assertEqual(candidate["uniqueness_points"], 10)
        self.assertEqual(candidate["score"], 80)
        self.assertEqual(candidate["data_coverage"], 1.0)
        self.assertIn("unikhet 10/10", candidate["evidence_summary"])


    def test_ambiguous_candidate_pair_receives_no_uniqueness_bonus(self):
        state = {"records": {
            "r1": {
                "record_key": "r1", "diary_number": "123-2026",
                "title": "Anmälan om naturvårdsbränning vid Fågelmossen i Västerbotten",
                "columns": {"Diarienummer": "123-2026"}
            },
            "r2": {
                "record_key": "r2", "diary_number": "124-2026",
                "title": "Uppföljning efter naturvårdsbränning vid Fågelmossen i Västerbotten",
                "columns": {"Diarienummer": "124-2026"}
            }
        }}
        source = {"features": [{
            "id": 9, "properties": {
                "OBJECTID": 9, "Namn": "Fågelmossen",
                "Län": "Västerbotten", "Typ": "T2.3 Controlled burning"
            }
        }]}
        report = build_timeline(state, source)
        self.assertEqual(report["link_candidate_count"], 2)
        for candidate in report["link_candidates"]:
            self.assertEqual(candidate["geometry_candidate_count"], 2)
            self.assertEqual(candidate["uniqueness_points"], 0)
            self.assertEqual(candidate["ambiguity"], "geometry_matches_multiple_diary_records")


if __name__ == "__main__":
    unittest.main()
