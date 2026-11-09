#!/usr/bin/env python3
"""Build conservative cross-tile match candidates from one SCA event archive.

This is an analysis product only: it never mutates the append-only source events
and never assigns authoritative SCA object identifiers.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import transform

WORLD = 2 * math.pi * 6378137.0
ELIGIBLE = {"geometry_added", "geometry_changed_candidate",
            "geometry_missing_candidate", "geometry_removed_confirmed"}
CLASS_KEYS = ("SKOTSEL_KL_resolved", "SKOTSEL_KL", "klass", "class")
MOTIVE_KEYS = ("MOTIV_KL_resolved", "MOTIV_KL", "motiv", "motive")


def read_events(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def tile_parts(event: dict[str, Any]) -> tuple[int, int, int] | None:
    tile = event.get("source_tile") or event.get("tile")
    if isinstance(tile, dict):
        try:
            return int(tile["z"]), int(tile["x"]), int(tile["y"])
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(tile, str):
        try:
            z, x, y = (int(v) for v in tile.split("/"))
            return z, x, y
        except (TypeError, ValueError):
            return None
    return None


def event_geometry(event: dict[str, Any]):
    geom = event.get("new_geometry") or event.get("geometry")
    if not isinstance(geom, dict) or not geom.get("type"):
        return None
    try:
        return shape(geom)
    except Exception:
        return None


def to_web_mercator(geom, z: int, x: int, y: int, extent: int = 4096):
    span = WORLD / (2 ** z)
    origin_x = -WORLD / 2 + x * span
    origin_y = WORLD / 2 - y * span
    return transform(lambda px, py, zz=None: (
        origin_x + px * span / extent,
        origin_y - py * span / extent
    ), geom)


def property_value(properties: dict[str, Any], keys: tuple[str, ...]):
    for key in keys:
        if properties.get(key) not in (None, ""):
            return str(properties[key]).strip()
    return None


def prepare(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter]:
    observations, skipped = [], Counter()
    for event in events:
        if event.get("event_type") not in ELIGIBLE:
            skipped["event_type_not_geometry_observation"] += 1
            continue
        tile = tile_parts(event)
        geom = event_geometry(event)
        if tile is None or geom is None:
            skipped["missing_tile_or_geometry"] += 1
            continue
        if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
            skipped["empty_or_non_polygon_geometry"] += 1
            continue
        z, x, y = tile
        if z < 1 or z > 24:
            skipped["unsupported_zoom"] += 1
            continue
        extent = int(event.get("extent") or 4096)
        if extent <= 0:
            skipped["invalid_extent"] += 1
            continue
        try:
            projected = to_web_mercator(geom, z, x, y, extent)
            if not projected.is_valid:
                projected = projected.buffer(0)
            if projected.is_empty or projected.area <= 0:
                skipped["invalid_projected_geometry"] += 1
                continue
        except Exception:
            skipped["projection_error"] += 1
            continue
        props = event.get("properties") or event.get("new_properties") or {}
        observations.append({
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "tile": [z, x, y],
            "layer": event.get("layer"),
            "geometry": projected,
            "area": float(projected.area),
            "properties": props,
            "class_value": property_value(props, CLASS_KEYS),
            "motive_value": property_value(props, MOTIVE_KEYS),
        })
    return observations, skipped


def compare(observations: list[dict[str, Any]], threshold: float = 0.80):
    pairs = []
    by_tile: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    for i, obs in enumerate(observations):
        by_tile[tuple(obs["tile"])].append(i)

    seen = set()
    for i, a in enumerate(observations):
        z, x, y = a["tile"]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                for j in by_tile.get((z, x + dx, y + dy), []):
                    if j <= i or (i, j) in seen:
                        continue
                    seen.add((i, j))
                    b = observations[j]
                    if a["layer"] != b["layer"]:
                        continue
                    try:
                        intersection = float(a["geometry"].intersection(b["geometry"]).area)
                    except Exception:
                        continue
                    smaller = min(a["area"], b["area"])
                    ratio = intersection / smaller if smaller else 0.0
                    if ratio < threshold:
                        continue
                    class_equal = a["class_value"] == b["class_value"]
                    motive_equal = a["motive_value"] == b["motive_value"]
                    attributes_equal = a["properties"] == b["properties"]
                    if attributes_equal:
                        classification = "strong_geometry_and_attributes_candidate"
                    elif class_equal and motive_equal:
                        classification = "geometry_overlap_attributes_compatible"
                    else:
                        classification = "geometry_overlap_attribute_conflict_review"
                    pairs.append({
                        "event_id_a": a["event_id"], "event_id_b": b["event_id"],
                        "tile_a": a["tile"], "tile_b": b["tile"],
                        "event_type_a": a["event_type"], "event_type_b": b["event_type"],
                        "intersection_m2_3857": intersection,
                        "intersection_over_smaller": ratio,
                        "class_equal": class_equal, "motive_equal": motive_equal,
                        "all_properties_equal": attributes_equal,
                        "candidate_class": classification,
                        "identity_resolved": False,
                    })
    return pairs


def build_report(events: list[dict[str, Any]], source_name: str,
                 threshold: float = 0.80) -> dict[str, Any]:
    observations, skipped = prepare(events)
    pairs = compare(observations, threshold)
    counts = Counter(p["candidate_class"] for p in pairs)
    return {
        "schema_version": 1,
        "purpose": "Conservative cross-tile match candidates from a single SCA event archive",
        "source_archive": source_name,
        "matching_threshold_intersection_over_smaller": threshold,
        "input_event_count": len(events),
        "eligible_geometry_observations": len(observations),
        "skipped_event_counts": dict(skipped),
        "cross_tile_candidate_pairs": len(pairs),
        "candidate_pairs_by_class": dict(counts),
        "pairs": pairs,
        "limits": [
            "Candidate pairs are not confirmed SCA object identities.",
            "Only geometries present in this event archive are compared; this is not a full national object census.",
            "Only same-zoom adjacent tiles and the same source layer are compared.",
            "MVT tile buffers/generalization can create overlap; genuine source polygons can also overlap.",
            "EPSG:3857 intersection areas are diagnostic, not authoritative hectares.",
            "No source events are changed, merged, deleted or made notification-eligible.",
            "Missing or removed events are historical observations and do not imply current absence in neighboring tiles.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.80)
    args = parser.parse_args()
    if not 0 < args.threshold <= 1:
        parser.error("--threshold must be greater than 0 and at most 1")
    events = read_events(args.events)
    report = build_report(events, args.events.name, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "input_event_count", "eligible_geometry_observations",
        "cross_tile_candidate_pairs", "candidate_pairs_by_class",
        "skipped_event_counts")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
