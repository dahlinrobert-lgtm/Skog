from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "data-platform" / "scripts"))
from build_harvest_event_bundle import build_bundle, build_samrad_history  # noqa: E402
from validate_event_bundle import SCHEMA, validate_bundle  # noqa: E402


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

    def samrad_fixture(self, far_away=False):
        lon, lat = (20.0, 64.0) if far_away else (19.6, 63.7)
        return {
            "source_id": "skogsstyrelsen.samrad",
            "checked_at": "2026-11-02T11:00:00Z",
            "status": "success",
            "scope_hash": "samrad-scope-hash",
            "counts": {"points": {"pages": 1, "records_fetched_in_envelope": 0, "records_in_scope": 0, "records_outside_scope": 0, "records_missing_geometry": 0, "records_geometry_error": 0}, "lines": {"pages": 1, "records_fetched_in_envelope": 0, "records_in_scope": 0, "records_outside_scope": 0, "records_missing_geometry": 0, "records_geometry_error": 0}, "areas": {"pages": 1, "records_fetched_in_envelope": 1, "records_in_scope": 1, "records_outside_scope": 0, "records_missing_geometry": 0, "records_geometry_error": 0}},
            "layers": {
                "points": {"features": []},
                "lines": {"features": []},
                "areas": {"features": [{
                    "type": "Feature", "id": 456,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon - 0.002, lat - 0.002], [lon + 0.002, lat - 0.002],
                            [lon + 0.002, lat + 0.002], [lon - 0.002, lat + 0.002],
                            [lon - 0.002, lat - 0.002]
                        ]]
                    },
                    "properties": {
                        "ObjectId": 456, "Beteckn": "S 456-2026", "UUID": "samrad-uuid-456",
                        "Kommun": "TEST", "Status": "Registrerad", "Inkomdatum": 1790812800000,
                        "Samradsatgard": "Skogsavverkning"
                    }
                }]}
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

    def test_samrad_becomes_separate_event_and_supported_spatial_candidate(self):
        bundle = build_bundle(self.fixture(), {}, self.samrad_fixture())
        self.assertEqual(len(bundle["source_runs"]), 2)
        self.assertEqual(len(bundle["events"]), 2)
        self.assertEqual(len(bundle["relationships"]), 1)
        relation = bundle["relationships"][0]
        self.assertEqual(relation["relationship_type"], "possible_follow_up")
        self.assertEqual(relation["confidence_class"], "supported")
        self.assertEqual(relation["review_status"], "needs_review")
        self.assertEqual(len(bundle["chains"][0]["event_ids"]), 2)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(validate_bundle(bundle, schema), [])

    def test_distant_samrad_record_is_not_linked(self):
        bundle = build_bundle(self.fixture(), {}, self.samrad_fixture(far_away=True))
        self.assertEqual(len(bundle["events"]), 2)
        self.assertEqual(bundle["relationships"], [])
        self.assertEqual(len(bundle["chains"][0]["event_ids"]), 1)

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


    def test_samrad_history_keeps_one_case_and_distinct_versions(self):
        first = self.samrad_fixture()
        first['checked_at'] = '2026-11-02T11:00:00Z'
        second = json.loads(json.dumps(first))
        second['checked_at'] = '2026-11-03T11:00:00Z'
        second['layers']['areas']['features'][0]['properties']['Status'] = 'Kompletterad i källan'
        runs, observations, events, evidence, index = build_samrad_history([
            ('data/samrad_snapshots/samrad_20261102T110000Z.json.gz', first),
            ('data/samrad_snapshots/samrad_20261103T110000Z.json.gz', second),
        ])
        self.assertEqual((len(runs), len(observations), len(events), len(index), len(evidence)), (2, 2, 1, 1, 2))
        self.assertEqual(events[0]['first_observed_at'], '2026-11-02T11:00:00Z')
        self.assertEqual(events[0]['last_observed_at'], '2026-11-03T11:00:00Z')

    def test_samrad_history_retains_record_missing_from_later_snapshot(self):
        first = self.samrad_fixture()
        first['checked_at'] = '2026-11-02T11:00:00Z'
        later = json.loads(json.dumps(first))
        later['checked_at'] = '2026-11-03T11:00:00Z'
        later['layers']['areas']['features'] = []
        later['counts']['areas'].update({'records_fetched_in_envelope': 0, 'records_in_scope': 0})
        runs, observations, events, evidence, index = build_samrad_history([
            ('data/samrad_snapshots/samrad_20261102T110000Z.json.gz', first),
            ('data/samrad_snapshots/samrad_20261103T110000Z.json.gz', later),
        ])
        self.assertEqual((len(runs), len(observations), len(events)), (2, 1, 1))
        self.assertIn('inte tolkas som avslut', events[0]['summary'])
        self.assertEqual(events[0]['last_observed_at'], '2026-11-02T11:00:00Z')

    def test_partial_samrad_snapshot_is_excluded_from_history(self):
        complete = self.samrad_fixture()
        partial = json.loads(json.dumps(complete))
        partial['checked_at'] = '2026-11-03T11:00:00Z'
        partial['status'] = 'partial'
        runs, observations, events, evidence, index = build_samrad_history([
            ('data/samrad_snapshots/samrad_20261102T110000Z.json.gz', complete),
            ('data/samrad_snapshots/samrad_20261103T110000Z.json.gz', partial),
        ])
        self.assertEqual((len(runs), len(observations)), (1, 1))
        self.assertEqual(events[0]['last_observed_at'], '2026-11-02T11:00:00Z')

    def test_duplicate_samrad_snapshot_is_not_double_counted(self):
        snapshot = self.samrad_fixture()
        path = 'data/samrad_snapshots/samrad_20261102T110000Z.json.gz'
        runs, observations, events, evidence, index = build_samrad_history([(path, snapshot), (path, snapshot)])
        self.assertEqual((len(runs), len(observations), len(events)), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
