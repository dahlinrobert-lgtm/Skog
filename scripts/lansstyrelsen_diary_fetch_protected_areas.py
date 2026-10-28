#!/usr/bin/env python3
"""Fetch the official Nature Conservation Register protected-area layer as GeoJSON."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://geodata.naturvardsverket.se/naturvardsregistret/wfs"
TYPE_NAME = "Naturvardsregistret_WFS:SkyddadeOmraden"


def request_json(url: str, timeout: int = 90) -> dict:
    req = Request(url, headers={"User-Agent": "Skog-protected-area-geocoder/1.0", "Accept": "application/geo+json, application/json"})
    with urlopen(req, timeout=timeout) as response:
        body = response.read()
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"WFS returned HTTP {response.status}")
        content_type = response.headers.get("Content-Type", "")
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"WFS response was not valid JSON (Content-Type: {content_type})") from exc


def fetch_all(page_size: int = 1000, max_features: int = 100000) -> dict:
    features = []
    start_index = 0
    seen_ids = set()
    while start_index < max_features:
        params = {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": TYPE_NAME, "outputFormat": "application/json",
            "srsName": "urn:ogc:def:crs:OGC::CRS84",
            "count": page_size, "startIndex": start_index,
        }
        url = BASE_URL + "?" + urlencode(params)
        doc = request_json(url)
        page = doc.get("features")
        if not isinstance(page, list):
            raise RuntimeError(f"WFS response has no features array at startIndex={start_index}")
        if not page:
            break
        for feature in page:
            properties = feature.get("properties") or {}
            fid = feature.get("id") or properties.get("NVRID") or properties.get("OBJECTID")
            if fid is not None:
                if fid in seen_ids:
                    continue
                seen_ids.add(fid)
            features.append(feature)
        if len(page) < page_size:
            break
        start_index += len(page)
    if not features:
        raise RuntimeError("WFS returned zero features; refusing to write an empty dataset")
    return {"type": "FeatureCollection", "name": "Naturvardsregistret_WFS:SkyddadeOmraden", "features": features}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/lansstyrelsen-diary/official-protected-areas.geojson"))
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--max-features", type=int, default=100000)
    args = parser.parse_args()
    if not 1 <= args.page_size <= 5000:
        parser.error("--page-size must be between 1 and 5000")
    if args.max_features < 1:
        parser.error("--max-features must be positive")
    data = fetch_all(args.page_size, args.max_features)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({"output": str(args.output), "feature_count": len(data["features"]), "source": BASE_URL, "type_name": TYPE_NAME}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
