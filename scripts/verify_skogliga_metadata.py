#!/usr/bin/env python3
"""Verify Skogsstyrelsen Omdrev 3 raster metadata samples and extreme pixels against live REST services."""
from __future__ import annotations
import json, os, tempfile, zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import rasterio
import requests
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = DATA_DIR / "metadata-outlier-verification.json"
METADATA_QUERY_URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0/query"
IMAGE_IDENTIFY_URL = "https://geodata.skogsstyrelsen.se/arcgis/rest/services/Publikt/SkogligaGrunddata_3_1/ImageServer/identify"
METADATA_FIELDS = "Indexruta,Las_Namn,Datum,Lov_Avlov,Skannermodell,Block,CenterLanNamn,CenterKommunNamn,Omdrev"
NODATA_FALLBACK = -1
METADATA_TILE_M = 2500
MAX_SAMPLES_PER_RASTER = int(os.environ.get("MAX_METADATA_SAMPLES", "2500"))
QUERY_BATCH_SIZE = 150
OUTLIER_LIMIT = 4265
CODES = [x.strip() for x in os.environ.get("RASTER_CODES", "12,21,23").split(",") if x.strip()]


def post_json(session, url, params, label):
    response = session.post(url, data=params, timeout=(30, 120))
    if not response.ok:
        raise RuntimeError(f"{label}: HTTP {response.status_code}: {response.text[:500]}")
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"{label}: ArcGIS error: {json.dumps(payload['error'], ensure_ascii=False)[:1000]}")
    return payload


def evenly_sample(items, limit):
    if len(items) <= limit:
        return items
    indices = np.linspace(0, len(items) - 1, num=limit, dtype=np.int64)
    return [items[int(i)] for i in indices]


def inspect_archive(archive_path):
    """Read the TIFF in large windows; sample one valid cell per 2.5 km grid tile."""
    with tempfile.TemporaryDirectory(prefix="skog-metadata-verify-") as temp:
        with zipfile.ZipFile(archive_path) as archive:
            members = [m for m in archive.infolist()
                       if not m.is_dir() and Path(m.filename).suffix.lower() in {".tif", ".tiff"}]
            if len(members) != 1:
                raise ValueError(f"{archive_path.name}: expected exactly one TIFF, found {len(members)}")
            member = members[0]
            tif_path = Path(temp) / Path(member.filename).name
            with archive.open(member) as source, tif_path.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)

        with rasterio.open(tif_path) as ds:
            if ds.crs is None or ds.crs.to_epsg() != 3006:
                raise ValueError(f"{archive_path.name}: expected EPSG:3006, got {ds.crs}")
            if ds.count < 1:
                raise ValueError(f"{archive_path.name}: raster has no bands")
            nodata = ds.nodata if ds.nodata is not None else NODATA_FALLBACK
            samples_by_tile = {}
            outliers = []
            total = nodata_count = zero_count = positive_count = 0
            max_value = None
            max_location = None
            block_w, block_h = 1024, 512

            for row_off in range(0, ds.height, block_h):
                height = min(block_h, ds.height - row_off)
                for col_off in range(0, ds.width, block_w):
                    width = min(block_w, ds.width - col_off)
                    arr = ds.read(1, window=Window(col_off, row_off, width, height), masked=False)
                    total += int(arr.size)
                    valid = arr != nodata
                    nodata_count += int(arr.size - np.count_nonzero(valid))
                    zero_count += int(np.count_nonzero(valid & (arr == 0)))
                    positive_count += int(np.count_nonzero(arr > 0))

                    if np.any(valid):
                        vals = arr[valid]
                        local_max = int(vals.max())
                        if max_value is None or local_max > max_value:
                            max_value = local_max
                            rr0, cc0 = np.argwhere(arr == local_max)[0]
                            x, y = ds.transform * (col_off + int(cc0) + 0.5, row_off + int(rr0) + 0.5)
                            max_location = {"x": round(x, 3), "y": round(y, 3)}

                        rr, cc = np.nonzero(valid)
                        xs = ds.transform.c + (col_off + cc + 0.5) * ds.transform.a
                        ys = ds.transform.f + (row_off + rr + 0.5) * ds.transform.e
                        tile_x = np.floor(xs / METADATA_TILE_M).astype(np.int64)
                        tile_y = np.floor(ys / METADATA_TILE_M).astype(np.int64)
                        keys = tile_y * 1_000_000 + tile_x
                        unique_keys, first_indices = np.unique(keys, return_index=True)
                        for idx in first_indices.tolist():
                            tile_key = (int(tile_x[idx]), int(tile_y[idx]))
                            if tile_key not in samples_by_tile:
                                samples_by_tile[tile_key] = {
                                    "x": round(float(xs[idx]), 3),
                                    "y": round(float(ys[idx]), 3),
                                    "sample_value": int(arr[rr[idx], cc[idx]]),
                                }

                    over_rows, over_cols = np.where(arr > OUTLIER_LIMIT)
                    for rr, cc in zip(over_rows.tolist(), over_cols.tolist()):
                        x, y = ds.transform * (col_off + cc + 0.5, row_off + rr + 0.5)
                        outliers.append({"x": round(x, 3), "y": round(y, 3), "local_value": int(arr[rr, cc])})

            samples = evenly_sample(list(samples_by_tile.values()), MAX_SAMPLES_PER_RASTER)
            summary = {
                "archive": archive_path.name, "raster": member.filename,
                "crs": ds.crs.to_string(), "width": ds.width, "height": ds.height,
                "resolution_m": [float(ds.res[0]), float(ds.res[1])], "nodata": nodata,
                "total_pixels": total, "nodata_pixels": nodata_count,
                "zero_pixels": zero_count, "positive_pixels": positive_count,
                "exact_maximum": max_value, "maximum_cell_center": max_location,
                "occupied_2_5km_tiles_sampled_before_cap": len(samples_by_tile),
                "metadata_sample_points_used": len(samples),
                "outlier_cells_over_4265": len(outliers),
            }
            return summary, samples, outliers


