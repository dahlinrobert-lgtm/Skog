#!/usr/bin/env python3
"""Metadata-only probe of the Jönköping protected-tree completed-actions layer.

Do not request feature rows or geometries here. The catalogue metadata marks
this dataset as non-open and confidentiality K2; access and reuse terms must be
confirmed with the data owner before any feature collection is attempted.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAYER_URL = "https://ext-geodata-lokala-visning.lansstyrelsen.se/arcgis/rest/services/LSTF/LSTF_inventerade_skyddsvarda_trad_EXT/MapServer/1"
USER_AGENT = "Skog-Protected-Tree-Metadata-Probe/1.0"


def get_json(url: str, params: dict) -> dict:
    target = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        target,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"ArcGIS metadata request failed: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("error"):
        raise RuntimeError(f"ArcGIS returned an error: {payload!r}")
    return payload


def summarize_metadata(metadata: dict, count_payload: dict) -> dict:
    fields = metadata.get("fields") or []
    count = count_payload.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"Expected integer count-only response, got {count_payload!r}")
    return {
        "layer_name": metadata.get("name"),
        "type": metadata.get("type"),
        "geometry_type": metadata.get("geometryType"),
        "object_id_field": metadata.get("objectIdField"),
        "global_id_field": metadata.get("globalIdField"),
        "capabilities": metadata.get("capabilities"),
        "max_record_count": metadata.get("maxRecordCount"),
        "spatial_reference": metadata.get("extent", {}).get("spatialReference") if isinstance(metadata.get("extent"), dict) else metadata.get("spatialReference"),
        "field_names": [field.get("name") for field in fields],
        "field_types": {field.get("name"): field.get("type") for field in fields if field.get("name")},
        "feature_count": count,
        "feature_rows_requested": False,
        "geometry_rows_requested": False,
        "catalogue_access_warning": {
            "is_open_data": False,
            "confidentiality": "K2",
            "decision": "Do not collect feature rows or publish coordinates until the data owner confirms access and reuse conditions.",
        },
    }


def run_probe() -> dict:
    metadata = get_json(LAYER_URL, {"f": "pjson"})
    if metadata.get("type") != "Feature Layer":
        raise RuntimeError(f"Expected Feature Layer, got {metadata.get('type')!r}")
    if metadata.get("geometryType") != "esriGeometryPoint":
        raise RuntimeError(f"Expected point layer, got {metadata.get('geometryType')!r}")
    # Count only: no object IDs, attributes, geometries or coordinates are fetched.
    count_payload = get_json(LAYER_URL.rstrip("/") + "/query", {
        "where": "1=1",
        "returnCountOnly": "true",
        "returnGeometry": "false",
        "f": "json",
    })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": LAYER_URL,
        "metadata_only": True,
        **summarize_metadata(metadata, count_payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("catalogue-probe/protected-tree-layer-probe.json"))
    args = parser.parse_args()
    result = run_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
