#!/usr/bin/env python3
"""Validate a Skog event bundle, including cross-record references."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - actionable CLI error
    raise SystemExit("Missing dependency: install requirements.txt (jsonschema).") from exc

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "data-platform" / "schemas" / "event-bundle.schema.json"


def unique_index(rows: list[dict[str, Any]], key: str, label: str, errors: list[str]) -> set[str]:
    values: set[str] = set()
    for index, row in enumerate(rows):
        value = row.get(key)
        if value in values:
            errors.append(f"duplicate {label}: {value!r}")
        values.add(value)
    return values


def validate_bundle(bundle: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        f"schema: {'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in validator.iter_errors(bundle)
    ]
    if errors or not isinstance(bundle, dict):
        return errors

    runs = bundle["source_runs"]
    observations = bundle["observations"]
    events = bundle["events"]
    evidence = bundle["evidence"]
    relationships = bundle["relationships"]
    chains = bundle["chains"]

    run_ids = unique_index(runs, "run_id", "run_id", errors)
    observation_ids = unique_index(observations, "observation_id", "observation_id", errors)
    event_ids = unique_index(events, "event_id", "event_id", errors)
    relationship_ids = unique_index(relationships, "relationship_id", "relationship_id", errors)
    unique_index(chains, "chain_id", "chain_id", errors)

    source_keys: set[tuple[str, str, str]] = set()
    for row in observations:
        key = (row["source_id"], row["source_record_id"], row["content_hash"])
        if key in source_keys:
            errors.append(f"duplicate source observation version: {key!r}")
        source_keys.add(key)
        if row["run_id"] not in run_ids:
            errors.append(f"observation {row['observation_id']}: unknown run_id {row['run_id']!r}")

    evidence_keys: set[tuple[str, str, str]] = set()
    for row in evidence:
        if row["event_id"] not in event_ids:
            errors.append(f"evidence: unknown event_id {row['event_id']!r}")
        if row["observation_id"] not in observation_ids:
            errors.append(f"evidence: unknown observation_id {row['observation_id']!r}")
        key = (row["event_id"], row["observation_id"], row["evidence_role"])
        if key in evidence_keys:
            errors.append(f"duplicate event evidence link: {key!r}")
        evidence_keys.add(key)

    for row in relationships:
        if row["from_event_id"] not in event_ids:
            errors.append(f"relationship {row['relationship_id']}: unknown from_event_id")
        if row["to_event_id"] not in event_ids:
            errors.append(f"relationship {row['relationship_id']}: unknown to_event_id")
        if row["from_event_id"] == row["to_event_id"]:
            errors.append(f"relationship {row['relationship_id']}: self-link is not allowed")
        for ref in row.get("evidence_refs", []):
            if ref not in observation_ids:
                errors.append(f"relationship {row['relationship_id']}: unknown evidence observation {ref!r}")

    for row in chains:
        unknown = sorted(set(row["event_ids"]) - event_ids)
        if unknown:
            errors.append(f"chain {row['chain_id']}: unknown event_ids {unknown!r}")

    # A failed or partial source run must never be used as evidence of source absence.
    run_by_id = {row["run_id"]: row for row in runs}
    for row in observations:
        run = run_by_id.get(row["run_id"])
        if run and run["status"] != "success" and row["quality_status"] == "valid":
            errors.append(
                f"observation {row['observation_id']}: valid observation references "
                f"{run['status']} run {run['run_id']!r}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", nargs="?", type=Path,
                        default=ROOT / "data-platform" / "examples" / "event-bundle.example.json")
    args = parser.parse_args()
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_bundle(bundle, schema)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Event bundle valid: "
        f"{len(bundle['source_runs'])} runs, "
        f"{len(bundle['observations'])} observations, "
        f"{len(bundle['events'])} events, "
        f"{len(bundle['evidence'])} evidence links, "
        f"{len(bundle['relationships'])} relationships, "
        f"{len(bundle['chains'])} chains."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
