#!/usr/bin/env python3
"""Inspect Länsstyrelsen's fire-ban ArcGIS FeatureServer metadata only.

Manual, read-only connector bootstrap. It does not query feature records,
download geometries, create operational snapshots, or schedule work.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_ID = "lansstyrelsen.fire_ban"
SERVICE_URL = (
    "https://ext-geodata-nationella-visning.lansstyrelsen.se/arcgis/rest/"
    "services/LST/LST_eldningsforbud_EXT/FeatureServer"
)
USER_AGENT = "Skog-data-platform/0.1 (manual metadata-only inspection)"


def fetch_json(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url.rstrip('/')}?{urllib.parse.urlencode({'f': 'json'})}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ArcGIS REST endpoint returned non-JSON: {url}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"ArcGIS REST response was not a JSON object: {url}")
    if data.get("error"):
        raise RuntimeError(f"ArcGIS REST error at {url}: {data['error']}")
    return data


def layer_refs(service: dict[str, Any], max_layers: int) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for collection in ("layers", "tables"):
        values = service.get(collection, [])
        if values is None:
            continue
        if not isinstance(values, list):
            raise RuntimeError(f"ArcGIS service field '{collection}' is not a list")
        for item in values:
            if not isinstance(item, dict) or not isinstance(item.get("id"), int):
                raise RuntimeError(f"Invalid ArcGIS {collection} entry: {item!r}")
            refs.append({"collection": collection, "id": item["id"], "name": item.get("name")})
    ids = [(item["collection"], item["id"]) for item in refs]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate layer/table IDs in ArcGIS service metadata")
    if len(refs) > max_layers:
        raise RuntimeError(
            f"Service advertises {len(refs)} layers/tables; safety cap is {max_layers}. "
            "Review the service before increasing --max-layers."
        )
    return refs


def inspect_service(
    fetcher=fetch_json, service_url: str = SERVICE_URL, timeout: int = 20,
    max_layers: int = 25,
) -> dict[str, Any]:
    if not 1 <= max_layers <= 50:
        raise ValueError("max_layers must be between 1 and 50")
    service = fetcher(service_url, timeout)
    refs = layer_refs(service, max_layers)
    layer_metadata = []
    for ref in refs:
        metadata = fetcher(f"{service_url.rstrip('/')}/{ref['id']}", timeout)
        capabilities = metadata.get("advancedQueryCapabilities")
        layer_metadata.append({
            "collection": ref["collection"],
            "id": ref["id"],
            "service_list_name": ref.get("name"),
            "name": metadata.get("name"),
            "type": metadata.get("type"),
            "geometry_type": metadata.get("geometryType"),
            "object_id_field": metadata.get("objectIdField"),
            "global_id_field": metadata.get("globalIdField"),
            "fields": metadata.get("fields"),
            "extent": metadata.get("extent"),
            "spatial_reference": metadata.get("spatialReference"),
            "max_record_count": metadata.get("maxRecordCount"),
            "advanced_query_capabilities": capabilities,
            "supports_pagination": capabilities.get("supportsPagination")
            if isinstance(capabilities, dict) else None,
            "editing_info": metadata.get("editingInfo"),
        })
    return {
        "inspection_schema_version": "1.0",
        "source_id": SOURCE_ID,
        "service_url": service_url,
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inspection_type": "service_and_layer_metadata_only",
        "service": {
            "current_version": service.get("currentVersion"),
            "service_description": service.get("serviceDescription"),
            "description": service.get("description"),
            "capabilities": service.get("capabilities"),
            "supported_query_formats": service.get("supportedQueryFormats"),
            "max_record_count": service.get("maxRecordCount"),
            "layers_and_tables_advertised": len(refs),
            "spatial_reference": service.get("spatialReference"),
            "initial_extent": service.get("initialExtent"),
            "full_extent": service.get("fullExtent"),
        },
        "layers": layer_metadata,
        "safety": {
            "feature_records_requested": False,
            "geometry_requested": False,
            "snapshot_created": False,
            "scheduled": False,
            "request_count": 1 + len(refs),
            "max_layer_metadata_requests": max_layers,
        },
        "limitations": [
            "Metadata inspection does not prove feature-query completeness or national coverage.",
            "Object ID fields and global IDs are reported, not assumed stable until tested.",
            "Service metadata does not by itself grant storage, commercial-use or customer-display rights.",
            "No feature records or geometries are downloaded by this connector.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None,
                        help="optional JSON output path; no output file is written by default")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-layers", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be between 1 and 60 seconds")
    result = inspect_service(timeout=args.timeout, max_layers=args.max_layers)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