def query_metadata_for_points(session, points):
    found = {}
    for start in range(0, len(points), QUERY_BATCH_SIZE):
        batch = points[start:start + QUERY_BATCH_SIZE]
        geometry = {"points": [[p["x"], p["y"]] for p in batch], "spatialReference": {"wkid": 3006}}
        payload = post_json(session, METADATA_QUERY_URL, {
            "where": "1=1",
            "geometry": json.dumps(geometry, separators=(",", ":")),
            "geometryType": "esriGeometryMultipoint", "inSR": "3006",
            "spatialRel": "esriSpatialRelIntersects", "outFields": METADATA_FIELDS,
            "returnGeometry": "false", "f": "json",
        }, "metadata sample query")
        for feature in payload.get("features", []):
            attrs = feature.get("attributes") or {}
            key = (str(attrs.get("Indexruta", "")), str(attrs.get("Omdrev", "")))
            if key != ("", ""):
                found[key] = attrs
    return list(found.values())


def query_metadata_at_point(session, x, y):
    geometry = {"x": x, "y": y, "spatialReference": {"wkid": 3006}}
    payload = post_json(session, METADATA_QUERY_URL, {
        "where": "1=1", "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryPoint", "inSR": "3006",
        "spatialRel": "esriSpatialRelIntersects", "outFields": METADATA_FIELDS,
        "returnGeometry": "false", "f": "json",
    }, f"metadata point query {x},{y}")
    return [feature.get("attributes", {}) for feature in payload.get("features", [])]


def identify_band(session, x, y, band_id):
    rendering_rule = {
        "rasterFunction": "Urval",
        "rasterFunctionArguments": {"BandIds": [band_id, 9], "IncludedRanges": [0, 65535, 0, 2]},
    }
    return post_json(session, IMAGE_IDENTIFY_URL, {
        "geometry": json.dumps({"x": x, "y": y, "spatialReference": {"wkid": 3006}}, separators=(",", ":")),
        "geometryType": "esriGeometryPoint",
        "mosaicRule": json.dumps({"where": "Omdrev=3"}, separators=(",", ":")),
        "renderingRule": json.dumps(rendering_rule, separators=(",", ":")),
        "pixelSize": "10,10", "returnGeometry": "false",
        "returnCatalogItems": "false", "returnPixelValues": "false", "f": "json",
    }, f"ImageServer identify band {band_id} at {x},{y}")


def parse_identified_value(payload):
    value = payload.get("value")
    try:
        return int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def unix_day_to_date(value):
    if value is None or value <= 0:
        return None
    return (datetime(1970, 1, 1) + timedelta(days=value)).date().isoformat()


