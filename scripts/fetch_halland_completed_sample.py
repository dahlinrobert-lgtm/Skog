#!/usr/bin/env python3
"""Fetch a reproducible sample of real completed-harvest polygons intersecting the Halland volume raster extent."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaUtfordavverkning/MapServer/1/query"
FIELDS = "OBJECTID,Lannr,Lan,Kommunnr,Kommun,Arendear,Beteckn,Avverktyp,Skogstyp,AnmaldHa,SkogsodlHa,Natforha,Avvdatum,KallaDatum,KallaAreal,Forebild,Efterbild,Arealha"
# Extent of the committed Halland raster, in SWEREF 99 TM (EPSG:3006).
EXTENT = {"xmin": 250000, "ymin": 6200000, "xmax": 450000, "ymax": 6400000,
          "spatialReference": {"wkid": 3006}}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    if not 1 <= args.limit <= 2000:
        raise ValueError("--limit must be between 1 and 200")
    params = {
        "where": "Lannr = '13'",
        "geometry": json.dumps(EXTENT, separators=(",", ":")),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "3006",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": FIELDS,
        "returnGeometry": "true",
        "outSR": "3006",
        "f": "geojson",
        "resultRecordCount": min(args.limit, 200),
        "resultOffset": 0,
        "orderByFields": "OBJECTID ASC",
    }
    features = []
    page_size = min(args.limit, 200)
    source_more = False
    for offset in range(0, args.limit, page_size):
        params["resultRecordCount"] = min(page_size, args.limit - offset)
        params["resultOffset"] = offset
        response = requests.get(URL, params=params, timeout=90,
                                headers={"User-Agent": "Skogskoll-real-polygon-validation/1.0"})
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"Skogsstyrelsen ArcGIS error: {data['error']}")
        page = data.get("features")
        if not isinstance(page, list):
            raise RuntimeError("Source response did not contain a GeoJSON feature list")
        source_more = source_more or bool(data.get("exceededTransferLimit"))
        page = [f for f in page if (f.get("properties") or {}).get("Lannr") == "13"
                and f.get("geometry")]
        features.extend(page)
        if len(page) < params["resultRecordCount"]:
            break
    if not features:
        raise RuntimeError("No real Halland completed-harvest polygons returned for the raster extent")
    collection = {
        "type": "FeatureCollection",
        "name": "halland_completed_harvest_validation_sample",
        "metadata": {
            "source": URL,
            "source_layer": 1,
            "query": {"Lannr": "13", "extent_epsg3006": EXTENT,
                      "order": "OBJECTID ASC", "requested_limit": args.limit},
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "count": len(features),
            "source_more_matching_features": source_more,
            "pagination_page_size": page_size,
            "note": "Live source sample for validation only; not a complete county inventory. Pagination is ordered by OBJECTID."
        },
        "features": features,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}: {len(features)} real Halland polygons; source={URL}")

if __name__ == "__main__":
    main()
