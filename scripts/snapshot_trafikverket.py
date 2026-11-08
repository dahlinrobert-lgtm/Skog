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


def query_count(layer_url, layer_name):
    result = request_json(
        layer_url.rstrip("/") + "/query",
        {"where": "1=1", "returnCountOnly": "true", "f": "json"},
        context=f"Count query for {layer_name}",
    )
    count = result.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"Count query for {layer_name}: missing integer count in {result}")
    return count


def query_page(layer_url, offset, page_size, layer_name, oid_field):
    """Query JSON pages first; GeoJSON is a compatibility fallback."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultOffset": str(offset),
        "resultRecordCount": str(page_size),
        "f": "json",
    }
    if oid_field:
        params["orderByFields"] = f"{oid_field} ASC"
    else:
        params["orderByFields"] = "OBJECTID ASC"

    try:
        return request_json(
            layer_url.rstrip("/") + "/query",
            params,
            context=f"Feature page for {layer_name}, offset {offset}",
        )
    except RuntimeError as first_error:
        # On some MapServer layers GeoJSON is supported by the service generally
        # but not for a specific query/pagination combination. Retry the same
        # page as GeoJSON only after retaining the JSON error as diagnostic info.
        fallback = dict(params)
        fallback["f"] = "geojson"
        try:
            return request_json(
                layer_url.rstrip("/") + "/query",
                fallback,
                context=f"GeoJSON feature page for {layer_name}, offset {offset}",
            )
        except RuntimeError as second_error:
            raise RuntimeError(
                f"Both JSON and GeoJSON page requests failed for {layer_name} "
                f"at offset {offset}. JSON error: {first_error}. "
                f"GeoJSON error: {second_error}"
            ) from second_error


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
    expected_count = query_count(layer_url, name)
    oid_field = layer.get("objectIdField") or layer.get("objectIdFieldName")
    if not oid_field:
        oid_field = next(
            (field.get("name") for field in layer.get("fields", [])
             if field.get("type") == "esriFieldTypeOID"),
            None,
        )
    page_size = min(BATCH_SIZE, int(layer.get("maxRecordCount") or BATCH_SIZE))
    features = []
    seen = set()
    offset = 0
    has_more = expected_count > 0

    while has_more:
        payload = query_page(layer_url, offset, page_size, name, oid_field)
        raw_page = payload.get("features", [])
        page = [normalize_feature(feature) for feature in raw_page]
        exceeded = payload.get("exceededTransferLimit")
        if not page and exceeded:
            raise RuntimeError(
                f"ArcGIS reports exceededTransferLimit but returned no features "
                f"for {name} at offset {offset}; refusing to advance blindly"
            )
        if not page:
            has_more = False
            break
        for feature in page:
            identity = feature_identity(feature, oid_field)
            if identity in seen:
                raise RuntimeError(
                    f"Duplicate feature across pages in {name} at offset {offset}; "
                    "refusing an unreliable snapshot"
                )
            seen.add(identity)
            features.append(feature)
        offset += len(page)
        has_more = bool(exceeded)
        if not has_more and len(features) < expected_count:
            # If server omits exceededTransferLimit, count remains the authoritative
            # completeness target; continue at the next offset.
            has_more = offset < expected_count
        if offset > expected_count:
            raise RuntimeError(
                f"Pagination exceeded source count in {name}: "
                f"{offset} records returned for count {expected_count}"
            )
        time.sleep(0.15)

    if len(features) != expected_count:
        raise RuntimeError(
            f"Layer count mismatch for {name}: downloaded {len(features)} of {expected_count}"
        )

    selected = [feature for feature in features if in_envelope(feature)]
    collection = {"type": "FeatureCollection", "name": name, "features": selected}
    raw = json.dumps(collection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with out.open("wb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as gz:
            gz.write(raw)

    return {
        "id": layer_id,
        "name": name,
        "geometry_type": layer.get("geometryType"),
        "id_query_mode": "count-plus-offset-pagination",
        "source_object_count": expected_count,
        "downloaded_source_feature_count": len(features),
        "pilot_envelope_feature_count": len(selected),
        "file": str(out),
        "compressed_bytes": out.stat().st_size,
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
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
