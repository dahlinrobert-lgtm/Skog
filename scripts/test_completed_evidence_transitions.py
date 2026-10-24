#!/usr/bin/env python3
"""Regression tests for completed-layer evidence transitions."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shapely.geometry import mapping, box

from scripts import analyze_changes as ac


def make_feature(oid, geom, date_ms=1735689600000, municipality="NORDMALING"):
    return {
        "type": "Feature",
        "id": str(oid),
        "properties": {
            "OBJECTID": int(oid),
            "Beteckn": f"A {oid}-2024",
            "Kommun": municipality,
            "Inkomdatum": 1704067200000,
            "AnmaldHa": 1.0,
            "Avvdatum": date_ms,
            "Arealha": geom.area / 10000,
        },
        "geometry": mapping(geom),
    }


def archive(path, stamp, features):
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump({"type": "FeatureCollection", "checked_at": stamp, "features": features}, handle)


class EvidenceTransitionTests(unittest.TestCase):
    def test_first_archive_is_baseline_not_new_evidence(self):
        before = make_feature("10", box(0, 0, 100, 100))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "completed_20261024T000000Z.geojson.gz"
            archive(p, "2026-10-24T00:00:00Z", [before])
            with patch.object(ac, "SNAPSHOTS", Path(tmp)):
                result = ac.evidence_transition_events(
                    {"1": make_feature("1", box(0, 0, 100, 100))}, []
                )
            self.assertEqual(result["snapshot_count"], 1)
            self.assertEqual(result["events"], [])

    def test_new_completed_polygon_overlapping_plan_emits_event(self):
        planned = make_feature("1", box(0, 0, 100, 100))
        done = make_feature("10", box(0, 0, 60, 100))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive(root / "completed_20261024T000000Z.geojson.gz", "2026-10-24T00:00:00Z", [])
            archive(root / "completed_20261025T000000Z.geojson.gz", "2026-10-25T00:00:00Z", [done])
            with patch.object(ac, "SNAPSHOTS", root):
                result = ac.evidence_transition_events({"1": planned}, [])
            self.assertEqual(len(result["events"]), 1)
            event = result["events"][0]
            self.assertEqual(event["event_type"], "new_completed_detection_overlap")
            self.assertEqual(event["planned_object_id"], "1")
            self.assertEqual(event["completed_object_id"], "10")
            self.assertAlmostEqual(event["intersection_ha"], 0.6)
            self.assertIn("not proof", event["meaning"])

    def test_unrelated_new_polygon_does_not_emit_event(self):
        planned = make_feature("1", box(0, 0, 100, 100))
        done = make_feature("10", box(200, 200, 300, 300))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive(root / "completed_20261024T000000Z.geojson.gz", "2026-10-24T00:00:00Z", [])
            archive(root / "completed_20261025T000000Z.geojson.gz", "2026-10-25T00:00:00Z", [done])
            with patch.object(ac, "SNAPSHOTS", root):
                result = ac.evidence_transition_events({"1": planned}, [])
            self.assertEqual(result["events"], [])

    def test_existing_polygon_geometry_change_can_emit_event(self):
        planned = make_feature("1", box(0, 0, 100, 100))
        old_done = make_feature("10", box(0, 0, 20, 100))
        new_done = make_feature("10", box(0, 0, 60, 100))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive(root / "completed_20261024T000000Z.geojson.gz", "2026-10-24T00:00:00Z", [old_done])
            archive(root / "completed_20261025T000000Z.geojson.gz", "2026-10-25T00:00:00Z", [new_done])
            with patch.object(ac, "SNAPSHOTS", root):
                result = ac.evidence_transition_events({"1": planned}, [])
            self.assertEqual(len(result["events"]), 1)
            self.assertEqual(result["events"][0]["event_type"], "completed_detection_changed_overlap")
            self.assertTrue(result["events"][0]["geometry_changed"])

    def test_outside_three_year_window_not_counted(self):
        planned = make_feature("1", box(0, 0, 100, 100))
        old_date_done = make_feature("10", box(0, 0, 60, 100), date_ms=1600000000000)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive(root / "completed_20261024T000000Z.geojson.gz", "2026-10-24T00:00:00Z", [])
            archive(root / "completed_20261025T000000Z.geojson.gz", "2026-10-25T00:00:00Z", [old_date_done])
            with patch.object(ac, "SNAPSHOTS", root):
                result = ac.evidence_transition_events({"1": planned}, [])
            self.assertEqual(result["events"], [])


if __name__ == "__main__":
    unittest.main()
