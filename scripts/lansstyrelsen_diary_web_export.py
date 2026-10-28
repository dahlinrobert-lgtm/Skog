#!/usr/bin/env python3
"""Export geocoding matches to a compact GeoJSON feature collection for the public map."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _map_feature(record: dict[str, Any], location: dict[str, Any], index: int) -> dict[str, Any] | None:
    coordinates = location.get("coordinates")
    if not isinstance(coordinates, dict):
        return None
    try:
        lon, lat = float(coordinates["longitude"]), float(coordinates["latitude"])
        radius = float(location.get("circle_radius_m") or 0)
    except (KeyError, TypeError, ValueError):
        return None
    if not (-180 <= lon <= 180 and -90 <= lat <= 90) or radius <= 0:
        return None

    geo = record.get("geocoding") or {}
    match = location.get("match") or geo.get("match") or {}
    mismatch = bool(location.get("category_mismatch") or match.get("category_mismatch"))
    confidence = "low" if mismatch else str(geo.get("confidence") or "medium")
    properties = {
        "feature_id": f"{record.get('record_key') or record.get('diary_number') or 'case'}:{index}",
        "diary_number": record.get("diary_number") or "",
        "diary": record.get("diary") or "",
        "title": record.get("title") or "",
        "candidate_name": location.get("candidate_name") or match.get("candidate_name") or "",
        "official_name": location.get("official_name") or match.get("official_name") or "",
        "confidence": confidence,
        "confidence_reason": (
            "Official protection type differs from the title; inspect the source before relying on this location."
            if mismatch else geo.get("confidence_reason") or ""
        ),
        "source_url": match.get("source") or location.get("source_url") or "",
        "source_dataset": match.get("source_dataset") or location.get("source_dataset") or "",
        "match_method": match.get("match_method") or "",
        "circle_radius_m": int(round(radius)),
        "circle_explanation": location.get("circle_explanation") or
            "Circle encloses the matched official area; it does not claim to be the planned burn footprint.",
        "category_mismatch": mismatch,
        "clues": geo.get("clues") or [],
    }
    return {
        "type": "Feature",
        "id": properties["feature_id"],
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def build_map_data(report: dict[str, Any]) -> dict[str, Any]:
    output_features = []
    source_records = report.get("features") or []
    for record in source_records:
        geo = record.get("geocoding") or {}
        locations = geo.get("locations")
        if isinstance(locations, list) and locations:
            for index, location in enumerate(locations, start=1):
                feature = _map_feature(record, location, index)
                if feature:
                    output_features.append(feature)
            continue
        # Backward compatibility with reports containing a single coordinates/match object.
        if geo.get("coordinates"):
            location = {
                "coordinates": geo.get("coordinates"),
                "circle_radius_m": geo.get("circle_radius_m"),
                "candidate_name": (geo.get("match") or {}).get("candidate_name"),
                "official_name": (geo.get("match") or {}).get("official_name"),
                "match": geo.get("match"),
                "circle_explanation": (geo.get("popup") or {}).get("circle_explanation"),
                "category_mismatch": (geo.get("match") or {}).get("category_mismatch"),
            }
            feature = _map_feature(record, location, 1)
            if feature:
                output_features.append(feature)
    return {
        "type": "FeatureCollection",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report_record_count": len(source_records),
        "map_location_count": len(output_features),
        "features": output_features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/lansstyrelsen-diary/geocoding-matches.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/lansstyrelsen-geocoding.json"))
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    data = build_map_data(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({
        "output": str(args.output),
        "source_report_record_count": data["source_report_record_count"],
        "map_location_count": data["map_location_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
