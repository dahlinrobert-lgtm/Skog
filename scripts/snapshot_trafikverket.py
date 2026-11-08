#!/usr/bin/env python3
"""Fetch immutable weekly Trafikverket GeoJSON snapshots for the Gräsmyr pilot."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERVICES = [
    ("miljowebb", "https://vektor.trafikverket.se/gis/rest/services/MWLEXGEO/MiljowebbGeo/MapServer"),
    ("viltolyckor", "https://vektor.trafikverket.se/gis/rest/services/NVDB_p%C3%A5_karta/Viltolyckor_NVDBpakarta/MapServer"),
]
CENTRE = {"longitude": 19.66455, "latitude": 63.74646}
HALF_H = 37_500 / 111_000
HALF_W = 37_500 / (111_000 * math.cos(math.radians(CENTRE["latitude"])))
ENVELOPE = {
    "xmin": CENTRE["longitude"] - HALF_W,
    "ymin": CENTRE["latitude"] - HALF_H,
    "xmax": CENTRE["longitude"] + HALF_W,
    "ymax": CENTRE["latitude"] + HALF_H,
    "spatialReference": {"wkid": 4326},
}
ROOT = Path(os.environ.get("TRAFIKVERKET_SNAPSHOT_ROOT", "data/trafikverket/snapshots"))
DATE = os.environ.get("SNAPSHOT_DATE") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
BATCH_SIZE = int(os.environ.get("TRAFIKVERKET_BATCH_SIZE", "500"))


def request_json(url, params=None, attempts=5, context="ArcGIS request"):
    query = urllib.parse.urlencode(params or {"f": "pjson"})
    req = urllib.request.Request(
        url + ("&" if "?" in url else "?") + query,
        headers={"User-Agent": "Skog-Trafikverket-snapshot/1.0"},
    )
    last_error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
            if "error" in data:
                raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))
            return data
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(
                f"{context}: HTTP {exc.code}; endpoint={url}; "
                f"parameters={json.dumps(params or {}, ensure_ascii=False, sort_keys=True)}; "
                f"response={body[:3000]}"
            )
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = RuntimeError(
                f"{context}: endpoint={url}; "
                f"parameters={json.dumps(params or {}, ensure_ascii=False, sort_keys=True)}; "
                f"error={exc}"
            )
        if attempt < attempts - 1:
            time.sleep(min(2**attempt, 20))
    raise last_error


def spatial_params(envelope):
    geometry = {"xmin": envelope["xmin"], "ymin": envelope["ymin"], "xmax": envelope["xmax"], "ymax": envelope["ymax"], "spatialReference": {"wkid": 4326}}
    return {"where": "1=1", "geometry": json.dumps(geometry, separators=(",", ":")), "geometryType": "esriGeometryEnvelope", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"}


def query_spatial_count(layer_url, layer_name, envelope):
    params = {**spatial_params(envelope), "returnCountOnly": "true", "f": "json"}
    result = request_json(layer_url.rstrip("/") + "/query", params, context=f"Spatial count for {layer_name}")
    count = result.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"Spatial count for {layer_name}: missing integer count in {result}")
    return count


def split_envelope(e):
    x = (e["xmin"] + e["xmax"]) / 2
    y = (e["ymin"] + e["ymax"]) / 2
    return [
        {"xmin":e["xmin"],"ymin":e["ymin"],"xmax":x,"ymax":y},
        {"xmin":x,"ymin":e["ymin"],"xmax":e["xmax"],"ymax":y},
        {"xmin":e["xmin"],"ymin":y,"xmax":x,"ymax":e["ymax"]},
        {"xmin":x,"ymin":y,"xmax":e["xmax"],"ymax":e["ymax"]},
    ]


def query_spatial_features(layer_url, layer_name, envelope, oid_field):
    params = {**spatial_params(envelope), "outFields":"*", "returnGeometry":"true", "outSR":"4326", "f":"json"}
    payload = request_json(layer_url.rstrip("/") + "/query", params, context=f"Spatial feature query for {layer_name}")
    if payload.get("exceededTransferLimit"):
        return None
    rows = [normalize_feature(row) for row in payload.get("features", [])]
    ids = []
    for row in rows:
        props = row.get("attributes") or row.get("properties") or {}
        value = props.get(oid_field)
        if value is None:
            raise RuntimeError(f"Spatial response for {layer_name} lacks OID field {oid_field}")
        ids.append(int(value))
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"Duplicate OIDs in spatial response for {layer_name}")
    return rows


def collect_spatial_features(layer_url, layer_name, oid_field, max_record_count):
    """Fetch only the pilot area; recursively subdivide dense tiles below ArcGIS limits."""
    expected = query_spatial_count(layer_url, layer_name, ENVELOPE)
    if expected == 0:
        return [], 0, 0
    limit = max(1, min(int(max_record_count or 1000), 1000))
    collected = {}
    accepted = 0
    visited = 0

    def visit(tile, depth):
        nonlocal accepted, visited
        visited += 1
        if visited > 20000:
            raise RuntimeError(f"{layer_name}: exceeded 20000 spatial tiles")
        count = query_spatial_count(layer_url, layer_name, tile)
        if count == 0:
            return
        if count <= limit:
            rows = query_spatial_features(layer_url, layer_name, tile, oid_field)
            if rows is not None and len(rows) == count:
                for feature in rows:
                    props = feature.get("attributes") or feature.get("properties") or {}
                    oid = int(props[oid_field])
                    canonical = json.dumps(feature, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                    if oid in collected:
                        previous = json.dumps(collected[oid], sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                        if canonical != previous:
                            raise RuntimeError(f"{layer_name}: conflicting content for OID {oid} across tiles")
                    else:
                        collected[oid] = feature
                accepted += 1
                return
        if depth >= 12:
            raise RuntimeError(f"{layer_name}: unable to safely collect tile at depth {depth}, count={count}")
        for child in split_envelope(tile):
            visit(child, depth + 1)

    visit(ENVELOPE, 0)
    if len(collected) != expected:
        raise RuntimeError(f"{layer_name}: spatial completeness mismatch: unique={len(collected)}, root_count={expected}")
    return list(collected.values()), expected, accepted


def feature_identity(feature, oid_field):
    properties = feature.get("attributes") or feature.get("properties") or {}
    if oid_field and properties.get(oid_field) is not None:
        return str(properties[oid_field])
    for key, value in properties.items():
        if key.lower() in {"objectid", "object_id", "fid"} and value is not None:
            return str(value)
    canonical = json.dumps(
        {"geometry": feature.get("geometry"), "properties": properties},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_feature(feature):
    """Normalize ArcGIS JSON feature records into GeoJSON feature objects."""
    if "properties" in feature and "type" in feature:
        return feature
    geometry = feature.get("geometry")
    attributes = feature.get("attributes") or {}
    if geometry and "x" in geometry and "y" in geometry:
        geometry = {"type": "Point", "coordinates": [geometry["x"], geometry["y"]]}
    elif geometry and "paths" in geometry:
        paths = geometry["paths"]
        geometry = {"type": "LineString", "coordinates": paths[0]} if len(paths) == 1 else {
            "type": "MultiLineString", "coordinates": paths
        }
    elif geometry and "rings" in geometry:
        geometry = {"type": "Polygon", "coordinates": geometry["rings"]}
    elif geometry and "points" in geometry:
        geometry = {"type": "MultiPoint", "coordinates": geometry["points"]}
    return {"type": "Feature", "geometry": geometry, "properties": attributes}


def positions(coords):
    if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
        yield coords
    elif isinstance(coords, (list, tuple)):
        for child in coords:
            yield from positions(child)


def in_envelope(feature):
    coords = list(positions((feature.get("geometry") or {}).get("coordinates", [])))
    if not coords:
        return False
    xs = [point[0] for point in coords]
    ys = [point[1] for point in coords]
    return not (
        max(xs) < ENVELOPE["xmin"] or min(xs) > ENVELOPE["xmax"]
        or max(ys) < ENVELOPE["ymin"] or min(ys) > ENVELOPE["ymax"]
    )


def save_layer(service_key, layer, base_url):
    layer_id = layer["id"]
    name = layer.get("name", f"layer-{layer_id}")
    safe = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    folder = ROOT / DATE / service_key
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{layer_id:02d}-{safe}.geojson.gz"
    layer_url = f"{base_url.rstrip('/')}/{layer_id}"
    oid_field = layer.get("objectIdField") or layer.get("objectIdFieldName")
    if not oid_field:
        oid_field = next((field.get("name") for field in layer.get("fields", []) if field.get("type") == "esriFieldTypeOID"), None)
    if not oid_field:
        raise RuntimeError(f"{name}: no OID field exposed by layer metadata")
    features, expected, accepted_tiles = collect_spatial_features(
        layer_url, name, oid_field, layer.get("maxRecordCount", 1000)
    )
    collection = {"type": "FeatureCollection", "name": name, "features": features}
    raw = json.dumps(collection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with out.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as gz:
            gz.write(raw)
    return {
        "id": layer_id, "name": name, "geometry_type": layer.get("geometryType"),
        "collection_method": "adaptive-spatial-tiles", "oid_field": oid_field,
        "source_object_count": None, "pilot_envelope_expected_count": expected,
        "source_object_id_count": expected, "downloaded_feature_count": len(features),
        "downloaded_source_feature_count": len(features), "pilot_envelope_feature_count": len(features),
        "accepted_spatial_tiles": accepted_tiles, "file": str(out),
        "compressed_bytes": out.stat().st_size, "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "fields": [field.get("name") for field in layer.get("fields", [])],
    }


def main():
    snapshot = {
        "snapshot_date_utc": DATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "area": {
            "name": "Gräsmyr pilot",
            "centre_wgs84": CENTRE,
            "envelope_wgs84": ENVELOPE,
            "description": "Approximate 75 km x 75 km discovery envelope; not a property boundary.",
        },
        "services": [],
        "status": "complete",
    }
    total = 0
    for key, base in SERVICES:
        meta = request_json(base, {"f": "pjson"}, context=f"Service metadata for {key}")
        service = {
            "key": key,
            "url": base,
            "spatial_reference": meta.get("spatialReference"),
            "layers": [],
        }
        for layer in meta.get("layers", []):
            detail = request_json(
                f"{base}/{layer['id']}",
                {"f": "pjson"},
                context=f"Layer metadata for {key} layer {layer['id']} ({layer.get('name')})",
            )
            if detail.get("type") != "Feature Layer" or not detail.get("geometryType"):
                continue
            merged = {**layer, **detail}
            row = save_layer(key, merged, base)
            service["layers"].append(row)
            total += row["pilot_envelope_feature_count"]
            print(
                f"{key} layer {layer['id']} {layer.get('name')}: "
                f"{row['pilot_envelope_feature_count']} in pilot envelope "
                f"({row['downloaded_source_feature_count']}/{row['source_object_count']} "
                "source features verified)",
                flush=True,
            )
        snapshot["services"].append(service)

    snapshot["total_pilot_envelope_features"] = total
    snapshot["total_downloaded_features"] = total
    snapshot["total_feature_layers"] = sum(len(service["layers"]) for service in snapshot["services"])
    snapshot["manifest_sha256"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    manifest = ROOT / DATE / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshot {DATE}: {snapshot['total_feature_layers']} layers, {total} features in pilot envelope")
    print(f"Manifest: {manifest}")
    if total == 0:
        raise RuntimeError("Snapshot contains zero features; refusing to report success.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
