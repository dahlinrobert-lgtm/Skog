#!/usr/bin/env python3
"""Bounded, read-only query probe for Sveaskog ArcGIS feature layers.

Fetches layer definitions, counts, tiny attribute pages and at most one geometry
per target layer. It does not perform a national feature export or create snapshots.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

TIMEOUT = (15, 45)
OUT = Path("artifacts/sveaskog-layer-query-probe.json")
SERVICES = [
    {
        "title": "Sveaskogs markinnehav",
        "url": "https://SADKarttjansterProd3.sveaskog.se/server/rest/services/Verksamhet_Gem_Ext/ExternMarkinnehav_strovskog/MapServer",
        "priority": "primary",
    },
    {
        "title": "Ekologiska landskap",
        "url": "https://SADKarttjansterProd3.sveaskog.se/server/rest/services/Verksamhet_Gem_Ext/ExternEkologisktLandskap/MapServer",
        "priority": "secondary",
    },
    {
        "title": "Ekoparker",
        "url": "https://SADKarttjansterProd3.sveaskog.se/server/rest/services/Verksamhet_Gem_Ext/ExternEkoparker/MapServer",
        "priority": "secondary",
    },
    {
        "title": "Naturvårdsskogar",
        "url": "https://SADKarttjansterProd3.sveaskog.se/server/rest/services/Verksamhet_Gem_Ext/ExternNaturvardsskogar/MapServer",
        "priority": "secondary",
    },
    {
        "title": "Strövskogar",
        "url": "https://SADKarttjansterProd3.sveaskog.se/server/rest/services/Verksamhet_Gem_Ext/ExternStrovskogar/MapServer",
        "priority": "secondary",
    },
    {
        "title": "Vindkraft",
        "url": "https://SADKarttjansterProd3.sveaskog.se/server/rest/services/Verksamhet_Gem_Ext/ExternVindkraft/MapServer",
        "priority": "secondary",
    },
]


def request_json(session: requests.Session, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = session.get(url, params=params or {"f": "pjson"}, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("ArcGIS response was not a JSON object")
    if payload.get("error"):
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload


def safe_layer_meta(payload: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "id", "name", "type", "geometryType", "objectIdField", "globalIdField",
        "displayField", "maxRecordCount", "capabilities", "advancedQueryCapabilities",
        "supportsAdvancedQueries", "supportsStatistics", "supportsPagination",
        "supportsOrderBy", "supportsQueryWithResultType", "hasZ", "hasM",
        "extent", "spatialReference", "editingInfo", "fields", "indexes",
    )
    return {key: payload[key] for key in keep if key in payload}


def summarize_geometry(geometry: Any) -> dict[str, Any] | None:
    if not isinstance(geometry, dict):
        return None
    summary: dict[str, Any] = {"geometry_keys": sorted(geometry.keys())}
    for key in ("x", "y", "z"):
        if key in geometry:
            summary[key] = geometry[key]
    paths = geometry.get("paths")
    rings = geometry.get("rings")
    points = geometry.get("points")
    coords = paths or rings or points
    if isinstance(coords, list):
        summary["coordinate_parts"] = len(coords)
        summary["coordinate_count"] = sum(
            len(part) if isinstance(part, list) else 0 for part in coords
        )
        flat = [xy for part in coords if isinstance(part, list) for xy in part if isinstance(xy, list) and len(xy) >= 2]
        if flat:
            xs = [p[0] for p in flat]
            ys = [p[1] for p in flat]
            summary["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
    return summary


def inspect_feature_layer(session: requests.Session, service: dict[str, str], layer_stub: dict[str, Any]) -> dict[str, Any]:
    layer_id = layer_stub.get("id")
    layer_url = f"{service['url'].rstrip('/')}/{layer_id}"
    result: dict[str, Any] = {"layer_id": layer_id, "layer_url": layer_url}
    try:
        meta = request_json(session, layer_url)
        result["metadata"] = safe_layer_meta(meta)
        oid = meta.get("objectIdField") or next(
            (f["name"] for f in meta.get("fields", []) if f.get("type") == "esriFieldTypeOID"),
            None,
        )
        result["object_id_field_resolved"] = oid
        if not oid:
            result["query_test"] = {"status": "skipped", "reason": "No object ID field advertised"}
            return result

        count = request_json(session, f"{layer_url}/query", {
            "where": "1=1", "returnCountOnly": "true", "f": "json",
        })
        result["count_test"] = {"status": "ok", "count": count.get("count")}

        base_params = {
            "where": "1=1",
            "outFields": oid,
            "returnGeometry": "false",
            "orderByFields": f"{oid} ASC",
            "resultRecordCount": "3",
            "f": "json",
        }
        page1 = request_json(session, f"{layer_url}/query", base_params)
        feats1 = page1.get("features") or []
        ids1 = [f.get("attributes", {}).get(oid) for f in feats1]
        result["page_test"] = {
            "status": "ok",
            "requested_page_size": 3,
            "returned_page_1": len(feats1),
            "page_1_ids": ids1,
            "exceeded_transfer_limit_page_1": page1.get("exceededTransferLimit", False),
        }
        if meta.get("advancedQueryCapabilities", {}).get("supportsPagination", True):
            p2 = dict(base_params, resultOffset="3")
            page2 = request_json(session, f"{layer_url}/query", p2)
            feats2 = page2.get("features") or []
            ids2 = [f.get("attributes", {}).get(oid) for f in feats2]
            result["page_test"].update({
                "returned_page_2": len(feats2),
                "page_2_ids": ids2,
                "page_ids_disjoint": not bool(set(ids1) & set(ids2)),
                "pagination_offset_supported": True,
            })
        else:
            result["page_test"]["pagination_offset_supported"] = False

        if ids1:
            sample = request_json(session, f"{layer_url}/query", {
                "objectIds": str(ids1[0]),
                "outFields": "*",
                "returnGeometry": "false",
                "f": "json",
            })
            features = sample.get("features") or []
            attrs = features[0].get("attributes", {}) if features else {}
            result["attribute_sample"] = {
                "status": "ok",
                "fields_returned": sorted(attrs.keys()),
                "attributes": attrs,
            }
            geom = request_json(session, f"{layer_url}/query", {
                "objectIds": str(ids1[0]),
                "outFields": oid,
                "returnGeometry": "true",
                "returnZ": "false",
                "returnM": "false",
                "f": "json",
            })
            geometry_features = geom.get("features") or []
            result["geometry_sample"] = {
                "status": "ok",
                "geometry": summarize_geometry(geometry_features[0].get("geometry")) if geometry_features else None,
            }
        result["query_test"] = {"status": "ok"}
    except Exception as exc:  # preserve per-layer diagnostics and continue
        result["query_test"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    return result


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Skog-Sveaskog-Layer-Query-Probe/1.0 (bounded read-only)"})
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Inspect public Sveaskog ArcGIS sublayer metadata, counts, small pagination pages and one geometry sample",
        "licensing_status": "unverified",
        "full_feature_export_performed": False,
        "snapshot_or_schedule_enabled": False,
        "limits": {
            "attribute_sample_per_layer": 1,
            "geometry_sample_per_layer": 1,
            "pagination_page_size": 3,
            "full_feature_payload_downloaded": False,
        },
        "services": [],
        "limitations": [
            "Counts and small samples do not prove a complete national export.",
            "No full feature set or complete object-ID list was downloaded.",
            "Public query access does not establish commercial reuse, storage or redistribution rights.",
            "A MapServer service extent may not be equivalent to complete national coverage.",
        ],
    }
    for service in SERVICES:
        item: dict[str, Any] = {"title": service["title"], "url": service["url"], "priority": service["priority"]}
        try:
            root = request_json(session, service["url"])
            item["service"] = {
                key: root[key] for key in (
                    "serviceDescription", "description", "capabilities", "maxRecordCount",
                    "supportedQueryFormats", "supportedExtensions", "spatialReference",
                    "initialExtent", "fullExtent", "layers", "tables",
                ) if key in root
            }
            layers = root.get("layers") or []
            item["feature_layers"] = [
                inspect_feature_layer(session, service, layer)
                for layer in layers if layer.get("type") == "Feature Layer"
            ]
            item["service_status"] = "ok"
        except Exception as exc:
            item["service_status"] = "error"
            item["error"] = f"{type(exc).__name__}: {exc}"
        report["services"].append(item)

    primary = next((s for s in report["services"] if s["title"] == "Sveaskogs markinnehav"), {})
    layer_results = primary.get("feature_layers", [])
    report["result_summary"] = {
        "services_checked": len(report["services"]),
        "services_ok": sum(s.get("service_status") == "ok" for s in report["services"]),
        "ownership_sublayers": len(layer_results),
        "ownership_sublayers_with_counts": sum("count_test" in x and x["count_test"].get("status") == "ok" for x in layer_results),
        "ownership_sublayers_with_query_success": sum(x.get("query_test", {}).get("status") == "ok" for x in layer_results),
        "ownership_sublayers_with_errors": sum(x.get("query_test", {}).get("status") == "error" for x in layer_results),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["result_summary"], ensure_ascii=False, indent=2))
    print(f"Report: {OUT}")
    return 0 if report["result_summary"]["ownership_sublayers_with_query_success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
