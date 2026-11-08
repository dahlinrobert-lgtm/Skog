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


def request_json(url, params=None, attempts=5):
    query = urllib.parse.urlencode(params or {"f": "pjson"})
    req = urllib.request.Request(
        url + ("&" if "?" in url else "?") + query,
        headers={"User-Agent": "Skog-Trafikverket-snapshot/1.0"},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
            if "error" in data:
                raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError):
            if attempt == attempts - 1:
                raise
            time.sleep(min(2**attempt, 20))


def query_count(layer_url):
    """Return the unfiltered source count; this form is broadly supported by ArcGIS."""
    result = request_json(layer_url.rstrip("/") + "/query", {
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
    })
    count = result.get("count")
    if not isinstance(count, int):
        raise RuntimeError(f"ArcGIS count response missing integer count: {result}")
    return count


def query_page(layer_url, offset, page_size):
    """Fetch one ordered page with geometry; do not depend on object-ID query support."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "orderByFields": "OBJECTID ASC",
        "resultOffset": str(offset),
        "resultRecordCount": str(page_size),
        "f": "geojson",
    }
    try:
        return request_json(layer_url.rstrip("/") + "/query", params)
    except Exception as exc:
        # Some MapServer layers reject the explicit sort field even though they
        # support pagination. Retry without the sort; completeness is checked
        # against the count and unique object IDs below.
        if "OBJECTID" not in str(exc).upper() and "ORDER" not in str(exc).upper():
            raise
        params.pop("orderByFields", None)
        return request_json(layer_url.rstrip("/") + "/query", params)


def feature_identity(feature, oid_field):
    properties = feature.get("properties") or {}
    if oid_field and properties.get(oid_field) is not None:
        return str(properties[oid_field])
    for key, value in properties.items():
        if key.lower() in {"objectid", "object_id", "fid"} and value is not None:
            return str(value)
    # Geometry+properties fingerprint allows reliable duplicate detection even
    # when the service omits the OID field in layer metadata.
    canonical = json.dumps(
        {"geometry": feature.get("geometry"), "properties": properties},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    expected_count = query_count(layer_url)
    oid_field = layer.get("objectIdField") or layer.get("objectIdFieldName")
    page_size = min(BATCH_SIZE, int(layer.get("maxRecordCount") or BATCH_SIZE))
    features = []
    seen = set()
    offset = 0

    while offset < expected_count:
        payload = query_page(layer_url, offset, page_size)
        page = payload.get("features", [])
        if not page:
            raise RuntimeError(
                f"Pagination ended early for layer {layer_id} ({name}): "
                f"{len(features)} of {expected_count} source features"
            )
        for feature in page:
            identity = feature_identity(feature, oid_field)
            if identity in seen:
                raise RuntimeError(
                    f"Duplicate feature across pages in layer {layer_id} ({name}); "
                    "refusing an unreliable snapshot"
                )
            seen.add(identity)
            features.append(feature)
        offset += len(page)
        if len(page) < page_size and offset < expected_count:
            raise RuntimeError(
                f"Short page for layer {layer_id} ({name}): "
                f"{offset} of {expected_count} source features"
            )
        time.sleep(0.15)

    if len(features) != expected_count:
        raise RuntimeError(
            f"Layer count mismatch for {layer_id} ({name}): "
            f"downloaded {len(features)} of {expected_count}"
        )

    # Preserve the source count but only persist geometries intersecting the
    # Gräsmyr pilot envelope. Bounding-box intersection is conservative for
    # lines/polygons and avoids clipping or modifying source geometry.
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
        meta = request_json(base, {"f": "pjson"})
        service = {
            "key": key,
            "url": base,
            "spatial_reference": meta.get("spatialReference"),
            "layers": [],
        }
        for layer in meta.get("layers", []):
            detail = request_json(f"{base}/{layer['id']}", {"f": "pjson"})
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
