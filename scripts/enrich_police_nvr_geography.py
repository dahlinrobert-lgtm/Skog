#!/usr/bin/env python3
"""Add NVDB road and intersection context to Police–NVR temporal candidates.

This is a review-only enrichment step. It never confirms or rejects a match.
The input temporal candidate CSV is preserved; a new output CSV is written.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import pyogrio
from pyproj import CRS, Transformer
from shapely.geometry import Point


ROAD_LAYER = "NVDB_DK_O_111_Vagnummer"
CROSSING_LAYER = "NVDB_DK_O_22_Korsning"
ROAD_FIELDS = [
    "ELEMENT_ID", "Europavag", "Huvudnummer", "Lankroll",
]
CROSSING_FIELDS = [
    "ELEMENT_ID", "Generaliseringstyp", "Ingar_i_trafikplats",
    "Namn", "Trafikplatsnamn",
]


def parse_road_number(value: str) -> tuple[str, int] | None:
    """Return (kind, number), where kind is 'european' or 'national'."""
    text = (value or "").casefold().replace("–", "-").strip()
    match = re.search(r"\be\s?(\d{1,3})\b", text)
    if match:
        return "european", int(match.group(1))
    match = re.search(
        r"\b(?:riksväg|länsväg|väg)\s*(\d{1,4})\b", text
    )
    if match:
        return "national", int(match.group(1))
    return None


def safe_float(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def first_value(row: dict[str, str], names: tuple[str, ...]):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return value
    return ""


def yes(value) -> bool:
    return str(value or "").strip().casefold() in {"ja", "yes", "true", "1"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_layer(path: Path, layer: str, columns: list[str]):
    frame = pyogrio.read_dataframe(path, layer=layer)
    missing = [field for field in columns if field not in frame.columns]
    if missing:
        raise ValueError(f"{layer}: required fields missing: {missing}")
    if frame.crs is None:
        raise ValueError(f"{layer}: CRS is missing")
    return frame


def clean_text(value) -> str:
    """Return an empty string for null-like values, including pandas NaN."""
    if value is None:
        return ""
    try:
        if value != value:  # NaN is unequal to itself
            return ""
    except (TypeError, ValueError):
        pass
    value = str(value).strip()
    return "" if value.casefold() in {"nan", "none", "<na>"} else value


def extract_place_reference(row: dict[str, str]) -> str:
    """Use the explicit place field, or a conservative 'between X and Y' cue."""
    explicit = clean_text(row.get("police_place_reference"))
    if explicit:
        return explicit
    text = clean_text(row.get("police_text"))
    match = re.search(r"\bmellan\s+(.+?)\s+och\s+([^.,;]+)", text, re.IGNORECASE)
    return match.group(2).strip() if match else ""


def place_search_term(reference: str) -> str:
    """Remove a leading compass qualifier; retain the actual named locality."""
    value = re.sub(r"\s+", " ", str(reference or "")).strip()
    value = re.sub(r"^(?:norra|södra|östra|västra)\s+", "", value, flags=re.IGNORECASE)
    return value


def find_named_place_matches(crossings, reference: str):
    """Return NVDB crossing rows matching a police place label.

    Searches both the crossing name and traffic-place name. Missing names are
    represented by an empty result, never interpreted as a geographic conflict.
    """
    term = place_search_term(reference)
    if not term:
        return term, crossings.iloc[0:0].copy()
    name_mask = crossings["Namn"].fillna("").str.contains(term, case=False, regex=False)
    traffic_mask = crossings["Trafikplatsnamn"].fillna("").str.contains(term, case=False, regex=False)
    return term, crossings.loc[name_mask | traffic_mask].copy()


def enrich_candidate(
    row: dict[str, str],
    roads,
    crossings,
    transformer: Transformer,
    road_radius: float,
    crossing_radius: float,
    traffic_place_radius: float,
    intersection_radius: float,
) -> dict[str, str]:
    out = dict(row)
    lat = safe_float(first_value(row, (
        "nvr_latitude_wgs84", "latitude_wgs84", "lat", "latitude"
    )))
    lon = safe_float(first_value(row, (
        "nvr_longitude_wgs84", "longitude_wgs84", "lon", "longitude"
    )))
    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        out.update({
            "geo_review_status": "missing_or_invalid_coordinates",
            "location_context": "unknown",
        })
        return out

    x, y = transformer.transform(lon, lat)
    point = Point(x, y)
    out["geo_point_x_sweref99tm"] = f"{x:.3f}"
    out["geo_point_y_sweref99tm"] = f"{y:.3f}"

    road_text = first_value(row, (
        "police_road_reference", "police_text", "police_place_reference"
    ))
    parsed_road = parse_road_number(road_text)
    out["geo_police_road_reference"] = road_text
    out["geo_parsed_road_number"] = (
        str(parsed_road[1]) if parsed_road else ""
    )

    # Named-place evidence is independent of road-number evidence.
    place_reference = extract_place_reference(row)
    place_term, named_places = find_named_place_matches(crossings, place_reference)
    out["geo_police_place_reference"] = place_reference
    out["geo_place_search_term"] = place_term
    if not named_places.empty:
        named_distances = named_places.geometry.distance(point)
        nearest_place_idx = named_distances.idxmin()
        nearest_place = named_places.loc[nearest_place_idx]
        out["geo_named_place_match_count"] = str(len(named_places))
        out["geo_named_place_distance_m"] = f"{float(named_distances.loc[nearest_place_idx]):.1f}"
        out["geo_named_place_element_id"] = str(nearest_place["ELEMENT_ID"])
        out["geo_named_place_type"] = clean_text(nearest_place["Generaliseringstyp"])
        out["geo_named_place_name"] = clean_text(nearest_place["Namn"])
        out["geo_named_traffic_place_name"] = clean_text(nearest_place["Trafikplatsnamn"])
        out["geo_named_place_match_status"] = "matched_nvdb_name"
    else:
        out["geo_named_place_match_count"] = "0"
        out["geo_named_place_distance_m"] = ""
        out["geo_named_place_element_id"] = ""
        out["geo_named_place_type"] = ""
        out["geo_named_place_name"] = ""
        out["geo_named_traffic_place_name"] = ""
        out["geo_named_place_match_status"] = (
            "no_place_reference" if not place_term else "no_named_nvdb_object"
        )

    road_distances = roads.geometry.distance(point)
    nearest_all_idx = road_distances.idxmin()
    nearest_all = roads.loc[nearest_all_idx]
    out["geo_nearest_road_element_id"] = str(nearest_all["ELEMENT_ID"])
    out["geo_nearest_road_number"] = (
        f"E{int(nearest_all['Huvudnummer'])}"
        if yes(nearest_all["Europavag"])
        else str(nearest_all["Huvudnummer"])
    )
    out["geo_nearest_road_role"] = str(nearest_all["Lankroll"])
    out["geo_nearest_road_distance_m"] = f"{float(road_distances.loc[nearest_all_idx]):.1f}"

    if parsed_road:
        kind, number = parsed_road
        if kind == "european":
            mask = roads["Europavag"].astype(str).str.casefold().eq("ja") & (
                roads["Huvudnummer"].astype(str).eq(str(number))
            )
        else:
            mask = roads["Europavag"].astype(str).str.casefold().eq("nej") & (
                roads["Huvudnummer"].astype(str).eq(str(number))
            )
        stated = roads.loc[mask]
        if not stated.empty:
            stated_distances = stated.geometry.distance(point)
            idx = stated_distances.idxmin()
            feature = stated.loc[idx]
            out["geo_stated_road_distance_m"] = f"{float(stated_distances.loc[idx]):.1f}"
            out["geo_stated_road_element_id"] = str(feature["ELEMENT_ID"])
            out["geo_stated_road_role"] = str(feature["Lankroll"])
            out["geo_stated_road_within_radius"] = (
                "yes" if float(stated_distances.loc[idx]) <= road_radius else "no"
            )
        else:
            out["geo_stated_road_distance_m"] = ""
            out["geo_stated_road_element_id"] = ""
            out["geo_stated_road_role"] = ""
            out["geo_stated_road_within_radius"] = "no_matching_nvdb_object"
    else:
        out["geo_stated_road_distance_m"] = ""
        out["geo_stated_road_element_id"] = ""
        out["geo_stated_road_role"] = ""
        out["geo_stated_road_within_radius"] = "unparsed_police_road"

    crossing_distances = crossings.geometry.distance(point)
    nearby = crossings.loc[crossing_distances <= crossing_radius].copy()
    nearby["geo_distance_m"] = crossing_distances.loc[nearby.index]
    nearby = nearby.sort_values("geo_distance_m")

    out["geo_crossing_count_300m"] = str(len(nearby))
    if nearby.empty:
        out.update({
            "geo_nearest_crossing_distance_m": "",
            "geo_nearest_crossing_type": "",
            "geo_nearest_crossing_element_id": "",
            "geo_traffic_place_names_300m": "",
            "geo_traffic_place_nearest_distance_m": "",
            "geo_simple_crossing_nearest_distance_m": "",
        })
        out["location_context"] = (
            "road_segment_or_unclassified"
            if parsed_road else "unknown"
        )
    else:
        first = nearby.iloc[0]
        out["geo_nearest_crossing_distance_m"] = f"{float(first['geo_distance_m']):.1f}"
        out["geo_nearest_crossing_type"] = str(first["Generaliseringstyp"] or "")
        out["geo_nearest_crossing_element_id"] = str(first["ELEMENT_ID"])

        traffic = nearby[
            nearby["Ingar_i_trafikplats"].map(yes)
            & nearby["Generaliseringstyp"].astype(str).str.casefold().isin(
                {"avfart/påfart", "avfart", "påfart"}
            )
        ]
        traffic_names = sorted({
            str(v).strip() for v in traffic["Trafikplatsnamn"].dropna()
            if str(v).strip()
        })
        out["geo_traffic_place_names_300m"] = ";".join(traffic_names)
        out["geo_traffic_place_nearest_distance_m"] = (
            f"{float(traffic['geo_distance_m'].min()):.1f}"
            if not traffic.empty else ""
        )

        simple = nearby[
            nearby["Generaliseringstyp"].astype(str).str.casefold().eq("enkel korsning")
        ]
        out["geo_simple_crossing_nearest_distance_m"] = (
            f"{float(simple['geo_distance_m'].min()):.1f}"
            if not simple.empty else ""
        )

        nearest_traffic = (
            float(traffic["geo_distance_m"].min()) if not traffic.empty else None
        )
        nearest_simple = (
            float(simple["geo_distance_m"].min()) if not simple.empty else None
        )
        if nearest_traffic is not None and nearest_traffic <= traffic_place_radius:
            out["location_context"] = "traffic_place_nearby_exact_road_not_assumed"
        elif nearest_simple is not None and nearest_simple <= intersection_radius:
            out["location_context"] = "simple_intersection_nearby"
        elif nearest_simple is not None or nearest_traffic is not None:
            out["location_context"] = "road_segment_near_crossing"
        else:
            out["location_context"] = "road_segment_or_unclassified"

    out["geo_review_status"] = "review_only_not_confirmed"
    out["geo_thresholds"] = json.dumps({
        "road_search_radius_m": road_radius,
        "crossing_search_radius_m": crossing_radius,
        "traffic_place_radius_m": traffic_place_radius,
        "simple_intersection_radius_m": intersection_radius,
    }, ensure_ascii=False, sort_keys=True)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True,
                        help="Temporal candidate CSV; it is never modified.")
    parser.add_argument("--nvdb-gpkg", type=Path, required=True,
                        help="Local NVDB GeoPackage in EPSG:3006.")
    parser.add_argument("--output", type=Path, required=True,
                        help="New geographically enriched review CSV.")
    parser.add_argument("--road-search-radius-m", type=float, default=1000)
    parser.add_argument("--crossing-search-radius-m", type=float, default=300)
    parser.add_argument("--traffic-place-radius-m", type=float, default=150)
    parser.add_argument("--simple-intersection-radius-m", type=float, default=100)
    args = parser.parse_args()

    if not args.nvdb_gpkg.is_file():
        parser.error(f"NVDB GeoPackage not found: {args.nvdb_gpkg}")
    for value in (
        args.road_search_radius_m, args.crossing_search_radius_m,
        args.traffic_place_radius_m, args.simple_intersection_radius_m,
    ):
        if value < 0:
            parser.error("All distance thresholds must be non-negative.")

    candidates = read_csv(args.candidates)
    if not candidates:
        parser.error("Candidate CSV contains no data rows.")

    roads = load_layer(args.nvdb_gpkg, ROAD_LAYER, ROAD_FIELDS)
    crossings = load_layer(args.nvdb_gpkg, CROSSING_LAYER, CROSSING_FIELDS)

    road_crs = CRS.from_user_input(roads.crs)
    crossing_crs = CRS.from_user_input(crossings.crs)
    if road_crs != crossing_crs:
        raise ValueError(f"Layer CRS mismatch: roads={road_crs}, crossings={crossing_crs}")
    if not road_crs.is_projected:
        raise ValueError(f"Expected projected NVDB CRS, got {road_crs}")

    transformer = Transformer.from_crs("EPSG:4326", road_crs, always_xy=True)
    enriched = [
        enrich_candidate(
            row, roads, crossings, transformer,
            args.road_search_radius_m, args.crossing_search_radius_m,
            args.traffic_place_radius_m, args.simple_intersection_radius_m,
        )
        for row in candidates
    ]

    fields = list(dict.fromkeys(
        key for row in enriched for key in row.keys()
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched)

    summary = {
        "status": "completed",
        "input_candidate_rows": len(candidates),
        "output_candidate_rows": len(enriched),
        "review_only": True,
        "named_place_match_counts": {},
        "location_context_counts": {},
        "output": str(args.output),
    }
    for row in enriched:
        place_status = row.get("geo_named_place_match_status", "unknown")
        summary["named_place_match_counts"][place_status] = (
            summary["named_place_match_counts"].get(place_status, 0) + 1
        )
        key = row.get("location_context", "unknown")
        summary["location_context_counts"][key] = (
            summary["location_context_counts"].get(key, 0) + 1
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
