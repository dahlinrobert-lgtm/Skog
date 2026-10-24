#!/usr/bin/env python3
"""Regression tests for durable cutting-notification history and change events."""
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from scripts.notification_history import build_history, canonical_hash, scope_hash, write_event_log


def feature(oid, designation=None, area=1.0, x=19.6, status="Anmält för avverkning"):
    return {
        "type": "Feature", "id": oid,
        "properties": {"OBJECTID": oid, "Beteckn": designation or f"case-{oid}",
                       "AnmaldHa": area, "ArendeStatus": status},
        "geometry": {"type": "Point", "coordinates": [x, 63.7]},
    }


def snapshot(at, features, radius=10, status="ok", query_scope="radius"):
    if query_scope == "bbox":
        params = {
            "geometry": json.dumps({"xmin": 19.45, "ymin": 63.65, "xmax": 19.85, "ymax": 63.85}),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
        }
    else:
        params = {
            "geometry": json.dumps({"x": 19.66455, "y": 63.74646, "spatialReference": {"wkid": 4326}}),
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "distance": "10000",
            "units": "esriSRUnit_Meter",
            "spatialRel": "esriSpatialRelIntersects",
        }
    return {
        "checked_at": at,
        "area": {"latitude": 63.74646, "longitude": 19.66455, "radius_km": radius},
        "cutting_notifications": {
            "status": status,
            "url": "https://example.test/query?" + urlencode(params),
            "features": features,
        },
    }


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
        self.assertTrue(any(e["event_type"] == "reappeared_or_newly_observed" for e in events))

    def test_changed_scope_does_not_emit_missing_case_or_record_change(self):
        _, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1")], radius=10)),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [feature("1", area=2)], radius=12)),
        ])
        self.assertFalse(any(e["event_type"] in {"not_returned", "record_changed"} for e in events))
        self.assertTrue(any(e["event_type"] == "comparison_skipped_scope_changed" for e in events))

    def test_bbox_to_radius_transition_never_becomes_not_returned(self):
        history, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1"), feature("2")], query_scope="bbox")),
            ("b.json", snapshot("2026-10-24T06:00:00Z", [feature("2")], query_scope="radius")),
            ("c.json", snapshot("2026-10-25T05:00:00Z", [feature("2")], query_scope="radius")),
        ])
        self.assertFalse(any(e.get("event_type") == "not_returned" and e.get("notification_id") == "1" for e in events))
        self.assertTrue(any(e.get("event_type") == "scope_changed" and e.get("notification_id") == "1" for e in events))
        self.assertEqual(history["cases"]["1"]["observation_status"], "scope_changed")
        self.assertEqual(history["cases"]["2"]["observation_status"], "observed")

    def test_query_geometry_change_is_detected_even_when_configured_area_is_same(self):
        old_scope = scope_hash(snapshot("2026-10-24T05:00:00Z", [], query_scope="bbox"))
        new_scope = scope_hash(snapshot("2026-10-24T06:00:00Z", [], query_scope="radius"))
        self.assertNotEqual(old_scope, new_scope)

    def test_failed_snapshot_is_not_compared(self):
        _, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1")])),
            ("bad.json", snapshot("2026-10-25T05:00:00Z", [], status="error")),
            ("b.json", snapshot("2026-10-26T05:00:00Z", [feature("1")])),
        ])
        self.assertFalse(any(e["event_type"] == "not_returned" for e in events))
        self.assertFalse(any(e["event_type"] == "record_changed" for e in events))

    def test_attribute_change_emits_old_and_new_values_without_splitting_identity(self):
        history, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1", area=1.0)])),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [feature("1", area=2.5)])),
        ])
        self.assertEqual(history["case_count"], 1)
        self.assertEqual(history["cases"]["1"]["attributes"]["AnmaldHa"], 2.5)
        changed = [e for e in events if e["event_type"] == "record_changed"]
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["changed_attributes"]["AnmaldHa"], {"old": 1.0, "new": 2.5})
        self.assertEqual(changed[0]["previous_snapshot"], "a.json")
        self.assertFalse(changed[0]["geometry_changed"])

    def test_geometry_change_is_logged(self):
        _, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1", x=19.6)])),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [feature("1", x=19.61)])),
        ])
        changed = [e for e in events if e["event_type"] == "record_changed"]
        self.assertEqual(len(changed), 1)
        self.assertTrue(changed[0]["geometry_changed"])

    def test_no_change_emits_no_record_change(self):
        _, events = build_history([
            ("a.json", snapshot("2026-10-24T05:00:00Z", [feature("1")])),
            ("b.json", snapshot("2026-10-25T05:00:00Z", [feature("1")])),
        ])
        self.assertFalse(any(e["event_type"] == "record_changed" for e in events))

    def test_event_log_rewrite_removes_obsolete_derived_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "events.jsonl"
            path.write_text(json.dumps({"event_type": "not_returned", "notification_id": "1"}) + "\n",
                            encoding="utf-8")
            current_events = [{"event_type": "scope_changed", "notification_id": "1"}]
            self.assertEqual(write_event_log(current_events, path), 1)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows, current_events)

    def test_hash_is_order_independent(self):
        self.assertEqual(canonical_hash({"a": 1, "b": 2}), canonical_hash({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
