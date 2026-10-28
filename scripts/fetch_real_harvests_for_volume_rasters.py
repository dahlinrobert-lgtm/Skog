#!/usr/bin/env python3
"""Fetch reproducible real completed-harvest polygons within committed raster extents."""
from __future__ import annotations

import argparse
import json
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import rasterio
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query"
FIELDS = "OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,Avvdatum,Arealha"
RASTER_CODES = ("07", "10", "12", "13", "21", "23")
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "skogliga-grunddata"
PAGE_SIZE = 200
MAX_CONSECUTIVE_FAILURES = 8


def make_session():
    """Retry transient HTTP/network failures without changing query semantics."""
    retry = Retry(
        total=6,
        connect=6,
        read=6,
        status=6,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "Skogskoll-volume-attributes/1.1"})
    return session


def raster_extent(code):
    archive_path = DATA_DIR / f"sks_Volym_omdrev3_{code}.zip"
    with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory() as temp:
        members = [
            m for m in archive.namelist()
            if not m.endswith("/") and Path(m).suffix.lower() in {".tif", ".tiff"}
        ]
        if len(members) != 1:
            raise ValueError(f"{archive_path.name}: expected one TIFF, found {len(members)}")
        target = Path(temp) / Path(members[0]).name
        with archive.open(members[0]) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        with rasterio.open(target) as ds:
            if ds.crs is None or ds.crs.to_epsg() != 3006:
                raise ValueError(f"Raster {code} expected EPSG:3006, got {ds.crs}")
            b = ds.bounds
            return {
                "xmin": b.left,
                "ymin": b.bottom,
                "xmax": b.right,
                "ymax": b.top,
                "spatialReference": {"wkid": 3006},
            }


def fetch(code, extent, limit, session):
    params = {
        "where": "1=1",
        "geometry": json.dumps(extent, separators=(",", ":")),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "3006",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": PAGE_SIZE,
        "resultOffset": 0,
        "orderByFields": "OBJECTID ASC",
    }
    features_by_id = {}
    offset = 0
    more = False
    consecutive_failures = 0

    while True:
        params["resultOffset"] = offset
        try:
            response = session.get(URL, params=params, timeout=(20, 120))
            response.raise_for_status()
            data = response.json()
            if data.get("error"):
                raise RuntimeError(f"Raster {code}: ArcGIS error {data['error']}")
            page = data.get("features")
            if not isinstance(page, list):
                raise ValueError(f"Raster {code}: missing feature list")
        except (requests.RequestException, ValueError) as exc:
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                raise RuntimeError(
                    f"Raster {code}: request failed at resultOffset={offset} after "
                    f"{consecutive_failures} consecutive failures; "
                    f"{len(features_by_id)} unique polygons fetched so far. Last error: {exc}"
                ) from exc
            delay = min(60, 2 ** consecutive_failures)
            print(
                f"Raster {code}: temporary request failure at offset {offset} "
                f"({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}); "
                f"retrying in {delay}s: {exc}",
                flush=True,
            )
            time.sleep(delay)
            continue

        consecutive_failures = 0
        more = more or bool(data.get("exceededTransferLimit"))
        for feature in page:
            if not feature.get("geometry"):
                continue
            attrs = feature.get("properties") or feature.get("attributes") or {}
            object_id = attrs.get("OBJECTID")
            key = str(object_id) if object_id is not None else f"offset:{offset}:count:{len(features_by_id)}"
            features_by_id.setdefault(key, feature)

        offset += len(page)
        print(
            f"Raster {code}: fetched page ending at offset {offset}; "
            f"{len(features_by_id)} unique polygons retained",
            flush=True,
        )
        if not page or len(page) < PAGE_SIZE or (limit and len(features_by_id) >= limit):
            break

    features = list(features_by_id.values())
    if limit and len(features) > limit:
        features = features[:limit]
    return {
        "type": "FeatureCollection",
        "name": f"real_completed_harvest_raster_{code}",
        "metadata": {
            "raster_code": code,
            "extent_epsg3006": extent,
            "source": URL,
            "source_layer": 1,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "count": len(features),
            "requested_limit": limit or "all",
            "source_more_matching_features": more,
            "note": (
                "Polygons intersecting the exact original raster extent; limit 0 means "
                "all returned features. Results are deduplicated by OBJECTID."
            ),
        },
        "features": features,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="Maximum features per raster; 0 fetches all")
    parser.add_argument("--raster-codes", default="07,10,12,13,21,23")
    args = parser.parse_args()
    if args.limit < 0:
        raise ValueError("--limit must be >= 0")
    codes = tuple(value.strip() for value in args.raster_codes.split(",") if value.strip())
    if not codes or any(code not in RASTER_CODES for code in codes):
        raise ValueError("--raster-codes must contain one or more of: " + ", ".join(RASTER_CODES))

    with make_session() as session:
        groups = [fetch(code, raster_extent(code), args.limit, session) for code in codes]
    doc = {
        "type": "FeatureCollection",
        "name": "real_completed_harvest_polygons_by_volume_raster",
        "metadata": {
            "source": "Skogsstyrelsen öppna utförda avverkningar",
            "note": (
                "Features are grouped by raster coverage; polygons may occur in more than "
                "one raster group at raster boundaries."
            ),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "raster_groups": groups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "Fetched polygons by raster: "
        + ", ".join(f'{group["metadata"]["raster_code"]}={group["metadata"]["count"]}' for group in groups)
    )


if __name__ == "__main__":
    main()
