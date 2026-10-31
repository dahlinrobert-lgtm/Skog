#!/usr/bin/env python3
"""Read-only discovery probe for Sveaskog's public ArcGIS Web AppBuilder map.

The probe fetches public item metadata/configuration and service metadata only.
It does not download features, create snapshots, or infer licensing.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

APP_ID = "7b4e41ab44ff41eaab3daa4379115a5e"
ORG = "https://sveaskog.maps.arcgis.com"
PORTALS = ["https://www.arcgis.com", ORG]
TIMEOUT = (15, 45)
OUT = Path("artifacts/sveaskog-arcgis-probe.json")
UUID_RE = re.compile(r"(?i)\b[0-9a-f]{32}\b")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def get_json(session: requests.Session, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = session.get(url, params=params or {"f": "pjson"}, timeout=TIMEOUT)
    result: dict[str, Any] = {
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "resolved_url": response.url,
    }
    try:
        payload = response.json()
        result["json"] = payload
        if isinstance(payload, dict) and payload.get("error"):
            result["service_error"] = payload["error"]
    except ValueError:
        result["body_preview"] = response.text[:500]
    return result


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def collect_ids(value: Any) -> set[str]:
    found: set[str] = set()
    for node in walk(value):
        for key, item in node.items():
            if isinstance(item, str) and ("item" in key.lower() or "webmap" in key.lower()):
                found.update(UUID_RE.findall(item))
    return found


def collect_layers(webmap: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for node in walk(webmap):
        if isinstance(node.get("url"), str) and node["url"].startswith(("http://", "https://")):
            if "operationalLayers" in node or "url" in node:
                found.append({
                    "title": node.get("title") or node.get("name"),
                    "url": node["url"].rstrip("/"),
                    "layer_type": node.get("layerType") or node.get("type"),
                    "item_id": node.get("itemId"),
                    "visibility": node.get("visibility"),
                })
    unique = {(x["url"], x.get("title")): x for x in found}
    return list(unique.values())


def inspect_service(session: requests.Session, layer: dict[str, Any]) -> dict[str, Any]:
    url = layer["url"]
    result: dict[str, Any] = {"configured_layer": layer}
    try:
        meta = get_json(session, url, {"f": "pjson"})
        payload = meta.get("json", {})
        result["metadata_response"] = {k: v for k, v in meta.items() if k != "json"}
        if isinstance(payload, dict):
            fields = payload.get("fields") or []
            result["service_metadata"] = {
                key: payload.get(key) for key in (
                    "name", "type", "description", "geometryType", "objectIdField",
                    "globalIdField", "displayField", "maxRecordCount", "capabilities",
                    "advancedQueryCapabilities", "supportsAdvancedQueries",
                    "supportsStatistics", "supportsPagination", "hasZ", "hasM",
                    "extent", "spatialReference", "editingInfo", "copyrightText",
                ) if key in payload
            }
            result["fields"] = [
                {k: field.get(k) for k in ("name", "alias", "type", "length", "nullable")}
                for field in fields
            ]
            if payload.get("layers"):
                result["sublayers"] = [
                    {k: child.get(k) for k in ("id", "name", "type", "geometryType")}
                    for child in payload["layers"]
                ]
    except requests.RequestException as exc:
        result["request_error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-Sveaskog-ArcGIS-Discovery/1.0 (read-only)"})
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Discover public ArcGIS app, web map references, and service metadata without downloading features",
        "app_item_id": APP_ID,
        "licensing_status": "unverified",
        "feature_download_performed": False,
        "weekly_schedule_enabled": False,
        "portal_attempts": [],
        "candidate_webmap_items": [],
        "operational_layers": [],
        "limitations": [
            "A public item or service response does not establish permission for commercial reuse, storage, or redistribution.",
            "Layer metadata does not prove complete national feature export; no feature query was run.",
            "Only items explicitly referenced by the app configuration are treated as web-map candidates.",
        ],
    }
    app_data: dict[str, Any] | None = None
    successful_app_metadata = False
    for portal in PORTALS:
        base = f"{portal}/sharing/rest/content/items/{APP_ID}"
        attempt: dict[str, Any] = {"portal": portal}
        try:
            metadata = get_json(session, base)
            attempt["item_metadata"] = {k: v for k, v in metadata.items() if k != "json"}
            item = metadata.get("json")
            if isinstance(item, dict):
                attempt["item"] = {
                    k: item.get(k) for k in (
                        "id", "title", "type", "typeKeywords", "owner", "access",
                        "created", "modified", "description", "snippet", "url",
                    ) if k in item
                }
                successful_app_metadata = successful_app_metadata or metadata.get("http_status") == 200 and not item.get("error")
            data = get_json(session, f"{base}/data")
            attempt["item_data"] = {k: v for k, v in data.items() if k != "json"}
            if isinstance(data.get("json"), dict):
                app_data = data["json"]
                attempt["item_data_keys"] = sorted(app_data.keys())
            report["portal_attempts"].append(attempt)
            if app_data:
                break
        except requests.RequestException as exc:
            attempt["request_error"] = f"{type(exc).__name__}: {exc}"
            report["portal_attempts"].append(attempt)

    if app_data is not None:
        ids = collect_ids(app_data)
        report["app_configuration_item_ids"] = sorted(ids)
        for item_id in sorted(ids):
            for portal in PORTALS:
                base = f"{portal}/sharing/rest/content/items/{item_id}"
                try:
                    meta = get_json(session, base)
                    data = get_json(session, f"{base}/data")
                    candidate: dict[str, Any] = {
                        "item_id": item_id,
                        "portal": portal,
                        "metadata_response": {k: v for k, v in meta.items() if k != "json"},
                        "data_response": {k: v for k, v in data.items() if k != "json"},
                    }
                    item = meta.get("json")
                    if isinstance(item, dict):
                        candidate["item"] = {
                            k: item.get(k) for k in ("id", "title", "type", "owner", "access", "url")
                            if k in item
                        }
                    map_data = data.get("json")
                    if isinstance(map_data, dict):
                        candidate["data_keys"] = sorted(map_data.keys())
                        candidate["operational_layer_count"] = len(map_data.get("operationalLayers") or [])
                        if map_data.get("operationalLayers"):
                            layers = collect_layers(map_data)
                            report["operational_layers"].extend(layers)
                    report["candidate_webmap_items"].append(candidate)
                    if isinstance(map_data, dict) and map_data.get("operationalLayers"):
                        break
                except requests.RequestException as exc:
                    report["candidate_webmap_items"].append({
                        "item_id": item_id, "portal": portal,
                        "request_error": f"{type(exc).__name__}: {exc}",
                    })

    deduped = {(x["url"], x.get("title")): x for x in report["operational_layers"]}
    report["operational_layers"] = list(deduped.values())
    report["layer_service_inspection"] = [
        inspect_service(session, layer) for layer in report["operational_layers"]
    ]
    report["result_summary"] = {
        "app_metadata_retrieved": successful_app_metadata,
        "app_configuration_retrieved": app_data is not None,
        "webmap_candidates": len(report["candidate_webmap_items"]),
        "operational_layers_found": len(report["operational_layers"]),
        "service_metadata_responses": sum(
            1 for x in report["layer_service_inspection"] if x.get("service_metadata")
        ),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["result_summary"], ensure_ascii=False, indent=2))
    print(f"Report: {OUT}")
    return 0 if successful_app_metadata else 1


if __name__ == "__main__":
    raise SystemExit(main())
