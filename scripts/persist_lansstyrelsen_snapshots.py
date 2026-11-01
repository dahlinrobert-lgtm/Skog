#!/usr/bin/env python3
"""Append immutable, reconciled Länsstyrelsen diary search snapshots.

Snapshot rows are observations at collection time, not a claim that a case was
newly created or that an absent case was removed. Failed/incomplete intervals
are recorded in the run manifest but never emitted as snapshot rows.
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

def load_json(path: Path, default: Any) -> Any:
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))

def validate_interval(item: dict) -> tuple[bool,str|None]:
    total=item.get("source_total")
    count=item.get("extracted_unique_ids")
    if item.get("error"): return False,str(item["error"])
    if not item.get("pager_complete"): return False,"pagination_not_complete"
    if total is None or count is None: return False,"unknown_source_total_or_extracted_count"
    if int(total)!=int(count): return False,f"count_mismatch:{count}!={total}"
    if not item.get("reconciled"): return False,"interval_not_reconciled"
    return True,None

def build_rows(run: dict) -> tuple[list[dict],dict]:
    rows=[]; seen={}
    for interval in run.get("intervals",[]):
        ok,why=validate_interval(interval)
        if not ok:
            continue
        county=str(run["county"]).strip()
        phrase=str(run["search_term"]).strip()
        for raw in interval.get("records",[]):
            diary_number=str(raw.get("diary_number") or "").strip()
            if not diary_number:
                return [],{"ok":False,"error":"record_without_diary_number"}
            key=f"{county.casefold()}::{diary_number}"
            row={
                "run_id":run["run_id"],"observed_at":run["observed_at"],
                "county":county,"diary_number":diary_number,
                "search_terms":sorted(set([phrase])),
                "registration_interval":{"from":interval["from"],"to":interval["to"]},
                "source_date":raw.get("date") or raw.get("In/Upp-datum"),
                "title":raw.get("title") or raw.get("Ärenderubrik"),
                "status":raw.get("status") or raw.get("Status"),
                "public_case_url":next((x.get("href") for x in raw.get("links",[])
                                         if isinstance(x,dict) and x.get("href")),None),
                "columns":raw,
            }
            row["content_hash"]=digest({k:v for k,v in row.items() if k not in {"run_id","observed_at","content_hash","search_terms","registration_interval"}})
            if key in seen:
                prev=rows[seen[key]]
                prev["search_terms"]=sorted(set(prev["search_terms"]+[phrase]))
                # Preserve all source intervals in which this case matched.
                prev.setdefault("matching_intervals",[]).append(row["registration_interval"])
            else:
                row["matching_intervals"]=[row["registration_interval"]]
                seen[key]=len(rows); rows.append(row)
    return rows,{"ok":True,"unique_records":len(rows)}

def persist(run:dict, snapshots_root:Path, manifest_path:Path) -> dict:
    intervals=run.get("intervals",[])
    checks=[validate_interval(x) for x in intervals]
    complete=bool(intervals) and all(ok for ok,_ in checks)
    rows,build=build_rows(run)
    complete=complete and build.get("ok",False)
    manifest={
        "schema_version":1,"run_id":run["run_id"],"observed_at":run["observed_at"],
        "source":run.get("source"),"county":run["county"],"search_term":run["search_term"],
        "interval_count":len(intervals),
        "intervals":[{k:v for k,v in x.items() if k!="records"} |
                     {"reconciled":validate_interval(x)[0],
                      "validation_error":validate_interval(x)[1],
                      "extracted_records":len(x.get("records",[]))}
                     for x in intervals],
        "intervals_complete":sum(ok for ok,_ in checks),
        "intervals_failed":sum(not ok for ok,_ in checks),
        "run_complete":complete,
        "snapshot_unique_record_count":len(rows) if complete else 0,
        "snapshot_written":False,
        "warning":"A missing case is not marked removed. This archive records only the records returned by completed source queries.",
    }
    if not complete:
        manifest["error"]="Run incomplete; no partial snapshot rows persisted."
    else:
        manifest["snapshot_written"]=True
        target=snapshots_root / run["observed_at"][:4] / run["observed_at"][5:7] / f"{run['run_id']}.jsonl"
        target.parent.mkdir(parents=True,exist_ok=True)
        # Immutable path: refuse to overwrite an earlier snapshot.
        if target.exists():
            raise FileExistsError(f"Snapshot already exists: {target}")
        target.write_text("".join(canonical(row)+"\n" for row in rows),encoding="utf-8")
        manifest["snapshot_path"]=str(target)
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    manifest_path.open("a",encoding="utf-8").write(canonical(manifest)+"\n")
    return manifest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--snapshots-root",type=Path,default=Path("data/lansstyrelsen-diary/snapshots"))
    parser.add_argument("--manifest",type=Path,default=Path("data/lansstyrelsen-diary/snapshot-runs.jsonl"))
    args=parser.parse_args()
    run=json.loads(args.input.read_text(encoding="utf-8"))
    result=persist(run,args.snapshots_root,args.manifest)
    print(json.dumps(result,ensure_ascii=False))
    if not result["run_complete"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
