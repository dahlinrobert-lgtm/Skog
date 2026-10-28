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


def match_candidate(candidate: dict[str, Any], official_features: list[dict[str, Any]], name_fields: list[str]) -> dict[str, Any]:
    geocoding = candidate.get("geocoding") or {}
    clues = geocoding.get("clues") or []
    candidates = []
    for clue in clues:
        if clue.get("type") not in {"protected_area_name", "place_name_candidate"}:
            continue
        for value in split_candidate(str(clue.get("value") or "")):
            normalized = normalize(value)
            if len(normalized) < 3:
                continue
            candidates.append({"name": value, "source": clue.get("source", "title"), "normalized": normalized})

    matches = []
    seen = set()
    for candidate_name in candidates:
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
            key = (candidate_name["normalized"], str((feature.get("properties") or {}).get("NVRID") or (feature.get("properties") or {}).get("OBJECTID") or official_name))
            if key in seen:
                continue
            seen.add(key)
            matches.append({
                "candidate_name": candidate_name["name"],
                "candidate_source": candidate_name["source"],
                "official_name": official_name,
                "properties": feature.get("properties") or {},
                "geometry": feature.get("geometry"),
                "match_method": match_method,
                "source_dataset": (feature.get("properties") or {}).get("SOURCE_DATASET"),
                "source_url": (feature.get("properties") or {}).get("SOURCE_URL"),
            })

    result = dict(candidate)
    result_geo = dict(geocoding)
    if len(matches) == 1 and matches[0].get("geometry"):
        match = matches[0]
        geom = shape(match["geometry"])
        lon, lat, radius, geometry = radius_for_polygon(geom)
        result_geo.update({
            "status": "matched_official_protected_area",
            "confidence": "medium",
            "confidence_reason": "Unique exact name match to an official protected-area feature. The circle encloses the whole matched area and is not a burn perimeter.",
            "coordinates": {"longitude": round(lon, 7), "latitude": round(lat, 7)},
            "circle_radius_m": int(math.ceil(radius)),
            "geometry": geometry,
            "match": {
                "official_name": match["official_name"],
                "candidate_name": match["candidate_name"],
                "candidate_source": match["candidate_source"],
                "source": match.get("source_url") or OFFICIAL_SOURCE,
                "source_dataset": match.get("source_dataset"),
                "official_properties": match["properties"],
                "match_method": match["match_method"],
            },
        })
    elif matches:
        result_geo.update({
            "status": "ambiguous_official_matches",
            "confidence": "low",
            "confidence_reason": "More than one official feature matches the extracted name; no coordinate assigned.",
            "coordinates": None, "circle_radius_m": None, "geometry": None,
            "candidate_matches": [{k: m[k] for k in ("candidate_name", "official_name", "candidate_source", "properties")} for m in matches],
        })
    else:
        result_geo.update({
            "status": "no_official_protected_area_match",
            "confidence_reason": "No exact match found in the supplied official protected-area dataset; municipality/place-name matching remains a separate step.",
            "coordinates": None, "circle_radius_m": None, "geometry": None,
        })
    result["geocoding"] = result_geo
    result["geocoding"]["popup"] = {
        "title": result.get("title", ""),
        "diary_number": result.get("diary_number", ""),
        "confidence": result_geo.get("confidence"),
        "confidence_reason": result_geo.get("confidence_reason"),
        "clues": clues,
        "match": result_geo.get("match"),
        "circle_explanation": "Circle encloses the matched protected area; it does not claim to be the planned burn footprint.",
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
