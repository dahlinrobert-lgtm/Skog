#!/usr/bin/env python3
"""Fetch the public Life2Taiga nature-conservation action polygons from Länsstyrelsen."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LAYER_URL = "https://ext-hostedgeodata.lansstyrelsen.se/arcgis/rest/services/Hosted/Life2Taiga_v3_Extern/FeatureServer/13"
USER_AGENT = "Skog-Life2Taiga-collector/1.0"
PAGE_SIZE = 1000


def get_json(url: str, timeout: int = 90) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"HTTP {response.status} for {url}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("error"):
        raise RuntimeError(f"ArcGIS service error: {payload.get('error') if isinstance(payload, dict) else 'invalid JSON'}")
    return payload


def fetch_layer(base_url: str = LAYER_URL, *, pause_seconds: float = 0.1) -> dict:
    metadata = get_json(base_url + "?f=pjson")
    if metadata.get("type") != "Feature Layer":
        raise RuntimeError(f"Expected an ArcGIS Feature Layer, got {metadata.get('type')!r}")
    fields = metadata.get("fields")
    if not isinstance(fields, list) or not fields:
        raise RuntimeError("Feature service metadata contained no fields")
    max_record_count = metadata.get("maxRecordCount") or PAGE_SIZE
    page_size = max(1, min(PAGE_SIZE, int(max_record_count)))
    features = []
    seen_ids = set()
    offset = 0
    while True:
        params = urlencode({
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
            "resultRecordCount": page_size,
            "resultOffset": offset,
            "orderByFields": metadata.get("objectIdField") or "OBJECTID",
        })
        page = get_json(base_url + "/query?" + params)
        page_features = page.get("features")
        if not isinstance(page_features, list):
            raise RuntimeError("ArcGIS query response did not contain a GeoJSON features list")
        for feature in page_features:
            if not isinstance(feature, dict) or not isinstance(feature.get("geometry"), dict):
                continue
            properties = feature.get("properties") or {}
            object_id_field = metadata.get("objectIdField") or "OBJECTID"
            object_id = properties.get(object_id_field, feature.get("id"))
            key = str(object_id) if object_id is not None else json.dumps(feature, sort_keys=True, ensure_ascii=False)
            if key in seen_ids:
                continue
            seen_ids.add(key)
            features.append(feature)
        offset += len(page_features)
        if not page_features or len(page_features) < page_size:
            break
        if offset > 1_000_000:
            raise RuntimeError("Refusing to fetch more than one million features without a bounded query")
        if pause_seconds:
            time.sleep(pause_seconds)

    if not features:
        raise RuntimeError("Life2Taiga service returned zero geometries; refusing to publish an empty dataset")
    return {
        "type": "FeatureCollection",
        "name": metadata.get("name") or "Life2Taiga Naturvårdsåtgärder",
        "source_url": base_url,
        "source_layer_id": 13,
        "source_layer_name": metadata.get("name") or "Life2Taiga Naturvårdsåtgärder",
        "source_description": metadata.get("description") or "",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_editing_info": metadata.get("editingInfo") or {},
        "feature_count": len(features),
        "geometry_type": metadata.get("geometryType") or "",
        "spatial_reference": "EPSG:4326",
        "features": features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/data/lifetaiga-naturvardsatgarder.geojson"))
    args = parser.parse_args()
    data = fetch_layer()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({
        "output": str(args.output),
        "source_layer_name": data["source_layer_name"],
        "feature_count": data["feature_count"],
        "geometry_type": data["geometry_type"],
        "generated_at": data["generated_at"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
