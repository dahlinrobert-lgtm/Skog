#!/usr/bin/env python3
"""Tests for immutable Länsstyrelsen monthly snapshot persistence."""
import tempfile, unittest
from pathlib import Path
from persist_lansstyrelsen_snapshots import persist

def make_run():
    return {
      "run_id":"test-run-001","observed_at":"2026-11-01T12:00:00+00:00",
      "source":"https://diarium.lansstyrelsen.se/default.aspx",
      "county":"Länsstyrelsen i Norrbottens län","search_term":"vattenverksamhet",
      "intervals":[{
        "from":"2026-10-01","to":"2026-10-31","source_total":2,
        "extracted_unique_ids":2,"pager_complete":True,"reconciled":True,
        "records":[
          {"diary_number":"100-2026","title":"A","status":"Handläggning",
           "date":"2026-10-03","links":[{"href":"CaseInfo.aspx?caseID=1"}]},
          {"diary_number":"101-2026","title":"B","status":"Avslutat",
           "date":"2026-10-04","links":[{"href":"CaseInfo.aspx?caseID=2"}]}
        ]
      }]
    }

class SnapshotPersistenceTests(unittest.TestCase):
    def test_complete_run_writes_immutable_jsonl_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); run=make_run()
            m=persist(run,root/"snapshots",root/"manifest.jsonl")
            self.assertTrue(m["run_complete"])
            self.assertTrue(m["snapshot_written"])
            target=root/m["snapshot_path"]
            self.assertEqual(len(target.read_text().splitlines()),2)
            self.assertEqual(len((root/"manifest.jsonl").read_text().splitlines()),1)

    def test_incomplete_run_writes_manifest_but_no_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); run=make_run()
            run["intervals"][0]["pager_complete"]=False
            m=persist(run,root/"snapshots",root/"manifest.jsonl")
            self.assertFalse(m["run_complete"])
            self.assertFalse(m["snapshot_written"])
            self.assertFalse((root/"snapshots").exists())
            self.assertEqual(len((root/"manifest.jsonl").read_text().splitlines()),1)

    def test_repeated_diary_rows_merge_matching_intervals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); run=make_run()
            row=run["intervals"][0]["records"][0]
            run["intervals"][0]["records"]=[row,row]
            run["intervals"][0]["source_total"]=1
            run["intervals"][0]["extracted_unique_ids"]=1
            # A duplicate record is collapsed by its key.
            m=persist(run,root/"snapshots",root/"manifest.jsonl")
            self.assertEqual(m["snapshot_unique_record_count"],1)

    def test_snapshot_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); run=make_run()
            persist(run,root/"snapshots",root/"manifest.jsonl")
            with self.assertRaises(FileExistsError):
                persist(run,root/"snapshots",root/"manifest.jsonl")

if __name__=="__main__":
    unittest.main()
