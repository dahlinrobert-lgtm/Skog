#!/usr/bin/env python3
"""Measure completed-harvest timing relative to Omdrev laser-scan dates.

For each completed-harvest polygon, intersect 2.5 km metadata tiles and retain
scan observations by survey round. Report the latest registered scan before the
harvest date and earliest registered scan after it. Dates are evidence from the
metadata service; they are not necessarily a complete flight history.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import tempfile
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
METADATA_JSON = ROOT / "raster-three-omdrev" / "flight_metadata" / "laser_scan_index_tiles_esrijson.json"
DEFAULT_OUTPUT = ROOT / "raster-three-omdrev" / "flight_metadata"
COMPLETED_URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query"
COMPLETED_FIELDS = "OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,Avvdatum,Arealha,KallaDatum,KallaAreal,Forebild,Efterbild"
TO_TM = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True).transform
PAGE_SIZE = 200


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        # The completed-harvest service uses ArcGIS epoch milliseconds.
        if numeric > 100_000_000_000:
            return datetime.fromtimestamp(numeric / 1000, tz=timezone.utc).date()
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def arcgis_scan_date(value):
    """Normalize the metadata layer's date field, which may be epoch ms or text."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 100_000_000_000:
            return datetime.fromtimestamp(numeric / 1000, tz=timezone.utc).date()
        text = str(int(numeric))
    else:
        text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        try:
            return datetime.strptime(text, "%Y%m%d").date()
        except ValueError:
            return None
    return parse_date(text)


def polygonal(geometry):
    if not geometry:
        return None
    try:
        geom = shape(geometry)
        if geom.is_empty or not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty:
            return None
        return transform(TO_TM, geom)
    except Exception:
        return None


def fetch_completed(extent, limit, session):
    params = {
        "where": "Avvdatum IS NOT NULL",
        "geometry": json.dumps(extent, separators=(",", ":")),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "3006",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": COMPLETED_FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": PAGE_SIZE,
        "resultOffset": 0,
        "orderByFields": "OBJECTID ASC",
    }
    features = {}
    offset = 0
    while True:
        params["resultOffset"] = offset
        response = session.get(COMPLETED_URL, params=params, timeout=(25, 120))
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(f"Completed-harvest service error: {payload['error']}")
        page = payload.get("features")
        if not isinstance(page, list):
            raise RuntimeError("Completed-harvest service returned no feature list")
        for feature in page:
            attrs = feature.get("properties") or feature.get("attributes") or {}
            oid = attrs.get("OBJECTID") or feature.get("id")
            if oid is None or not feature.get("geometry"):
                continue
            features[str(oid)] = feature
        offset += len(page)
        print(f"Completed polygons fetched: {len(features)} (offset {offset})", flush=True)
        if not page or len(page) < PAGE_SIZE or (limit and len(features) >= limit):
            break
        time.sleep(0.15)
    result = list(features.values())
    return result[:limit] if limit else result


