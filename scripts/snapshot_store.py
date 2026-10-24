#!/usr/bin/env python3
"""Read and write backwards-compatible full/delta planned-notification snapshots."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FORMAT = "feature-delta-v1"
CHECKPOINT_DAYS = 30


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def feature_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    value = feature.get("id") or props.get("OBJECTID") or props.get("Beteckn")
    return str(value) if value not in (None, "") else ""


def snapshot_scope(snapshot: dict[str, Any]) -> str:
    cuts = snapshot.get("cutting_notifications") or {}
    area = snapshot.get("area") or {}
    return canonical_hash({
        "url": cuts.get("url"),
        "area": {
            "latitude": area.get("latitude"),
            "longitude": area.get("longitude"),
            "radius_km": area.get("radius_km"),
        },
    })


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _feature_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cuts = snapshot.get("cutting_notifications") or {}
    result = {}
    for feature in cuts.get("features") or []:
        key = feature_id(feature)
        if key:
            result[key] = feature
    return result


def _is_successful(snapshot: dict[str, Any]) -> bool:
    cuts = snapshot.get("cutting_notifications") or {}
    return cuts.get("status") == "ok" and isinstance(cuts.get("features"), list)


def read_snapshot_rows(snapshots_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Return chronological full snapshots, transparently reconstructing delta files.

    Legacy full JSON files remain supported. A delta whose declared base is absent or
    unreadable is skipped rather than interpreted as an empty/current state.
    """
    raw_rows = []
    for path in snapshots_dir.glob("*.json"):
        raw = _read(path)
        if raw is not None:
            raw_rows.append((path.name, raw))
    raw_rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))

    reconstructed: dict[str, dict[str, Any]] = {}
    rows: list[tuple[str, dict[str, Any]]] = []
    for filename, raw in raw_rows:
        if raw.get("snapshot_format") != FORMAT:
            if _is_successful(raw):
                reconstructed[filename] = raw
                rows.append((filename, raw))
            continue

        base_name = raw.get("base_snapshot")
        base = reconstructed.get(str(base_name)) if base_name else None
        delta = raw.get("feature_delta")
        if not isinstance(base, dict) or not isinstance(delta, dict):
            continue
        if not _is_successful(base):
            continue
        current = json.loads(json.dumps(raw))
        current.pop("snapshot_format", None)
        current.pop("base_snapshot", None)
        current.pop("feature_delta", None)
        current_cuts = dict(current.get("cutting_notifications") or {})
        base_features = _feature_map(base)
        for key in delta.get("removed", []):
            base_features.pop(str(key), None)
        for key in delta.get("added", []):
            feature = (delta.get("features") or {}).get(str(key))
            if isinstance(feature, dict):
                base_features[str(key)] = feature
        for key in delta.get("updated", []):
            feature = (delta.get("features") or {}).get(str(key))
            if isinstance(feature, dict):
                base_features[str(key)] = feature
        current_cuts["features"] = [base_features[key] for key in sorted(base_features)]
        current_cuts["count"] = len(current_cuts["features"])
        current["cutting_notifications"] = current_cuts
        if _is_successful(current):
            reconstructed[filename] = current
            rows.append((filename, current))
    rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))
    return rows


def write_snapshot(snapshot: dict[str, Any], snapshots_dir: Path,
                   previous_snapshot: dict[str, Any] | None = None,
                   previous_filename: str | None = None,
                   checkpoint_days: int = CHECKPOINT_DAYS) -> dict[str, Any]:
    """Write a full checkpoint or a compact feature delta; never write failed queries."""
    cuts = snapshot.get("cutting_notifications") or {}
    if cuts.get("status") != "ok" or not isinstance(cuts.get("features"), list):
        raise ValueError("Refusing to persist an unsuccessful cutting-notification query")

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    stamp = str(snapshot.get("checked_at") or datetime.now(timezone.utc).isoformat())
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    filename = parsed.strftime("%Y%m%dT%H%M%SZ") + ".json"
    destination = snapshots_dir / filename

    force_checkpoint = previous_snapshot is None or not previous_filename
    if previous_snapshot is not None:
        if not _is_successful(previous_snapshot) or snapshot_scope(previous_snapshot) != snapshot_scope(snapshot):
            force_checkpoint = True

    latest_checkpoint_time = None
    if not force_checkpoint:
        rows = read_snapshot_rows(snapshots_dir)
        for old_name, old_snapshot in reversed(rows):
            raw = _read(snapshots_dir / old_name) or {}
            if raw.get("snapshot_format") != FORMAT:
                latest_checkpoint_time = old_snapshot.get("checked_at")
                break
        if latest_checkpoint_time:
            try:
                dt = datetime.fromisoformat(str(latest_checkpoint_time).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                force_checkpoint = parsed - dt >= timedelta(days=checkpoint_days)
            except ValueError:
                force_checkpoint = True
        else:
            force_checkpoint = True

    if force_checkpoint:
        destination.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"filename": filename, "format": "full", "feature_count": len(cuts["features"]), "changed_features": len(cuts["features"])}

    previous_features = _feature_map(previous_snapshot or {})
    current_features = _feature_map(snapshot)
    previous_ids, current_ids = set(previous_features), set(current_features)
    added = sorted(current_ids - previous_ids)
    removed = sorted(previous_ids - current_ids)
    updated = sorted(
        key for key in current_ids & previous_ids
        if canonical_hash(current_features[key]) != canonical_hash(previous_features[key])
    )
    changed_ids = set(added) | set(updated)
    compact = json.loads(json.dumps(snapshot))
    compact_cuts = dict(compact.get("cutting_notifications") or {})
    compact_cuts.pop("features", None)
    compact_cuts["count"] = len(current_features)
    compact["cutting_notifications"] = compact_cuts
    compact["snapshot_format"] = FORMAT
    compact["base_snapshot"] = previous_filename
    compact["feature_delta"] = {
        "added": added,
        "updated": updated,
        "removed": removed,
        "features": {key: current_features[key] for key in sorted(changed_ids)},
        "feature_count_before": len(previous_features),
        "feature_count_after": len(current_features),
    }
    destination.write_text(json.dumps(compact, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {
        "filename": filename,
        "format": "delta",
        "feature_count": len(current_features),
        "added": len(added),
        "updated": len(updated),
        "removed": len(removed),
    }
