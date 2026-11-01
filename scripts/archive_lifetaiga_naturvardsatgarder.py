#!/usr/bin/env python3
"""Archive Life2Taiga nature-conservation restoration polygons with durable history.

The source is a project dataset, not a complete national register of all
nature-conservation management. Source attributes are retained verbatim;
category, date and completion semantics are not inferred.
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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LAYER_URL = "https://ext-hostedgeodata.lansstyrelsen.se/arcgis/rest/services/Hosted/Life2Taiga_v3_Extern/FeatureServer/13"
REQUIRED_FIELDS = {"globalid", "objectid", "symbology", "area_ha"}
USER_AGENT = "Skog-Life2Taiga-archive/1.0"


def request_json(url: str, params: dict, retries: int = 4) -> dict:
    target = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(target, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
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
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
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


def stable_key(feature: dict) -> str:
    attrs = feature.get("attributes") or {}
    value = attrs.get("globalid") or attrs.get("GlobalID")
    if not value:
        raise RuntimeError("Feature missing stable GlobalID; refusing to build unreliable history")
    return str(value).strip().strip("{}").lower()


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


def fetch_features(layer_url: str = LAYER_URL, *, batch_size: int = 250, delay: float = 0.1) -> tuple[dict, list[dict], str]:
    metadata = request_json(layer_url, {"f": "pjson"})
    if metadata.get("type") != "Feature Layer":
        raise RuntimeError(f"Expected Feature Layer, got {metadata.get('type')!r}")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise RuntimeError(f"Expected polygon geometry, got {metadata.get('geometryType')!r}")
    fields = {field.get("name", "").lower() for field in metadata.get("fields", [])}
    missing = sorted(REQUIRED_FIELDS - fields)
    if missing:
        raise RuntimeError(f"Source schema changed; missing required fields: {missing}")
    oid_field = metadata.get("objectIdField") or next(
        field.get("name") for field in metadata.get("fields", []) if field.get("type") == "esriFieldTypeOID"
    )
    query_url = layer_url.rstrip("/") + "/query"
    ids = request_json(query_url, {
        "where": "1=1", "returnIdsOnly": "true", "returnGeometry": "false", "f": "json"
    }).get("objectIds")
    if not isinstance(ids, list) or not ids:
        raise RuntimeError("Source returned no object IDs; refusing to publish an empty snapshot")
    expected = set(int(value) for value in ids)
    features: list[dict] = []
    returned: set[int] = set()
    for offset in range(0, len(ids), batch_size):
        batch = ids[offset:offset + batch_size]
        params = {
            "objectIds": ",".join(map(str, batch)), "outFields": "*",
            "returnGeometry": "true", "returnZ": "false", "returnM": "false", "f": "json",
        }
        try:
            result = request_json(query_url, params, retries=1)
        except Exception:
            result = request_post_json(query_url, params)
        batch_features = result.get("features") or []
        if result.get("exceededTransferLimit"):
            raise RuntimeError(f"Transfer limit exceeded at object-ID offset {offset}")
        for feature in batch_features:
            attrs = feature.get("attributes") or {}
            oid = attrs.get(oid_field)
            if oid is None or not isinstance(feature.get("geometry"), dict):
                raise RuntimeError("Feature missing object ID or polygon geometry")
            returned.add(int(oid))
            features.append(feature)
        if delay:
            time.sleep(delay)
    if returned != expected or len(features) != len(expected):
        raise RuntimeError(
            f"Incomplete export: expected={len(expected)}, returned={len(features)}, "
            f"missing={len(expected-returned)}, unexpected={len(returned-expected)}"
        )
    keys = [stable_key(feature) for feature in features]
    if len(set(keys)) != len(keys):
        raise RuntimeError("Duplicate GlobalID values detected; refusing to write ambiguous history")
    features.sort(key=lambda feature: int(feature["attributes"][oid_field]))
    metadata["_archive_object_id_field"] = oid_field
    return metadata, features, query_url


def detect_changes(previous: dict, features: list[dict], observed_at: str) -> list[dict]:
    old_features = previous.get("features", [])
    old = {stable_key(feature): feature for feature in old_features}
    new = {stable_key(feature): feature for feature in features}
    if len(old) != len(old_features) or len(new) != len(features):
        raise RuntimeError("Duplicate GlobalID in previous or current snapshot")
    changes = []
    for key, feature in new.items():
        attrs = feature.get("attributes") or {}
        oid = attrs.get("objectid", attrs.get("OBJECTID"))
        if key not in old:
            changes.append({"observed_at": observed_at, "change": "added", "source_globalid": key, "object_id": oid, "feature": feature})
        elif canonical_hash(feature) != canonical_hash(old[key]):
            changes.append({"observed_at": observed_at, "change": "updated", "source_globalid": key, "object_id": oid, "feature": feature})
    for key in sorted(set(old) - set(new)):
        attrs = old[key].get("attributes") or {}
        oid = attrs.get("objectid", attrs.get("OBJECTID"))
        changes.append({"observed_at": observed_at, "change": "removed_from_source", "source_globalid": key, "object_id": oid})
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/lifetaiga-naturvardsatgarder"))
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 1000:
        parser.error("--batch-size must be between 1 and 1000")
    if not 0 <= args.delay <= 10:
        parser.error("--delay must be between 0 and 10 seconds")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    current_path = args.output_dir / "current.json.gz"
    history_path = args.output_dir / "history" / "events.jsonl"
    report_path = args.output_dir / "latest-report.json"
    previous = read_snapshot(current_path)
    metadata, features, query_url = fetch_features(batch_size=args.batch_size, delay=args.delay)
    observed_at = datetime.now(timezone.utc).isoformat()
    changes = detect_changes(previous, features, observed_at)
    baseline_created = not bool(previous)
    oid_field = metadata["_archive_object_id_field"]
    action_counts = Counter((feature.get("attributes") or {}).get("symbology") or "NULL" for feature in features)
    county_counts = Counter((feature.get("attributes") or {}).get("lan") or "NULL" for feature in features)

    snapshot = {
        "schema_version": 1, "source": LAYER_URL, "query_endpoint": query_url,
        "layer_name": metadata.get("name"), "service_description": metadata.get("description"),
        "object_id_field": oid_field, "global_id_field": "globalid",
        "spatial_reference": metadata.get("extent", {}).get("spatialReference") or metadata.get("spatialReference"),
        "source_extent": metadata.get("extent"), "observed_at": observed_at,
        "feature_count": len(features), "features": features,
    }
    if baseline_created or changes:
        write_snapshot(current_path, snapshot)
    if changes:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as stream:
            for event in changes:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")

    report = {
        "observed_at": observed_at, "source": LAYER_URL, "query_endpoint": query_url,
        "layer_name": metadata.get("name"), "expected_feature_count": len(features),
        "returned_feature_count": len(features), "baseline_created": baseline_created,
        "new_features": sum(item["change"] == "added" for item in changes),
        "updated_features": sum(item["change"] == "updated" for item in changes),
        "removed_from_source": sum(item["change"] == "removed_from_source" for item in changes),
        "history_events_written": len(changes),
        "action_category_counts": dict(sorted(action_counts.items())),
        "county_counts": dict(sorted(county_counts.items())),
        "note": "Life2Taiga project layer only; not a complete national register. Source attributes retained without inferring planned/completed status.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
