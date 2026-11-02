#!/usr/bin/env python3
"""Collect 2.5 km laser-scan metadata intersecting the locally stored Omdrev 3 rasters.

The raster ZIP files are downloaded from the user's OneDrive by the preceding
workflow step. Their actual GeoTIFF bounds drive the metadata queries; no county
or manually estimated bounding boxes are hard-coded here.
"""
from __future__ import annotations

import csv
import json
import re
import tempfile
import time
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import rasterio
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
OUT = ROOT / "raster-three-omdrev" / "flight_metadata"
LAYER = (
    "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/"
    "Geodataportal/GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0"
)
DEFAULT_RASTER_CODES = ("12", "21", "23")
BATCH_SIZE = 500


def get_json(session: requests.Session, url: str, params: dict) -> dict:
    response = session.get(url, params=params, timeout=(30, 120))
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload


def post_json(session: requests.Session, url: str, data: dict) -> dict:
    """POST long ArcGIS query parameters to avoid oversized request URLs."""
    response = session.post(url, data=data, timeout=(30, 120))
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload


def inspect_raster_archive(archive_path: Path) -> dict:
    """Read the single TIFF in a ZIP and return its real extent and grid metadata."""
    if not archive_path.is_file():
        raise FileNotFoundError(f"Raster archive is missing: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="skog-flight-raster-") as temp_dir:
        with zipfile.ZipFile(archive_path) as archive:
            members = [
                item for item in archive.infolist()
                if not item.is_dir()
                and Path(item.filename).suffix.lower() in {".tif", ".tiff"}
            ]
            if len(members) != 1:
                raise ValueError(
                    f"{archive_path.name}: expected exactly one TIFF, found {len(members)}"
                )
            member = members[0]
            local_tif = Path(temp_dir) / Path(member.filename).name
            with archive.open(member) as source, local_tif.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)

        with rasterio.open(local_tif) as dataset:
            if dataset.crs is None or dataset.crs.to_epsg() != 3006:
                raise ValueError(
                    f"{archive_path.name}: expected EPSG:3006, got {dataset.crs}"
                )
            if dataset.count < 1:
                raise ValueError(f"{archive_path.name}: TIFF contains no raster bands")
            bounds = dataset.bounds
            return {
                "raster_code": archive_path.stem.rsplit("_", 1)[-1],
                "archive": archive_path.name,
                "tiff_member": member.filename,
                "crs": dataset.crs.to_string(),
                "width": dataset.width,
                "height": dataset.height,
                "resolution_x_m": float(dataset.res[0]),
                "resolution_y_m": float(dataset.res[1]),
                "bounds_epsg3006": {
                    "xmin": float(bounds.left),
                    "ymin": float(bounds.bottom),
                    "xmax": float(bounds.right),
                    "ymax": float(bounds.top),
                },
                "nodata": dataset.nodata,
            }


def choose_field(fields: list[str], candidates: tuple[str, ...]) -> str | None:
    lookup = {name.lower(): name for name in fields}
    return next((lookup[name.lower()] for name in candidates if name.lower() in lookup), None)


