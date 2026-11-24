#!/usr/bin/env python3
"""Collect Skogsstyrelsen Samråd point, line and polygon layers for the pilot area.

The collector stores complete, immutable daily snapshots. It refuses to publish
if any layer fails or pagination cannot be reconciled. The exact circular area
filter is applied locally after querying a conservative WGS84 envelope.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "area.json"
DATA = ROOT / "data"
SNAPSHOTS = DATA / "samrad_snapshots"
LATEST = DATA / "samrad_latest.json"
SOURCE_ID = "skogsstyrelsen.samrad"
PAGE_SIZE = 300
MAX_PAGES = 1000
HEADERS = {"User-Agent": "Skog-Samrad-Archive/1.0"}
FIELDS = "ObjectId,Lannr,Lan,Kommunnr,Kommun,ArendeAr,Beteckn,Status,Inkomdatum,AnmaldHa,SkogsTyp,Samradsatgard,UUID"
LAYERS = {
    "points": "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer/0/query",
    "lines": "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer/1/query",
    "areas": "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer/2/query",
}
TO_TM = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True).transform


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def query_envelope(latitude: float, longitude: float, radius_m: float) -> dict[str, float]:
    lat_delta = radius_m / 110540 * 1.05
    lon_delta = radius_m / (111320 * max(0.1, abs(__import__("math").cos(__import__("math").radians(latitude))))) * 1.05
    return {
        "xmin": longitude - lon_delta, "ymin": latitude - lat_delta,
        "xmax": longitude + lon_delta, "ymax": latitude + lat_delta,
    }


def query_params(envelope: dict[str, float], offset: int) -> dict[str, Any]:
    return {
        "where": "1=1",
        "geometry": json.dumps({**envelope, "spatialReference": {"wkid": 4326}}, separators=(",", ":")),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": FIELDS,
        "returnGeometry": "true",
        "returnTrueCurves": "false",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": str(PAGE_SIZE),
        "resultOffset": str(offset),
        "orderByFields": "ObjectId",
    }


def fetch_layer(session: requests.Session, name: str, url: str, envelope: dict[str, float]) -> dict[str, Any]:
    features: dict[str, dict[str, Any]] = {}
    pages = 0
    offset = 0
    request_urls = []
    while pages < MAX_PAGES:
        response = session.get(url, params=query_params(envelope, offset), timeout=90, headers=HEADERS)
        response.raise_for_status()
        request_urls.append(response.url)
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(f"{name}: ArcGIS error: {payload['error']}")
        page = payload.get("features")
        if not isinstance(page, list):
            raise RuntimeError(f"{name}: response did not contain a GeoJSON feature list")
        if not page:
            if payload.get("exceededTransferLimit"):
                raise RuntimeError(f"{name}: empty page still reports exceededTransferLimit")
            break
        added = 0
        for feature in page:
            props = feature.get("properties") or {}
            oid = feature.get("id")
            if oid in (None, ""):
                oid = props.get("ObjectId")
            if oid in (None, ""):
                oid = props.get("OBJECTID")
            if oid in (None, ""):
                raise RuntimeError(f"{name}: feature without stable ObjectId")
            key = str(oid)
            if key not in features:
                features[key] = feature
                added += 1
        pages += 1
        if added == 0:
            raise RuntimeError(f"{name}: pagination returned no new IDs at offset {offset}")
        offset += len(page)
        if len(page) < PAGE_SIZE and not payload.get("exceededTransferLimit"):
            break
    else:
        raise RuntimeError(f"{name}: exceeded safety cap of {MAX_PAGES} pages")

    return {
        "layer": name,
        "url": url,
        "status": "success",
        "pages": pages,
        "records_fetched": len(features),
        "request_urls": request_urls,
        "features": [features[key] for key in sorted(features)],
    }


def filter_to_radius(collection: dict[str, Any], latitude: float, longitude: float, radius_m: float) -> dict[str, Any]:
    centre = transform(TO_TM, Point(longitude, latitude))
    circle = centre.buffer(radius_m)
    retained = []
    missing_geometry = 0
    geometry_errors = 0
    outside_scope = 0
    for feature in collection["features"]:
        geometry = feature.get("geometry")
        if not geometry:
            missing_geometry += 1
            continue
        try:
            projected = transform(TO_TM, shape(geometry))
            if not projected.is_valid:
                projected = projected.buffer(0)
            if projected.is_empty or not projected.intersects(circle):
                outside_scope += 1
                continue
            retained.append(feature)
        except Exception:
            geometry_errors += 1
    result = dict(collection)
    result["features"] = retained
    result["records_in_scope"] = len(retained)
    result["records_outside_scope"] = outside_scope
    result["records_missing_geometry"] = missing_geometry
    result["records_geometry_error"] = geometry_errors
    return result


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_snapshot(path: Path, value: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(gzip.compress(payload, mtime=0))
    os.replace(temporary, path)
    return path.stat().st_size


def collect(config: dict[str, Any], session: requests.Session | None = None) -> dict[str, Any]:
    latitude = float(config["latitude"])
    longitude = float(config["longitude"])
    radius_m = float(config["radius_km"]) * 1000
    envelope = query_envelope(latitude, longitude, radius_m)
    scope = {
        "latitude": latitude, "longitude": longitude, "radius_m": radius_m,
        "query_envelope": envelope, "fields": FIELDS, "layers": LAYERS,
    }
    scope_hash = canonical_hash(scope)
    client = session or requests.Session()
    layer_results = {}
    # Fetch all layers before constructing/publishing the snapshot. Any error aborts the run.
    for name, url in LAYERS.items():
        fetched = fetch_layer(client, name, url, envelope)
        layer_results[name] = filter_to_radius(fetched, latitude, longitude, radius_m)

    checked_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "checked_at": checked_at,
        "status": "success",
        "scope_hash": scope_hash,
        "scope": scope,
        "area": config.get("name"),
        "layers": layer_results,
        "counts": {
            name: {
                "records_fetched_in_envelope": layer["records_fetched"],
                "records_in_scope": layer["records_in_scope"],
                "records_outside_scope": layer["records_outside_scope"],
                "records_missing_geometry": layer["records_missing_geometry"],
                "records_geometry_error": layer["records_geometry_error"],
                "pages": layer["pages"],
            }
            for name, layer in layer_results.items()
        },
        "notes": [
            "Point, line and polygon layers are stored separately; they may represent multiple geometries for one Samråd case.",
            "The source Beteckn/UUID fields are preserved for later case-level grouping.",
            "Absence from a later snapshot is not interpreted as cancellation, deletion or completed action.",
            "The spatial query uses a conservative envelope and then applies an exact EPSG:3006 circular intersection filter.",
        ],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_small_manifest(result: dict[str, Any], snapshot_path: str, snapshot_bytes: int, snapshot_sha256: str) -> dict[str, Any]:
    layer_manifest = {}
    for name in ("points", "lines", "areas"):
        layer = result.get("layers", {}).get(name, {})
        counts = result.get("counts", {}).get(name, {})
        missing_geometry = counts.get("records_missing_geometry")
        geometry_errors = counts.get("records_geometry_error")
        geometry_counts_valid = isinstance(missing_geometry, int) and isinstance(geometry_errors, int)
        layer_complete = (
            layer.get("status") == "success"
            and isinstance(counts.get("pages"), int)
            and isinstance(counts.get("records_fetched_in_envelope"), int)
            and isinstance(counts.get("records_in_scope"), int)
            and geometry_counts_valid
            and missing_geometry == 0
            and geometry_errors == 0
        )
        layer_manifest[name] = {
            "status": "complete_for_configured_scope" if layer_complete else "partial_or_unknown",
            "pagination_status": "exhausted" if layer.get("status") == "success" else "unknown",
            "pages": counts.get("pages"),
            "records_fetched_in_envelope": counts.get("records_fetched_in_envelope"),
            "records_in_scope": counts.get("records_in_scope"),
            "records_outside_scope": counts.get("records_outside_scope"),
            "records_missing_geometry": counts.get("records_missing_geometry"),
            "records_geometry_error": counts.get("records_geometry_error"),
        }
    complete = all(item["status"] == "complete_for_configured_scope" for item in layer_manifest.values())
    return {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "status": "success" if complete else "partial",
        "completeness_status": "complete_for_configured_scope" if complete else "partial_or_unknown",
        "completeness_basis": "all three configured layers paginated to exhaustion; all fetched features assigned to in-scope/outside-scope with no missing or failed geometries",
        "source_total_reconciled": False,
        "checked_at": result.get("checked_at"),
        "scope_hash": result.get("scope_hash"),
        "scope": result.get("scope"),
        "snapshot": {
            "path": snapshot_path,
            "bytes": snapshot_bytes,
            "sha256": snapshot_sha256,
        },
        "layers": layer_manifest,
    }


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        result = collect(config)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1
    stamp = datetime.fromisoformat(result["checked_at"].replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = SNAPSHOTS / f"samrad_{stamp}.json.gz"
    size = write_snapshot(snapshot_path, result)
    snapshot_relative_path = str(snapshot_path.relative_to(ROOT))
    manifest = build_small_manifest(result, snapshot_relative_path, size, sha256_file(snapshot_path))
    atomic_write_json(LATEST, result)
    manifest_path = DATA / "samrad_latest_manifest.json"
    atomic_write_json(manifest_path, manifest)
    print(json.dumps({
        "status": result["status"], "checked_at": result["checked_at"],
        "scope_hash": result["scope_hash"], "counts": result["counts"],
        "snapshot": snapshot_relative_path, "snapshot_bytes": size,
        "latest": str(LATEST.relative_to(ROOT)),
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_status": manifest["completeness_status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
