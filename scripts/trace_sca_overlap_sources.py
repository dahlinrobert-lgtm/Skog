#!/usr/bin/env python3
"""Trace prioritized SCA overlap relations to their decoded z12 MVT source features.

This is a provenance/sample export, not an authoritative object-identity test.
The geometries are decoded MVT tile geometries reconstructed into EPSG:3857.
"""
from __future__ import annotations
import csv, hashlib, json, os
from collections import Counter
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import transform

INPUT = Path("input")
OUT = Path("output")
WORLD = 20037508.342789244
Z = 12
DEFAULT_LIMIT = 60


def tile_to_3857(geom, tx, ty, extent):
    span = (2 * WORLD) / (2 ** Z)
    def convert(x, y, z=None):
        xx = -WORLD + (tx + x / extent) * span
        yy = WORLD - (ty + 1.0 - y / extent) * span
        return (xx, yy) if z is None else (xx, yy, z)
    return transform(convert, geom)


def parse_source_key(key):
    parts = str(key).split(":")
    if len(parts) < 6:
        raise ValueError(f"Unparseable source key: {key}")
    batch, zoom, tx, ty = map(int, parts[:4])
    layer = ":".join(parts[4:-1])
    index = int(parts[-1])
    return batch, zoom, tx, ty, layer, index


def load_raw_index():
    index = {}
    paths = sorted(INPUT.rglob("sca-national-voluntary-tile-expansion-z12.json"))
    if not paths:
        raise SystemExit("No raw z12 tile expansion JSON files found under input/")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        batch = int(data["batch"])
        for tile in data.get("tile_results", []):
            tile_id = (batch, int(tile["z"]), int(tile["x"]), int(tile["y"]))
            index[tile_id] = (path.name, tile)
    return index, paths


def load_projected_features():
    features = {}
    paths = sorted(INPUT.rglob("sca-voluntary-batch-epsg3857.geojson"))
    if not paths:
        raise SystemExit("No projected geometry batch GeoJSON files found under input/")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for feature in data.get("features", []):
            key = str(feature.get("id", ""))
            if key:
                features[key] = feature
    return features, paths


