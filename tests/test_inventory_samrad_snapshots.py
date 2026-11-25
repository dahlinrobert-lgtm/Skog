from __future__ import annotations
import gzip, json, tempfile, unittest
from pathlib import Path
from scripts.inventory_samrad_snapshots import case_identity_index, inventory_snapshot_files

def complete_snapshot():
    def layer(features):
        count = len(features)
        return ({"status":"success","features":features},
                {"pages":1 if count else 0,"records_fetched_in_envelope":count,
                 "records_in_scope":count,"records_outside_scope":0,
                 "records_missing_geometry":0,"records_geometry_error":0})
    points, pc = layer([])
    lines, lc = layer([{"id":47112,"properties":{"ObjectId":47112}}])
    areas, ac = layer([])
    return {"source_id":"skogsstyrelsen.samrad","status":"success",
            "checked_at":"2026-11-01T12:00:00Z","scope_hash":"test-scope",
            "layers":{"points":points,"lines":lines,"areas":areas},
            "counts":{"points":pc,"lines":lc,"areas":ac}}

class SamradArchiveInventoryTests(unittest.TestCase):
    def test_complete_snapshot_is_eligible_and_exposes_stable_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"samrad_20261101T120000Z.json.gz"
            with gzip.open(path,"wt",encoding="utf-8") as handle: json.dump(complete_snapshot(),handle)
            rows,_=inventory_snapshot_files(Path(tmp))
        self.assertEqual(rows[0]["eligibility"],"eligible")
        self.assertTrue(rows[0]["production_gate_complete"])
        self.assertEqual(rows[0]["layer_ids"]["lines"],["lines:47112"])

    def test_case_identity_uses_the_production_grouping_rule(self):
        snapshot = complete_snapshot()
        snapshot["layers"]["lines"]["features"][0]["properties"]["Beteckn"] = "ABC-123"
        index = case_identity_index(snapshot)
        self.assertEqual(index["lines:47112"]["group_key"], "case:abc-123")
        self.assertTrue(index["lines:47112"]["event_id"].startswith("samrad-case:"))

    def test_legacy_format_without_geometry_counters_is_not_assumed_complete(self):
        snapshot = complete_snapshot()
        for count in snapshot["counts"].values():
            count.pop("records_outside_scope")
            count.pop("records_missing_geometry")
            count.pop("records_geometry_error")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"samrad_20261101T120000Z.json.gz"
            with gzip.open(path,"wt",encoding="utf-8") as handle: json.dump(snapshot,handle)
            rows,_=inventory_snapshot_files(Path(tmp))
        self.assertEqual(rows[0]["eligibility"],"excluded")
        self.assertFalse(rows[0]["production_gate_complete"])
        self.assertTrue(any("records_missing_geometry" in reason for reason in rows[0]["reasons"]))

    def test_partial_snapshot_is_excluded_with_reason(self):
        snapshot=complete_snapshot()
        snapshot["layers"]["lines"]["status"]="partial"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"samrad_20261101T120000Z.json.gz"
            with gzip.open(path,"wt",encoding="utf-8") as handle: json.dump(snapshot,handle)
            rows,_=inventory_snapshot_files(Path(tmp))
        self.assertEqual(rows[0]["eligibility"],"excluded")
        self.assertIn("lines:layer_status_not_success",rows[0]["reasons"])

    def test_unreadable_archive_is_reported_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"samrad_20261101T120000Z.json.gz"
            path.write_bytes(b"not a gzip file")
            rows,_=inventory_snapshot_files(Path(tmp))
        self.assertEqual(rows[0]["eligibility"],"unreadable")
        self.assertNotIn("layer_ids",rows[0])

if __name__=="__main__": unittest.main()
