#!/usr/bin/env python3
"""Report storage and repetition metrics for planned-notification snapshots."""
import json
from pathlib import Path

from snapshot_store import feature_id, read_snapshot_rows

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "data" / "snapshots"


def main():
    paths = [
        path for path in SNAPSHOTS.glob("*.json")
        if not path.name.startswith("completed_")
    ]
    stored_bytes = sum(path.stat().st_size for path in paths)
    rows = read_snapshot_rows(SNAPSHOTS)
    unchanged = added = updated = removed = possible_full_bytes = 0
    comparable_pairs = 0
    previous = None

    for _, snapshot in rows:
        features = {
            feature_id(item): item
            for item in (snapshot.get("cutting_notifications") or {}).get("features", [])
            if feature_id(item)
        }
        possible_full_bytes += len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if previous is not None:
            old_features = previous
            old_ids, new_ids = set(old_features), set(features)
            added += len(new_ids - old_ids)
            removed += len(old_ids - new_ids)
            updated += sum(
                old_features[key] != features[key]
                for key in old_ids & new_ids
            )
            unchanged += sum(
                old_features[key] == features[key]
                for key in old_ids & new_ids
            )
            comparable_pairs += 1
        previous = features

    unchanged_candidates = unchanged + updated
    print(json.dumps({
        "snapshot_files": len(paths),
        "reconstructable_snapshots": len(rows),
        "stored_snapshot_bytes": stored_bytes,
        "stored_snapshot_mib": round(stored_bytes / (1024 * 1024), 3),
        "average_file_bytes": round(stored_bytes / len(paths)) if paths else 0,
        "full_snapshot_equivalent_bytes": possible_full_bytes,
        "full_snapshot_equivalent_mib": round(possible_full_bytes / (1024 * 1024), 3),
        "comparable_pairs": comparable_pairs,
        "unchanged_feature_observations": unchanged,
        "changed_existing_feature_observations": updated,
        "added_feature_observations": added,
        "not_returned_feature_observations": removed,
        "unchanged_share_of_existing_feature_observations_pct": round(100 * unchanged / unchanged_candidates, 1) if unchanged_candidates else None,
        "note": "Missing IDs mean not returned by the query, not proof of felling or deletion. Full-snapshot equivalent is a reconstructed-data estimate, not a Git repository-size estimate."
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