def verify_outlier(session, item):
    x, y = item["x"], item["y"]
    volume_payload = identify_band(session, x, y, 0)
    day_payload = identify_band(session, x, y, 7)
    leaf_payload = identify_band(session, x, y, 8)
    volume = parse_identified_value(volume_payload)
    unix_day = parse_identified_value(day_payload)
    leaf = parse_identified_value(leaf_payload)
    return {
        **item, "server_volume_m3sk_per_ha": volume, "server_unix_day": unix_day,
        "server_scan_date": unix_day_to_date(unix_day), "server_leaf_status": leaf,
        "server_leaf_status_label": {1: "med löv", 2: "utan löv"}.get(leaf),
        "matches_local_value": volume == item["local_value"] if volume is not None else False,
        "metadata_service_records": query_metadata_at_point(session, x, y),
        "raw_identify_responses": {"volume": volume_payload, "unix_day": day_payload, "leaf_status": leaf_payload},
    }


def summarize_metadata(records):
    by_omdrev = Counter(str(r.get("Omdrev")) for r in records)
    by_date = Counter(str(r.get("Datum")) for r in records if r.get("Datum"))
    by_leaf = Counter(str(r.get("Lov_Avlov")) for r in records if r.get("Lov_Avlov") is not None)
    return {
        "unique_tile_omdrev_records": len(records),
        "omdrev_counts": dict(sorted(by_omdrev.items())),
        "scan_date_counts": dict(sorted(by_date.items())),
        "leaf_status_counts": dict(sorted(by_leaf.items())),
        "records": records,
    }


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Skogskoll-metadata-verification/1.0"})
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_raster_codes": CODES, "published_volume_max_m3sk_per_ha": OUTLIER_LIMIT,
        "metadata_service": METADATA_QUERY_URL, "image_service": IMAGE_IDENTIFY_URL,
        "method": {
            "raster_scan": "Full raster scan in 1024x512 windows; originals are read-only.",
            "metadata_sampling": "One valid pixel centre per global 2.5 km grid tile, evenly capped per raster.",
            "metadata_query": "ArcGIS MapServer point/multipoint spatial queries in EPSG:3006.",
            "outlier_check": "Every local cell above 4,265 is identified against the current ImageServer with Omdrev=3; volume, UnixDay and leaf-status bands are queried separately.",
            "zero_handling": "Zero is kept separate from NoData.",
            "limitations": [
                "Metadata sample is representative, not a proof that every valid pixel has been joined to a metadata feature.",
                "ImageServer verification reflects the currently published service and may differ from the April 2026 ZIP export.",
                "A server mismatch is reported for investigation and never silently substituted into the local raster.",
            ],
        },
        "rasters": [], "outlier_verification": [], "errors": [],
    }

    for code in CODES:
        archive_path = DATA_DIR / f"sks_Volym_omdrev3_{code}.zip"
        if not archive_path.exists():
            report["errors"].append({"raster_code": code, "error": f"Missing archive: {archive_path.name}"})
            continue
        try:
            summary, samples, outliers = inspect_archive(archive_path)
            metadata_records = query_metadata_for_points(session, samples)
            report["rasters"].append({**summary, "metadata_sample": summarize_metadata(metadata_records)})
            print(f"RASTER {code}: samples={len(samples)} metadata_tiles={len(metadata_records)} outliers={len(outliers)} max={summary['exact_maximum']}", flush=True)
            for outlier in outliers:
                try:
                    report["outlier_verification"].append({"raster_code": code, **verify_outlier(session, outlier)})
                except Exception as exc:
                    report["errors"].append({"raster_code": code, "outlier": outlier, "error": f"{type(exc).__name__}: {exc}"})
        except Exception as exc:
            report["errors"].append({"raster_code": code, "error": f"{type(exc).__name__}: {exc}"})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report: {OUT.relative_to(ROOT)}", flush=True)
    print(f"Raster reports: {len(report['rasters'])}; outlier checks: {len(report['outlier_verification'])}; errors: {len(report['errors'])}", flush=True)
    return 1 if report["errors"] or len(report["rasters"]) != len(CODES) else 0


if __name__ == "__main__":
    raise SystemExit(main())