def load_scan_observations(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for feature in payload.get("features", []):
        attrs = feature.get("attributes") or {}
        geom = polygonal(feature.get("geometry"))
        scan_date = arcgis_scan_date(attrs.get("Datum"))
        if geom is None or scan_date is None:
            continue
        rows.append({
            "index_tile": attrs.get("Indexruta"),
            "survey_round": attrs.get("Omdrev"),
            "scan_date": scan_date,
            "scan_file": attrs.get("Las_Namn"),
            "leaf_status": attrs.get("Lov_Avlov"),
            "scanner_model": attrs.get("Skannermodell"),
            "flight_block": attrs.get("Block"),
            "tile_geometry": geom,
        })
    return rows


def choose_scan_dates(observations, harvest_date):
    before = [item for item in observations if item["scan_date"] < harvest_date]
    after = [item for item in observations if item["scan_date"] > harvest_date]
    # Same-day observations are neither before nor after. Keep them separately.
    same = [item for item in observations if item["scan_date"] == harvest_date]
    previous = max(before, key=lambda item: item["scan_date"]) if before else None
    following = min(after, key=lambda item: item["scan_date"]) if after else None

    def compact(item, prefix):
        if item is None:
            return {
                f"{prefix}_scan_date": None,
                f"{prefix}_survey_round": None,
                f"{prefix}_scan_file": None,
                f"{prefix}_leaf_status": None,
                f"{prefix}_flight_block": None,
            }
        return {
            f"{prefix}_scan_date": item["scan_date"].isoformat(),
            f"{prefix}_survey_round": item["survey_round"],
            f"{prefix}_scan_file": item["scan_file"],
            f"{prefix}_leaf_status": item["leaf_status"],
            f"{prefix}_flight_block": item["flight_block"],
        }

    return {
        **compact(previous, "previous"),
        **compact(following, "next"),
        "days_since_previous_scan": (harvest_date - previous["scan_date"]).days if previous else None,
        "days_until_next_scan": (following["scan_date"] - harvest_date).days if following else None,
        "same_day_scan_count": len(same),
        "scan_observations_intersecting": len(observations),
        "has_before_and_after": bool(previous and following),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="Maximum completed polygons; 0 means all")
    parser.add_argument("--raster-codes", default="12,21,23")
    args = parser.parse_args()

    if not METADATA_JSON.is_file():
        raise FileNotFoundError(f"Missing scan metadata: {METADATA_JSON}")
    metadata = load_scan_observations(METADATA_JSON)
    if not metadata:
        raise RuntimeError("No usable dated scan metadata observations")

    # The raster extent list is recorded in the scan-collection summary. We fetch
    # harvest polygons separately per selected extent to preserve clear spatial scope.
    summary_path = METADATA_JSON.parent / "laser_scan_metadata_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    extent_by_code = {
        item["raster_code"]: item["bounds_epsg3006"]
        for item in summary.get("raster_extents", [])
    }
    codes = [x.strip() for x in args.raster_codes.split(",") if x.strip()]
    missing = sorted(set(codes) - set(extent_by_code))
    if missing:
        raise ValueError(f"Selected raster extents missing from summary: {missing}")

    session = requests.Session()
    session.headers["User-Agent"] = "Skogskoll-harvest-scan-intervals/1.0"

    # Cache scan polygons in an STRtree-like bounding-box grid: only scan tiles
    # overlapping the requested completed polygon envelope are tested precisely.
    by_code_features = {}
    for code in codes:
        b = extent_by_code[code]
        extent = {
            "xmin": b["xmin"], "ymin": b["ymin"], "xmax": b["xmax"], "ymax": b["ymax"],
            "spatialReference": {"wkid": 3006},
        }
        by_code_features[code] = fetch_completed(extent, args.limit, session)

    # Build a simple 2.5 km spatial hash for candidate scan tiles.
    grid = defaultdict(list)
    for item in metadata:
        minx, miny, maxx, maxy = item["tile_geometry"].bounds
        gx0, gx1 = math.floor(minx / 2500), math.floor(maxx / 2500)
        gy0, gy1 = math.floor(miny / 2500), math.floor(maxy / 2500)
        for gx in range(gx0, gx1 + 1):
            for gy in range(gy0, gy1 + 1):
                grid[(gx, gy)].append(item)

    out_rows = []
    count = Counter()
    for code, features in by_code_features.items():
        for feature in features:
            attrs = feature.get("properties") or feature.get("attributes") or {}
            harvest_date = parse_date(attrs.get("Avvdatum"))
            harvest_geom = polygonal(feature.get("geometry"))
            if harvest_date is None or harvest_geom is None:
                count["missing_date_or_geometry"] += 1
                continue
            minx, miny, maxx, maxy = harvest_geom.bounds
            candidates = {}
            for gx in range(math.floor(minx / 2500), math.floor(maxx / 2500) + 1):
                for gy in range(math.floor(miny / 2500), math.floor(maxy / 2500) + 1):
                    for item in grid.get((gx, gy), []):
                        key = (str(item["index_tile"]), str(item["survey_round"]), item["scan_date"].isoformat(), str(item["scan_file"]))
                        candidates[key] = item
            intersecting = []
            for item in candidates.values():
                tile = item["tile_geometry"]
                if not harvest_geom.intersects(tile):
                    continue
                intersection = harvest_geom.intersection(tile)
                if intersection.is_empty or intersection.area <= 0:
                    continue
                intersecting.append(item)

            observations = intersecting
            # Keep each scan round/date separately; derive closest preceding and
            # following observations for each polygon, not from a national average.
            temporal = choose_scan_dates(observations, harvest_date)
            harvest_id = str(attrs.get("OBJECTID") or feature.get("id") or "")
            base = {
                "raster_code": code,
                "completed_object_id": harvest_id,
                "case_number": attrs.get("Beteckn"),
                "municipality": attrs.get("Kommun"),
                "county": attrs.get("Lan"),
                "harvest_date": harvest_date.isoformat(),
                "source_area_ha": attrs.get("Arealha"),
                "harvest_type": attrs.get("Avverktyp"),
                "scan_tile_count": len({str(item["index_tile"]) for item in intersecting}),
                "scan_observation_count": len(intersecting),
                **temporal,
                "interpretation": (
                    "Nearest registered metadata scan dates intersecting this completed polygon. "
                    "This brackets the harvest only when a scan exists both before and after. "
                    "A missing side means the interval is open, not zero."
                ),
            }
            out_rows.append(base)
            count["completed_polygons"] += 1
            if temporal["previous_scan_date"] and temporal["next_scan_date"]:
                count["bracketed_by_scans"] += 1
            elif temporal["previous_scan_date"]:
                count["only_previous_scan"] += 1
            elif temporal["next_scan_date"]:
                count["only_next_scan"] += 1
            else:
                count["no_scan_observation"] += 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "completed_harvest_scan_intervals.csv"
    json_path = args.output_dir / "completed_harvest_scan_intervals_summary.json"
    columns = [
        "raster_code", "completed_object_id", "case_number", "municipality", "county",
        "harvest_date", "source_area_ha", "harvest_type", "scan_tile_count",
        "scan_observation_count", "previous_scan_date", "previous_survey_round",
        "previous_scan_file", "previous_leaf_status", "previous_flight_block",
        "days_since_previous_scan", "next_scan_date", "next_survey_round",
        "next_scan_file", "next_leaf_status", "next_flight_block", "days_until_next_scan",
        "same_day_scan_count", "has_before_and_after", "interpretation",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(out_rows)

    output_summary = {
        "source_completed_harvest_layer": COMPLETED_URL,
        "source_scan_metadata": str(METADATA_JSON.relative_to(ROOT)),
        "selected_raster_codes": codes,
        "completed_polygons_examined": len(out_rows),
        "scan_observations_loaded": len(metadata),
        "counts": dict(count),
        "date_logic": (
            "For every completed-harvest polygon, intersect scan-index polygons and "
            "identify the closest registered scan date strictly before and strictly "
            "after Avvdatum. Days are calendar-day differences."
        ),
        "important_limitations": [
            "Avvdatum is the source layer's reported completed-harvest date; it is not necessarily the exact felling day for every part of the polygon.",
            "The completed-harvest layer is satellite-derived and may describe a detected event rather than the actual operational date; preserve the source date and provenance.",
            "Scan metadata may expose only a latest date when a tile has multiple scan events. The derived interval can therefore be wider than the true flight interval.",
            "A scan-index tile is an approximately 2.5 km reference area, not an aircraft trajectory; polygon overlap gives spatial context, not proof that every part of the harvest polygon was scanned on that date.",
            "When either the previous or next scan is missing, the corresponding interval is open and must not be represented as zero or as an exact delay.",
            "This workflow uses metadata observations from the selected raster extents and only evaluates completed polygons within those extents.",
        ],
    }
    json_path.write_text(json.dumps(output_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output_summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