def load_priorities():
    paths = sorted(INPUT.rglob("sca-national-overlap-priority-review.csv"))
    if len(paths) != 1:
        raise SystemExit(f"Expected exactly one priority CSV, found {len(paths)}")
    with paths[0].open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def choose_sample(rows, limit):
    """Deterministic stratified sample; all candidates remain review-only."""
    selected, seen = [], set()
    ordered = sorted(rows, key=lambda r: (
        int(r.get("review_priority", 9)),
        r.get("review_bucket", ""),
        r.get("source_key_a", ""), r.get("source_key_b", "")))
    strata = [
        (lambda r: r.get("review_bucket") == "partial_same_class_fragment_signal", min(20, limit // 3)),
        (lambda r: r.get("review_bucket") == "partial_cross_class", min(20, limit // 3)),
        (lambda r: r.get("motive_relation") == "different", min(15, limit // 4)),
        (lambda r: r.get("review_priority") == "1", limit),
    ]
    for predicate, quota in strata:
        count = 0
        for row in ordered:
            pair = (row["source_key_a"], row["source_key_b"])
            if pair in seen or not predicate(row):
                continue
            selected.append(row)
            seen.add(pair)
            count += 1
            if count >= quota or len(selected) >= limit:
                break
        if len(selected) >= limit:
            break
    for row in ordered:
        pair = (row["source_key_a"], row["source_key_b"])
        if pair not in seen:
            selected.append(row)
            seen.add(pair)
        if len(selected) >= limit:
            break
    return selected


def get_raw_feature(source_key, raw_index):
    batch, zoom, tx, ty, layer_name, feature_index = parse_source_key(source_key)
    tile_entry = raw_index.get((batch, zoom, tx, ty))
    if not tile_entry:
        raise KeyError(f"Raw tile not found for {source_key}")
    raw_file, tile = tile_entry
    layer = next((x for x in tile.get("layers", []) if x.get("name") == layer_name), None)
    if layer is None:
        raise KeyError(f"Layer {layer_name} not found for {source_key}")
    features = layer.get("features", [])
    if feature_index >= len(features):
        raise IndexError(f"Feature index {feature_index} outside layer size {len(features)} for {source_key}")
    return raw_file, tile, layer, features[feature_index], feature_index


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    limit = int(os.environ.get("SAMPLE_LIMIT", DEFAULT_LIMIT))
    if not 1 <= limit <= 200:
        raise SystemExit("SAMPLE_LIMIT must be between 1 and 200")
    raw_index, raw_paths = load_raw_index()
    projected, projected_paths = load_projected_features()
    all_rows = load_priorities()
    sample = choose_sample(all_rows, limit)
    trace_rows, geo_features, missing = [], [], []
    for relation_index, rel in enumerate(sample, 1):
        for side in ("a", "b"):
            key = rel[f"source_key_{side}"]
            try:
                raw_file, tile, layer, feature, feature_index = get_raw_feature(key, raw_index)
                extent = int(layer.get("extent") or 4096)
                decoded = shape(feature["geometry"])
                projected_raw = tile_to_3857(decoded, int(tile["x"]), int(tile["y"]), extent)
                batch, zoom, tx, ty, layer_name, _ = parse_source_key(key)
                projected_feature = projected.get(key)
                props = feature.get("properties") or {}
                record = {
                    "relation_sample_id": relation_index,
                    "side": side,
                    "source_key": key,
                    "review_priority": rel.get("review_priority"),
                    "review_bucket": rel.get("review_bucket"),
                    "relation_category": rel.get("category"),
                    "canonical_class_pair": rel.get("canonical_class_pair"),
                    "motive_relation": rel.get("motive_relation"),
                    "other_source_key": rel[f"source_key_{'b' if side == 'a' else 'a'}"],
                    "source_batch": batch,
                    "source_zoom": zoom,
                    "source_tile_x": tx,
                    "source_tile_y": ty,
                    "source_layer": layer_name,
                    "source_feature_index": feature_index,
                    "source_feature_id": feature.get("id"),
                    "source_tile_http_status": tile.get("http_status"),
                    "source_tile_sha256": tile.get("sha256"),
                    "source_tile_url": tile.get("url"),
                    "raw_batch_file": raw_file,
                    "raw_properties_json": json.dumps(props, ensure_ascii=False, sort_keys=True),
                    "mvt_decoded_geometry_type": projected_raw.geom_type,
                    "mvt_decoded_geometry_valid": projected_raw.is_valid,
                    "mvt_decoded_geometry_sha256_epsg3857": hashlib.sha256(projected_raw.wkb).hexdigest(),
                    "projected_feature_present": projected_feature is not None,
                    "geometry_provenance": "decoded_mvt_tile_feature_reconstructed_to_epsg3857",
                    "identity_resolved": False,
                }
                trace_rows.append(record)
                geo_features.append({
                    "type": "Feature",
                    "id": f"sample-{relation_index}-{side}",
                    "properties": {k: v for k, v in record.items() if k != "raw_properties_json"},
                    "geometry": mapping(projected_raw),
                })
            except Exception as exc:
                missing.append({"relation_sample_id": relation_index, "side": side, "source_key": key, "error": str(exc)})
    fields = list(trace_rows[0].keys()) if trace_rows else ["relation_sample_id", "side", "source_key"]
    with (OUT / "sca-overlap-source-trace.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(trace_rows)
    fc = {"type": "FeatureCollection", "name": "SCA prioritized overlap sample - decoded MVT geometries",
          "crs": {"type": "name", "properties": {"name": "EPSG:3857"}}, "features": geo_features}
    (OUT / "sca-overlap-source-trace.geojson").write_text(
        json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    summary = {
        "priority_relations_available": len(all_rows),
        "sampled_relations": len(sample),
        "sampled_feature_sides_expected": len(sample) * 2,
        "traced_feature_sides": len(trace_rows),
        "missing_feature_sides": len(missing),
        "review_bucket_counts": dict(Counter(r.get("review_bucket", "") for r in sample)),
        "priority_counts": dict(Counter(r.get("review_priority", "") for r in sample)),
        "raw_batch_files": len(raw_paths),
        "projected_geometry_batch_files": len(projected_paths),
        "raw_tiles_indexed": len(raw_index),
        "geometry_provenance": "Decoded MVT tile feature geometry, reconstructed to EPSG:3857; not an authoritative unclipped WFS/OGC object geometry.",
        "identity_resolved_relations": 0,
        "missing": missing,
        "limitations": [
            "Tile geometry is MVT-decoded and may be clipped, buffered or generalized.",
            "Tile/source metadata proves provenance to a specific downloaded tile feature, not unique real-world object identity.",
            "No geometries are merged, dissolved, deleted or altered in source artifacts.",
            "The sample is a deterministic review extract, not a representative statistical sample."
        ]
    }
    (OUT / "sca-overlap-source-trace-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if missing:
        raise SystemExit("One or more sampled features could not be traced")


if __name__ == "__main__":
    main()
