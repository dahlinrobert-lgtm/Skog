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
