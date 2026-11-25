#!/usr/bin/env python3
"""Read-only inventory of dated Samråd snapshots against the production eligibility gate."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from shapely.geometry import shape

try:
    import build_harvest_event_bundle as builder
except ModuleNotFoundError:
    from scripts import build_harvest_event_bundle as builder

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "data" / "samrad_snapshots"
BUNDLE_PATH = ROOT / "data" / "harvest_event_bundle.json"
NAME_PATTERN = re.compile(r"^samrad_(\d{8}T\d{6}Z)\.json\.gz$")


def feature_ids(snapshot: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    layers = snapshot.get("layers")
    if not isinstance(layers, dict):
        return result
    for layer_name in ("points", "lines", "areas"):
        layer = layers.get(layer_name)
        features = layer.get("features") if isinstance(layer, dict) else None
        ids: list[str] = []
        if isinstance(features, list):
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                props = feature.get("properties") or {}
                value = feature.get("id")
                if value in (None, ""):
                    value = props.get("ObjectId")
                if value in (None, ""):
                    value = props.get("OBJECTID")
                if value not in (None, ""):
                    ids.append(f"{layer_name}:{value}")
        result[layer_name] = sorted(set(ids))
    return result


def eligibility_diagnostics(snapshot: dict[str, Any]) -> list[str]:
    """Explain the current production gate without changing or relaxing it."""
    reasons: list[str] = []
    if snapshot.get("source_id") != builder.SAMRAD_SOURCE:
        reasons.append("source_id_missing_or_unexpected")
    if snapshot.get("status") != "success":
        reasons.append("snapshot_status_not_success")
    if not builder.timestamp(snapshot.get("checked_at")):
        reasons.append("checked_at_missing_or_invalid")
    if not str(snapshot.get("scope_hash") or "").strip():
        reasons.append("scope_hash_missing")
    layers, counts = snapshot.get("layers"), snapshot.get("counts")
    if not isinstance(layers, dict):
        reasons.append("layers_missing_or_invalid")
    if not isinstance(counts, dict):
        reasons.append("counts_missing_or_invalid")
    if not isinstance(layers, dict) or not isinstance(counts, dict):
        return reasons
    required = ("pages", "records_fetched_in_envelope", "records_in_scope",
                "records_outside_scope", "records_missing_geometry", "records_geometry_error")
    for name in ("points", "lines", "areas"):
        layer, count = layers.get(name), counts.get(name)
        if not isinstance(layer, dict):
            reasons.append(f"{name}:layer_missing_or_invalid")
            continue
        if layer.get("status") != "success":
            reasons.append(f"{name}:layer_status_not_success")
        if not isinstance(count, dict):
            reasons.append(f"{name}:counts_missing_or_invalid")
            continue
        features = layer.get("features")
        if not isinstance(features, list):
            reasons.append(f"{name}:features_missing_or_invalid")
            continue
        if not features and count.get("records_in_scope") != 0:
            reasons.append(f"{name}:empty_features_without_zero_scope_count")
        missing = [key for key in required if not isinstance(count.get(key), int)]
        if missing:
            reasons.append(f"{name}:invalid_or_missing_integer_counts:{','.join(missing)}")
            continue
        if count["records_in_scope"] != len(features):
            reasons.append(f"{name}:records_in_scope_does_not_match_feature_count")
        if count["pages"] < 1 and not (
            count["pages"] == 0 and features == []
            and count["records_fetched_in_envelope"] == 0
            and count["records_in_scope"] == 0
            and count["records_outside_scope"] == 0
        ):
            reasons.append(f"{name}:invalid_page_count")
        if count["records_missing_geometry"] != 0:
            reasons.append(f"{name}:records_missing_geometry_nonzero")
        if count["records_geometry_error"] != 0:
            reasons.append(f"{name}:records_geometry_error_nonzero")
        if count["records_fetched_in_envelope"] != count["records_in_scope"] + count["records_outside_scope"]:
            reasons.append(f"{name}:envelope_count_reconciliation_failed")
    return reasons



def layer_diagnostics(snapshot: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    layers = snapshot.get("layers")
    counts = snapshot.get("counts")
    for name in ("points", "lines", "areas"):
        layer = layers.get(name) if isinstance(layers, dict) else None
        count = counts.get(name) if isinstance(counts, dict) else None
        features = layer.get("features") if isinstance(layer, dict) else None
        if not isinstance(features, list):
            result[name] = {"layer_status": layer.get("status") if isinstance(layer, dict) else None,
                            "features_count": None, "count_fields_present": sorted(count) if isinstance(count, dict) else [],
                            "layer_fields_present": sorted(key for key in layer if key != "features") if isinstance(layer, dict) else [],
                            "layer_numeric_metadata": {key: value for key, value in layer.items() if key != "features" and isinstance(value, int) and not isinstance(value, bool)} if isinstance(layer, dict) else {},
                            "geometry_missing_or_empty": None, "geometry_unparseable": None, "geometry_invalid": None}
            continue
        missing = unparseable = invalid = 0
        ids: list[str] = []
        for feature in features:
            if not isinstance(feature, dict):
                unparseable += 1
                continue
            props = feature.get("properties") or {}
            object_id = feature.get("id") or props.get("ObjectId") or props.get("OBJECTID")
            if object_id not in (None, ""):
                ids.append(str(object_id))
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                missing += 1
                continue
            try:
                parsed = shape(geometry)
                if parsed.is_empty:
                    missing += 1
                elif not parsed.is_valid:
                    invalid += 1
            except Exception:
                unparseable += 1
        result[name] = {
            "layer_status": layer.get("status") if isinstance(layer, dict) else None,
            "features_count": len(features),
            "count_fields_present": sorted(count) if isinstance(count, dict) else [],
            "layer_fields_present": sorted(key for key in layer if key != "features") if isinstance(layer, dict) else [],
            "layer_numeric_metadata": {key: value for key, value in layer.items() if key != "features" and isinstance(value, int) and not isinstance(value, bool)} if isinstance(layer, dict) else {},
            "feature_ids_unique": len(ids) == len(set(ids)),
            "feature_ids_without_stable_id": len(features) - len(ids),
            "geometry_missing_or_empty": missing,
            "geometry_unparseable": unparseable,
            "geometry_invalid": invalid,
        }
    return result


def inventory_snapshot_files(directory: Path) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    rows: list[dict[str, Any]] = []
    eligible_ids: dict[str, set[str]] = defaultdict(set)
    for path in sorted(directory.glob("samrad_*.json.gz")):
        row: dict[str, Any] = {"file": path.name, "eligibility": "unknown", "reasons": []}
        if not NAME_PATTERN.fullmatch(path.name):
            row["eligibility"] = "excluded"
            row["reasons"] = ["filename_does_not_match_archive_pattern"]
            rows.append(row)
            continue
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                snapshot = json.load(handle)
        except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            row["eligibility"] = "unreadable"
            row["reasons"] = [f"{type(exc).__name__}:{str(exc)[:300]}"]
            rows.append(row)
            continue
        if not isinstance(snapshot, dict):
            row["eligibility"] = "excluded"
            row["reasons"] = ["payload_is_not_json_object"]
            rows.append(row)
            continue
        row["checked_at"] = snapshot.get("checked_at")
        row["source_id"] = snapshot.get("source_id")
        row["status"] = snapshot.get("status")
        row["scope_hash_present"] = bool(str(snapshot.get("scope_hash") or "").strip())
        row["layer_ids"] = feature_ids(snapshot)
        row["layer_counts"] = snapshot.get("counts") if isinstance(snapshot.get("counts"), dict) else None
        row["layer_diagnostics"] = layer_diagnostics(snapshot)
        row["production_gate_complete"] = builder.samrad_snapshot_is_complete(snapshot)
        row["reasons"] = eligibility_diagnostics(snapshot)
        row["eligibility"] = "eligible" if row["production_gate_complete"] else "excluded"
        if row["production_gate_complete"]:
            for ids in row["layer_ids"].values():
                for source_id in ids:
                    eligible_ids[source_id].add(source_id)
        rows.append(row)
    return rows, eligible_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "samrad-snapshot-inventory.json")
    args = parser.parse_args()

    rows, _ = inventory_snapshot_files(SNAPSHOT_DIR)
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    bundle_ids = {
        str(row.get("source_record_id"))
        for row in bundle.get("observations", [])
        if row.get("source_id") == builder.SAMRAD_SOURCE and row.get("source_record_id")
    }
    eligible_ids = {
        source_id
        for row in rows if row["eligibility"] == "eligible"
        for layer_ids in (row.get("layer_ids") or {}).values()
        for source_id in layer_ids
    }
    archive_only = sorted(eligible_ids - bundle_ids)
    bundle_only = sorted(bundle_ids - eligible_ids)
    counts = {
        "files_total": len(rows),
        "eligible": sum(row["eligibility"] == "eligible" for row in rows),
        "excluded": sum(row["eligibility"] == "excluded" for row in rows),
        "unreadable": sum(row["eligibility"] == "unreadable" for row in rows),
    }
    report = {
        "schema_version": 1,
        "mode": "read_only",
        "production_eligibility_function": "scripts/build_harvest_event_bundle.py:samrad_snapshot_is_complete",
        "snapshot_directory": "data/samrad_snapshots",
        "event_bundle": "data/harvest_event_bundle.json",
        "summary": counts,
        "eligible_archive_unique_source_record_ids": len(eligible_ids),
        "bundle_unique_samrad_source_record_ids": len(bundle_ids),
        "archive_ids_not_in_bundle": archive_only,
        "bundle_ids_not_in_eligible_archive": bundle_only,
        "snapshots": rows,
        "interpretation": [
            "Only snapshots accepted by the unchanged production gate contribute archive IDs.",
            "Excluded, unknown, partial or unreadable snapshots are never absence evidence.",
            "A later absence is not evidence of cancellation, deletion, expiry or completed work.",
            "The comparison is limited to stable layer:ObjectId values represented in source_record_id."
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.output.relative_to(ROOT)), "summary": counts,
                      "archive_ids_not_in_bundle": len(archive_only),
                      "bundle_ids_not_in_eligible_archive": len(bundle_only)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
