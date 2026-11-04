#!/usr/bin/env python3
"""Inspect raw MVT extent overflow for prioritized SCA overlap pairs.

This follows the tile-local decoded MVT coordinates before EPSG:3857
reconstruction. It measures whether each pair's features extend across the
shared tile edge toward the neighboring tile. It is a rendering/provenance
diagnostic, never an object-identity decision.
"""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path

from shapely.geometry import shape
from shapely import get_coordinates

INPUT = Path("input")
OUT = Path("output")
WORLD = 20037508.342789244
ZOOM = 12


def parse_source_key(key):
    parts = str(key).split(":")
    if len(parts) < 6:
        raise ValueError(f"Unparseable source key: {key}")
    batch, zoom, tx, ty = map(int, parts[:4])
    layer = ":".join(parts[4:-1])
    index = int(parts[-1])
    return batch, zoom, tx, ty, layer, index


def load_raw_tiles():
    tiles = {}
    paths = sorted(INPUT.rglob("sca-national-voluntary-tile-expansion-z12.json"))
    if not paths:
        raise SystemExit("No raw z12 tile expansion JSON files found")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        batch = int(data["batch"])
        for tile in data.get("tile_results", []):
            key = (batch, int(tile["z"]), int(tile["x"]), int(tile["y"]))
            tiles[key] = tile
    return tiles, paths


def get_feature(key, tile_index):
    batch, zoom, tx, ty, layer_name, feature_index = parse_source_key(key)
    tile = tile_index.get((batch, zoom, tx, ty))
    if tile is None:
        raise KeyError(f"Missing raw tile for {key}")
    layer = next((x for x in tile.get("layers", []) if x.get("name") == layer_name), None)
    if layer is None:
        raise KeyError(f"Missing layer {layer_name} for {key}")
    features = layer.get("features", [])
    if feature_index >= len(features):
        raise IndexError(f"Missing feature index {feature_index} for {key}")
    return tile, layer, features[feature_index]


def extent_metrics(source_key, tile_index):
    tile, layer, feature = get_feature(source_key, tile_index)
    extent = int(layer.get("extent") or 4096)
    geom = shape(feature["geometry"])
    coords = get_coordinates(geom)
    if len(coords) == 0:
        raise ValueError(f"Empty geometry for {source_key}")
    xs, ys = coords[:, 0], coords[:, 1]
    minx, miny = float(xs.min()), float(ys.min())
    maxx, maxy = float(xs.max()), float(ys.max())
    outside = (xs < 0) | (xs > extent) | (ys < 0) | (ys > extent)
    scale_m = (2 * WORLD / (2 ** ZOOM)) / extent
    return {
        "source_key": source_key,
        "source_tile_x": int(tile["x"]),
        "source_tile_y": int(tile["y"]),
        "source_layer_extent": extent,
        "mvt_vertex_count": int(len(coords)),
        "mvt_out_of_extent_vertex_count": int(outside.sum()),
        "mvt_out_of_extent_vertex_fraction": float(outside.mean()),
        "mvt_min_x": minx,
        "mvt_min_y": miny,
        "mvt_max_x": maxx,
        "mvt_max_y": maxy,
        "mvt_west_overshoot_units": max(0.0, -minx),
        "mvt_east_overshoot_units": max(0.0, maxx - extent),
        "mvt_south_overshoot_units": max(0.0, -miny),
        "mvt_north_overshoot_units": max(0.0, maxy - extent),
        "mvt_max_overshoot_m_approx": max(
            max(0.0, -minx), max(0.0, maxx - extent),
            max(0.0, -miny), max(0.0, maxy - extent)
        ) * scale_m,
        "mvt_source_feature_id": feature.get("id"),
        "mvt_source_tile_http_status": tile.get("http_status"),
        "mvt_source_tile_sha256": tile.get("sha256"),
        "mvt_source_tile_url": tile.get("url"),
        "geometry_valid": bool(geom.is_valid),
        "geometry_provenance": "raw_decoded_mvt_tile_local_coordinates",
    }


