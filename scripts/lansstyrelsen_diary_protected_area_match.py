#!/usr/bin/env python3
"""Match diary geographic clues to an official protected-area GeoJSON file.

The input GeoJSON must come from Naturvårdsverket's open Nature Conservation
Register. Only unique, high-quality name matches receive a coordinate/circle.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

OFFICIAL_SOURCE = "https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret/"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True).transform
TO_WGS84 = Transformer.from_crs("EPSG:3006", "EPSG:4326", always_xy=True).transform


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def split_candidate(value: str) -> list[str]:
    # A title can name two areas before a shared suffix, e.g. "Kynnefjäll och Kroppefjäll naturreservat".
    value = re.sub(r"(?i)\s+(?:naturreservatet|naturreservat|nationalparken|nationalpark|naturvårdsområde)$", "", value).strip()
    parts = re.split(r"(?i)\s+och\s+", value)
    return [part.strip() for part in parts if part.strip()]


def find_name_fields(features: list[dict[str, Any]]) -> list[str]:
    keys = set()
    for feature in features[:100]:
        keys.update((feature.get("properties") or {}).keys())
    candidates = [
        key for key in keys
        if any(token in normalize(str(key)).split() for token in ("namn", "name", "omradesnamn", "reservatsnamn"))
    ]
    return sorted(candidates, key=lambda item: (0 if normalize(item) in {"namn", "name"} else 1, item.casefold()))


def feature_name(feature: dict[str, Any], fields: list[str]) -> str:
    props = feature.get("properties") or {}
    for field in fields:
        value = props.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def radius_for_polygon(geom) -> tuple[float, float, float, dict]:
    """Return WGS84 point and radius (metres) enclosing the matched polygon."""
    projected = transform(TO_METERS, geom)
    point = projected.representative_point()
    # Distance to the farthest exterior coordinate creates a conservative enclosing circle.
    radius = max((point.distance(shape({"type": "Point", "coordinates": coord})) for coord in _all_coordinates(projected)), default=0.0)
    lon, lat = TO_WGS84(point.x, point.y)
    return lon, lat, radius, mapping(geom)


def _all_coordinates(geom):
    if geom.geom_type == "Polygon":
        for ring in [geom.exterior, *geom.interiors]:
            yield from ring.coords
    elif geom.geom_type == "MultiPolygon":
        for polygon in geom.geoms:
            yield from _all_coordinates(polygon)
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _all_coordinates(part)
    elif hasattr(geom, "coords"):
        yield from geom.coords


def _same_place_value(actual: str, clue: str) -> bool:
    actual_norm, clue_norm = normalize(actual), normalize(clue)
    return bool(actual_norm and clue_norm) and (
        actual_norm == clue_norm
        or f"{actual_norm}s" == clue_norm
        or f"{clue_norm}s" == actual_norm
    )


def _preferred_area_type(title: str) -> str | None:
    text = normalize(title)
    if "naturreservat" in text:
        return "naturreservat"
    if "nationalpark" in text:
        return "nationalpark"
    if "naturvardsomrade" in text:
        return "naturvardsomrade"
    return None


def _make_location(match: dict[str, Any], *, category_mismatch: bool) -> dict[str, Any]:
    geom = shape(match["geometry"])
    lon, lat, radius, geometry = radius_for_polygon(geom)
    return {
        "candidate_name": match["candidate_name"],
        "official_name": match["official_name"],
        "coordinates": {"longitude": round(lon, 7), "latitude": round(lat, 7)},
        "circle_radius_m": int(math.ceil(radius)),
        "geometry": geometry,
        "category_mismatch": category_mismatch,
        "match": {
            "official_name": match["official_name"],
            "candidate_name": match["candidate_name"],
            "candidate_source": match["candidate_source"],
            "source": match.get("source_url") or OFFICIAL_SOURCE,
            "source_dataset": match.get("source_dataset"),
            "official_properties": match["properties"],
            "match_method": match["match_method"],
            "category_mismatch": category_mismatch,
        },
        "circle_explanation": "Circle encloses the matched official area; it does not claim to be the planned burn footprint.",
    }


def match_candidate(candidate: dict[str, Any], official_features: list[dict[str, Any]], name_fields: list[str]) -> dict[str, Any]:
    geocoding = candidate.get("geocoding") or {}
    clues = geocoding.get("clues") or []
    title = str(candidate.get("title") or "")
    candidates = []
    seen_candidates: set[str] = set()
    for clue in clues:
        if clue.get("type") not in {"protected_area_name", "place_name_candidate"}:
            continue
        for value in split_candidate(str(clue.get("value") or "")):
            normalized = normalize(value)
            if len(normalized) < 3 or normalized in seen_candidates:
                continue
            seen_candidates.add(normalized)
            candidates.append({"name": value, "source": clue.get("source", "title"), "normalized": normalized})

    # Only explicit municipality mentions in the case title may disambiguate.
    # The diary's Kommun/Postort columns can identify a sender rather than the burn site.
    title_municipalities = [
        str(clue.get("value") or "").strip()
        for clue in clues
        if clue.get("type") == "municipality" and clue.get("source") == "title" and str(clue.get("value") or "").strip()
    ]
    preferred_type = _preferred_area_type(title)
    candidate_groups = []
    all_ambiguous = []
    unique_matches = []

    for candidate_name in candidates:
        found = []
        seen_features = set()
        for feature in official_features:
            official_name = feature_name(feature, name_fields)
            official_normalized = normalize(official_name) if official_name else ""
            if not official_normalized:
                continue
            if official_normalized == candidate_name["normalized"]:
                match_method = "normalized_exact_name_unique"
            elif f"{official_normalized}s" == candidate_name["normalized"]:
                match_method = "normalized_swedish_genitive_suffix"
            else:
                continue
            props = feature.get("properties") or {}
            feature_id = str(props.get("NVRID") or props.get("OBJECTID") or feature.get("id") or official_name)
            # Deduplicate a duplicate record for the same official identifier.
            dedupe_key = (str(props.get("SOURCE_DATASET") or ""), feature_id)
            if dedupe_key in seen_features:
                continue
            seen_features.add(dedupe_key)
            found.append({
                "candidate_name": candidate_name["name"],
                "candidate_source": candidate_name["source"],
                "candidate_normalized": candidate_name["normalized"],
                "official_name": official_name,
                "properties": props,
                "geometry": feature.get("geometry"),
                "match_method": match_method,
                "source_dataset": props.get("SOURCE_DATASET"),
                "source_url": props.get("SOURCE_URL"),
            })

        if not found:
            continue

        category_mismatch = False
        if preferred_type:
            type_matches = [
                item for item in found
                if normalize(str(item["properties"].get("SKYDDSTYP") or item["properties"].get("SKYDDSFORM") or "")) == preferred_type
            ]
            if type_matches:
                found = type_matches
            else:
                category_mismatch = True

        municipality_used = False
        if title_municipalities:
            municipality_matches = [
                item for item in found
                if any(
                    _same_place_value(
                        str(item["properties"].get("KOMMUN") or ""),
                        municipality,
                    )
                    or any(
                        _same_place_value(part.strip(), municipality)
                        for part in re.split(r"[,;/]", str(item["properties"].get("KOMMUN") or ""))
                        if part.strip()
                    )
                    for municipality in title_municipalities
                )
            ]
            if municipality_matches:
                found = municipality_matches
                municipality_used = True

        group = {
            "candidate_name": candidate_name["name"],
            "matches": found,
            "category_mismatch": category_mismatch,
            "municipality_used": municipality_used,
        }
        candidate_groups.append(group)
        if len(found) == 1 and found[0].get("geometry"):
            unique_matches.append((found[0], category_mismatch))
        elif len(found) > 1:
            all_ambiguous.extend(found)

    result = dict(candidate)
    result_geo = dict(geocoding)
    locations = [
        _make_location(match, category_mismatch=mismatch)
        for match, mismatch in unique_matches
    ]
    category_mismatch_any = any(mismatch for _, mismatch in unique_matches)
    ambiguous_summary = [
        {
            "candidate_name": item["candidate_name"],
            "official_name": item["official_name"],
            "properties": item["properties"],
            "source_dataset": item.get("source_dataset"),
            "source_url": item.get("source_url"),
            "reason": "Several official features share this candidate name after applying title type and municipality clues.",
        }
        for item in all_ambiguous
    ]

    if locations and not all_ambiguous:
        if len(locations) == 1:
            location = locations[0]
            result_geo.update({
                "status": "matched_official_protected_area",
                "confidence": "low" if category_mismatch_any else "medium",
                "confidence_reason": (
                    "Unique name match, but the official protection type differs from the type stated in the title."
                    if category_mismatch_any
                    else "Unique official area-name match after applying relevant title clues."
                ),
                "coordinates": location["coordinates"],
                "circle_radius_m": location["circle_radius_m"],
                "geometry": location["geometry"],
                "match": location["match"],
                "locations": locations,
            })
        else:
            result_geo.update({
                "status": "matched_multiple_official_protected_areas",
                "confidence": "low" if category_mismatch_any else "medium",
                "confidence_reason": (
                    "Several distinct area names matched official features. At least one official protection type differs from the title; review that location."
                    if category_mismatch_any
                    else "Several distinct named areas in the title each matched a unique official feature."
                ),
                "coordinates": None,
                "circle_radius_m": None,
                "geometry": None,
                "match": None,
                "locations": locations,
            })
    elif locations and all_ambiguous:
        result_geo.update({
            "status": "partially_matched_with_ambiguities",
            "confidence": "low",
            "confidence_reason": "Some named areas matched uniquely, but at least one candidate still has multiple official features.",
            "coordinates": None,
            "circle_radius_m": None,
            "geometry": None,
            "match": None,
            "locations": locations,
            "ambiguous_candidates": ambiguous_summary,
        })
    elif all_ambiguous:
        result_geo.update({
            "status": "ambiguous_official_matches",
            "confidence": "low",
            "confidence_reason": "Several official features match the same candidate name; title municipality/type clues were not enough to choose one.",
            "coordinates": None,
            "circle_radius_m": None,
            "geometry": None,
            "match": None,
            "candidate_matches": ambiguous_summary,
        })
    else:
        result_geo.update({
            "status": "no_official_protected_area_match",
            "confidence_reason": "No exact or Swedish-genitive name match found in the supplied official protected-area datasets; other geographic clues and case attachments may still help.",
            "coordinates": None,
            "circle_radius_m": None,
            "geometry": None,
            "match": None,
        })

    result["geocoding"] = result_geo
    result["geocoding"]["popup"] = {
        "title": result.get("title", ""),
        "diary_number": result.get("diary_number", ""),
        "confidence": result_geo.get("confidence"),
        "confidence_reason": result_geo.get("confidence_reason"),
        "clues": clues,
        "match": result_geo.get("match"),
        "locations": locations,
        "ambiguous_candidates": result_geo.get("ambiguous_candidates") or result_geo.get("candidate_matches") or [],
        "circle_explanation": "Each circle encloses the matched official area; it does not claim to be the planned burn footprint.",
    }
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=Path("data/lansstyrelsen-diary/geocoding-candidates.json"))
    parser.add_argument("--official-geojson", type=Path, required=True, help="GeoJSON exported from Naturvårdsverket's open protected-area register")
    parser.add_argument("--output", type=Path, default=Path("data/lansstyrelsen-diary/geocoding-matches.json"))
    args = parser.parse_args()
    candidates_doc = json.loads(args.candidates.read_text(encoding="utf-8"))
    official_doc = json.loads(args.official_geojson.read_text(encoding="utf-8"))
    features = official_doc.get("features") or []
    fields = find_name_fields(features)
    source_feature_count = official_doc.get("source_feature_count")
    if not features and not isinstance(source_feature_count, int):
        raise SystemExit("Official GeoJSON has no features and no successful source count; refusing to geocode.")
    if features and not fields:
        raise SystemExit("Official GeoJSON has no recognizable name field; refusing to geocode.")
    matched = [match_candidate(item, features, fields) for item in candidates_doc.get("features", [])]
    counts: dict[str, int] = {}
    for item in matched:
        status = item["geocoding"].get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    output = {
        "schema_version": 1,
        "source": OFFICIAL_SOURCE,
        "official_feature_count": source_feature_count if isinstance(source_feature_count, int) else len(features),
        "candidate_matching_feature_count": len(features),
        "name_fields_used": fields,
        "dataset_counts": official_doc.get("dataset_counts", {}),
        "record_count": len(matched),
        "summary": dict(sorted(counts.items())),
        "features": matched,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "record_count": len(matched), "official_feature_count": output["official_feature_count"], "candidate_matching_feature_count": len(features), "name_fields_used": fields, "summary": output["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
