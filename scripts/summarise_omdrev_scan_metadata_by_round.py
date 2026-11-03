#!/usr/bin/env python3
"""Create round-aware scan metadata inventory and raster coverage summaries.

The overlay CSV repeats the same scan metadata against each raster round to
support spatial comparison. This script deliberately deduplicates source
metadata records and uses one raster grid (Omdrev 3) for the metadata overlay
summary, while keeping metadata round and raster round as separate concepts.
"""
from __future__ import annotations
import csv, json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "raster-three-omdrev" / "cross_round_pilot"
OVERLAY = BASE / "volume_coverage_scan_metadata_overlay.csv"
OUT_META = BASE / "scan_metadata_inventory_by_round_tile.csv"
OUT_CELLS = BASE / "scan_metadata_cell_coverage_by_round_tile.csv"
OUT_JSON = BASE / "scan_metadata_round_aware_summary.json"

def parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None

def main():
    if not OVERLAY.is_file():
        raise FileNotFoundError(OVERLAY)

    # Source metadata is repeated for raster rounds 1, 2 and 3 in the overlay.
    # Keep one copy per ArcGIS object ID; raster round 3 is used only as the
    # reference grid for summarising spatial intersections.
    features = {}
    cells = defaultdict(dict)
    with OVERLAY.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            oid = str(row.get("metadata_object_id") or "")
            tile = str(row.get("raster_tile_code") or "")
            if oid:
                # One source object may intersect more than one raster tile extent.
                features[(oid, tile)] = row
            if row.get("raster_survey_round") == "3":
                key = (row["raster_tile_code"], row["grid_row"], row["grid_col"])
                meta_round = str(row.get("metadata_survey_round") or "unknown")
                # Preserve one record per source feature per cell.
                cells[(meta_round, *key)][oid] = row

    inventory = defaultdict(list)
    for (oid, tile), row in features.items():
        key = (str(row.get("metadata_survey_round") or "unknown"), tile)
        inventory[key].append((oid, row))

    metadata_rows = []
    metadata_summary = []
    for (meta_round, tile), records in sorted(inventory.items()):
        dates = sorted(d for _, r in records if (d := parse_date(r.get("metadata_scan_date_raw"))))
        index_tiles = {str(r.get("metadata_index_tile")) for _, r in records if r.get("metadata_index_tile")}
        leaf = defaultdict(int)
        for _, r in records:
            leaf[str(r.get("metadata_leaf_status") or "unknown")] += 1
        row = {
            "metadata_survey_round": meta_round,
            "raster_tile_code": tile,
            "unique_metadata_records": len(records),
            "unique_index_tile_labels": len(index_tiles),
            "unique_scan_dates": len(dates),
            "first_scan_date": dates[0].isoformat() if dates else "",
            "last_scan_date": dates[-1].isoformat() if dates else "",
            "records_leaf_status_1": leaf["1"],
            "records_leaf_status_2": leaf["2"],
            "records_leaf_status_unknown": leaf["unknown"],
        }
        metadata_rows.append(row)
        metadata_summary.append(row)

    cell_rows = []
    # Each output row is one (metadata round, raster tile, 2 km cell).
    # Coverage is the raster valid fraction in that cell; it is not attributed
    # to a particular scan record.
    for (meta_round, tile, gr, gc), recs in sorted(cells.items()):
        first = next(iter(recs.values()))
        frac = float(first["raster_valid_fraction"])
        overlaps = [float(r["cell_area_overlap_fraction"]) for r in recs.values()
                    if r.get("cell_area_overlap_fraction") not in (None, "")]
        cell_rows.append({
            "metadata_survey_round": meta_round,
            "raster_reference_round": 3,
            "raster_tile_code": tile,
            "grid_row": gr, "grid_col": gc,
            "raster_valid_fraction": frac,
            "valid_pixels_present": frac > 0,
            "metadata_record_count": len(recs),
            "metadata_overlap_fraction_sum": round(sum(overlaps), 6),
            "metadata_overlap_fraction_max": round(max(overlaps), 6) if overlaps else 0,
        })

    def write_csv(path, rows):
        if not rows:
            raise RuntimeError(f"No rows to write: {path.name}")
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    write_csv(OUT_META, metadata_rows)
    write_csv(OUT_CELLS, cell_rows)

    by_group = defaultdict(list)
    for row in cell_rows:
        by_group[(row["metadata_survey_round"], row["raster_tile_code"])].append(row)
    cell_summary = []
    for (meta_round, tile), rows in sorted(by_group.items()):
        cell_summary.append({
            "metadata_survey_round": meta_round,
            "raster_reference_round": 3,
            "raster_tile_code": tile,
            "cells_intersecting_metadata": len(rows),
            "cells_with_any_valid_raster_pixels": sum(r["valid_pixels_present"] for r in rows),
            "cells_with_no_valid_raster_pixels": sum(not r["valid_pixels_present"] for r in rows),
            "mean_raster_valid_fraction_in_intersecting_cells":
                sum(r["raster_valid_fraction"] for r in rows) / len(rows),
            "note": "Spatial intersection only; raster validity is not attributed to an individual scan."
        })

    result = {
        "purpose": "Round-aware inventory of scan-index metadata and spatial association with Omdrev 3 raster coverage.",
        "metadata_deduplication": "One row per ArcGIS metadata object ID; source metadata is not counted once per raster round.",
        "reference_raster_round": 3,
        "survey_round_status": {
            "Omdrev 1": "historical survey round",
            "Omdrev 2": "historical survey round",
            "Omdrev 3": "ongoing; current metadata is a partial snapshot, not a final coverage total"
        },
        "metadata_by_round_and_tile": metadata_summary,
        "spatial_cells_by_metadata_round_and_tile": cell_summary,
        "limitations": [
            "The scan metadata layer uses 2.5 km index areas, not exact aircraft flight footprints.",
            "The same metadata source records were spatially overlaid with all raster rounds; this summary deduplicates them.",
            "A metadata polygon intersecting a 2 km cell does not prove that a specific raster pixel came from that scan.",
            "Omdrev 3 is ongoing; its current record counts and date ranges must not be interpreted as final national or tile coverage.",
            "The metadata service may not retain a complete flight-by-flight history for each index tile.",
            "NoData indicates no usable raster value in the downloaded product, not necessarily absence of laser scanning."
        ]
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
