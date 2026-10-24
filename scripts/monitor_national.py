#!/usr/bin/env python3
"""Nationwide daily archive of Skogsstyrelsen planned harvest notifications.

Uses ArcGIS object-ID discovery followed by bounded batches. Stores a compressed
full current state and compressed full/delta history; failed/incomplete queries
never replace the last known-good archive.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "national"
SNAPSHOTS = DATA / "snapshots"
LATEST = DATA / "latest.json.gz"
BASE_URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0/query"
BATCH_SIZE = 250
CHECKPOINT_DAYS = 30
HEADERS = {"User-Agent": "Skog-National-Notification-Archive/1.0"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def stamp(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def feature_id(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    value = feature.get("id") or props.get("OBJECTID") or props.get("Beteckn")
    return str(value) if value not in (None, "") else ""


def read_gzip_json(path: Path) -> dict[str, Any] | None:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else None
    except (OSError, EOFError, json.JSONDecodeError):
        return None


def write_gzip_json(path: Path, value: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=6) as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    return path.stat().st_size


def feature_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        feature_id(f): f
        for f in (snapshot.get("cutting_notifications") or {}).get("features", [])
        if feature_id(f)
    }


def create_delta(previous: dict[str, Any], current: dict[str, Any], base_name: str) -> dict[str, Any]:
    old, new = feature_map(previous), feature_map(current)
    old_ids, new_ids = set(old), set(new)
    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    updated = sorted(k for k in old_ids & new_ids if canonical_hash(old[k]) != canonical_hash(new[k]))
    geometry_unchanged = sorted(
        k for k in updated
        if canonical_hash(old[k].get("geometry")) == canonical_hash(new[k].get("geometry"))
    )
    payloads = {}
    for key in sorted(set(added) | set(updated)):
        feature = json.loads(json.dumps(new[key]))
        if key in geometry_unchanged:
            feature.pop("geometry", None)
        payloads[key] = feature
    compact = json.loads(json.dumps(current))
    cuts = dict(compact.get("cutting_notifications") or {})
    cuts.pop("features", None)
    compact["cutting_notifications"] = cuts
    compact["snapshot_format"] = "feature-delta-v1"
    compact["base_snapshot"] = base_name
    compact["feature_delta"] = {
        "added": added, "updated": updated, "removed": removed,
        "geometry_unchanged": geometry_unchanged, "features": payloads,
        "feature_count_before": len(old), "feature_count_after": len(new),
    }
    return compact


def apply_delta(base: dict[str, Any], delta_snapshot: dict[str, Any]) -> dict[str, Any]:
    delta = delta_snapshot.get("feature_delta") or {}
    features = feature_map(base)
    for key in delta.get("removed", []):
        features.pop(str(key), None)
    for key in delta.get("added", []):
        item = (delta.get("features") or {}).get(str(key))
        if isinstance(item, dict):
            features[str(key)] = item
    geometry_unchanged = {str(k) for k in delta.get("geometry_unchanged", [])}
    for key in delta.get("updated", []):
        key = str(key)
        item = (delta.get("features") or {}).get(key)
        if isinstance(item, dict):
            item = dict(item)
            if key in geometry_unchanged and key in features:
                item["geometry"] = features[key].get("geometry")
            features[key] = item
    result = json.loads(json.dumps(delta_snapshot))
    result.pop("snapshot_format", None)
    result.pop("base_snapshot", None)
    result.pop("feature_delta", None)
    cuts = dict(result.get("cutting_notifications") or {})
    cuts["features"] = [features[k] for k in sorted(features)]
    cuts["count"] = len(cuts["features"])
    result["cutting_notifications"] = cuts
    return result


def read_archive_rows(directory: Path) -> list[tuple[str, dict[str, Any]]]:
    raw_rows = []
    for path in directory.glob("*.json.gz"):
        raw = read_gzip_json(path)
        if raw is not None:
            raw_rows.append((path.name, raw))
    raw_rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))
    states: dict[str, dict[str, Any]] = {}
    rows = []
    for name, raw in raw_rows:
        if raw.get("snapshot_format") != "feature-delta-v1":
            if isinstance((raw.get("cutting_notifications") or {}).get("features"), list):
                states[name] = raw
                rows.append((name, raw))
            continue
        base = states.get(str(raw.get("base_snapshot") or ""))
        if base is None:
            continue
        current = apply_delta(base, raw)
        states[name] = current
        rows.append((name, current))
    rows.sort(key=lambda row: str(row[1].get("checked_at") or row[0]))
    return rows


def get_json(params: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    response = SESSION.get(BASE_URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError("ArcGIS error: " + json.dumps(data["error"], ensure_ascii=False))
    return data


def fetch_nationwide_features() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Discover all current object IDs, then fetch every ID in small batches."""
    id_response = get_json({"where": "1=1", "returnIdsOnly": "true", "returnGeometry": "false", "f": "json"})
    object_ids = id_response.get("objectIds")
    if not isinstance(object_ids, list):
        raise RuntimeError("ArcGIS did not return an objectIds list; refusing to publish a partial archive.")
    object_ids = sorted({int(x) for x in object_ids})
    if not object_ids:
        # Empty national results are suspicious for this national layer; fail closed.
        raise RuntimeError("ArcGIS returned zero object IDs; refusing to overwrite the archive with an empty baseline.")

    found: dict[str, dict[str, Any]] = {}
    batch_count = (len(object_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_index, start in enumerate(range(0, len(object_ids), BATCH_SIZE), start=1):
        batch = object_ids[start:start + BATCH_SIZE]
        params = {
            "objectIds": ",".join(map(str, batch)),
            "outFields": "*",
            "returnGeometry": "true",
            "returnTrueCurves": "false",
            "outSR": "4326",
            "f": "geojson",
        }
        data = get_json(params)
        features = data.get("features")
        if not isinstance(features, list):
            raise RuntimeError(f"ArcGIS batch {batch_index}/{batch_count} had no feature list.")
        for feature in features:
            key = feature_id(feature)
            if key:
                found[key] = feature
        if batch_index < batch_count:
            time.sleep(0.15)

    expected = {str(x) for x in object_ids}
    missing = sorted(expected - set(found))
    if missing:
        # Retry once in case records changed while the ID list was being fetched.
        for start in range(0, len(missing), BATCH_SIZE):
            batch = missing[start:start + BATCH_SIZE]
            data = get_json({
                "objectIds": ",".join(batch), "outFields": "*",
                "returnGeometry": "true", "returnTrueCurves": "false",
                "outSR": "4326", "f": "geojson",
            })
            for feature in data.get("features", []):
                key = feature_id(feature)
                if key:
                    found[key] = feature
        missing = sorted(expected - set(found))
    if missing:
        raise RuntimeError(
            f"Incomplete nationwide result: {len(found)}/{len(object_ids)} IDs fetched; "
            f"{len(missing)} IDs were still missing after retry. Last known-good data preserved."
        )

    features = sorted(found.values(), key=lambda f: feature_id(f))
    return features, {
        "object_id_count": len(object_ids),
        "feature_count": len(features),
        "batch_size": BATCH_SIZE,
        "batch_count": batch_count,
        "missing_after_retry": 0,
        "query_method": "returnIdsOnly + objectIds batches",
    }


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    checked = now_utc()
    features, diagnostics = fetch_nationwide_features()
    result = {
        "checked_at": stamp(checked),
        "scope": "Sweden — all features returned by Skogsstyrelsen Avverkningsanmälan layer",
        "source": BASE_URL,
        "cutting_notifications": {
            "status": "ok",
            "url": BASE_URL,
            "query_scope": {"where": "1=1", "coverage": "entire source layer; no spatial filter"},
            "count": len(features),
            "features": features,
            "diagnostics": diagnostics,
            "note": "Nationwide source-layer snapshot. This is not a property register; records missing from later queries are not by themselves proof of cancellation, deletion or felling.",
        },
    }

    previous = read_gzip_json(LATEST) if LATEST.exists() else None
    archive_rows = read_archive_rows(SNAPSHOTS)
    previous_filename = archive_rows[-1][0] if archive_rows else None
    force_full = previous is None or previous_filename is None
    if not force_full and archive_rows:
        try:
            last_full = None
            for archive_path in sorted(SNAPSHOTS.glob("*.json.gz")):
                raw = read_gzip_json(archive_path)
                if raw is not None and raw.get("snapshot_format") != "feature-delta-v1":
                    last_full = raw
            last_full_dt = datetime.fromisoformat(str(last_full["checked_at"]).replace("Z", "+00:00")) if last_full else None
            force_full = last_full_dt is None or checked - last_full_dt >= timedelta(days=CHECKPOINT_DAYS)
        except (KeyError, ValueError):
            force_full = True

    filename = checked.strftime("%Y%m%dT%H%M%SZ") + ".json.gz"
    if force_full:
        archive_payload = result
        archive_format = "full"
        change_counts = {"added": len(features), "updated": 0, "removed": 0}
    else:
        archive_payload = create_delta(previous, result, previous_filename)
        archive_format = "delta"
        delta = archive_payload["feature_delta"]
        change_counts = {
            "added": len(delta["added"]),
            "updated": len(delta["updated"]),
            "removed": len(delta["removed"]),
        }

    archive_bytes = write_gzip_json(SNAPSHOTS / filename, archive_payload)
    latest_bytes = write_gzip_json(LATEST, result)
    print(json.dumps({
        "checked_at": result["checked_at"],
        "scope": result["scope"],
        "status": "ok",
        **diagnostics,
        "archive_file": filename,
        "archive_format": archive_format,
        "archive_bytes": archive_bytes,
        "latest_compressed_bytes": latest_bytes,
        **change_counts,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
