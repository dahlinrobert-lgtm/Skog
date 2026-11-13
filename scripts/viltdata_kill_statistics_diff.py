#!/usr/bin/env python3
"""Compare two complete Viltdata public harvest-statistics snapshots.

The source snapshots are immutable. Changes are keyed by geography scope,
species ID and year; null is distinct from numeric zero.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from collections import Counter


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def is_missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_value(value):
    return None if is_missing(value) else value


def validate_complete_manifest(manifest, label):
    if manifest.get("complete") is not True or manifest.get("status") != "complete":
        raise ValueError(f"{label} snapshot is not complete")
    species = manifest.get("species")
    requests = [
        item for item in manifest.get("requests", [])
        if item.get("kind") == "statistics"
    ]
    expected = manifest.get("statistics_requests_expected")
    if not isinstance(species, list) or not species:
        raise ValueError(f"{label} manifest has no species inventory")
    if not isinstance(expected, int) or len(requests) != expected:
        raise ValueError(f"{label} manifest statistics request count does not match expected")
    if any(item.get("status") != "ok" for item in requests):
        raise ValueError(f"{label} manifest contains unsuccessful statistics requests")
    return species, requests


def extract_observations(run_dir: pathlib.Path):
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing manifest: {manifest_path}")
    manifest = load_json(manifest_path)
    species, requests = validate_complete_manifest(manifest, run_dir.name)

    id_by_name = {}
    for item in species:
        name = str(item.get("name", "")).strip()
        species_id = item.get("id")
        if not name or not isinstance(species_id, int):
            raise ValueError(f"Invalid species inventory entry in {manifest_path}")
        key = name.casefold()
        if key in id_by_name and id_by_name[key] != species_id:
            raise ValueError(f"Ambiguous species name in manifest: {name}")
        id_by_name[key] = species_id

    observations = {}
    seen_scope_species = set()
    years_seen = set()
    for request in requests:
        scope = request.get("scope")
        species_ids = request.get("species_ids")
        relative_file = request.get("file")
        if not isinstance(scope, str) or not isinstance(species_ids, list) or not relative_file:
            raise ValueError(f"Invalid statistics request metadata in {manifest_path}")
        raw_path = run_dir / pathlib.Path(relative_file)
        if not raw_path.is_file():
            raise ValueError(f"Missing raw statistics file: {raw_path}")
        payload = load_json(raw_path)
        labels = payload.get("labels")
        datasets = payload.get("dataSets")
        if not isinstance(labels, list) or not labels or not isinstance(datasets, list):
            raise ValueError(f"Invalid labels/dataSets in {raw_path}")
        years = []
        for year in labels:
            try:
                years.append(int(year))
            except (TypeError, ValueError):
                raise ValueError(f"Invalid year label {year!r} in {raw_path}") from None
        if len(set(years)) != len(years):
            raise ValueError(f"Duplicate year labels in {raw_path}")
        years_seen.update(years)

        batch_ids = set(species_ids)
        dataset_ids = set()
        for dataset in datasets:
            name = str(dataset.get("label", "")).strip()
            species_id = id_by_name.get(name.casefold())
            if species_id is None:
                raise ValueError(f"Unknown dataset species {name!r} in {raw_path}")
            if species_id not in batch_ids:
                raise ValueError(f"Unexpected species ID {species_id} in {raw_path}")
            if species_id in dataset_ids:
                raise ValueError(f"Duplicate species ID {species_id} in {raw_path}")
            values = dataset.get("data")
            if not isinstance(values, list) or len(values) != len(years):
                raise ValueError(f"Dataset/year length mismatch in {raw_path}: {name}")
            dataset_ids.add(species_id)
            seen_key = (scope, species_id)
            if seen_key in seen_scope_species:
                raise ValueError(f"Species {species_id} appears in multiple batches for {scope}")
            seen_scope_species.add(seen_key)
            for year, value in zip(years, values):
                key = (scope, species_id, year)
                if key in observations:
                    raise ValueError(f"Duplicate observation key: {key}")
                observations[key] = normalize_value(value)

        if dataset_ids != batch_ids:
            missing_ids = sorted(batch_ids - dataset_ids)
            raise ValueError(f"Missing species datasets {missing_ids} in {raw_path}")

    expected_scopes = {item.get("scope") for item in requests}
    if not expected_scopes or None in expected_scopes:
        raise ValueError(f"No valid scopes in {manifest_path}")
    expected_species_ids = {item["id"] for item in species}
    for scope in expected_scopes:
        actual = {sid for seen_scope, sid in seen_scope_species if seen_scope == scope}
        if actual != expected_species_ids:
            raise ValueError(
                f"Species coverage mismatch for {scope}: "
                f"missing={sorted(expected_species_ids - actual)}, "
                f"unexpected={sorted(actual - expected_species_ids)}"
            )

    return manifest, observations, sorted(years_seen)


def classify(old, new):
    if old is None and new is None:
        return "unchanged"
    if old is None and new == 0:
        return "new_zero"
    if old is None:
        return "new_value"
    if new is None:
        return "became_missing"
    if old == new:
        return "unchanged"
    return "value_changed"


def compare_runs(baseline_dir: pathlib.Path, current_dir: pathlib.Path):
    baseline_manifest, old_values, old_years = extract_observations(baseline_dir)
    current_manifest, new_values, new_years = extract_observations(current_dir)

    if baseline_manifest.get("report_type") != current_manifest.get("report_type"):
        raise ValueError("Snapshots have different report types")
    if baseline_manifest.get("report_type") != "kill":
        raise ValueError("Only kill (harvest) snapshots are supported")

    old_keys = set(old_values)
    new_keys = set(new_values)
    if old_keys != new_keys:
        raise ValueError(
            "Snapshot observation coverage differs; refusing to infer additions/removals "
            f"(baseline-only={len(old_keys - new_keys)}, current-only={len(new_keys - old_keys)})"
        )

    names = {item["id"]: item["name"] for item in current_manifest["species"]}
    changes = []
    counts = Counter()
    for scope, species_id, year in sorted(old_keys, key=lambda key: (key[0], key[1], key[2])):
        old = old_values[(scope, species_id, year)]
        new = new_values[(scope, species_id, year)]
        change_type = classify(old, new)
        counts[change_type] += 1
        if change_type != "unchanged":
            changes.append({
                "scope": scope,
                "species_id": species_id,
                "species": names.get(species_id),
                "year": year,
                "change": change_type,
                "old_value": old,
                "new_value": new,
            })

    summary = {
        "schema_version": 1,
        "report_type": "kill",
        "baseline_run_id": baseline_manifest.get("run_id", baseline_dir.name),
        "current_run_id": current_manifest.get("run_id", current_dir.name),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "baseline_observations": len(old_values),
        "current_observations": len(new_values),
        "changed_observations": len(changes),
        "counts": {name: counts.get(name, 0) for name in (
            "new_value", "new_zero", "value_changed", "became_missing", "unchanged"
        )},
        "years": {"baseline": old_years, "current": new_years},
    }
    return summary, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=pathlib.Path, help="Baseline snapshot directory")
    parser.add_argument("current", type=pathlib.Path, help="Current snapshot directory")
    parser.add_argument("--output", type=pathlib.Path,
                        help="Output directory (default: <snapshot-root>/diffs/<baseline>_to_<current>)")
    args = parser.parse_args()

    try:
        summary, changes = compare_runs(args.baseline, args.current)
        output = args.output or (
            args.baseline.parent / "diffs" /
            f"{args.baseline.name}_to_{args.current.name}"
        )
        output.mkdir(parents=True, exist_ok=False)
        (output / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output / "changes.json").write_text(
            json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "status": "complete",
            "output_dir": str(output),
            "changed_observations": summary["changed_observations"],
            "counts": summary["counts"],
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
