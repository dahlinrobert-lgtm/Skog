#!/usr/bin/env python3
"""Transform raw SCA z12 MVT tile-local geometries to EPSG:3857 GeoJSON.

This stage preserves every tile feature and its provenance. It deliberately
does not dissolve, deduplicate, or claim unique area counts.
"""
from __future__ import annotations
import hashlib, json, math
from collections import Counter
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import transform

INPUT_DIR = Path("input")
OUT_DIR = Path("output")
WORLD = 20037508.342789244
Z = 12


def tile_to_3857(geom, tx, ty, extent):
    span = (2 * WORLD) / (2 ** Z)
    def convert(x, y, z=None):
        xx = -WORLD + (tx + x / extent) * span
        yy = WORLD - (ty + y / extent) * span
        if z is None:
            return xx, yy
        return xx, yy, z
    return transform(convert, geom)


def main():
    sources = sorted(INPUT_DIR.glob("*.json"))
    if len(sources) != 1:
        raise SystemExit(f"Expected one raw batch JSON in input/, found {len(sources)}")
    raw_path = sources[0]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    records, manifest = [], []
    states = Counter()
    geometry_types = Counter()
    classes = Counter()
    motives = Counter()
    invalid = 0
    for tile in raw["tile_results"]:
        states[tile["state"]] += 1
        for layer in tile.get("layers", []):
            extent = int(layer.get("extent") or 4096)
            for index, feature in enumerate(layer.get("features", [])):
                geom_json = feature.get("geometry")
                if not geom_json:
                    invalid += 1
                    continue
                try:
                    local = shape(geom_json)
                    projected = tile_to_3857(local, int(tile["x"]), int(tile["y"]), extent)
                    if projected.is_empty or not projected.is_valid:
                        invalid += 1
                    props = feature.get("properties") or {}
                    source_key = f'{raw.get("batch")}:{tile["z"]}:{tile["x"]}:{tile["y"]}:{layer["name"]}:{index}'
                    geom_hash = hashlib.sha256(projected.wkb).hexdigest()
                    geometry_types[projected.geom_type] += 1
                    classes[props.get("SKOTSEL_KL_resolved", "<missing>")] += 1
                    motives[props.get("MOTIV_resolved", "<missing>")] += 1
                    records.append({
                        "type": "Feature",
                        "id": source_key,
                        "properties": {
                            **props,
                            "source_batch": raw.get("batch"),
                            "source_zoom": tile["z"],
                            "source_tile_x": tile["x"],
                            "source_tile_y": tile["y"],
                            "source_layer": layer["name"],
                            "source_feature_id": feature.get("id"),
                            "source_feature_index": index,
                            "source_tile_sha256": tile.get("sha256"),
                            "source_geometry_sha256_epsg3857": geom_hash,
                            "source_url": tile.get("url"),
                        },
                        "geometry": mapping(projected),
                    })
                    manifest.append({
                        "source_key": source_key,
                        "source_tile": [tile["z"], tile["x"], tile["y"]],
                        "source_layer": layer["name"],
                        "source_feature_id": feature.get("id"),
                        "geometry_type": projected.geom_type,
                        "geometry_sha256_epsg3857": geom_hash,
                        "is_valid": projected.is_valid,
                        "area_m2_web_mercator": projected.area,
                        "bounds_epsg3857": list(projected.bounds),
                    })
                except Exception as exc:
                    invalid += 1
                    manifest.append({"source_tile":[tile.get("z"),tile.get("x"),tile.get("y")],
                                     "source_feature_id":feature.get("id"),"error":str(exc)[:240]})
    hash_members = {}
    for item in manifest:
        h = item.get("geometry_sha256_epsg3857")
        if h:
            hash_members.setdefault(h, []).append(item)
    duplicate_groups = {h: members for h, members in hash_members.items() if len(members) > 1}
    duplicate_review = [
        {
            "geometry_sha256_epsg3857": h,
            "representation_count": len(members),
            "source_keys": [m.get("source_key") for m in members],
            "source_tiles": [m.get("source_tile") for m in members],
            "geometry_type": members[0].get("geometry_type"),
            "area_m2_web_mercator": members[0].get("area_m2_web_mercator"),
        }
        for h, members in duplicate_groups.items()
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fc = {"type":"FeatureCollection","name":"SCA voluntary set-asides z12 batch",
          "crs":{"type":"name","properties":{"name":"EPSG:3857"}},"features":records}
    (OUT_DIR/"sca-voluntary-batch-epsg3857.geojson").write_text(
        json.dumps(fc,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (OUT_DIR/"sca-voluntary-batch-manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary = {
        "input_file":str(raw_path),
        "batch":raw.get("batch"),
        "seed_count":len(raw.get("selected_z9_seeds",[])),
        "selected_z9_seeds":raw.get("selected_z9_seeds"),
        "source_tiles":len(raw.get("tile_results",[])),
        "tile_states":dict(states),
        "source_feature_records":len(records),
        "geometry_types":dict(geometry_types),
        "classification":dict(classes),
        "motives":dict(motives),
        "invalid_or_failed_geometries":invalid,
        "exact_geometry_duplicate_groups":len(duplicate_groups),
        "exact_duplicate_feature_records":sum(len(members)-1 for members in duplicate_groups.values()),
        "unique_exact_geometry_hashes":len(hash_members),
        "exact_duplicate_review":duplicate_review,
        "coordinate_system":"EPSG:3857, reconstructed from XYZ z12 tile coordinates and MVT extent",
        "limitations":[
            "Every source tile feature is retained; feature records are not unique SCA areas.",
            "MVT tile clipping/generalization can create partial geometries at tile edges.",
            "Exact geometry hashes only detect byte-identical projected geometries, not clipped fragments.",
            "No dissolve, inferred object identity, or unique area total is produced.",
            "Web Mercator areas are diagnostic only and should not be used as authoritative area measurements."
        ]
    }
    (OUT_DIR/"sca-voluntary-batch-summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
