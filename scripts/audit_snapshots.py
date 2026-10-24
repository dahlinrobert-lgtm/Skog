#!/usr/bin/env python3
"""Measure full/delta storage for both planned and completed layer history."""
import gzip
import json
from pathlib import Path

try:
    from scripts.completed_snapshot_store import read_completed_archives
    from scripts.snapshot_store import feature_id, read_snapshot_rows
except ModuleNotFoundError:
    from completed_snapshot_store import read_completed_archives
    from snapshot_store import feature_id, read_snapshot_rows

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "snapshots"


def compare_states(states):
    unchanged = updated = added = removed = 0
    for old, new in zip(states, states[1:]):
        old_ids, new_ids = set(old), set(new)
        added += len(new_ids - old_ids)
        removed += len(old_ids - new_ids)
        for key in old_ids & new_ids:
            if old[key] == new[key]:
                unchanged += 1
            else:
                updated += 1
    total = unchanged + updated
    return {
        "comparable_pairs": max(0, len(states) - 1),
        "unchanged_existing_feature_observations": unchanged,
        "changed_existing_feature_observations": updated,
        "added_feature_observations": added,
        "not_returned_feature_observations": removed,
        "unchanged_share_pct": round(100 * unchanged / total, 1) if total else None,
    }


def main():
    planned_paths = [p for p in SNAPSHOTS.glob("*.json") if not p.name.startswith("completed_")]
    completed_paths = list(SNAPSHOTS.glob("completed_*.geojson.gz"))
    planned_rows = read_snapshot_rows(SNAPSHOTS)
    completed_rows = read_completed_archives(SNAPSHOTS)

    planned_states = []
    planned_full_equivalent = 0
    for _, snapshot in planned_rows:
        fmap = {
            feature_id(feature): feature
            for feature in (snapshot.get("cutting_notifications") or {}).get("features", [])
            if feature_id(feature)
        }
        planned_states.append(fmap)
        planned_full_equivalent += len(
            json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )

    completed_states = []
    completed_full_equivalent = 0
    for _, collection in completed_rows:
        fmap = {
            str(feature.get("id") or (feature.get("properties") or {}).get("OBJECTID") or ""): feature
            for feature in collection.get("features", [])
            if feature.get("id") is not None or (feature.get("properties") or {}).get("OBJECTID") is not None
        }
        completed_states.append(fmap)
        serialized = json.dumps(collection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        completed_full_equivalent += len(gzip.compress(serialized, mtime=0))

    planned_bytes = sum(p.stat().st_size for p in planned_paths)
    completed_bytes = sum(p.stat().st_size for p in completed_paths)
    print(json.dumps({
        "generated_from": "current committed data/snapshots",
        "planned": {
            "files": len(planned_paths),
            "reconstructable_states": len(planned_rows),
            "stored_bytes": planned_bytes,
            "stored_mib": round(planned_bytes / (1024 * 1024), 3),
            "full_equivalent_bytes_uncompressed": planned_full_equivalent,
            "repetition": compare_states(planned_states),
        },
        "completed": {
            "files": len(completed_paths),
            "reconstructable_states": len(completed_rows),
            "stored_compressed_bytes": completed_bytes,
            "stored_compressed_mib": round(completed_bytes / (1024 * 1024), 3),
            "full_equivalent_compressed_bytes": completed_full_equivalent,
            "full_equivalent_compressed_mib": round(completed_full_equivalent / (1024 * 1024), 3),
            "repetition": compare_states(completed_states),
        },
        "note": "Repetition metrics are feature-level comparisons between consecutive reconstructable states. IDs missing from a query mean not returned, not proof of deletion or felling. Full-equivalent figures are estimates, not Git historical-storage measurements."
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
