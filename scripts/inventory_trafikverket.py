#!/usr/bin/env python3
"""Read-only inventory of Trafikverket environmental and wildlife ArcGIS layers.

Queries service metadata and feature counts in a 75 x 75 km envelope around
Gräsmyr. It deliberately downloads no feature geometries and changes no source
data. Uses only Python's standard library.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENVIRONMENT_URL = (
    "https://vektor.trafikverket.se/gis/rest/services/"
    "MWLEXGEO/MiljowebbGeo/MapServer"
)
WILDLIFE_URL = (
    "https://vektor.trafikverket.se/gis/rest/services/"
    "NVDB_p%C3%A5_karta/Viltolyckor_NVDBpakarta/MapServer"
)
# Gräsmyr pilot centre (WGS84), with a 75 km x 75 km test envelope.
CENTRE = {"longitude": 19.66455, "latitude": 63.74646}
HALF_HEIGHT_DEGREES = 37_500 / 111_000
# Correct longitude scale for latitude so the test window is approximately square.
import math
HALF_WIDTH_DEGREES = 37_500 / (111_000 * math.cos(math.radians(CENTRE["latitude"])))
OUT = Path(os.environ.get("TRAFIKVERKET_OUTPUT", "artifacts/trafikverket-inventory.json"))

def get_json(url: str, params: dict | None = None) -> dict:
    query = urllib.parse.urlencode(params or {"f": "pjson"})
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": "Skog-Trafikverket-inventory/1.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(f"ArcGIS error from {url}: {payload['error']}")
    return payload

def layer_count(layer_url: str) -> dict:
    xmin = CENTRE["longitude"] - HALF_WIDTH_DEGREES
    xmax = CENTRE["longitude"] + HALF_WIDTH_DEGREES
    ymin = CENTRE["latitude"] - HALF_HEIGHT_DEGREES
    ymax = CENTRE["latitude"] + HALF_HEIGHT_DEGREES
    geometry = json.dumps({
        "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
        "spatialReference": {"wkid": 4326},
    }, separators=(",", ":"))
    params = {
        "where": "1=1",
        "geometry": geometry,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "returnCountOnly": "true",
        "f": "json",
    }
    result = get_json(layer_url.rstrip("/") + "/query", params)
    return {"count_in_test_envelope": result.get("count"), "count_error": result.get("error")}

def inspect_service(name: str, url: str) -> dict:
    metadata = get_json(url)
    layers = []
    for item in metadata.get("layers", []):
        layer_id = item["id"]
        layer_url = f"{url.rstrip('/')}/{layer_id}"
        try:
            detail = get_json(layer_url)
            row = {
                "id": layer_id,
                "name": item.get("name"),
                "type": detail.get("type"),
                "geometry_type": detail.get("geometryType"),
                "object_id_field": detail.get("objectIdField"),
                "max_record_count": detail.get("maxRecordCount"),
                "fields": [
                    {"name": f.get("name"), "type": f.get("type"), "alias": f.get("alias")}
                    for f in detail.get("fields", [])
                ],
                "query_formats": detail.get("supportedQueryFormats"),
                "supports_pagination": detail.get("advancedQueryCapabilities", {}).get("supportsPagination"),
            }
            if detail.get("type") == "Feature Layer" and detail.get("geometryType"):
                try:
                    row.update(layer_count(layer_url))
                except Exception as exc:  # preserve the inventory even if one layer query fails
                    row["count_error"] = str(exc)
            else:
                row["note"] = "Group/table layer; not queried for feature count."
            layers.append(row)
            time.sleep(0.15)
        except Exception as exc:
            layers.append({"id": layer_id, "name": item.get("name"), "inspection_error": str(exc)})
    return {
        "service_name": name,
        "url": url,
        "service_description": metadata.get("serviceDescription") or metadata.get("description"),
        "spatial_reference": metadata.get("spatialReference"),
        "supported_query_formats": metadata.get("supportedQueryFormats"),
        "max_record_count": metadata.get("maxRecordCount"),
        "layers": layers,
    }

def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Read-only service/layer inventory and feature-count coverage probe",
        "area": {
            "name": "Gräsmyr pilot",
            "centre_wgs84": CENTRE,
            "envelope_wgs84": {
                "xmin": CENTRE["longitude"] - HALF_WIDTH_DEGREES,
                "ymin": CENTRE["latitude"] - HALF_HEIGHT_DEGREES,
                "xmax": CENTRE["longitude"] + HALF_WIDTH_DEGREES,
                "ymax": CENTRE["latitude"] + HALF_HEIGHT_DEGREES,
                "note": "Approximate 75 km x 75 km envelope; not a geodesic square or property boundary.",
            },
        },
        "services": [],
    }
    failures = []
    for name, url in [
        ("Miljöwebb Landskap", ENVIRONMENT_URL),
        ("NVDB viltolyckor", WILDLIFE_URL),
    ]:
        try:
            result["services"].append(inspect_service(name, url))
        except Exception as exc:
            failures.append({"service": name, "error": str(exc)})
    result["service_failures"] = failures
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    layer_total = sum(len(s["layers"]) for s in result["services"])
    queried = sum(
        1 for s in result["services"] for layer in s["layers"]
        if "count_in_test_envelope" in layer
    )
    print(f"Services inspected: {len(result['services'])}; layers: {layer_total}; feature layers counted: {queried}")
    print(f"Output: {OUT}")
    if failures:
        print("Service failures:", json.dumps(failures, ensure_ascii=False))
    return 1 if not result["services"] else 0

if __name__ == "__main__":
    sys.exit(main())
