#!/usr/bin/env python3
"""Read-only inventory of GeoPackage layers and fields for NVDB topology review.

The tool does not infer connectivity, alter source files, or export feature rows.
It reports schema evidence needed to decide whether a supplied NVDB package
contains reference-link, node and port relationships.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pyogrio


TOPOLOGY_TERMS = re.compile(
    r"(referenslänk|referenslanks|länk.?id|link.?id|nod|node|port|"
    r"från.?nod|till.?nod|start.?nod|slut.?nod|oid|object.?id|"
    r"nätelement|network.?element|from|to)",
    re.IGNORECASE,
)


def field_inventory(fields: list[str]) -> dict:
    matches = [field for field in fields if TOPOLOGY_TERMS.search(str(field))]
    return {
        "field_count": len(fields),
        "fields": [str(field) for field in fields],
        "topology_candidate_fields": matches,
    }


def inspect_geopackage(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"GeoPackage not found: {path}")

    layers = pyogrio.list_layers(path)
    result = {
        "status": "completed",
        "inspection_only": True,
        "source_file": path.name,
        "layer_count": len(layers),
        "layers": [],
        "limitations": [
            "Field names are clues only; they do not prove semantic connectivity.",
            "No feature rows or geometries are exported.",
            "Inspect official product specifications and actual relationship values before routing.",
        ],
    }

    for layer_name, geometry_type in layers:
        info = pyogrio.read_info(path, layer=str(layer_name))
        fields = [str(field) for field in info.get("fields", [])]
        inventory = field_inventory(fields)
        result["layers"].append({
            "layer": str(layer_name),
            "geometry_type": str(geometry_type),
            "feature_count": int(info.get("features", 0)),
            "crs": str(info.get("crs") or ""),
            **inventory,
        })

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory NVDB GeoPackage layers and possible topology fields."
    )
    parser.add_argument("--gpkg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = inspect_geopackage(args.gpkg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "layer_count": report["layer_count"],
        "output": str(args.output),
        "topology_candidate_layers": [
            layer["layer"] for layer in report["layers"]
            if layer["topology_candidate_fields"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
