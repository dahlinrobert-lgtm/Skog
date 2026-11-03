#!/usr/bin/env python3
"""Poll Skogsstyrelsen's national laser-scan metadata layer.

A full snapshot is archived only when the published feature set changes.
The service is manually published, so polling frequency is independent of
publication frequency. Omdrev 3 is not assumed to be complete.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "skogsstyrelsen" / "laser_scan_metadata"
LAYER = (
    "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/"
    "Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0"
)
BATCH_SIZE = 500


def request_json(session: requests.Session, url: str, params: dict) -> dict:
    response = session.get(url, params=params, timeout=(30, 180))
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    snapshots = OUT / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    latest_path = OUT / "latest.json"

    session = requests.Session()
    session.headers["User-Agent"] = "Skogskoll-metadata-change-monitor/1.0"

    service = request_json(session, LAYER, {"f": "json"})
    layer_fields = service.get("fields", [])
    oid_field = service.get("objectIdField") or next(
        (f["name"] for f in layer_fields if f.get("type") == "esriFieldTypeOID"),
        None,
    )
    if not oid_field:
        raise RuntimeError("ArcGIS layer did not expose an object ID field")

    # returnIdsOnly is not limited by the layer's maxRecordCount.
    ids_result = request_json(session, LAYER + "/query", {
        "f": "json",
        "where": "1=1",
        "returnIdsOnly": "true",
    })
    object_ids = sorted(ids_result.get("objectIds") or [])
    if not object_ids:
        raise RuntimeError("Metadata query returned zero object IDs; refusing to archive")

    features = []
    for offset in range(0, len(object_ids), BATCH_SIZE):
        batch = object_ids[offset:offset + BATCH_SIZE]
        result = request_json(session, LAYER + "/query", {
            "f": "json",
            "objectIds": ",".join(map(str, batch)),
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 3006,
        })
        batch_features = result.get("features") or []
        returned = {f.get("attributes", {}).get(oid_field) for f in batch_features}
        missing = set(batch) - returned
        if missing:
            raise RuntimeError(
                f"ArcGIS returned {len(missing)} fewer features than requested; "
                "refusing to treat a partial response as a new publication"
            )
        features.extend(batch_features)
        time.sleep(0.1)

    features.sort(key=lambda f: f.get("attributes", {}).get(oid_field))
    # Hash attributes AND geometry: detect additions, removals, attribute edits
    # and spatial corrections, not just changed record counts.
    fingerprint_payload = [
        {
            "attributes": feature.get("attributes") or {},
            "geometry": feature.get("geometry"),
        }
        for feature in features
    ]
    fingerprint = hashlib.sha256(canonical_bytes(fingerprint_payload)).hexdigest()

    previous = None
    if latest_path.exists():
        previous = json.loads(latest_path.read_text(encoding="utf-8"))
    if previous and previous.get("content_sha256") == fingerprint:
        print(json.dumps({
            "status": "unchanged",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "feature_count": len(features),
            "content_sha256": fingerprint,
            "latest_snapshot": previous.get("snapshot"),
        }, ensure_ascii=False))
        return

    detected_at = datetime.now(timezone.utc)
    stamp = detected_at.strftime("%Y%m%dT%H%M%SZ")
    snapshot_name = f"{stamp}_{fingerprint[:12]}.json.gz"
    snapshot_path = snapshots / snapshot_name
    document = {
        "source": LAYER,
        "service_name": service.get("name"),
        "source_service_description": service.get("description"),
        "source_service_document_info": service.get("documentInfo"),
        "layer_id": 0,
        "object_id_field": oid_field,
        "spatial_reference": {"wkid": 3006},
        "feature_count": len(features),
        "content_sha256": fingerprint,
        "detected_at_utc": detected_at.isoformat(),
        "previous_snapshot": previous.get("snapshot") if previous else None,
        "publication_semantics": (
            "Detection time is when this workflow observed the content. "
            "It is not the source publication timestamp or scan date."
        ),
        "features": features,
    }
    with gzip.open(snapshot_path, "wb", compresslevel=9) as target:
        target.write(json.dumps(
            document, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8"))

    latest = {
        "source": LAYER,
        "checked_at_utc": detected_at.isoformat(),
        "detected_at_utc": detected_at.isoformat(),
        "feature_count": len(features),
        "content_sha256": fingerprint,
        "snapshot": f"snapshots/{snapshot_name}",
        "previous_snapshot": previous.get("snapshot") if previous else None,
        "change_type": "initial_baseline" if not previous else "content_changed",
    }
    latest_path.write_text(
        json.dumps(latest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": latest["change_type"], **latest}, ensure_ascii=False))


if __name__ == "__main__":
    main()
