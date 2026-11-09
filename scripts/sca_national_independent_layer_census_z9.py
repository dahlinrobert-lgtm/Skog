#!/usr/bin/env python3
"""Independent national z9 census of SCA ownership and voluntary MVT layers.

Both layers are queried for every tile in the broad Sweden bbox. This avoids
using the ownership layer as a gate for voluntary-set-aside discovery.
Responses are summarized (not geometries); failures remain explicit and the
JSON checkpoint is updated throughout the run.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, threading, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
import mapbox_vector_tile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

Z = 9
BBOX = {"west": 10.5, "south": 55.0, "east": 24.5, "north": 69.5}
LAYERS = {
    "ownership": "https://olga.scaskog.com/map/sca_mark/{z}/{x}/{y}.pbf",
    "voluntary": "https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf",
}
WORKERS = 2
TIMEOUT = (20, 60)
OUT = Path("sca-national-independent-layer-census-z9.json")
LOCAL = threading.local()


def xyz(lon, lat, z):
    n = 2 ** z
    lat = max(-85.05112878, min(85.05112878, lat))
    return (int((lon + 180) / 360 * n),
            int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n))


def tile_range():
    x0, y1 = xyz(BBOX["west"], BBOX["south"], Z)
    x1, y0 = xyz(BBOX["east"], BBOX["north"], Z)
    n = 2 ** Z
    return [(x, y) for x in range(max(0, x0), min(n - 1, x1) + 1)
                   for y in range(max(0, y0), min(n - 1, y1) + 1)]


def session():
    if getattr(LOCAL, "session", None) is not None:
        return LOCAL.session
    retry = Retry(total=4, connect=4, read=3, status=3,
                  backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Skog-SCA-independent-national-census/1.0",
        "Accept": "application/vnd.mapbox-vector-tile, application/x-protobuf, */*",
    })
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=2))
    LOCAL.session = s
    return s


def fetch_one(sess, layer_key, x, y):
    url = LAYERS[layer_key].format(z=Z, x=x, y=y)
    try:
        r = sess.get(url, timeout=TIMEOUT)
        raw = r.content
        base = {"status": r.status_code, "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                "content_type": r.headers.get("Content-Type"),
                "server": r.headers.get("Server"),
                "body_preview": raw[:240].decode("utf-8", errors="replace") if r.status_code != 200 else None}
        if r.status_code == 404:
            return {**base, "state": "not_found_404", "layers": []}
        if r.status_code != 200:
            return {**base, "state": "http_error", "layers": []}
        try:
            decoded = mapbox_vector_tile.decode(raw)
            infos = []
            for name, layer in decoded.items():
                features = layer.get("features", [])
                types = Counter((f.get("geometry") or {}).get("type", "unknown") for f in features)
                keys = sorted({k for f in features for k in (f.get("properties") or {})})
                infos.append({"name": name, "feature_count": len(features),
                              "geometry_types": dict(types), "property_keys": keys})
            n = sum(v["feature_count"] for v in infos)
            return {**base, "state": "valid_mvt_with_features" if n else "valid_mvt_empty",
                    "layers": infos}
        except Exception as e:
            return {**base, "state": "decode_error", "error": str(e)[:240], "layers": []}
    except Exception as e:
        return {"state": "request_error", "error": str(e)[:240], "layers": []}


def write_checkpoint(rows, total, complete, out_path=OUT):
    def summary():
        result = {"bbox": BBOX, "zoom": Z, "tiles_in_bbox": total,
                  "tiles_completed": complete}
        for key in LAYERS:
            states = Counter(row[key].get("state", "pending") for row in rows)
            result[key + "_states"] = dict(states)
            result[key + "_feature_records"] = sum(
                sum(layer["feature_count"] for layer in row[key].get("layers", []))
                for row in rows)
            result[key + "_tiles_with_features"] = sum(
                row[key].get("state") == "valid_mvt_with_features" for row in rows)
        return result
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "purpose": "Independent national z9 census: ownership and voluntary layers queried for every tile, not ownership-gated.",
        "source_layers": LAYERS,
        "summary": summary(),
        "interpretation": [
            "Both layers were queried independently for every tile in the bbox.",
            "HTTP 404 means the tile endpoint returned not found; it is not proof of no SCA land or no set-aside.",
            "Valid empty MVT means no features were returned for that layer and tile at z9.",
            "Feature counts are tile feature records, not unique parcels or unique voluntary areas.",
            "z9 is a low zoom screening level; it is not the final polygon inventory.",
            "The broad bbox includes sea and some neighboring-country areas; it is not a legal SCA ownership boundary.",
            "No geometries are merged or deduplicated in this census.",
        ],
        "tile_results": rows,
    }
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, out_path)
    return payload["summary"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args()
    tiles = tile_range()
    rows = []
    completed = 0
    def task(xy):
        x, y = xy
        s = session()
        return {"z": Z, "x": x, "y": y,
                "ownership": fetch_one(s, "ownership", x, y),
                "voluntary": fetch_one(s, "voluntary", x, y)}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(task, xy) for xy in tiles]
        for future in as_completed(futures):
            rows.append(future.result())
            completed += 1
            if completed % 25 == 0 or completed == len(tiles):
                rows.sort(key=lambda r: (r["x"], r["y"]))
                summary = write_checkpoint(rows, len(tiles), completed, args.out)
                print(json.dumps({"progress": completed, **summary}, ensure_ascii=False), flush=True)
    rows.sort(key=lambda r: (r["x"], r["y"]))
    print(json.dumps(write_checkpoint(rows, len(tiles), completed, args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
