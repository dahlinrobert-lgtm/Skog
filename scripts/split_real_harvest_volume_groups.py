#!/usr/bin/env python3
"""Split the grouped real-harvest GeoJSON into one GeoJSON file per raster code."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--raster-codes", required=True, help="Comma-separated raster codes")
    args = parser.parse_args()

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    groups = {
        str(group.get("metadata", {}).get("raster_code")): group
        for group in doc.get("raster_groups", [])
    }
    requested = [item.strip() for item in args.raster_codes.split(",") if item.strip()]
    if not requested:
        raise SystemExit("--raster-codes did not contain any raster codes")

    print(f"FETCH_OUTPUT_KEYS={list(doc)}", flush=True)
    print(f"AVAILABLE_RASTER_GROUPS={list(groups)}", flush=True)

    for code in requested:
        group = groups.get(code)
        if group is None:
            raise SystemExit(
                f"Raster group {code} missing; top-level keys={list(doc)}; "
                f"available groups={list(groups)}"
            )
        features = group.get("features")
        if not isinstance(features, list):
            raise SystemExit(f"Raster group {code} has no feature list")
        target = Path(f"real-polygons-{code}.geojson")
        payload = {"type": "FeatureCollection", "features": features}
        target.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"Prepared raster {code}: {len(features)} polygons -> {target}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
