#!/usr/bin/env python3
"""Review-only nearest-road matching against one or more NVDB GeoPackages.

The input CSV is never modified. Each event is queried with a projected
bounding box, so nationwide runs do not need to load every road feature into
memory. A missing candidate is not evidence that no road exists: dataset
coverage must be known independently.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import pyogrio
from pyproj import CRS, Transformer
from shapely.geometry import Point


ROAD_LAYER = "NVDB_DK_O_111_Vagnummer"
ROAD_FIELDS = ["ELEMENT_ID", "Europavag", "Huvudnummer", "Lankroll"]


def clean(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"", "none", "nan", "<na>"} else text


def safe_float(value):
    try:
        result = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def road_number(row) -> str:
    number = clean(row.get("Huvudnummer"))
    european = clean(row.get("Europavag")).casefold() in {"ja", "yes", "true", "1"}
    return f"E{number}" if european and number else number


def prepare_sources(paths: list[Path]):
    sources = []
    errors = []
    for path in paths:
        try:
            info = pyogrio.read_info(path, layer=ROAD_LAYER)
            crs_value = info.get("crs")
            if not crs_value:
                raise ValueError("CRS saknas")
            crs = CRS.from_user_input(crs_value)
            if not crs.is_projected:
                raise ValueError(f"Förväntade projicerat CRS, fick {crs.to_string()}")
            if not crs.axis_info or any(
                not math.isclose(axis.unit_conversion_factor, 1.0, rel_tol=0, abs_tol=1e-9)
                for axis in crs.axis_info[:2]
            ):
                raise ValueError(
                    f"Avstånd i meter kräver meterbaserat CRS, fick {crs.to_string()}"
                )
            missing = [field for field in ROAD_FIELDS if field not in info.get("fields", [])]
            if missing:
                raise ValueError(f"Fält saknas: {missing}")
            sources.append({
                "path": path,
                "crs": crs,
                "transformer": Transformer.from_crs("EPSG:4326", crs, always_xy=True),
            })
        except Exception as exc:
            errors.append({"source": path.name, "error": str(exc)})
    return sources, errors


def search_event(lat, lon, sources, radius_m: float, max_candidates: int):
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return {
            "geo_nvdb_search_status": "missing_or_invalid_coordinates",
            "geo_nvdb_candidate_count": "0",
            "geo_nvdb_candidates": "[]",
            "geo_nvdb_sources_queried": "0",
            "geo_nvdb_sources_failed": "0",
        }

    candidates = []
    source_errors = []
    queried = 0

    for source in sources:
        path = source["path"]
        try:
            x, y = source["transformer"].transform(lon, lat)
            bounds = (x - radius_m, y - radius_m, x + radius_m, y + radius_m)
            frame = pyogrio.read_dataframe(
                path,
                layer=ROAD_LAYER,
                columns=ROAD_FIELDS,
                bbox=bounds,
            )
            queried += 1
            if frame.empty:
                continue

            for _, feature in frame.iterrows():
                geometry = feature.geometry
                if geometry is None or geometry.is_empty:
                    continue
                distance = float(geometry.distance(Point(x, y)))
                if distance > radius_m:
                    continue
                candidates.append({
                    "source_file": path.name,
                    "element_id": clean(feature.get("ELEMENT_ID")),
                    "road_number": road_number(feature),
                    "road_role": clean(feature.get("Lankroll")),
                    "distance_m": round(distance, 2),
                })
        except Exception as exc:
            source_errors.append({"source": path.name, "error": str(exc)})

    # County extracts can overlap at boundaries. Keep the closest copy of an
    # identical source feature, but preserve distinct road identities.
    deduplicated = {}
    for item in candidates:
        key = (item["element_id"], item["road_number"], item["road_role"])
        if key not in deduplicated or item["distance_m"] < deduplicated[key]["distance_m"]:
            deduplicated[key] = item

    ordered = sorted(
        deduplicated.values(),
        key=lambda item: (
            item["distance_m"], item["road_number"],
            item["element_id"], item["source_file"],
        ),
    )
    selected = ordered[:max_candidates]

    if source_errors:
        status = "partial_source_read"
    elif selected:
        status = "completed_with_candidates"
    else:
        status = "completed_no_candidate_in_search_window"

    nearest = selected[0] if selected else {}
    return {
        "geo_nvdb_search_status": status,
        "geo_nvdb_candidate_count": str(len(ordered)),
        "geo_nvdb_nearest_road_number": nearest.get("road_number", ""),
        "geo_nvdb_nearest_road_element_id": nearest.get("element_id", ""),
        "geo_nvdb_nearest_road_role": nearest.get("road_role", ""),
        "geo_nvdb_nearest_road_distance_m": (
            str(nearest["distance_m"]) if nearest else ""
        ),
        "geo_nvdb_candidates": json.dumps(selected, ensure_ascii=False, sort_keys=True),
        "geo_nvdb_sources_queried": str(queried),
        "geo_nvdb_sources_failed": str(len(source_errors)),
        "geo_nvdb_source_errors": json.dumps(source_errors, ensure_ascii=False),
        "geo_nvdb_search_radius_m": str(radius_m),
        "geo_review_status": "review_only_not_confirmed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True,
                        help="CSV with WGS84 event coordinates; never modified.")
    parser.add_argument("--nvdb-gpkg", type=Path, action="append", required=True,
                        help="NVDB GeoPackage; repeat for multiple county extracts.")
    parser.add_argument("--output", type=Path, required=True,
                        help="New CSV containing review-only road evidence.")
    parser.add_argument("--latitude-field", default="nvr_latitude_wgs84")
    parser.add_argument("--longitude-field", default="nvr_longitude_wgs84")
    parser.add_argument("--search-radius-m", type=float, default=1000)
    parser.add_argument("--max-candidates", type=int, default=5)
    args = parser.parse_args()

    if args.search_radius_m <= 0 or args.max_candidates < 1:
        parser.error("Sökradie måste vara positiv och max-kandidater minst 1.")
    missing = [path for path in args.nvdb_gpkg if not path.is_file()]
    if missing:
        parser.error(f"NVDB-filer saknas: {missing}")

    with args.candidates.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            parser.error("Indata saknar CSV-rubrik.")
        required = [args.latitude_field, args.longitude_field]
        absent = [field for field in required if field not in reader.fieldnames]
        if absent:
            parser.error(f"Koordinatfält saknas: {absent}")
        rows = list(reader)

    sources, source_init_errors = prepare_sources(args.nvdb_gpkg)
    if not sources:
        parser.error(f"Inga NVDB-källor kunde läsas: {source_init_errors}")

    enriched = []
    for row in rows:
        result = search_event(
            safe_float(row.get(args.latitude_field)),
            safe_float(row.get(args.longitude_field)),
            sources, args.search_radius_m, args.max_candidates,
        )
        if source_init_errors:
            result["geo_nvdb_search_status"] = "partial_source_read"
            result["geo_nvdb_sources_failed"] = str(
                int(result.get("geo_nvdb_sources_failed", "0")) + len(source_init_errors)
            )
            result["geo_nvdb_source_errors"] = json.dumps(
                source_init_errors + json.loads(result.get("geo_nvdb_source_errors", "[]")),
                ensure_ascii=False,
            )
        enriched.append({**row, **result})

    fields = list(dict.fromkeys(key for row in enriched for key in row))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enriched)

    counts = {}
    for row in enriched:
        status = row["geo_nvdb_search_status"]
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({
        "status": "completed" if not source_init_errors else "partial",
        "input_rows": len(rows),
        "output_rows": len(enriched),
        "source_files": len(args.nvdb_gpkg),
        "source_initialization_errors": source_init_errors,
        "row_status_counts": counts,
        "review_only": True,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
