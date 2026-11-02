#!/usr/bin/env python3
"""Create a small, auditable sample snapshot from Länsstyrelsen's Åtgärder i vatten REST service.

The default run is deliberately limited to five features per geometry layer.
No credentials are required for the public read service. This script is read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = (
    "https://ext-geodata-acc.lansstyrelsen.se/arcgis/rest/services/"
    "atgarderivatten/lst_aiv_read/MapServer"
)
LAYERS = {0: "punkt", 1: "linje", 2: "polygon"}
SOURCE_ID = "lansstyrelsen.actions_in_water"
ATTRIBUTION = (
    "Källa: Länsstyrelsen – Åtgärder i vatten "
    "(gemensamt system med Havs- och vattenmyndigheten)."
)


def fetch_json(url: str, params: dict[str, object], timeout: int) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": "Skog-data-platform/0.1 (read-only pilot)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"REST endpoint returned non-JSON: {url}") from exc
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"ArcGIS REST error at {url}: {data['error']}")
    return data


def write_json(path: Path, data: dict) -> str:
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=5,
                        help="maximum sample features per layer (default: 5; max: 100)")
    parser.add_argument("--out", type=Path, default=Path("data/snapshots/actions-in-water"))
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100; this pilot intentionally does not bulk-download")

    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = args.out / stamp
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    layer_results = []
    for layer_id, layer_name in LAYERS.items():
        layer_url = f"{BASE}/{layer_id}"
        query_url = f"{layer_url}/query"
        count_data = fetch_json(
            query_url,
            {"where": "1=1", "returnCountOnly": "true", "f": "json"},
            args.timeout,
        )
        count = count_data.get("count")
        if not isinstance(count, int):
            raise RuntimeError(f"Count response missing integer 'count' for layer {layer_id}")

        # Preserve source-native ArcGIS JSON in SWEREF 99 TM (EPSG:3006).
        raw_data = fetch_json(
            query_url,
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "resultOffset": 0,
                "resultRecordCount": args.limit,
                "outSR": 3006,
                "f": "json",
            },
            args.timeout,
        )
        raw_file = f"{layer_name}.arcgis.json"
        raw_sha = write_json(snapshot_dir / raw_file, raw_data)
        features = raw_data.get("features", [])
        if not isinstance(features, list):
            raise RuntimeError(f"Invalid features array for layer {layer_id}")

        # GeoJSON is a separate derived export, explicitly reprojected to WGS 84.
        geo_data = fetch_json(
            query_url,
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "resultOffset": 0,
                "resultRecordCount": args.limit,
                "outSR": 4326,
                "f": "geojson",
            },
            args.timeout,
        )
        geo_file = f"{layer_name}.geojson"
        geo_sha = write_json(snapshot_dir / geo_file, geo_data)

        layer_results.append({
            "layer_id": layer_id,
            "layer_name": layer_name,
            "geometry_type": {0: "point", 1: "polyline", 2: "polygon"}[layer_id],
            "source_feature_count": count,
            "sample_feature_count": len(features),
            "sample_limit": args.limit,
            "source_native_file": raw_file,
            "source_native_spatial_reference": "EPSG:3006",
            "source_native_sha256": raw_sha,
            "geojson_file": geo_file,
            "geojson_spatial_reference": "EPSG:4326",
            "geojson_sha256": geo_sha,
        })

    manifest = {
        "manifest_version": "1.0",
        "snapshot_id": f"actions-in-water-{stamp}",
        "source_id": SOURCE_ID,
        "dataset_name": "Åtgärder i vatten – Länsstyrelsernas publika lästjänst",
        "producer": "Länsstyrelserna och Havs- och vattenmyndigheten; registrerade uppgifter kan komma från flera åtgärdsansvariga aktörer",
        "distributor": "Länsstyrelserna",
        "endpoint": BASE,
        "retrieved_at": retrieved_at.isoformat().replace("+00:00", "Z"),
        "request_scope": "first N features from each geometry layer; not a complete dataset extract",
        "sample_limit_per_layer": args.limit,
        "layers": layer_results,
        "licence_assessment": {
            "basis": "Länsstyrelsens published open-data terms for Åtgärder i vatten",
            "condition": "free copying, processing and distribution with Länsstyrelsen credited",
            "attribution": ATTRIBUTION,
            "cc0_not_assumed": True,
            "note": "A third-party inventory reports CC0 for a Swagger API, but this pilot uses the official ArcGIS REST read service. No official layer-specific CC0 evidence has been established here.",
        },
        "processing": {
            "organisation": "Skog",
            "description": "Small read-only sample; native ArcGIS JSON retained; separate GeoJSON export requested in EPSG:4326",
            "script": "data-platform/scripts/collect_actions_in_water_sample.py",
            "script_version": "0.1.0",
        },
        "limitations": [
            "Sample is limited to the first N records per layer and is not a full snapshot.",
            "No incremental change or deletion tracking is implemented.",
            "Project, action initiative and actual action are separate source concepts; this layer exposes linked identifiers and names.",
            "A registered action is not proof of independently verified completion.",
            "Attachments are not collected.",
        ],
    }
    manifest_sha = write_json(snapshot_dir / "manifest.json", manifest)
    print(json.dumps({
        "snapshot_dir": str(snapshot_dir),
        "manifest_sha256": manifest_sha,
        "layers": layer_results,
        "status": "sample_created",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