def directional_overflow(a, b):
    """Check overflow toward the opposite tile for cardinal shared edges."""
    dx = int(b["source_tile_x"]) - int(a["source_tile_x"])
    dy = int(b["source_tile_y"]) - int(a["source_tile_y"])
    if max(abs(dx), abs(dy)) != 1:
        return {"tile_dx_a_to_b": dx, "tile_dy_a_to_b": dy,
                "a_overflow_toward_b": False, "b_overflow_toward_a": False,
                "shared_edge_overflow_pattern": "not_adjacent"}
    checks = []
    if dx == 1:
        checks.extend([a["mvt_east_overshoot_units"] > 0, b["mvt_west_overshoot_units"] > 0])
    elif dx == -1:
        checks.extend([a["mvt_west_overshoot_units"] > 0, b["mvt_east_overshoot_units"] > 0])
    if dy == 1:
        # With y_coord_down=False, local y grows north; XYZ y grows south.
        checks.extend([a["mvt_south_overshoot_units"] > 0, b["mvt_north_overshoot_units"] > 0])
    elif dy == -1:
        checks.extend([a["mvt_north_overshoot_units"] > 0, b["mvt_south_overshoot_units"] > 0])
    # Determine directional match for the axes that actually separate the tiles.
    if dx:
        a_x = a["mvt_east_overshoot_units"] > 0 if dx == 1 else a["mvt_west_overshoot_units"] > 0
        b_x = b["mvt_west_overshoot_units"] > 0 if dx == 1 else b["mvt_east_overshoot_units"] > 0
    else:
        a_x = b_x = True
    if dy:
        a_y = a["mvt_south_overshoot_units"] > 0 if dy == 1 else a["mvt_north_overshoot_units"] > 0
        b_y = b["mvt_north_overshoot_units"] > 0 if dy == 1 else b["mvt_south_overshoot_units"] > 0
    else:
        a_y = b_y = True
    a_ok, b_ok = a_x and a_y, b_x and b_y
    if a_ok and b_ok:
        pattern = "both_features_overflow_toward_each_other"
    elif a_ok or b_ok:
        pattern = "one_feature_overflows_toward_neighbor"
    else:
        pattern = "no_directional_extent_overflow"
    return {
        "tile_dx_a_to_b": dx, "tile_dy_a_to_b": dy,
        "a_overflow_toward_b": bool(a_ok),
        "b_overflow_toward_a": bool(b_ok),
        "shared_edge_overflow_pattern": pattern,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    edge_csvs = sorted(INPUT.rglob("sca-mvt-tile-edge-pair-diagnostics.csv"))
    if len(edge_csvs) != 1:
        raise SystemExit(f"Expected one edge pair diagnostics CSV, found {len(edge_csvs)}")
    with edge_csvs[0].open(encoding="utf-8-sig", newline="") as f:
        relations = list(csv.DictReader(f))
    tile_index, raw_paths = load_raw_tiles()
    output = []
    feature_metrics = {}
    for rel in relations:
        a = feature_metrics.setdefault(rel["source_key_a"], extent_metrics(rel["source_key_a"], tile_index))
        b = feature_metrics.setdefault(rel["source_key_b"], extent_metrics(rel["source_key_b"], tile_index))
        direction = directional_overflow(a, b)
        output.append({
            "relation_sample_id": rel["relation_sample_id"],
            "review_priority": rel["review_priority"],
            "review_bucket": rel["review_bucket"],
            "canonical_class_pair": rel["canonical_class_pair"],
            "motive_relation": rel["motive_relation"],
            "source_key_a": rel["source_key_a"],
            "source_key_b": rel["source_key_b"],
            "tile_edge_pattern_epsg3857": rel["tile_edge_pattern"],
            "overlap_smaller_fraction_epsg3006": rel["overlap_smaller_fraction"],
            "area_ratio_epsg3006": rel["area_ratio"],
            "iou_epsg3006": rel["iou"],
            "hausdorff_m_epsg3006": rel["hausdorff_m_epsg3006"],
            **{f"a_{k}": v for k, v in a.items() if k != "source_key"},
            **{f"b_{k}": v for k, v in b.items() if k != "source_key"},
            **direction,
            "identity_resolved": False,
            "interpretation": "mvt_extent_diagnostic_only_no_identity_resolution",
        })
    fields = list(output[0].keys()) if output else []
    with (OUT / "sca-mvt-extent-overflow-pair-diagnostics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    with (OUT / "sca-mvt-extent-overflow-feature-diagnostics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        feature_rows = list(feature_metrics.values())
        writer = csv.DictWriter(f, fieldnames=list(feature_rows[0].keys()) if feature_rows else [])
        writer.writeheader()
        writer.writerows(feature_rows)
    summary = {
        "input_relations": len(output),
        "unique_source_features": len(feature_metrics),
        "raw_z12_batches": len(raw_paths),
        "raw_z12_tiles_indexed": len(tile_index),
        "shared_edge_overflow_pattern_counts": dict(Counter(r["shared_edge_overflow_pattern"] for r in output)),
        "review_bucket_counts": dict(Counter(r["review_bucket"] for r in output)),
        "features_with_out_of_extent_vertices": sum(1 for r in feature_metrics.values() if r["mvt_out_of_extent_vertex_count"] > 0),
        "features_with_at_least_5pct_out_of_extent_vertices": sum(1 for r in feature_metrics.values() if r["mvt_out_of_extent_vertex_fraction"] >= 0.05),
        "max_mvt_overshoot_m_approx": max((r["mvt_max_overshoot_m_approx"] for r in feature_metrics.values()), default=0.0),
        "identity_resolved_relations": 0,
        "limitations": [
            "MVT extent overflow confirms coordinates outside the nominal tile extent but does not reveal the renderer's clipping/buffer rules completely.",
            "Directional overflow toward an adjacent tile is evidence of tile-buffer overlap, not proof of a shared source object.",
            "Feature IDs and properties may be non-unique or incomplete in the public MVT layer.",
            "All relations and source feature observations are retained; no geometry is changed, merged, dissolved or deleted."
        ],
    }
    (OUT / "sca-mvt-extent-overflow-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not output or len(feature_metrics) > len(relations) * 2:
        raise SystemExit("Unexpected feature indexing invariant")


if __name__ == "__main__":
    main()
