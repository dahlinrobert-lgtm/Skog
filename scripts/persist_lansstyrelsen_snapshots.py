#!/usr/bin/env python3
"""Append immutable, reconciled Länsstyrelsen diary search snapshots.

Each file is one complete run for one county and one phrase. Reconciled month
intervals only are emitted. Incomplete attempts get a manifest entry but no
snapshot rows. Absence is never interpreted as source deletion.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def canonical(value: Any) -> str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def validate_interval(item: dict) -> tuple[bool,str|None]:
    total=item.get("source_total"); count=item.get("extracted_unique_ids")
    if item.get("error"): return False,str(item["error"])
    if not item.get("pager_complete"): return False,"pagination_not_complete"
    if total is None or count is None: return False,"unknown_source_total_or_extracted_count"
    if int(total)!=int(count): return False,f"count_mismatch:{count}!={total}"
    if not item.get("reconciled"): return False,"interval_not_reconciled"
    records=item.get("records")
    if not isinstance(records,list) or len(records)!=int(count):
        return False,"records_missing_or_count_mismatch"
    ids=[str(x.get("diary_number") or "").strip() for x in records]
    if any(not x for x in ids) or len(set(ids))!=len(ids):
        return False,"missing_or_duplicate_diary_numbers_in_records"
    return True,None

def build_rows(run: dict) -> tuple[list[dict],dict]:
    rows=[]; seen={}
    for interval in run.get("intervals",[]):
        ok,_=validate_interval(interval)
        if not ok: continue
        county=str(run["county"]).strip(); phrase=str(run["search_term"]).strip()
        for raw in interval["records"]:
            diary_number=str(raw["diary_number"]).strip()
            key=f"{county.casefold()}::{diary_number}"
            row={
              "run_id":run["run_id"],"observed_at":run["observed_at"],
              "county":county,"diary_number":diary_number,
              "search_terms":[phrase],
              "registration_interval":{"from":interval["from"],"to":interval["to"]},
              "source_date":raw.get("date") or raw.get("In/Upp-datum"),
              "title":raw.get("title") or raw.get("Ärenderubrik"),
              "status":raw.get("status") or raw.get("Status"),
              "public_case_url":next((x.get("href") for x in raw.get("links",[])
                                      if isinstance(x,dict) and x.get("href")),None),
              "columns":raw,
            }
            row["content_hash"]=digest({k:v for k,v in row.items()
              if k not in {"run_id","observed_at","content_hash","search_terms","registration_interval"}})
            if key in seen:
                prev=rows[seen[key]]
                prev["search_terms"]=sorted(set(prev["search_terms"]+[phrase]))
                prev["matching_intervals"].append(row["registration_interval"])
            else:
                row["matching_intervals"]=[row["registration_interval"]]
                seen[key]=len(rows); rows.append(row)
    return rows,{"ok":True,"unique_records":len(rows)}

def persist(run:dict,snapshots_root:Path,manifest_path:Path) -> dict:
    intervals=run.get("intervals",[])
    checks=[validate_interval(x) for x in intervals]
    # A single phrase/county/month run must contain exactly one requested
    # interval. The orchestrator can declare complete only after every run succeeds.
    complete=len(intervals)==1 and all(ok for ok,_ in checks)
    rows,build=build_rows(run); complete=complete and build.get("ok",False)
    manifest={
      "schema_version":1,"run_id":run["run_id"],"observed_at":run["observed_at"],
      "source":run.get("source"),"county":run["county"],"search_term":run["search_term"],
      "interval_count":len(intervals),
      "intervals":[{k:v for k,v in x.items() if k!="records"} |
        {"reconciled":validate_interval(x)[0],"validation_error":validate_interval(x)[1],
         "extracted_records":len(x.get("records",[]))} for x in intervals],
      "intervals_complete":sum(ok for ok,_ in checks),"intervals_failed":sum(not ok for ok,_ in checks),
      "run_complete":complete,"snapshot_unique_record_count":len(rows) if complete else 0,
      "snapshot_written":False,
      "warning":"A missing case is not marked removed. This is an observation of returned public search results.",
    }
    if not complete:
      manifest["error"]="Run incomplete; no snapshot rows persisted."
    else:
      target=snapshots_root/run["observed_at"][:4]/run["observed_at"][5:7]/f"{run['run_id']}.jsonl"
      target.parent.mkdir(parents=True,exist_ok=True)
      if target.exists(): raise FileExistsError(f"Snapshot already exists: {target}")
      target.write_text("".join(canonical(row)+"\n" for row in rows),encoding="utf-8")
      manifest["snapshot_written"]=True; manifest["snapshot_path"]=str(target)
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    with manifest_path.open("a",encoding="utf-8") as stream:
      stream.write(canonical(manifest)+"\n")
    return manifest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--snapshots-root",type=Path,default=Path("data/lansstyrelsen-diary/snapshots"))
    parser.add_argument("--manifest",type=Path,default=Path("data/lansstyrelsen-diary/snapshot-runs.jsonl"))
    a=parser.parse_args()
    run=json.loads(a.input.read_text(encoding="utf-8"))
    result=persist(run,a.snapshots_root,a.manifest)
    print(json.dumps(result,ensure_ascii=False))
    if not result["run_complete"]: raise SystemExit(1)
if __name__=="__main__": main()
