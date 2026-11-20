#!/usr/bin/env python3
"""Restore missing historical Länsstyrelsen case metadata from a trusted Git baseline.

Baseline values fill gaps and restore missing handling rows. Non-empty current
observations remain authoritative. A machine-readable report is written so the
restoration can be reviewed before the resulting PR is merged.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys

# When this file is executed directly, Python puts scripts/ (not the repository
# root) on sys.path. Add the repository root so the shared collector module can
# be imported consistently in GitHub Actions and local runs.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.collect_lansstyrelsen_case_handlings import merge_case_record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument(
        "--details",
        type=Path,
        default=Path("data/lansstyrelsen-diary/case-details.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("lansstyrelsen-history-restoration-report.json"),
    )
    args = parser.parse_args()

    relative = args.details.as_posix()
    baseline_raw = subprocess.check_output(
        ["git", "show", f"{args.baseline_ref}:{relative}"], text=True
    )
    baseline = json.loads(baseline_raw)
    current = json.loads(args.details.read_text(encoding="utf-8"))
    baseline_cases = baseline.get("cases") or {}
    current_cases = current.setdefault("cases", {})

    restored_cases = 0
    restored_handlings = 0
    restored_fields = 0
    for key, old_record in baseline_cases.items():
        fresh = current_cases.get(key)
        if fresh is None:
            current_cases[key] = old_record
            restored_cases += 1
            restored_handlings += len(old_record.get("handlings") or [])
            restored_fields += sum(
                1 for value in (old_record.get("case") or {}).values()
                if value is not None and str(value).strip()
            )
            continue

        before_handlings = {
            h.get("handling_key") or h.get("handling_number")
            for h in (fresh.get("handlings") or [])
        }
        before_case = dict(fresh.get("case") or {})
        merged = merge_case_record(old_record, fresh)
        after_handlings = {
            h.get("handling_key") or h.get("handling_number")
            for h in (merged.get("handlings") or [])
        }
        restored_handlings += len(after_handlings - before_handlings)
        restored_fields += sum(
            1 for field, value in (old_record.get("case") or {}).items()
            if value is not None and str(value).strip()
            and not (before_case.get(field) is not None and str(before_case.get(field)).strip())
        )
        current_cases[key] = merged

    args.details.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema_version": "1.0",
        "baseline_ref": args.baseline_ref,
        "baseline_case_count": len(baseline_cases),
        "current_case_count": len(current_cases),
        "restored_cases": restored_cases,
        "restored_handling_rows": restored_handlings,
        "restored_case_fields": restored_fields,
        "status": "completed",
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
