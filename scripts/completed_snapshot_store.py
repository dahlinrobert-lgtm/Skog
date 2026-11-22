#!/usr/bin/env python3
"""Write and reconstruct full/delta archives for completed-harvest GeoJSON."""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FORMAT = "completed-feature-delta-v1"
CHECKPOINT_DAYS = 30
PREFIX = "completed_"
SUFFIX = ".geojson.gz"


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def feature_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    value = feature.get("id") or props.get("OBJECTID") or props.get("Beteckn")
    return str(value) if value not in (None, "") else ""


def _feature_map(collection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for feature in collection.get("features") or []:
        key = feature_id(feature)
        if key:
            result[key] = feature
    return result


def _read_raw(path: Path) -> dict[str, Any] | None:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else None
    except (OSError, EOFError, json.JSONDecodeError):
        return None


def _write_gzip(path: Path, value: dict[str, Any]) -> int:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(payload, mtime=0))
    return path.stat().st_size


def _apply_delta_features(base_features: dict[str, dict[str, Any]], raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Apply a validated archive delta to a feature map without copying full history."""
    delta = raw.get("feature_delta")
    if not isinstance(delta, dict):
        raise ValueError("Invalid completed archive delta")
    features = dict(base_features)
    for key in delta.get("removed", []):
        features.pop(str(key), None)
    payloads = delta.get("features") or {}
    for key in delta.get("added", []):
        item = payloads.get(str(key))
        if isinstance(item, dict):
            features[str(key)] = item
    geometry_unchanged = {str(key) for key in delta.get("geometry_unchanged", [])}
    for key in delta.get("updated", []):
        key = str(key)
        item = payloads.get(key)
        if not isinstance(item, dict):
            continue
        if key in geometry_unchanged and key in features:
            item = dict(item)
            item["geometry"] = features[key].get("geometry")
        features[key] = item
    return features


def iter_completed_archive_transitions(snapshots_dir: Path):
    """Yield only added/updated features for consecutive, complete archive states.

    The archive chain is streamed: memory use is bounded by one reconstructed
    feature map instead of retaining every historical full state. Broken delta
    chains and scope changes reset the comparison baseline rather than implying
    removals or transitions.
    """
    paths = sorted(snapshots_dir.glob(f"{PREFIX}*{SUFFIX}"))
    state: dict[str, dict[str, Any]] = {}
    state_filename = None
    state_checked_at = None
    state_scope = None

    for path in paths:
        raw = _read_raw(path)
        if raw is None:
            state = {}
            state_filename = None
            state_checked_at = None
            state_scope = None
            continue

        filename = path.name
        checked_at = raw.get("checked_at")
        scope = raw.get("query_scope_sha256")

        if raw.get("snapshot_format") != FORMAT:
            if not isinstance(raw.get("features"), list):
                state = {}
                state_filename = None
                state_checked_at = None
                state_scope = None
                continue
            current = _feature_map(raw)
            comparable = bool(
                state and state_filename and state_scope and scope
                and state_scope == scope
                and state_checked_at != checked_at
            )
            if comparable:
                changed = {
                    key: item for key, item in current.items()
                    if key not in state or canonical_hash(item) != canonical_hash(state[key])
                }
                before = {key: state[key] for key in changed if key in state}
                if changed:
                    yield {
                        "before_snapshot": state_filename,
                        "after_snapshot": filename,
                        "before_checked_at": state_checked_at,
                        "after_checked_at": checked_at,
                        "scope_sha256": scope,
                        "before_features": before,
                        "after_features": changed,
                    }
            state = current
            state_filename = filename
            state_checked_at = checked_at
            state_scope = scope
            continue

        delta = raw.get("feature_delta")
        base_name = raw.get("base_snapshot")
        if (
            not isinstance(delta, dict)
            or not state
            or base_name != state_filename
            or not scope
            or scope != state_scope
        ):
            # Never bridge a broken chain or a changed query scope.
            state = {}
            state_filename = None
            state_checked_at = None
            state_scope = None
            continue

        changed_ids = sorted({
            str(key) for key in (delta.get("added", []) + delta.get("updated", []))
        })
        before = {key: state[key] for key in changed_ids if key in state}
        payloads = delta.get("features") or {}
        after = {}
        geometry_unchanged = {str(key) for key in delta.get("geometry_unchanged", [])}
        for key in changed_ids:
            item = payloads.get(key)
            if not isinstance(item, dict):
                continue
            if key in geometry_unchanged and key in state:
                item = dict(item)
                item["geometry"] = state[key].get("geometry")
            after[key] = item

        state = _apply_delta_features(state, raw)
        if state_checked_at != checked_at and after:
            yield {
                "before_snapshot": state_filename,
                "after_snapshot": filename,
                "before_checked_at": state_checked_at,
                "after_checked_at": checked_at,
                "scope_sha256": scope,
                "before_features": before,
                "after_features": after,
            }
        state_filename = filename
        state_checked_at = checked_at
        state_scope = scope


def read_latest_completed_archive(snapshots_dir: Path):
    """Return only the latest reconstructable complete archive state."""
    state: dict[str, dict[str, Any]] = {}
    state_filename = None
    state_metadata = None
    for path in sorted(snapshots_dir.glob(f"{PREFIX}*{SUFFIX}")):
        raw = _read_raw(path)
        if raw is None:
            state = {}
            state_filename = None
            state_metadata = None
            continue
        if raw.get("snapshot_format") != FORMAT:
            if not isinstance(raw.get("features"), list):
                state = {}
                state_filename = None
                state_metadata = None
                continue
            state = _feature_map(raw)
            state_filename = path.name
            state_metadata = raw
            continue
        if (
            not isinstance(raw.get("feature_delta"), dict)
            or not state
            or raw.get("base_snapshot") != state_filename
            or not raw.get("query_scope_sha256")
            or raw.get("query_scope_sha256") != (state_metadata or {}).get("query_scope_sha256")
        ):
            state = {}
            state_filename = None
            state_metadata = None
            continue
        state = _apply_delta_features(state, raw)
        state_filename = path.name
        state_metadata = raw

    if not state_filename or not state_metadata:
        return None
    collection = {
        key: value for key, value in state_metadata.items()
        if key not in {"snapshot_format", "base_snapshot", "feature_delta"}
    }
    collection["type"] = state_metadata.get("type") or "FeatureCollection"
    collection["features"] = [state[key] for key in sorted(state)]
    return state_filename, collection


def read_completed_archives(snapshots_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Load chronological archives, rebuilding delta archives against their declared base.

    Older compressed GeoJSON FeatureCollections stay readable. A delta whose base is
    missing or unreadable is skipped, never treated as an empty source layer.
    """
    raw_rows = []
    for path in snapshots_dir.glob(f"{PREFIX}*{SUFFIX}"):
        raw = _read_raw(path)
        if raw is not None:
            raw_rows.append((path.name, raw))
    raw_rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))

    reconstructed: dict[str, dict[str, Any]] = {}
    rows: list[tuple[str, dict[str, Any]]] = []
    for filename, raw in raw_rows:
        if raw.get("snapshot_format") != FORMAT:
            if isinstance(raw.get("features"), list):
                reconstructed[filename] = raw
                rows.append((filename, raw))
            continue

        base_name = raw.get("base_snapshot")
        base = reconstructed.get(str(base_name)) if base_name else None
        delta = raw.get("feature_delta")
        if not isinstance(base, dict) or not isinstance(delta, dict):
            continue
        if (
            not raw.get("query_scope_sha256")
            or raw.get("query_scope_sha256") != base.get("query_scope_sha256")
        ):
            continue

        features = _feature_map(base)
        for key in delta.get("removed", []):
            features.pop(str(key), None)
        payloads = delta.get("features") or {}
        for key in delta.get("added", []):
            item = payloads.get(str(key))
            if isinstance(item, dict):
                features[str(key)] = item
        geometry_unchanged = {str(key) for key in delta.get("geometry_unchanged", [])}
        for key in delta.get("updated", []):
            key = str(key)
            item = payloads.get(key)
            if not isinstance(item, dict):
                continue
            if key in geometry_unchanged and key in features:
                item = dict(item)
                item["geometry"] = features[key].get("geometry")
            features[key] = item

        current = {
            key: value for key, value in raw.items()
            if key not in {"snapshot_format", "base_snapshot", "feature_delta"}
        }
        current["type"] = raw.get("type") or "FeatureCollection"
        current["features"] = [features[key] for key in sorted(features)]
        reconstructed[filename] = current
        rows.append((filename, current))

    rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))
    return rows


