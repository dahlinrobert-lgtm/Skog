#!/usr/bin/env python3
"""Archive Skogsstyrelsen's national approximate burned-area layer.

The service is queried by object ID in bounded batches. The latest full snapshot
is gzip-compressed; subsequent additions, changes and removals are appended to
an NDJSON history. No third-party packages are required.
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

LAYER_URL = (
    "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/"
    "Geodataportal/GeodataportalVisaBrand/MapServer/0"
)
REQUIRED_FIELDS = {
    "OBJECTID", "BrandTyp", "Artal", "ArealHa", "LanNamn",
    "KommunNamn", "DatumBrand", "DatumUppdaterad",
}


def request_json(url: str, params: dict, retries: int = 4) -> dict:
    query = urllib.parse.urlencode(params)
    target = url + ("&" if "?" in url else "?") + query
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                target,
                headers={"User-Agent": "Skogskoll-data-collector/1.0"},
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if "error" in payload:
                raise RuntimeError(f"ArcGIS error: {payload['error']}")
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after {retries} attempts: {last_error}")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/skogsstyrelsen-brandomraden"))
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 1000:
        parser.error("--batch-size must be between 1 and 1000")
    if not 0 <= args.delay <= 10:
        parser.error("--delay must be between 0 and 10 seconds")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    current_path = args.output_dir / "current.json.gz"
    history_path = args.output_dir / "history" / "events.jsonl"
    previous = read_snapshot(current_path)
    previous_features = {
        int(feature["attributes"]["OBJECTID"]): feature
        for feature in previous.get("features", [])
    }

    metadata = request_json(LAYER_URL, {"f": "pjson"})
    field_names = {field.get("name") for field in metadata.get("fields", [])}
    missing_fields = sorted(REQUIRED_FIELDS - field_names)
    if missing_fields:
        raise RuntimeError(f"Layer schema changed; missing required fields: {missing_fields}")
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise RuntimeError(f"Unexpected geometry type: {metadata.get('geometryType')}")

    ids_response = request_json(
        LAYER_URL + "/query",
        {"where": "1=1", "returnIdsOnly": "true", "returnGeometry": "false", "f": "json"},
    )
    object_ids = sorted(set(ids_response.get("objectIds") or []))
    if ids_response.get("objectIds") is None:
        raise RuntimeError("ArcGIS did not return objectIds; refusing to publish an empty snapshot")

    features = []
    returned_ids = set()
    for offset in range(0, len(object_ids), args.batch_size):
        batch = object_ids[offset:offset + args.batch_size]
        result = request_json(
            LAYER_URL + "/query",
            {
                "objectIds": ",".join(map(str, batch)),
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "3006",
                "returnZ": "false",
                "returnM": "false",
                "f": "json",
            },
        )
        batch_features = result.get("features") or []
        if result.get("exceededTransferLimit"):
            raise RuntimeError(f"Transfer limit exceeded for object ID batch at offset {offset}")
        for feature in batch_features:
            attrs = feature.get("attributes") or {}
            oid = attrs.get("OBJECTID")
            if oid is None:
                raise RuntimeError("Feature without OBJECTID returned by ArcGIS")
            returned_ids.add(int(oid))
            features.append(feature)
        if args.delay:
            time.sleep(args.delay)

    missing_ids = sorted(set(map(int, object_ids)) - returned_ids)
    unexpected_ids = sorted(returned_ids - set(map(int, object_ids)))
    if missing_ids or unexpected_ids or len(features) != len(object_ids):
        raise RuntimeError(
            f"Incomplete export: expected={len(object_ids)}, returned={len(features)}, "
            f"missing_ids={len(missing_ids)}, unexpected_ids={len(unexpected_ids)}"
        )

    features.sort(key=lambda feature: int(feature["attributes"]["OBJECTID"]))
    observed_at = datetime.now(timezone.utc).isoformat()
    new_by_id = {int(f["attributes"]["OBJECTID"]): f for f in features}
    brand_types = Counter((f["attributes"].get("BrandTyp") or "NULL") for f in features)
    years = Counter(str(f["attributes"].get("Artal") or "NULL") for f in features)
    feature_hashes = {oid: canonical_hash(feature) for oid, feature in new_by_id.items()}
    previous_hashes = {oid: canonical_hash(feature) for oid, feature in previous_features.items()}

    changes = []
    if previous:
        for oid, feature in new_by_id.items():
            if oid not in previous_features:
                changes.append({"observed_at": observed_at, "change": "added", "object_id": oid, "feature": feature})
            elif feature_hashes[oid] != previous_hashes[oid]:
                changes.append({"observed_at": observed_at, "change": "updated", "object_id": oid, "feature": feature})
        for oid in sorted(set(previous_features) - set(new_by_id)):
            changes.append({"observed_at": observed_at, "change": "removed", "object_id": oid})
        if changes:
            history_path.parent.mkdir(parents=True, exist_ok=True)
            with history_path.open("a", encoding="utf-8") as stream:
                for event in changes:
                    stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")

    snapshot = {
        "schema_version": 1,
        "source": LAYER_URL,
        "layer_name": metadata.get("name"),
        "spatial_reference": 3006,
        "observed_at": observed_at,
        "feature_count": len(features),
        "features": features,
    }
    write_snapshot(current_path, snapshot)

    report = {
        "observed_at": observed_at,
        "source": LAYER_URL,
        "layer_name": metadata.get("name"),
        "expected_feature_count": len(object_ids),
        "returned_feature_count": len(features),
        "missing_object_ids": missing_ids,
        "unexpected_object_ids": unexpected_ids,
        "brand_type_counts": dict(sorted(brand_types.items())),
        "year_counts": dict(sorted(years.items())),
        "new_features": sum(1 for e in changes if e["change"] == "added"),
        "changed_features": sum(1 for e in changes if e["change"] == "updated"),
        "removed_features": sum(1 for e in changes if e["change"] == "removed"),
        "baseline_created": not bool(previous),
        "history_events_written": len(changes),
    }
    (args.output_dir / "latest-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
