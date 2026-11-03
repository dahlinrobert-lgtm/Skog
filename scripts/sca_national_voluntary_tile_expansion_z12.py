#!/usr/bin/env python3
"""Expand independent z9 voluntary-positive seeds to z12 polygon tiles.

The input seed set is reconstructed deterministically from the full z9 bbox
rather than copied from an artifact. Only z9 tiles are selected as parents
where the voluntary layer returned MVT features. Every descendant z12 tile is
requested, plus a configurable neighbor ring. This is a first national
geometry-harvest tranche; results remain tile records with provenance.
"""
from __future__ import annotations
import hashlib, json, math, os, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
import mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

Z0, Z = 9, 12
BBOX = {"west": 10.5, "south": 55.0, "east": 24.5, "north": 69.5}
URL = "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf"
WORKERS = 3
TIMEOUT = (20, 60)
OUT = Path("sca-national-voluntary-tile-expansion-z12.json")


def xyz(lon, lat, z):
    n = 2 ** z
    lat = max(-85.05112878, min(85.05112878, lat))
    return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def load_positive_seeds():
    # Artifact ZIP contains the canonical census filename; discover the JSON
    # rather than relying on a stale/incorrect filename alias.
    candidates = sorted(Path("seed").glob("*.json"))
    if len(candidates) != 1:
        raise SystemExit(
            f"Expected exactly one census JSON in seed/, found {len(candidates)}: "
            + ", ".join(str(p) for p in candidates)
        )
    source = candidates[0]
    census = json.loads(source.read_text(encoding="utf-8"))
    rows = census.get("tile_results", [])
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"Census JSON has no tile_results: {source}")
    positive_rows = [
        row for row in rows
        if row.get("voluntary", {}).get("state") == "valid_mvt_with_features"
    ]
    # Process the densest point/cluster tiles first. This is still the full
    # positive seed set; ordering only makes early batches a useful validation
    # sample instead of starting at the western edge of the census bbox.
    positive_rows.sort(key=lambda row: (
        -sum(int(layer.get("feature_count", 0)) for layer in row.get("voluntary", {}).get("layers", [])),
        int(row["x"]), int(row["y"])
    ))
    seeds = [(int(row["x"]), int(row["y"])) for row in positive_rows]
    if not seeds:
        raise SystemExit("No voluntary-positive z9 seeds found in census artifact")
    return seeds, census.get("summary", {})


def make_session():
    retry = Retry(total=4, connect=4, read=3, status=3, backoff_factor=1,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    s = requests.Session()
    s.headers.update({"User-Agent": "Skog-SCA-national-voluntary-z12/1.0",
                      "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf, */*"})
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=3, pool_maxsize=3))
    return s


def decode_tile(x, y):
    url = URL.format(z=Z, x=x, y=y)
    try:
        r = make_session().get(url, timeout=TIMEOUT)
        raw = r.content
        base = {"http_status": r.status_code, "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                "url": url}
        if r.status_code == 404:
            return {**base, "state": "not_found_404", "layers": []}
        if r.status_code != 200:
            return {**base, "state": "http_error", "layers": []}
        try:
            decoded = mapbox_vector_tile.decode(raw)
            layers = []
            for name, obj in decoded.items():
                feats = obj.get("features", [])
                # Preserve source geometry and MVT properties in tile-local coordinates.
                layers.append({
                    "name": name,
                    "extent": obj.get("extent"),
                    "feature_count": len(feats),
                    "features": [{
                        "id": f.get("id"),
                        "type": (f.get("geometry") or {}).get("type"),
                        "geometry": f.get("geometry"),
                        "properties": f.get("properties") or {},
                    } for f in feats],
                })
            n = sum(x["feature_count"] for x in layers)
            return {**base, "state": "valid_mvt_with_features" if n else "valid_mvt_empty",
                    "layers": layers}
        except Exception as e:
            return {**base, "state": "decode_error", "error": str(e)[:240], "layers": []}
    except Exception as e:
        return {"state": "request_error", "error": str(e)[:240], "url": url, "layers": []}


def main():
    seeds, seed_summary = load_positive_seeds()
    batch = max(0, int(os.getenv("BATCH", "0")))
    batch_size = max(1, min(20, int(os.getenv("BATCH_SIZE", "4"))))
    radius = max(0, min(2, int(os.getenv("RADIUS", "1"))))
    start = batch * batch_size
    selected = seeds[start:start + batch_size]
    if not selected:
        raise SystemExit(f"Batch {batch} has no seeds; total seeds={len(seeds)}")
    n0 = 2 ** (Z - Z0)
    targets = set()
    for sx, sy in selected:
        for dx in range(n0):
            for dy in range(n0):
                x, y = sx*n0 + dx, sy*n0 + dy
                for nx in range(-radius, radius+1):
                    for ny in range(-radius, radius+1):
                        xx, yy = x+nx, y+ny
                        if 0 <= xx < 2**Z and 0 <= yy < 2**Z:
                            targets.add((xx, yy))
    targets = sorted(targets)
    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(decode_tile, x, y):(x,y) for x,y in targets}
        for i, future in enumerate(as_completed(futures), 1):
            x, y = futures[future]
            r = future.result()
            rows.append({"z": Z, "x": x, "y": y, **r})
            if i % 25 == 0 or i == len(futures):
                rows.sort(key=lambda q:(q["x"], q["y"]))
                payload = {
                    "purpose": "First tranche of national z12 voluntary polygon detail, expanded from z9 independent voluntary-positive seeds.",
                    "source": URL,
                    "zoom": Z,
                    "batch": batch,
                    "batch_size": batch_size,
                    "radius": radius,
                    "z9_positive_seed_count": len(seeds),
                    "seed_census_summary": seed_summary,
                    "selected_z9_seeds": [{"z":Z0,"x":x,"y":y} for x,y in selected],
                    "target_z12_tiles": len(targets),
                    "completed_z12_tiles": len(rows),
                    "tile_results": rows,
                    "interpretation": [
                        "Tile counts and feature records are not counts of unique voluntary areas.",
                        "Features retain source tile provenance; MVT geometry remains in tile-local coordinates.",
                        "A 404 is not proof that the geographic area lacks an avsättning.",
                        "Neighbor ring is used to reduce omission at tile edges; it does not establish complete parcel topology.",
                        "This is a batch of detailed source tiles, not yet a national inventory.",
                        "No deduplication, union, or area totals are asserted."
                    ]
                }
                OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))+"\n", encoding="utf-8")
                print(json.dumps({"completed":i,"total":len(targets),
                                  "states":dict(Counter(q["state"] for q in rows))}, ensure_ascii=False), flush=True)
    rows.sort(key=lambda q:(q["x"],q["y"]))
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"batch":batch,"positive_seed_count":len(seeds),"selected_seeds":len(selected),"target_tiles":len(targets),
                      "states":dict(Counter(q["state"] for q in rows)),
                      "feature_records":sum(sum(l["feature_count"] for l in q.get("layers",[])) for q in rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
