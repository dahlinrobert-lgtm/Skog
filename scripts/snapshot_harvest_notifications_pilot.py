#!/usr/bin/env python3
"""Create a complete, read-only Gräsmyr pilot snapshot of planned harvest notices.

This is deliberately separate from the existing bounded source probe and does not
write to customer databases, generate alerts, or classify missing records.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SERVICE = (
    "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/"
    "Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0"
)
CENTER = {"x": 19.66455, "y": 63.74646}
RADIUS_METERS = 10_000
BATCH_SIZE = 200
OUT_DIR = Path("data/skogsstyrelsen/harvest_notifications/grasmyr")
REQUEST_TIMEOUT = (20, 120)
REQUESTED_FIELDS = ["Beteckn", "Kommun", "Inkomdatum", "ArendeStatus", "AnmaldHa"]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def query_scope() -> dict[str, str]:
    return {
        "where": "1=1",
        "geometry": json.dumps(CENTER, separators=(",", ":")),
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "distance": str(RADIUS_METERS),
        "units": "esriSRUnit_Meter",
        "spatialRel": "esriSpatialRelIntersects",
    }


def request_json(session: requests.Session, url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("ArcGIS returned a non-object JSON response")
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload


def fetch_object_ids(session: requests.Session, oid_field: str) -> list[int]:
    params = {**query_scope(), "f": "json", "returnIdsOnly": "true"}
    result = request_json(session, SERVICE + "/query", params)
    ids = result.get("objectIds")
    if not isinstance(ids, list):
        raise RuntimeError("ArcGIS did not return an objectIds array")
    if not ids:
        raise RuntimeError("Scoped query returned zero IDs; refusing to publish an empty snapshot")
    if any(not isinstance(value, int) for value in ids):
        raise RuntimeError("ArcGIS returned a non-integer object ID")
    if len(ids) != len(set(ids)):
        raise RuntimeError("ArcGIS returned duplicate object IDs")
    return sorted(ids)


def fetch_complete_features(session: requests.Session, oid_field: str, object_ids: list[int]) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for offset in range(0, len(object_ids), BATCH_SIZE):
        batch = object_ids[offset : offset + BATCH_SIZE]
        params = {
            "f": "geojson",
            "objectIds": ",".join(str(value) for value in batch),
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
        }
        result = request_json(session, SERVICE + "/query", params)
        batch_features = result.get("features")
        if not isinstance(batch_features, list):
            raise RuntimeError("ArcGIS did not return a features array")
        if result.get("exceededTransferLimit"):
            raise RuntimeError("ArcGIS marked an object-ID batch as transfer-limited")
        returned_ids = []
        for feature in batch_features:
            properties = feature.get("properties") or {}
            value = feature.get("id", properties.get(oid_field))
            if value is None:
                raise RuntimeError(f"Feature missing technical object ID field {oid_field}")
            returned_ids.append(int(value))
        if len(returned_ids) != len(set(returned_ids)):
            raise RuntimeError("Duplicate object IDs within an ArcGIS batch")
        if set(returned_ids) != set(batch):
            missing = sorted(set(batch) - set(returned_ids))
            unexpected = sorted(set(returned_ids) - set(batch))
            raise RuntimeError(
                f"Object-ID batch mismatch: missing={len(missing)}, unexpected={len(unexpected)}"
            )
        features.extend(batch_features)
        time.sleep(0.05)

    all_ids = [int(f.get("id", (f.get("properties") or {}).get(oid_field))) for f in features]
    if len(all_ids) != len(set(all_ids)):
        raise RuntimeError("Duplicate object IDs across batches")
    if set(all_ids) != set(object_ids):
        raise RuntimeError("Fetched feature IDs do not equal the complete ID inventory")
    return sorted(features, key=lambda f: int(f.get("id", (f.get("properties") or {}).get(oid_field))))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "Skogskoll-complete-harvest-pilot/1.0"

    layer = request_json(session, SERVICE, {"f": "pjson"})
    oid_field = layer.get("objectIdField") or next(
        (field["name"] for field in layer.get("fields", []) if field.get("type") == "esriFieldTypeOID"),
        None,
    )
    if not oid_field:
        raise RuntimeError("Layer metadata does not expose an object ID field")

    valid_fields = {field.get("name") for field in layer.get("fields", [])}
    selected_fields = [oid_field, *[name for name in REQUESTED_FIELDS if name in valid_fields]]
    scope = query_scope()
    count_before_result = request_json(
        session, SERVICE + "/query", {**scope, "f": "json", "returnCountOnly": "true"}
    )
    count_before = count_before_result.get("count")
    if not isinstance(count_before, int) or count_before < 0:
        raise RuntimeError("ArcGIS did not return a valid scoped count")

    object_ids = fetch_object_ids(session, oid_field)
    if len(object_ids) != count_before:
        raise RuntimeError(
            f"Initial ID inventory ({len(object_ids)}) differs from scoped count ({count_before})"
        )
    features = fetch_complete_features(session, oid_field, object_ids)

    # Re-inventory IDs and count after extraction. Any source drift invalidates this run.
    final_ids = fetch_object_ids(session, oid_field)
    count_after_result = request_json(
        session, SERVICE + "/query", {**scope, "f": "json", "returnCountOnly": "true"}
    )
    count_after = count_after_result.get("count")
    if final_ids != object_ids or count_after != count_before:
        raise RuntimeError("Source ID inventory/count changed during scan; refusing to publish")

    captured_at = datetime.now(timezone.utc)
    stamp = captured_at.strftime("%Y%m%dT%H%M%SZ")
    collection = {
        "type": "FeatureCollection",
        "features": features,
    }
    raw = canonical_json(collection)
    digest = hashlib.sha256(raw).hexdigest()
    snapshot_name = f"grasmyr_10km_{stamp}.geojson.gz"
    snapshot_path = OUT_DIR / "snapshots" / snapshot_name
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(snapshot_path, "wb", compresslevel=9) as target:
        target.write(raw)

    manifest = {
        "source": SERVICE,
        "layer_id": 0,
        "object_id_field": oid_field,
        "selected_fields": selected_fields,
        "captured_at_utc": captured_at.isoformat(),
        "scope": {
            "type": "point_distance",
            "center_wgs84": CENTER,
            "radius_m": RADIUS_METERS,
            "query": scope,
        },
        "pagination": {
            "method": "returnIdsOnly_then_objectIds_batches",
            "batch_size": BATCH_SIZE,
            "id_count": len(object_ids),
            "feature_count": len(features),
            "unique_id_count": len({int(f.get("id", (f.get("properties") or {}).get(oid_field))) for f in features}),
            "count_before": count_before,
            "count_after": count_after,
            "id_inventory_stable_during_scan": True,
            "complete_scan": True,
        },
        "snapshot": f"snapshots/{snapshot_name}",
        "snapshot_bytes_uncompressed": len(raw),
        "snapshot_sha256": digest,
        "status": "success",
        "mode": "read-only pilot archive; no alerts; no customer database writes",
    }
    latest_path = OUT_DIR / "latest.json"
    latest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({
            "status": "failed",
            "complete_scan": False,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "No latest manifest is written on failure; previous snapshots remain untouched.",
        }, ensure_ascii=False))
        raise
