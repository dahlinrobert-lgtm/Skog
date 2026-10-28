#!/usr/bin/env python3
"""Download official protected-area shapefile packages and export candidate-matching features as GeoJSON.

The WFS endpoint rejects application/json. This fetcher uses the official
daily-updated ESRI Shape downloads, reprojects from their declared CRS to WGS84,
and retains only features relevant to diary geographic clues.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

from lansstyrelsen_diary_protected_area_match import normalize, split_candidate

BASE_URL = "https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret"
DATASETS = {
    "NR": "Naturreservat",
    "NP": "Nationalpark",
    "NVO": "Naturvårdsområde",
    "KR": "Kulturreservat",
    "DVO": "Djur- och växtskyddsområde",
    "LBSO": "Landskapsbildsskyddsområde",
    "OBO": "Biotopskyddsområde",
    "IF": "Interimistiskt förbud",
    "VSO": "Vattenskyddsområde",
}
USER_AGENT = "Skog-protected-area-geocoder/1.0"


def request_bytes(url: str, timeout: int = 120) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/zip, application/octet-stream"})
    with urlopen(req, timeout=timeout) as response:
        body = response.read()
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"Download returned HTTP {response.status}: {url}")
        if not body:
            raise RuntimeError(f"Download was empty: {url}")
        return body


def candidate_names(candidates_doc: dict) -> set[str]:
    names: set[str] = set()
    for record in candidates_doc.get("features", []):
        for clue in (record.get("geocoding") or {}).get("clues") or []:
            if clue.get("type") not in {"protected_area_name", "place_name_candidate"}:
                continue
            for value in split_candidate(str(clue.get("value") or "")):
                name = normalize(value)
                if len(name) >= 3:
                    names.add(name)
    return names


def is_candidate_name(official_name: str, wanted: set[str]) -> bool:
    normalized = normalize(official_name)
    # The clue may use Swedish genitive, e.g. "Fulufjällets nationalpark",
    # while the official feature is named "Fulufjället".
    return normalized in wanted or f"{normalized}s" in wanted


def _encoding_for(archive: zipfile.ZipFile, stem: str, directory: str) -> str:
    target = f"{stem}.cpg".casefold()
    cpg = next((
        name for name in archive.namelist()
        if name.rsplit("/", 1)[-1].casefold() == target
        and (name.rsplit("/", 1)[0] if "/" in name else "") == directory
    ), None)
    if not cpg:
        return "utf-8"
    value = archive.read(cpg).decode("ascii", errors="ignore").strip()
    aliases = {
        "1252": "cp1252", "ANSI 1252": "cp1252",
        "UTF8": "utf-8", "UTF-8": "utf-8", "65001": "utf-8",
        "ISO-8859-1": "latin1",
    }
    return aliases.get(value.upper(), aliases.get(value, value or "utf-8"))


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def parse_archive(payload: bytes, code: str, wanted: set[str]) -> tuple[list[dict], int]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"Official download {code}.zip was not a valid ZIP archive") from exc
    with archive:
        names = archive.namelist()
        shp_paths = [name for name in names if name.casefold().endswith(".shp")]
        if not shp_paths:
            raise RuntimeError(f"Official download {code}.zip contained no shapefile")
        output = []
        total = 0
        for shp_path in shp_paths:
            directory = shp_path.rsplit("/", 1)[0] if "/" in shp_path else ""
            stem = shp_path.rsplit("/", 1)[-1][:-4]
            by_basename = {
                name.rsplit("/", 1)[-1].casefold(): name
                for name in names
                if (name.rsplit("/", 1)[0] if "/" in name else "") == directory
            }
            stem_lower = stem.casefold()
            required = {ext: by_basename.get(f"{stem_lower}.{ext}") for ext in ("shp", "shx", "dbf", "prj")}
            if not all(required.values()):
                raise RuntimeError(f"Shapefile {shp_path} in {code}.zip is missing a required .shp/.shx/.dbf/.prj sidecar")
            try:
                source_crs = CRS.from_wkt(archive.read(required["prj"]).decode("utf-8", errors="replace"))
            except Exception as exc:
                raise RuntimeError(f"Could not read source CRS in {code}.zip ({shp_path})") from exc
            transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
            encoding = _encoding_for(archive, stem_lower, directory)
            try:
                reader = shapefile.Reader(
                    shp=io.BytesIO(archive.read(required["shp"])),
                    shx=io.BytesIO(archive.read(required["shx"])),
                    dbf=io.BytesIO(archive.read(required["dbf"])),
                    encoding=encoding,
                )
                field_names = [field[0] for field in reader.fields[1:]]
                name_fields = [
                    field for field in field_names
                    if normalize(field) in {"namn", "name", "omradesnamn", "reservatsnamn"}
                    or "namn" in normalize(field).split()
                ]
                if not name_fields:
                    raise RuntimeError(f"No recognizable area-name field in {code}.zip ({field_names!r})")
                for record in reader.iterShapeRecords():
                    total += 1
                    properties = {key: _json_value(value) for key, value in record.record.as_dict().items()}
                    official_name = next((str(properties.get(key) or "").strip() for key in name_fields if str(properties.get(key) or "").strip()), "")
                    if not official_name or not is_candidate_name(official_name, wanted):
                        continue
                    if record.shape.shapeType == shapefile.NULL:
                        continue
                    geom = shape(record.shape.__geo_interface__)
                    geom_wgs84 = transform(transformer.transform, geom)
                    if geom_wgs84.is_empty:
                        continue
                    properties["SOURCE_DATASET"] = code
                    properties["SOURCE_DATASET_LABEL"] = DATASETS.get(code, code)
                    properties["SOURCE_URL"] = f"{BASE_URL}/{code}.zip"
                    output.append({
                        "type": "Feature",
                        "id": f"{code}:{properties.get('NVRID') or properties.get('OBJECTID') or official_name}",
                        "properties": properties,
                        "geometry": mapping(geom_wgs84),
                    })
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"Could not decode attribute names in {code}.zip ({shp_path}); encoding={encoding}") from exc
    return output, total


def fetch_candidate_features(candidates_doc: dict, *, dataset_codes: tuple[str, ...] = tuple(DATASETS)) -> dict:
    wanted = candidate_names(candidates_doc)
    if not wanted:
        raise RuntimeError("No protected-area/place-name clues were available; refusing to produce a misleading empty match report")
    features = []
    counts = {}
    total_source_features = 0
    for code in dataset_codes:
        if code not in DATASETS:
            raise ValueError(f"Unknown official dataset code: {code}")
        payload = request_bytes(f"{BASE_URL}/{code}.zip")
        matches, source_count = parse_archive(payload, code, wanted)
        total_source_features += source_count
        counts[code] = {"label": DATASETS[code], "source_features": source_count, "candidate_name_matches": len(matches)}
        features.extend(matches)
    if total_source_features == 0:
        raise RuntimeError("Official downloads contained zero features; refusing to write an empty dataset")
    return {
        "type": "FeatureCollection",
        "name": "Naturvardsregistret_matching_features",
        "source": BASE_URL,
        "source_feature_count": total_source_features,
        "candidate_name_count": len(wanted),
        "dataset_counts": counts,
        "features": features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=Path("data/lansstyrelsen-diary/geocoding-candidates.json"))
    parser.add_argument("--output", type=Path, default=Path("data/lansstyrelsen-diary/official-protected-areas.geojson"))
    parser.add_argument("--datasets", default=",".join(DATASETS), help="Comma-separated official dataset codes")
    args = parser.parse_args()
    candidates_doc = json.loads(args.candidates.read_text(encoding="utf-8"))
    codes = tuple(code.strip().upper() for code in args.datasets.split(",") if code.strip())
    data = fetch_candidate_features(candidates_doc, dataset_codes=codes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(json.dumps({
        "output": str(args.output),
        "candidate_name_count": data["candidate_name_count"],
        "source_feature_count": data["source_feature_count"],
        "candidate_name_matches": len(data["features"]),
        "datasets": data["dataset_counts"],
        "source": BASE_URL,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
