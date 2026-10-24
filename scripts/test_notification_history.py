#!/usr/bin/env python3
"""Regression tests for durable cutting-notification history."""
import unittest
from scripts.notification_history import build_history, canonical_hash


def feature(oid, designation=None):
    return {"type": "Feature", "id": oid,
            "properties": {"OBJECTID": oid, "Beteckn": designation or f"case-{oid}"},
            "geometry": {"type": "Point", "coordinates": [19.6, 63.7]}}


def snapshot(at, features, radius=10, status="ok"):
    return {"checked_at": at,
            "area": {"latitude": 63.7, "longitude": 19.6, "radius_km": radius},
            "cutting_notifications": {"status": status, "url": "https://example.test/query?x=1",
                                      "features": features}}


class NotificationHistoryTests(unittest.TestCase):
    def test_missing_case_is_preserved_and_not_called_felled(self):
        history, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1"), feature("2")])),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [feature("2")])),
        ])
        self.assertIn("1", history["cases"])
        self.assertEqual(history["cases"]["1"]["observation_status"], "not_returned")
        self.assertEqual(history["cases"]["1"]["first_seen_at"], "2026-10-24T05:00:00Z")
        self.assertEqual(history["cases"]["1"]["first_not_returned_at"], "2026-10-25T05:00:00Z")
        self.assertTrue(any(e["event_type"] == "not_returned" for e in events))
        self.assertFalse(any(e["event_type"] == "felled" for e in events))

    def test_reappearance_preserves_first_seen(self):
        history, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1")])),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [])),
            ("c.json", snapshot("2026-10-26T05:00:00Z", [feature("1")])),
        ])
        case = history["cases"]["1"]
        self.assertEqual(case["observation_status"], "observed")
        self.assertEqual(case["first_seen_at"], "2026-10-24T05:00:00Z")
        self.assertEqual(case["last_reappeared_at"], "2026-10-26T05:00:00Z")
        self.assertTrue(any(e["event_type"] == "reappeared_or_newly_observed" for e in events))

    def test_changed_scope_does_not_emit_missing_case(self):
        _, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1")], radius=10)),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [], radius=12)),
        ])
        self.assertFalse(any(e["event_type"] == "not_returned" for e in events))
        self.assertTrue(any(e["event_type"] == "comparison_skipped_scope_changed" for e in events))

    def test_failed_snapshot_is_not_compared(self):
        _, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1")])),
            ("bad.json", snapshot("2026-10-25T05:00:00Z", [], status="error")),
            ("b.json", snapshot("2026-10-26T05:00:00Z", [feature("1")])),
        ])
        self.assertFalse(any(e["event_type"] == "not_returned" for e in events))

    def test_attribute_correction_does_not_split_identity(self):
        history, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1", "old")])),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [feature("1", "corrected")])),
        ])
        self.assertEqual(history["case_count"], 1)
        self.assertEqual(history["cases"]["1"]["attributes"]["Beteckn"], "corrected")
        self.assertFalse(events)

    def test_hash_is_order_independent(self):
        self.assertEqual(canonical_hash({"a": 1, "b": 2}), canonical_hash({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
