#!/usr/bin/env python3
"""Compare two immutable Viltdata geography inventory runs.

Identity is (level, API id). Parent-child links are compared separately from
record fields. Missing IDs are reported only when both runs are complete.
Python 3.10+, standard library only.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys


LEVELS = ("counties", "afos", "parts", "areas")


def load_run(run_dir):
    run_dir = pathlib.Path(run_dir)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("requests"), list):
        raise ValueError(f"Invalid manifest: {manifest_path}")

    records = {}
    links = set()
    for request in manifest["requests"]:
        if request.get("status") != "ok":
            continue
        level = request.get("level")
        rel_file = request.get("file")
        if level not in LEVELS or not rel_file:
            continue
        path = run_dir / rel_file
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Expected JSON array: {path}")
        parent_id = request.get("parent_id")
        parent_level = {
            "afos": "counties",
            "parts": "afos",
            "areas": "parts",
        }.get(level)
        for item in payload:
            if not isinstance(item, dict) or not isinstance(item.get("id"), int):
                raise ValueError(f"Invalid record in {path}")
            key = (level, item["id"])
            if key in records and records[key] != item:
                raise ValueError(f"Conflicting metadata for {level} id={item['id']}")
            records[key] = item
            if parent_level:
                links.add((parent_level, parent_id, level, item["id"]))

    return {
        "run_dir": str(run_dir),
        "manifest": manifest,
        "records": records,
        "links": links,
    }


def record_changes(old, new):
    fields = sorted(set(old) | set(new))
    return [
        {"field": field, "before": old.get(field), "after": new.get(field)}
        for field in fields if old.get(field) != new.get(field)
    ]


def compare_runs(baseline_dir, current_dir):
    baseline = load_run(baseline_dir)
    current = load_run(current_dir)
    old_records, new_records = baseline["records"], current["records"]
    old_keys, new_keys = set(old_records), set(new_records)
    both_complete = (
        baseline["manifest"].get("complete") is True
        and current["manifest"].get("complete") is True
    )

    added = [
        {"level": level, "id": ident, "record": new_records[(level, ident)]}
        for level, ident in sorted(new_keys - old_keys)
    ]
    changed = []
    for level, ident in sorted(old_keys & new_keys):
        fields = record_changes(old_records[(level, ident)], new_records[(level, ident)])
        if fields:
            changed.append({"level": level, "id": ident, "changes": fields})

    removed = []
    if both_complete:
        removed = [
            {"level": level, "id": ident, "record": old_records[(level, ident)]}
            for level, ident in sorted(old_keys - new_keys)
        ]

    old_links, new_links = baseline["links"], current["links"]
    link_additions = [
        {"parent_level": pl, "parent_id": pi, "child_level": cl, "child_id": ci}
        for pl, pi, cl, ci in sorted(new_links - old_links)
    ]
    link_removals = []
    if both_complete:
        link_removals = [
            {"parent_level": pl, "parent_id": pi, "child_level": cl, "child_id": ci}
            for pl, pi, cl, ci in sorted(old_links - new_links)
        ]

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "baseline_run": baseline["run_dir"],
        "current_run": current["run_dir"],
        "baseline_complete": baseline["manifest"].get("complete") is True,
        "current_complete": current["manifest"].get("complete") is True,
        "deletions_enabled": both_complete,
        "counts": {
            "baseline_records": len(old_records),
            "current_records": len(new_records),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "relationship_additions": len(link_additions),
            "relationship_removals": len(link_removals),
            "unconfirmed_missing": len(old_keys - new_keys) if not both_complete else 0,
            "unconfirmed_relationship_removals": len(old_links - new_links) if not both_complete else 0,
        },
        "added": added,
        "removed": removed,
        "changed": changed,
        "relationship_additions": link_additions,
        "relationship_removals": link_removals,
        "safety_notes": [
            "Identity is based on API level and ID, never title.",
            "Area parentId is retained as a record field; part-to-area membership is tracked separately from manifest request parameters.",
            "Missing records and removed relationships are reported only when both snapshots are complete.",
            "Raw snapshot data is read-only and is never modified.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="Baseline timestamped inventory directory")
    parser.add_argument("current", help="Current timestamped inventory directory")
    parser.add_argument("--output", help="Output JSON file; defaults to data/viltdata/geography-comparisons/")
    args = parser.parse_args()

    report = compare_runs(args.baseline, args.current)
    if args.output:
        output = pathlib.Path(args.output)
    else:
        base_name = pathlib.Path(args.baseline).name
        current_name = pathlib.Path(args.current).name
        output = pathlib.Path("data/viltdata/geography-comparisons") / f"{base_name}__{current_name}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite comparison: {output}")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report["counts"],
                      "deletions_enabled": report["deletions_enabled"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
