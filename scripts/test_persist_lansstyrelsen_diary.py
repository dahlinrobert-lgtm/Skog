#!/usr/bin/env python3
"""Unit tests for Länsstyrelsen diary history persistence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "persist_lansstyrelsen_diary.py"


class DiaryHistoryTests(unittest.TestCase):
    def make_run(self, term: str, title: str = "Testärende", page: int = 1) -> dict:
        return {
            "source": "https://diarium.lansstyrelsen.se/default.aspx",
            "tested_at_utc": "2026-10-27T10:00:00+00:00",
            "requested_county": "Länsstyrelsen i Norrbottens län",
            "search_term": term,
            "request_ok": True,
            "error": None,
            "result_count": 1,
            "reported_total_results": 1,
            "total_reconciled": True,
            "pagination": {"pages_read": 1, "has_next_page": False},
            "results": [{
                "diary_number": "1234-2026",
                "title": title,
                "Ärenderubrik": title,
                "status": "Handläggning",
                "Status": "Handläggning",
                "date": "2026-10-20",
                "In/Upp-datum": "2026-10-20",
                "links": [{"text": "1234-2026", "href": "CaseInfo.aspx?caseID=123"}],
                "page_number": page,
            }],
        }

    def invoke(self, run: dict, state: Path, events: Path, summary: Path) -> dict:
        input_path = state.parent / "input.json"
        input_path.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(input_path),
             "--state", str(state), "--events", str(events), "--summary", str(summary)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        result["_summary_path"] = str(summary)
        return result

    def test_baseline_then_same_record_via_other_query_has_no_change_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, events, summary = root / "state.json", root / "events.jsonl", root / "summary.json"
            first = self.invoke(self.make_run("naturvårdsbränning"), state, events, summary)
            state_after_first = json.loads(state.read_text(encoding="utf-8"))
            first_hash = next(iter(state_after_first["records"].values()))["content_hash"]
            second = self.invoke(self.make_run("reservat", page=2), state, events, summary)
            state_after_second = json.loads(state.read_text(encoding="utf-8"))
            second_hash = next(iter(state_after_second["records"].values()))["content_hash"]

            self.assertEqual(first_hash, second_hash)
            self.assertEqual(first["first_seen_events"], 1)
            self.assertEqual(first["changed_events"], 0)
            self.assertEqual(second["first_seen_events"], 0)
            self.assertEqual(second["changed_events"], 0)
            saved = json.loads(state.read_text(encoding="utf-8"))
            record = next(iter(saved["records"].values()))
            self.assertEqual(record["queries_seen"], ["naturvårdsbränning", "reservat"])
            self.assertEqual(record["observation_count"], 2)
            saved_events = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["event_type"] for event in saved_events], ["first_seen", "observed"])

    def test_unchanged_source_record_appends_observation_event(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, events, summary = root / "state.json", root / "events.jsonl", root / "summary.json"
            self.invoke(self.make_run("naturvårdsbränning"), state, events, summary)
            second_run = self.make_run("reservat", page=2)
            second_run["tested_at_utc"] = "2026-10-27T11:00:00+00:00"
            result = self.invoke(second_run, state, events, summary)

            saved_events = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["event_type"] for event in saved_events], ["first_seen", "observed"])
            self.assertEqual(result["observation_events"], 1)
            self.assertEqual(result["changed_events"], 0)
            saved = json.loads(state.read_text(encoding="utf-8"))
            record = next(iter(saved["records"].values()))
            self.assertEqual(record["observation_count"], 2)

    def test_source_title_change_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, events, summary = root / "state.json", root / "events.jsonl", root / "summary.json"
            self.invoke(self.make_run("naturvårdsbränning"), state, events, summary)
            changed = self.make_run("naturvårdsbränning", title="Ändrad ärenderubrik")
            changed["tested_at_utc"] = "2026-10-27T11:00:00+00:00"
            result = self.invoke(changed, state, events, summary)
            self.assertEqual(result["changed_events"], 1)
            saved_events = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(saved_events[-1]["event_type"], "record_changed")
            self.assertEqual(saved_events[-1]["before"]["title"], "Testärende")
            self.assertEqual(saved_events[-1]["after"]["title"], "Ändrad ärenderubrik")

    def test_rejects_unreconciled_total(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = self.make_run("naturvårdsbränning")
            run["reported_total_results"] = 2
            run["total_reconciled"] = False
            input_path = root / "input.json"
            input_path.write_text(json.dumps(run), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(input_path),
                 "--state", str(root / "state.json"), "--events", str(root / "events.jsonl"),
                 "--summary", str(root / "summary.json")],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("extracted count matches", proc.stderr)

    def test_overlapping_search_terms_are_merged_without_duplicate_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, events, summary = root / "state.json", root / "events.jsonl", root / "summary.json"
            run = self.make_run("naturvårdsbränning")
            record = run["results"][0]
            record["query_terms"] = ["naturvårdsbränning", "reservat"]
            run["search_terms"] = ["naturvårdsbränning", "reservat"]
            run["queries"] = [
                {
                    "search_term": term,
                    "request_ok": True,
                    "result_count": 1,
                    "reported_total_results": 1,
                    "total_reconciled": True,
                    "pagination": {"pages_read": 1, "has_next_page": False},
                    "results": [record],
                }
                for term in run["search_terms"]
            ]
            run["reported_total_results"] = 2
            run["result_count"] = 1
            self.invoke(run, state, events, summary)
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["records"]), 1)
            saved_record = next(iter(saved["records"].values()))
            self.assertEqual(saved_record["queries_seen"], ["naturvårdsbränning", "reservat"])
            after = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(after["state_record_count_after"], 1)
            self.assertEqual(after["extracted_count"], 1)
            self.assertEqual(len(after["search_terms"]), 2)
            self.assertEqual(after["search_terms"], ["naturvårdsbränning", "reservat"])
            saved_events = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(saved_events), 1)
            self.assertTrue(saved_events[0]["baseline_only"])

    def test_does_not_mark_missing_ids_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, events, summary = root / "state.json", root / "events.jsonl", root / "summary.json"
            self.invoke(self.make_run("naturvårdsbränning"), state, events, summary)
            empty = self.make_run("naturvårdsbränning")
            empty["result_count"] = 0
            empty["reported_total_results"] = 0
            empty["results"] = []
            self.invoke(empty, state, events, summary)
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["records"]), 1)
            after = json.loads(summary.read_text(encoding="utf-8"))
            self.assertFalse(after["absent_ids_interpreted_as_removed"])


    def test_records_are_persisted_under_each_county_in_all_counties_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state, events, summary = root / "state.json", root / "events.jsonl", root / "summary.json"
            run = self.make_run("naturvårdsbränning")
            run["requested_county"] = "Alla län"
            run["counties"] = ["Länsstyrelsen i Norrbottens län", "Länsstyrelsen i Västerbottens län"]
            run["results"] = [
                {**run["results"][0], "diary": run["counties"][0], "diary_number": "1234-2026"},
                {**run["results"][0], "diary": run["counties"][1], "diary_number": "1234-2026"},
            ]
            run["result_count"] = 2
            run["reported_total_results"] = 2
            run["queries"] = [{
                "search_term": "naturvårdsbränning", "requested_county": c,
                "request_ok": True, "result_count": 1, "reported_total_results": 1,
                "total_reconciled": True, "pagination": {"pages_read": 1, "has_next_page": False},
                "results": [r],
            } for c, r in zip(run["counties"], run["results"])]
            run["per_query_counts"] = [{} for _ in run["queries"]]
            result = self.invoke(run, state, events, summary)
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["records"]), 2)
            self.assertIn("länsstyrelsen i norrbottens län::1234-2026", saved["records"])
            self.assertIn("länsstyrelsen i västerbottens län::1234-2026", saved["records"])
            after = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(after["diary"], "Alla län")
            self.assertEqual(after["counties"], run["counties"])
            self.assertEqual(after["query_count"], 2)



class DiaryMultiSearchValidationTests(unittest.TestCase):
    def test_parse_search_terms_deduplicates_case_insensitively(self):
        terms = ["naturvårdsbränning"]
        extras = "reservat, naturvårdsbränning\nbrand"
        import re
        for extra in re.split(r"[,;\n\r]+", extras or ""):
            extra = extra.strip()
            if extra and extra.casefold() not in {term.casefold() for term in terms}:
                terms.append(extra)
        self.assertEqual(terms, ["naturvårdsbränning", "reservat", "brand"])

    def test_overlapping_search_results_merge_by_diary_number(self):
        merged_by_id = {}
        inputs = [
            ("naturvårdsbränning", [{"diary_number": "1234-2026", "title": "A"}]),
            ("reservat", [
                {"diary_number": "1234-2026", "title": "A"},
                {"diary_number": "5678-2025", "title": "B"},
            ]),
        ]
        for term, records in inputs:
            for record in records:
                number = record["diary_number"]
                if number not in merged_by_id:
                    record["query_terms"] = [term]
                    merged_by_id[number] = record
                elif term not in merged_by_id[number]["query_terms"]:
                    merged_by_id[number]["query_terms"].append(term)
        self.assertEqual(len(merged_by_id), 2)
        self.assertEqual(
            merged_by_id["1234-2026"]["query_terms"],
            ["naturvårdsbränning", "reservat"],
        )

if __name__ == "__main__":
    unittest.main()
