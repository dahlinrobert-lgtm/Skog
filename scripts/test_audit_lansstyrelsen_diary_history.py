#!/usr/bin/env python3
"""Tests for Länsstyrelsen diary history integrity audit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_lansstyrelsen_diary_history import audit_history


class DiaryHistoryAuditTests(unittest.TestCase):
    def test_consistent_history_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path = root / "state.json"
            events_path = root / "events.jsonl"
            state_path.write_text(json.dumps({"records": {
                "county::123-2026": {
                    "record_key": "county::123-2026", "diary_number": "123-2026",
                    "diary": "County", "observation_count": 2,
                }
            }}), encoding="utf-8")
            events_path.write_text("\n".join([
                json.dumps({"event_id": "1", "event_type": "first_seen", "record_key": "county::123-2026"}),
                json.dumps({"event_id": "2", "event_type": "observed", "record_key": "county::123-2026"}),
            ]) + "\n", encoding="utf-8")
            report = audit_history(state_path, events_path)
            self.assertTrue(report["ok"])
            self.assertEqual(report["legacy_observation_count_mismatches"], 0)

    def test_legacy_count_gap_is_reported_but_not_misclassified_as_structural_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path = root / "state.json"
            events_path = root / "events.jsonl"
            state_path.write_text(json.dumps({"records": {
                "county::123-2026": {
                    "record_key": "county::123-2026", "diary_number": "123-2026",
                    "diary": "County", "observation_count": 5,
                    "first_observed_at": "2026-10-01T00:00:00+00:00",
                    "last_observed_at": "2026-10-03T00:00:00+00:00",
                }
            }}), encoding="utf-8")
            events_path.write_text(json.dumps({
                "event_id": "1", "event_type": "first_seen", "record_key": "county::123-2026"
            }) + "\n", encoding="utf-8")
            report = audit_history(state_path, events_path)
            self.assertTrue(report["ok"])
            self.assertEqual(report["legacy_observation_count_mismatches"], 1)
            gap = report["records_with_observation_count_mismatch"][0]
            self.assertEqual(gap["unexplained_observations"], 4)

    def test_duplicate_event_ids_fail_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path = root / "state.json"
            events_path = root / "events.jsonl"
            state_path.write_text(json.dumps({"records": {
                "county::123-2026": {
                    "record_key": "county::123-2026", "diary_number": "123-2026",
                    "diary": "County", "observation_count": 1,
                }
            }}), encoding="utf-8")
            duplicate = {"event_id": "same", "event_type": "first_seen", "record_key": "county::123-2026"}
            events_path.write_text(json.dumps(duplicate) + "\n" + json.dumps(duplicate) + "\n", encoding="utf-8")
            report = audit_history(state_path, events_path)
            self.assertFalse(report["ok"])
            self.assertEqual(report["duplicate_event_ids"], ["same"])

    def test_orphan_event_key_fails_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path = root / "state.json"
            events_path = root / "events.jsonl"
            state_path.write_text(json.dumps({"records": {}}), encoding="utf-8")
            events_path.write_text(json.dumps({
                "event_id": "orphan", "event_type": "observed", "record_key": "missing::123-2026"
            }) + "\n", encoding="utf-8")
            report = audit_history(state_path, events_path)
            self.assertFalse(report["ok"])
            self.assertEqual(report["event_keys_without_state_record"], ["missing::123-2026"])

    def test_non_object_event_json_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path = root / "state.json"
            events_path = root / "events.jsonl"
            state_path.write_text(json.dumps({"records": {}}), encoding="utf-8")
            events_path.write_text(json.dumps(["not", "an", "event"]) + "\n", encoding="utf-8")
            report = audit_history(state_path, events_path)
            self.assertFalse(report["ok"])
            self.assertEqual(report["error"], "invalid_event_shape")

    def test_record_without_first_seen_fails_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state_path = root / "state.json"
            events_path = root / "events.jsonl"
            state_path.write_text(json.dumps({"records": {
                "county::123-2026": {
                    "record_key": "county::123-2026", "diary_number": "123-2026",
                    "diary": "County", "observation_count": 1,
                }
            }}), encoding="utf-8")
            events_path.write_text(json.dumps({
                "event_id": "1", "event_type": "observed", "record_key": "county::123-2026"
            }) + "\n", encoding="utf-8")
            report = audit_history(state_path, events_path)
            self.assertFalse(report["ok"])
            self.assertEqual(report["records_missing_first_seen_event"], ["county::123-2026"])


if __name__ == "__main__":
    unittest.main()