def write_completed_archive(collection: dict[str, Any], snapshots_dir: Path,
                            previous_collection: dict[str, Any] | None = None,
                            previous_filename: str | None = None,
                            checkpoint_days: int = CHECKPOINT_DAYS,
                            prefer_delta: bool = False) -> dict[str, Any]:
    """Write a full checkpoint or compressed feature delta, choosing full if smaller.

    prefer_delta is intended for tests that exercise reconstruction independently
    of compression efficiency; production callers should leave it False.
    """
    if not isinstance(collection.get("features"), list):
        raise ValueError("Refusing to write completed archive without a GeoJSON feature list")
    scope = collection.get("query_scope_sha256")
    if not scope:
        raise ValueError("Refusing to write completed archive without a query-scope fingerprint")

    snapshots_dir.mkdir(parents=True, exist_ok=True)
    stamp = str(collection.get("checked_at") or datetime.now(timezone.utc).isoformat())
    try:
        observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
    except ValueError:
        observed = datetime.now(timezone.utc)
    filename = PREFIX + observed.strftime("%Y%m%dT%H%M%SZ") + SUFFIX
    destination = snapshots_dir / filename

    full_collection = json.loads(json.dumps(collection))
    full_payload = json.dumps(full_collection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    full_compressed_bytes = len(gzip.compress(full_payload, mtime=0))

    # A scope transition is always a checkpoint; this rule must take precedence
    # over any test-only compression preference.
    full_checkpoint = previous_collection is None or not previous_filename
    if previous_collection is not None:
        if (
            not previous_collection.get("query_scope_sha256")
            or previous_collection.get("query_scope_sha256") != scope
        ):
            full_checkpoint = True

    checkpoint_time = None
    if not full_checkpoint:
        rows = read_completed_archives(snapshots_dir)
        for old_name, old_collection in reversed(rows):
            raw = _read_raw(snapshots_dir / old_name) or {}
            if raw.get("snapshot_format") != FORMAT:
                checkpoint_time = old_collection.get("checked_at")
                break
        if checkpoint_time:
            try:
                prior = datetime.fromisoformat(str(checkpoint_time).replace("Z", "+00:00"))
                if prior.tzinfo is None:
                    prior = prior.replace(tzinfo=timezone.utc)
                full_checkpoint = observed - prior >= timedelta(days=checkpoint_days) and not prefer_delta
            except ValueError:
                full_checkpoint = True
        else:
            # No on-disk checkpoint chain yet (e.g. unit test with an in-memory base).
            # Production has a checkpoint in the archive directory before writing a delta.
            full_checkpoint = not prefer_delta

    # Test hook may bypass cadence checkpoints only for controlled reconstruction tests;
    # a query-scope transition always forces a full baseline.
    if full_checkpoint:
        archive_bytes = _write_gzip(destination, full_collection)
        return {
            "filename": filename, "format": "full", "feature_count": len(full_collection["features"]),
            "added": len(full_collection["features"]), "updated": 0, "removed": 0,
            "geometry_omitted": 0, "archive_bytes": archive_bytes,
            "full_compressed_bytes": full_compressed_bytes, "estimated_savings_pct": 0.0,
        }

    previous_features = _feature_map(previous_collection or {})
    current_features = _feature_map(full_collection)
    previous_ids, current_ids = set(previous_features), set(current_features)
    added = sorted(current_ids - previous_ids)
    removed = sorted(previous_ids - current_ids)
    updated = sorted(
        key for key in current_ids & previous_ids
        if canonical_hash(current_features[key]) != canonical_hash(previous_features[key])
    )
    geometry_unchanged = sorted(
        key for key in updated
        if canonical_hash(current_features[key].get("geometry")) ==
        canonical_hash(previous_features[key].get("geometry"))
    )
    changed_ids = set(added) | set(updated)
    payloads: dict[str, dict[str, Any]] = {}
    feature_hashes = {}
    for key in sorted(changed_ids):
        feature = json.loads(json.dumps(current_features[key]))
        if key in geometry_unchanged:
            feature.pop("geometry", None)
        payloads[key] = feature
        feature_hashes[key] = {
            "attributes_sha256": canonical_hash(current_features[key].get("properties") or {}),
            "geometry_sha256": canonical_hash(current_features[key].get("geometry")),
        }

    delta_collection = {
        key: value for key, value in full_collection.items() if key != "features"
    }
    delta_collection.update({
        "snapshot_format": FORMAT,
        "base_snapshot": previous_filename,
        "feature_count": len(current_features),
        "feature_delta": {
            "added": added,
            "updated": updated,
            "removed": removed,
            "geometry_unchanged": geometry_unchanged,
            "features": payloads,
            "feature_hashes": feature_hashes,
            "feature_count_before": len(previous_features),
            "feature_count_after": len(current_features),
        },
    })
    delta_payload = json.dumps(delta_collection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    delta_compressed_bytes = len(gzip.compress(delta_payload, mtime=0))

    # A full archive is safer and smaller when the source layer changes extensively.
    if delta_compressed_bytes >= full_compressed_bytes and not prefer_delta:
        archive_bytes = _write_gzip(destination, full_collection)
        return {
            "filename": filename, "format": "full_fallback", "feature_count": len(current_features),
            "added": len(added), "updated": len(updated), "removed": len(removed),
            "geometry_omitted": 0, "archive_bytes": archive_bytes,
            "full_compressed_bytes": full_compressed_bytes, "estimated_savings_pct": 0.0,
        }

    archive_bytes = _write_gzip(destination, delta_collection)
    return {
        "filename": filename, "format": "delta", "feature_count": len(current_features),
        "added": len(added), "updated": len(updated), "removed": len(removed),
        "geometry_omitted": len(geometry_unchanged), "archive_bytes": archive_bytes,
        "full_compressed_bytes": full_compressed_bytes,
        "estimated_savings_pct": round((1 - archive_bytes / full_compressed_bytes) * 100, 1) if full_compressed_bytes else 0.0,
    }
