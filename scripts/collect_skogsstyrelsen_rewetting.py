#!/usr/bin/env python3
"""Archive Skogsstyrelsen's public polygons for signed rewetting agreements.

This source represents agreement/management areas, not proof that ditch plugs
have been physically installed. Raw ArcGIS attributes and geometries are kept.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAYER_URL = (
    "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/"
    "Geodataportal/GeodataportalVisaAtervatningavtal/MapServer/0"
)
REQUIRED_FIELDS = {
    "OBJECTID", "Uuid", "Beteckn", "Lan", "Kommun", "ArendeAr",
    "AvtalatDatum", "KartaHektar", "Url", "shape_Length", "shape_Area",
}


def request_json(url: str, params: dict, retries: int = 4) -> dict:
    target = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                target, headers={"User-Agent": "Skog-Hydrology-archive/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("error"):
                raise RuntimeError(f"ArcGIS error: {payload.get('error') if isinstance(payload, dict) else 'invalid JSON'}")
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after {retries} attempts: {last_error}")


def request_post_json(url: str, params: dict, retries: int = 4) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={
                    "User-Agent": "Skog-Hydrology-archive/1.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("error"):
                raise RuntimeError(f"ArcGIS error: {payload.get('error') if isinstance(payload, dict) else 'invalid JSON'}")
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"POST request failed after {retries} attempts: {last_error}")


def canonical_hash(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_snapshot(path: Path) -> dict:
    if not path.exists():
        return {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def write_snapshot(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
    os.replace(temporary, path)


def query_endpoint(layer_url: str) -> str:
    candidates = [layer_url + "/query", layer_url.rsplit("/0", 1)[0] + "/query"]
    failures = []
    for candidate in candidates:
        try:
            result = request_json(candidate, {
                "where": "1=1", "returnIdsOnly": "true",
                "returnGeometry": "false", "f": "json",
            }, retries=1)
            if isinstance(result.get("objectIds"), list):
                return candidate
            failures.append(f"{candidate}: missing objectIds")
        except Exception as exc:
            failures.append(f"{candidate}: {exc}")
    raise RuntimeError("No working ArcGIS query endpoint: " + " | ".join(failures))


def fetch_features(layer_url: str, batch_size: int, delay: float) -> tuple[dict, list[dict], str]:
    metadata = request_json(layer_url, {"f": "pjson"})
    if metadata.get("type") != "Feature Layer":
        raise RuntimeError(f"Expected Feature Layer, got {metadata.get('type')!r}")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise RuntimeError(f"Unexpected geometry type: {metadata.get('geometryType')!r}")
    field_names = {field.get("name") for field in metadata.get("fields", [])}
    missing_fields = sorted(REQUIRED_FIELDS - field_names)
    if missing_fields:
        raise RuntimeError(f"Source schema changed; missing required fields: {missing_fields}")

    endpoint = query_endpoint(layer_url)
    ids_result = request_json(endpoint, {
        "where": "1=1", "returnIdsOnly": "true",
        "returnGeometry": "false", "f": "json",
    })
    object_ids = sorted(set(int(value) for value in ids_result.get("objectIds", [])))
    if not object_ids:
        raise RuntimeError("Source returned zero object IDs; refusing to publish an empty snapshot")

    features: list[dict] = []
    returned_ids: set[int] = set()
    for offset in range(0, len(object_ids), batch_size):
        batch = object_ids[offset:offset + batch_size]
        params = {
            "objectIds": ",".join(map(str, batch)),
            "outFields": "*", "returnGeometry": "true",
            "outSR": "3006", "returnZ": "false", "returnM": "false", "f": "json",
        }
        try:
            result = request_json(endpoint, params, retries=1)
        except Exception:
            result = request_post_json(endpoint, params)
        batch_features = result.get("features") or []
        if result.get("exceededTransferLimit"):
            raise RuntimeError(f"Transfer limit exceeded for batch offset {offset}")
        for feature in batch_features:
            attrs = feature.get("attributes") or {}
            oid = attrs.get("OBJECTID")
            if oid is None or not isinstance(feature.get("geometry"), dict):
                raise RuntimeError("Feature missing OBJECTID or polygon geometry")
            returned_ids.add(int(oid))
            features.append(feature)
        if delay:
            time.sleep(delay)

    expected = set(object_ids)
    if returned_ids != expected or len(features) != len(object_ids):
        raise RuntimeError(
            f"Incomplete export: expected={len(object_ids)}, returned={len(features)}, "
            f"missing={len(expected - returned_ids)}, unexpected={len(returned_ids - expected)}"
        )
    features.sort(key=lambda item: int(item["attributes"]["OBJECTID"]))
    return metadata, features, endpoint


def feature_key(feature: dict) -> str:
    attrs = feature.get("attributes") or {}
    value = attrs.get("Uuid")
    if not value:
        raise RuntimeError("Feature missing stable source UUID")
    return str(value).strip().strip("{}").lower()


def detect_changes(previous: dict, features: list[dict], observed_at: str) -> list[dict]:
    old = {feature_key(item): item for item in previous.get("features", [])}
    new = {feature_key(item): item for item in features}
    if len(old) != len(previous.get("features", [])) or len(new) != len(features):
        raise RuntimeError("Duplicate UUID detected in source snapshot")
    changes = []
    for source_id, feature in new.items():
        object_id = (feature.get("attributes") or {}).get("OBJECTID")
        if source_id not in old:
            changes.append({"observed_at": observed_at, "change": "added", "source_uuid": source_id, "object_id": object_id, "feature": feature})
        elif canonical_hash(feature) != canonical_hash(old[source_id]):
            changes.append({"observed_at": observed_at, "change": "updated", "source_uuid": source_id, "object_id": object_id, "feature": feature})
    for source_id in sorted(set(old) - set(new)):
        object_id = (old[source_id].get("attributes") or {}).get("OBJECTID")
        changes.append({"observed_at": observed_at, "change": "removed_from_source", "source_uuid": source_id, "object_id": object_id})
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/skogsstyrelsen-atervatning"))
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 1000:
        parser.error("--batch-size must be between 1 and 1000")
    if not 0 <= args.delay <= 10:
        parser.error("--delay must be between 0 and 10 seconds")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = args.output_dir / "current.json.gz"
    history_path = args.output_dir / "history" / "events.jsonl"
    report_path = args.output_dir / "latest-report.json"
    previous = read_snapshot(snapshot_path)

    metadata, features, endpoint = fetch_features(LAYER_URL, args.batch_size, args.delay)
    observed_at = datetime.now(timezone.utc).isoformat()
    changes = detect_changes(previous, features, observed_at)
    baseline_created = not bool(previous)

    snapshot = {
        "schema_version": 1,
        "source": LAYER_URL,
        "query_endpoint": endpoint,
        "layer_name": metadata.get("name"),
        "service_description": metadata.get("description"),
        "spatial_reference": 3006,
        "source_extent": metadata.get("extent"),
        "observed_at": observed_at,
        "feature_count": len(features),
        "features": features,
    }
    if baseline_created or changes:
        write_snapshot(snapshot_path, snapshot)
    if changes:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as stream:
            for event in changes:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")

    report = {
        "observed_at": observed_at,
        "source": LAYER_URL,
        "query_endpoint": endpoint,
        "layer_name": metadata.get("name"),
        "source_extent": metadata.get("extent"),
        "expected_feature_count": len(features),
        "returned_feature_count": len(features),
        "baseline_created": baseline_created,
        "new_features": sum(event["change"] == "added" for event in changes),
        "updated_features": sum(event["change"] == "updated" for event in changes),
        "removed_from_source": sum(event["change"] == "removed_from_source" for event in changes),
        "history_events_written": len(changes),
        "note": "Agreement/management polygons; not confirmation that physical ditch-plugging is completed.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
