#!/usr/bin/env python3
"""Flag repeated hunt-area titles within the same Viltdata part and parent.

Reads an immutable geography-inventory run. It never changes raw API responses.
Python 3.10+, standard library only.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import re
import unicodedata


def normalize_title(value):
    """Normalize Unicode, whitespace and case without removing meaningful text."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def inspect_run(run_dir):
    raw_areas = run_dir / "raw" / "areas"
    if not raw_areas.is_dir():
        raise FileNotFoundError(f"Missing raw area directory: {raw_areas}")

    groups = collections.defaultdict(list)
    files_read = 0
    records_read = 0
    for path in sorted(raw_areas.glob("*.json")):
        try:
            part_id = int(path.stem)
        except ValueError:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array in {path}")
        files_read += 1
        for item in payload:
            if not isinstance(item, dict):
                continue
            area_id = item.get("id")
            parent_id = item.get("parentId")
            title = item.get("title")
            if not isinstance(area_id, int) or not isinstance(title, str):
                continue
            records_read += 1
            if parent_id is None:
                continue
            normalized = normalize_title(title)
            if not normalized:
                continue
            groups[(part_id, parent_id, normalized)].append({
                "id": area_id,
                "parent_id": parent_id,
                "part_id": part_id,
                "title": title,
            })

    candidates = []
    for (part_id, parent_id, normalized), records in sorted(groups.items()):
        unique_ids = sorted({record["id"] for record in records})
        if len(unique_ids) < 2:
            continue
        candidates.append({
            "part_id": part_id,
            "parent_id": parent_id,
            "normalized_title": normalized,
            "title": records[0]["title"],
            "area_ids": unique_ids,
            "record_count": len(records),
        })

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_run": str(run_dir),
        "rule": "same part_id + parentId + normalized title, with at least two distinct area IDs",
        "files_read": files_read,
        "records_read": records_read,
        "candidate_groups": len(candidates),
        "candidate_records": sum(item["record_count"] for item in candidates),
        "candidates": candidates,
        "raw_data_modified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", help="Timestamped geography-inventory run directory")
    parser.add_argument("--output", help="Output JSON path (default: <run_dir>/qa/duplicate-area-titles.json)")
    args = parser.parse_args()

    run_dir = pathlib.Path(args.run_dir)
    report = inspect_run(run_dir)
    output = pathlib.Path(args.output) if args.output else run_dir / "qa" / "duplicate-area-titles.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(output),
        "files_read": report["files_read"],
        "records_read": report["records_read"],
        "candidate_groups": report["candidate_groups"],
        "candidate_records": report["candidate_records"],
        "raw_data_modified": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
