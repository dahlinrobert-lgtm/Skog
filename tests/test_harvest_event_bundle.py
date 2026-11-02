from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_harvest_event_bundle import build_bundle  # noqa: E402


class HarvestEventBundleTests(unittest.TestCase):
    def fixture(self):
        return {
            "checked_at": "2026-11-02T12:00:00Z",
            "area": {"name": "Testområde", "latitude": 63.7, "longitude": 19.6, "radius_km": 10},
            "cutting_notifications": {
                "status": "ok",
                "url": "https://example.test/query",
                "features": [{
                    "type": "Feature", "id": 123,
                    "geometry": {"type": "Point", "coordinates": [19.6, 63.7]},
                    "properties": {
                        "OBJECTID": 123, "Beteckn": "A 123-2026", "Kommun": "TEST",
                        "ArendeStatus": "Anmält för avverkning", "Inkomdatum": 1790899200000,
                        "AnmaldHa": 2.4
                    }
                }]
            }
        }

    def test_builds_one_stable_event_chain_per_source_record(self):
        bundle = build_bundle(self.fixture(), {})
        self.assertEqual(len(bundle["events"]), 1)
        self.assertEqual(len(bundle["chains"]), 1)
        self.assertEqual(bundle["events"][0]["event_type"], "planned_harvest_notification")
        self.assertEqual(bundle["chains"][0]["event_ids"], [bundle["events"][0]["event_id"]])
        self.assertEqual(bundle["events"][0]["confidence_class"], "verified")
        self.assertIn("inte belägg för att avverkning", bundle["events"][0]["summary"])

    def test_uses_history_first_seen_and_last_seen(self):
        history = {"cases": {"123": {
            "first_seen_at": "2026-10-01T10:00:00Z",
            "last_seen_at": "2026-11-01T10:00:00Z"
        }}}
        bundle = build_bundle(self.fixture(), history)
        self.assertEqual(bundle["events"][0]["first_observed_at"], "2026-10-01T10:00:00Z")
        self.assertEqual(bundle["events"][0]["last_observed_at"], "2026-11-01T10:00:00Z")

    def test_refuses_failed_or_empty_source_snapshot(self):
        latest = self.fixture()
        latest["cutting_notifications"]["status"] = "failed"
        with self.assertRaises(ValueError):
            build_bundle(latest, {})
        latest = self.fixture()
        latest["cutting_notifications"]["features"] = []
        with self.assertRaises(ValueError):
            build_bundle(latest, {})

    def test_refuses_duplicate_source_ids(self):
        latest = self.fixture()
        latest["cutting_notifications"]["features"].append(latest["cutting_notifications"]["features"][0])
        with self.assertRaises(ValueError):
            build_bundle(latest, {})


if __name__ == "__main__":
    unittest.main()