def normalize_scan_date(value) -> str | None:
    """Normalize ArcGIS Date milliseconds, YYYYMMDD values, or ISO date strings."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        numeric = int(value)
        if numeric >= 100_000_000_000:
            return datetime.fromtimestamp(numeric / 1000, tz=timezone.utc).date().isoformat()
        text = str(numeric)
    else:
        text = str(value).strip()

    if re.fullmatch(r"\d{8}", text):
        return datetime.strptime(text, "%Y%m%d").date().isoformat()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text


def main() -> None:
    import os

    raster_codes = tuple(
        code.strip()
        for code in os.environ.get("RASTER_CODES", ",".join(DEFAULT_RASTER_CODES)).split(",")
        if code.strip()
    )
    if not raster_codes:
        raise RuntimeError("RASTER_CODES is empty")

    OUT.mkdir(parents=True, exist_ok=True)
    raster_extents = [
        inspect_raster_archive(DATA_DIR / f"sks_Volym_omdrev3_{code}.zip")
        for code in raster_codes
    ]

    session = requests.Session()
    session.headers["User-Agent"] = "Skogskoll-flight-metadata/2.0"
    layer = get_json(session, LAYER, {"f": "json"})
    definitions = layer.get("fields", [])
    source_fields = [field["name"] for field in definitions]
    if not source_fields:
        raise RuntimeError("ArcGIS metadata layer returned no fields")

    field_map = {
        "index_tile": choose_field(source_fields, ("Indexruta",)),
        "scan_file": choose_field(source_fields, ("Las_Namn", "LasNamn")),
        "scan_date_raw": choose_field(source_fields, ("Datum", "datum")),
        "survey_round": choose_field(source_fields, ("Omdrev",)),
        "leaf_status": choose_field(source_fields, ("Lov_Avlov",)),
    }
    if not field_map["index_tile"] or not field_map["scan_date_raw"]:
        raise RuntimeError(
            f"Required metadata fields missing. Resolved={field_map}; available={source_fields}"
        )

    oid_field = layer.get("objectIdField") or next(
        (field["name"] for field in definitions if field.get("type") == "esriFieldTypeOID"),
        None,
    )
    if not oid_field:
        raise RuntimeError("Could not identify ArcGIS object ID field")

    features: dict[int, dict] = {}
    raster_object_ids: dict[str, set[int]] = {}

    for raster in raster_extents:
        bounds = raster["bounds_epsg3006"]
        geometry = {
            "xmin": bounds["xmin"], "ymin": bounds["ymin"],
            "xmax": bounds["xmax"], "ymax": bounds["ymax"],
            "spatialReference": {"wkid": 3006},
        }
        ids_payload = get_json(session, LAYER + "/query", {
            "f": "json",
            "where": "1=1",
            "returnIdsOnly": "true",
            "geometry": json.dumps(geometry, separators=(",", ":")),
            "geometryType": "esriGeometryEnvelope",
            "inSR": 3006,
            "spatialRel": "esriSpatialRelIntersects",
        })
        object_ids = ids_payload.get("objectIds") or []
        raster_code = raster["raster_code"]
        raster_object_ids[raster_code] = set(object_ids)

        for offset in range(0, len(object_ids), BATCH_SIZE):
            batch = object_ids[offset:offset + BATCH_SIZE]
            result = post_json(session, LAYER + "/query", {
                "f": "json",
                "objectIds": ",".join(map(str, batch)),
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": 3006,
            })
            for feature in result.get("features", []):
                oid = feature.get("attributes", {}).get(oid_field)
                if oid is not None:
                    features[oid] = feature
            time.sleep(0.1)

        print(
            f"Raster {raster_code}: {len(object_ids)} intersecting 2.5 km metadata records",
            flush=True,
        )

    rows = []
    for oid, feature in features.items():
        attributes = feature.get("attributes", {})
        row = {"object_id": oid}
        for canonical_name, source_name in field_map.items():
            row[canonical_name] = attributes.get(source_name) if source_name else None
        row["scan_date"] = normalize_scan_date(row.get("scan_date_raw"))
        row["raster_codes"] = ";".join(
            code for code, ids in raster_object_ids.items() if oid in ids
        )
        laz_name = str(row.get("scan_file") or "")
        block_match = re.search(
            r"(?<![A-Za-z0-9])\d{2}[A-Z]\d{3}(?![A-Za-z0-9])", laz_name
        )
        row["scan_block_candidate"] = block_match.group(0) if block_match else None
        for name in source_fields:
            row["source_" + name] = attributes.get(name)
        rows.append(row)

    canonical_columns = [
        "object_id", "raster_codes", "index_tile", "survey_round", "scan_date",
        "scan_date_raw", "scan_file", "scan_block_candidate", "leaf_status",
    ]
    columns = canonical_columns + ["source_" + name for name in source_fields]
    with (OUT / "laser_scan_index_tiles.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # Preserve the original ArcGIS geometry representation without mislabelling it
    # as GeoJSON. This retains exact source rings and EPSG:3006 coordinates.
    esri_json = {
        "geometryType": layer.get("geometryType"),
        "spatialReference": {"wkid": 3006},
        "features": [
            {
                "attributes": feature.get("attributes", {}),
                "geometry": feature.get("geometry"),
            }
            for feature in features.values()
        ],
    }
    (OUT / "laser_scan_index_tiles_esrijson.json").write_text(
        json.dumps(esri_json, ensure_ascii=False), encoding="utf-8"
    )

    round_counts = Counter(str(row.get("survey_round")) for row in rows)
    date_counts = Counter(str(row.get("scan_date")) for row in rows if row.get("scan_date"))
    summary = {
        "service": LAYER,
        "service_name": layer.get("name"),
        "spatial_reference": layer.get("extent", {}).get("spatialReference"),
        "object_id_field": oid_field,
        "source_fields": source_fields,
        "canonical_field_mapping": field_map,
        "feature_count": len(rows),
        "raster_codes": list(raster_codes),
        "raster_extents": raster_extents,
        "metadata_records_by_raster": {
            code: len(ids) for code, ids in raster_object_ids.items()
        },
        "records_by_survey_round": dict(sorted(round_counts.items())),
        "records_by_scan_date": dict(sorted(date_counts.items())),
        "date_semantics": (
            "The service can contain multiple survey-round records for a tile. "
            "The product metadata may report the latest scan date where a tile "
            "was scanned on multiple dates; this is not guaranteed to be a complete "
            "flight-by-flight history."
        ),
        "leaf_status_semantics": {"1": "with leaves", "2": "without leaves"},
        "limitations": [
            "A metadata tile is 2.5 km by 2.5 km and identifies a scan area, not an exact aircraft track.",
            "Intersection with a raster's outer extent does not prove overlap with valid raster pixels.",
            "A tile metadata date does not by itself prove which scan date was used for every raster pixel.",
            "The archive contains Omdrev 3 volume rasters; metadata for Omdrev 1 and 2 is retained where the service returns it for the same footprints.",
        ],
    }
    (OUT / "laser_scan_metadata_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
