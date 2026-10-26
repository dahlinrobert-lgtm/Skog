#!/usr/bin/env python3
"""Report geometric intersections for polygon pairs that share raster cell centres."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import rasterio
from pyproj import CRS, Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform as transform_geometry
from shapely.validation import explain_validity

try:
    from scripts.analyze_volume_for_polygon import load_features
except ModuleNotFoundError:
    from analyze_volume_for_polygon import load_features
from rasterio.features import rasterize
import numpy as np


def analyze_pairs(ds, features, source_crs):
    if ds.crs is None:
        raise ValueError("Raster has no CRS")
    project = Transformer.from_crs(source_crs, ds.crs, always_xy=True).transform
    raster_extent = box(ds.bounds.left, ds.bounds.bottom, ds.bounds.right, ds.bounds.top)
    projected = []
    for feature in features:
        geom = transform_geometry(project, feature["geometry"])
        clipped = geom.intersection(raster_extent)
        projected.append({"id": str(feature["feature_id"]), "geometry": geom,
                          "clipped": clipped, "properties": feature["properties"]})

    # Only test bounding boxes that overlap; use an STRtree to avoid O(n^2)
    # exact geometry intersections for the entire sample.
    from shapely.strtree import STRtree
    geoms = [item["clipped"] for item in projected]
    tree = STRtree(geoms)
    pair_records = {}
    for i, item in enumerate(projected):
        geom = item["clipped"]
        if geom.is_empty:
            continue
        for candidate in tree.query(geom):
            # Shapely 2 returns integer indices; handle Shapely 1 geometry objects too.
            j = int(candidate) if isinstance(candidate, (int, np.integer)) else next(
                (k for k, g in enumerate(geoms) if g is candidate), -1)
            if j <= i or j < 0:
                continue
            other = projected[j]
            if not geom.intersects(other["clipped"]):
                continue
            intersection = geom.intersection(other["clipped"])
            area = float(intersection.area)
            area_a = float(geom.area)
            area_b = float(other["clipped"].area)
            smaller_area = min(area_a, area_b)
            larger_area = max(area_a, area_b)
            overlap_smaller_pct = (100 * area / smaller_area) if smaller_area > 0 else None
            overlap_larger_pct = (100 * area / larger_area) if larger_area > 0 else None
            # Diagnostic classification only; never automatically alter source polygons.
            if area <= 0.01:
                severity = "touch_or_numerical_sliver"
            elif overlap_smaller_pct is not None and overlap_smaller_pct >= 1:
                severity = "material_relative_to_smaller_polygon"
            else:
                severity = "small_relative_overlap"
            props_a = item["properties"] or {}
            props_b = other["properties"] or {}
            images_a = {str(props_a.get(key)).strip() for key in ("Forebild", "Efterbild")
                        if props_a.get(key) not in (None, "") and str(props_a.get(key)).strip().lower() != "none"}
            images_b = {str(props_b.get(key)).strip() for key in ("Forebild", "Efterbild")
                        if props_b.get(key) not in (None, "") and str(props_b.get(key)).strip().lower() != "none"}
            shared_image_ids = sorted(images_a & images_b)
            # A shared before/after image can indicate linked change-detection
            # records rather than duplicate polygons. This is evidence only.
            if props_a.get("Forebild") and props_a.get("Forebild") == props_b.get("Efterbild"):
                image_relation = "a_before_matches_b_after"
            elif props_a.get("Efterbild") and props_a.get("Efterbild") == props_b.get("Forebild"):
                image_relation = "a_after_matches_b_before"
            elif shared_image_ids:
                image_relation = "shared_image_reference"
            else:
                image_relation = "no_shared_image_reference"
            pair_records[(i, j)] = {
                "feature_ids": [item["id"], other["id"]],
                "polygon_a_properties": props_a,
                "polygon_b_properties": props_b,
                "shared_image_ids": shared_image_ids,
                "source_image_relation": image_relation,
                "polygon_a_area_m2": round(area_a, 3),
                "polygon_b_area_m2": round(area_b, 3),
                "geometry_intersection_area_m2": round(area, 3),
                "geometry_intersection_area_ha": round(area / 10000, 6),
                "overlap_of_smaller_polygon_pct": round(overlap_smaller_pct, 6) if overlap_smaller_pct is not None else None,
                "overlap_of_larger_polygon_pct": round(overlap_larger_pct, 6) if overlap_larger_pct is not None else None,
                "overlap_severity": severity,
                "geometry_intersection_is_area_overlap": bool(area > 0.01),
                "geometry_intersection_type": intersection.geom_type,
                "polygon_a_valid": bool(geom.is_valid),
                "polygon_b_valid": bool(other["clipped"].is_valid),
                "polygon_a_validity_reason": explain_validity(geom),
                "polygon_b_validity_reason": explain_validity(other["clipped"]),
            }

    # Count cells selected by both polygons. Cell-centre inclusion matches the
    # existing ownership audit. Use a common local window for each candidate pair.
    for (i, j), record in pair_records.items():
        a, b = projected[i]["clipped"], projected[j]["clipped"]
        if a.is_empty or b.is_empty or not a.intersects(b):
            record["shared_cell_count"] = 0
            continue
        overlap = a.intersection(b)
        if overlap.is_empty:
            record["shared_cell_count"] = 0
            continue
        window = rasterio.windows.from_bounds(*overlap.bounds, transform=ds.transform)
        window = window.round_offsets().round_lengths().intersection(
            rasterio.windows.Window(0, 0, ds.width, ds.height))
        if window.width <= 0 or window.height <= 0:
            record["shared_cell_count"] = 0
            continue
        trans = ds.window_transform(window)
        shape = (int(window.height), int(window.width))
        ma = rasterize([(mapping(a), 1)], out_shape=shape, transform=trans,
                       fill=0, dtype="uint8", all_touched=False).astype(bool)
        mb = rasterize([(mapping(b), 1)], out_shape=shape, transform=trans,
                       fill=0, dtype="uint8", all_touched=False).astype(bool)
        record["shared_cell_count"] = int(np.count_nonzero(ma & mb))
        record["shared_cell_area_m2"] = round(record["shared_cell_count"] * abs(
            ds.transform.a * ds.transform.e - ds.transform.b * ds.transform.d), 3)

    return {
        "source_crs": source_crs.to_string(),
        "raster_crs": ds.crs.to_string(),
        "pixel_size_m": [abs(float(ds.transform.a)), abs(float(ds.transform.e))],
        "polygon_count": len(features),
        "candidate_pair_count": len(pair_records),
        "pairs_with_positive_area_overlap": sum(
            1 for x in pair_records.values() if x["geometry_intersection_is_area_overlap"]),
        "pairs_touching_only_or_numerical_sliver": sum(
            1 for x in pair_records.values() if not x["geometry_intersection_is_area_overlap"]),
        "pairs_with_shared_cell_centres": sum(1 for x in pair_records.values() if x["shared_cell_count"] > 0),
        "pairs": sorted(pair_records.values(), key=lambda x: (-x["shared_cell_count"],
                       -x["geometry_intersection_area_m2"], x["feature_ids"])),
        "interpretation": "A shared cell centre is an assignment overlap; positive geometric intersection area indicates the polygon geometries themselves overlap. Boundary touching or tiny numerical slivers are not counted as positive area overlap (threshold 0.01 m²).",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--polygon", required=True, type=Path)
    parser.add_argument("--raster", required=True, type=Path,
                        help="GeoTIFF or ZIP containing exactly one TIFF")
    parser.add_argument("--polygon-crs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    features, inferred_crs = load_features(args.polygon)
    source_crs = CRS.from_user_input(args.polygon_crs) if args.polygon_crs else inferred_crs
    with tempfile.TemporaryDirectory(prefix="skog-pair-overlap-") as tmp:
        raster_path = args.raster
        if raster_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(raster_path) as zf:
                tiffs = [m for m in zf.namelist() if not m.endswith("/")
                         and Path(m).suffix.lower() in {".tif", ".tiff"}]
                if len(tiffs) != 1:
                    raise ValueError(f"Expected exactly one TIFF in ZIP, found {len(tiffs)}")
                extracted = Path(tmp) / Path(tiffs[0]).name
                with zf.open(tiffs[0]) as src, extracted.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                raster_path = extracted
        with rasterio.open(raster_path) as ds:
            report = analyze_pairs(ds, features, source_crs)
    report["input_geojson"] = str(args.polygon)
    report["input_raster"] = str(args.raster)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Polygon pairs with shared cell centres:", report["pairs_with_shared_cell_centres"])
    print("Pairs with positive geometric area overlap:", report["pairs_with_positive_area_overlap"])
    print("Pairs touching only or numerical sliver:", report["pairs_touching_only_or_numerical_sliver"])
    print("Pairs material relative to smaller polygon (>=1%):",
          sum(1 for pair in report["pairs"]
              if pair.get("overlap_severity") == "material_relative_to_smaller_polygon"))
    for pair in report["pairs"]:
        if pair["shared_cell_count"] or pair["geometry_intersection_is_area_overlap"]:
            print("Pair", ",".join(pair["feature_ids"]),
                  "shared_cells=", pair["shared_cell_count"],
                  "geometry_overlap_m2=", pair["geometry_intersection_area_m2"],
                  "overlap_smaller_pct=", pair.get("overlap_of_smaller_polygon_pct"),
                  "severity=", pair.get("overlap_severity"),
                  "valid=", pair.get("polygon_a_valid"), pair.get("polygon_b_valid"),
                  "intersection_type=", pair["geometry_intersection_type"],
                  "source_image_relation=", pair.get("source_image_relation"),
                  "shared_image_ids=", ",".join(pair.get("shared_image_ids", [])))
            # Print only source fields useful for diagnosing whether overlap
            # pairs are likely duplicate records or distinct harvest cases.
            fields = ("OBJECTID", "Beteckn", "Avverktyp", "Avvdatum", "KallaDatum",
                      "Arealha", "KallaAreal", "Kommun", "Kommunnr", "Forebild", "Efterbild")
            for label in ("polygon_a_properties", "polygon_b_properties"):
                props = pair.get(label) or {}
                print("  ", label, json.dumps(
                    {key: props.get(key) for key in fields if key in props},
                    ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
