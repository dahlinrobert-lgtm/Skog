#!/usr/bin/env python3
"""Daily snapshot of Skogsstyrelsen completed-harvest polygons for Gräsmyr."""
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/area.json").read_text(encoding="utf-8"))
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
DATA.mkdir(exist_ok=True)
SNAPSHOTS.mkdir(exist_ok=True)

LAT = CONFIG["latitude"]
LON = CONFIG["longitude"]
RADIUS_M = int(float(CONFIG["radius_km"]) * 1000)
URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query"
FIELDS = "OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,SkogsodlHa,Natforha,Avvdatum,KallaDatum,KallaAreal,Forebild,Efterbild,Arealha"


def canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fetch():
    params = {
        "where": "1=1",
        "geometry": json.dumps({"x": LON, "y": LAT, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "distance": str(RADIUS_M),
        "units": "esriSRUnit_Meter",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": "2000",
    }
    response = requests.get(URL, params=params, timeout=90, headers={"User-Agent": "Skog-Grasmyr-monitor/0.4"})
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError(data["error"].get("message", "Skogsstyrelsen REST error"))
    if not isinstance(data.get("features"), list):
        raise RuntimeError("The completed-harvest service returned no valid GeoJSON feature list")
    if data.get("exceededTransferLimit"):
        raise RuntimeError("The completed-harvest query exceeded the service transfer limit; refusing to save an incomplete snapshot")
    return data, response.url


def main():
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    data, request_url = fetch()
    features = data["features"]
    compact = {}
    for feature in features:
        props = feature.get("properties") or {}
        key = str(feature.get("id") or props.get("OBJECTID") or "")
        if not key:
            continue
        compact[key] = {
            "properties": props,
            "geometry_sha256": canonical_hash(feature.get("geometry")),
        }

    current_path = DATA / "completed_latest.json"
    old = {}
    if current_path.exists():
        try:
            old_data = json.loads(current_path.read_text(encoding="utf-8"))
            old = old_data.get("features_by_id", {})
        except (OSError, json.JSONDecodeError):
            old = {}
    old_ids, current_ids = set(old), set(compact)
    is_baseline = not current_path.exists()
    result = {
        "checked_at": now.isoformat().replace("+00:00", "Z"),
        "source": URL,
        "request_url": request_url,
        "area": {"latitude": LAT, "longitude": LON, "radius_m": RADIUS_M},
        "count": len(features),
        "baseline": is_baseline,
        "new_ids": [] if is_baseline else sorted(current_ids - old_ids),
        "missing_ids": [] if is_baseline else sorted(old_ids - current_ids),
        "changed_geometry_ids": [] if is_baseline else sorted(
            key for key in current_ids & old_ids
            if compact[key]["geometry_sha256"] != old[key].get("geometry_sha256")
        ),
        "features_by_id": compact,
        "note": "Current public-layer snapshot. Missing IDs mean absent from this query, not proof of deletion or felling; service coverage, filtering and source revisions may also explain changes."
    }
    current_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep the full geometry as a compressed daily archive so later work can compare
    # actual shapes, not only attributes and hashes.
    archive_path = SNAPSHOTS / f"completed_{stamp}.geojson.gz"
    with gzip.open(archive_path, "wt", encoding="utf-8") as stream:
        json.dump({
            "type": "FeatureCollection",
            "name": "Skogsstyrelsen Utförda avverkningar",
            "checked_at": result["checked_at"],
            "source": URL,
            "features": features,
        }, stream, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({
        "checked_at": result["checked_at"],
        "count": len(features),
        "baseline": is_baseline,
        "new_ids": len(result["new_ids"]),
        "missing_ids": len(result["missing_ids"]),
        "changed_geometry_ids": len(result["changed_geometry_ids"]),
        "archive": str(archive_path.relative_to(ROOT)),
        "archive_bytes": archive_path.stat().st_size,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
