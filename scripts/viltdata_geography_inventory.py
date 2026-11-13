#!/usr/bin/env python3
"""Inventory public Viltdata geography endpoints. Python 3.10+, stdlib only."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://rapport.viltdata.se/umbraco/api"
ENDPOINTS = {
    "counties": ("StatisticsApi/GetCounties", None),
    "afos": ("AfoApi/GetAllAfosByCountyId", "countyId"),
    "parts": ("PartAfoApi/GetPartAfosByAfoID", "afoId"),
    "areas": ("HuntAreaApi/GetHuntAreasByPartAfoId", "partAfoId"),
}

def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def fetch(level, parent_id, out, attempts=3):
    path, param = ENDPOINTS[level]
    url = BASE + "/" + path
    if param:
        url += "?" + urllib.parse.urlencode({param: parent_id})
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Viltdata-public-metadata-inventory/0.1"})
    last_error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                body = response.read()
                status = response.status
                ctype = response.headers.get("Content-Type", "")
            if "json" not in ctype.lower():
                raise ValueError("Unexpected content type: " + ctype)
            payload = json.loads(body)
            if not isinstance(payload, list):
                raise ValueError("Expected JSON array")
            for record in payload:
                if not isinstance(record, dict) or not isinstance(record.get("id"), int) or not isinstance(record.get("title" if level != "counties" else "name", record.get("title")), str):
                    # Counties may use a different naming convention: preserve raw and validate IDs only.
                    if not isinstance(record, dict) or not isinstance(record.get("id"), int):
                        raise ValueError("Missing integer id in " + level)
            key = "root" if parent_id is None else str(parent_id)
            target = out / "raw" / level / (key + ".json")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            return payload, {"level": level, "parent_id": parent_id, "url": url, "retrieved_at": utcnow(),
                             "http_status": status, "content_type": ctype, "count": len(payload),
                             "sha256": hashlib.sha256(body).hexdigest(), "file": str(target.relative_to(out)),
                             "status": "ok"}
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
    return None, {"level": level, "parent_id": parent_id, "url": url, "retrieved_at": utcnow(),
                  "status": "error", "error": last_error}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/viltdata/geography-inventory")
    ap.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls")
    ap.add_argument("--max-counties", type=int, default=0, help="Limit for smoke tests; 0 = all")
    args = ap.parse_args()
    out = pathlib.Path(args.output) / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"started_at": utcnow(), "schema_version": 1, "source": BASE, "requests": [],
                "relationships": [], "issues": [], "complete": False}
    seen = {k: {} for k in ENDPOINTS}
    def collect(level, parent, parent_level=None):
        data, entry = fetch(level, parent, out)
        manifest["requests"].append(entry)
        if data is None:
            manifest["issues"].append({"type": "request_failed", "level": level, "parent_id": parent})
            return []
        ids = set()
        for record in data:
            ident = record["id"]
            if ident in ids:
                manifest["issues"].append({"type": "duplicate_in_response", "level": level, "id": ident, "parent_id": parent})
            ids.add(ident)
            if ident in seen[level] and seen[level][ident] != record:
                manifest["issues"].append({"type": "conflicting_id_metadata", "level": level, "id": ident})
            seen[level][ident] = record
            if parent_level:
                manifest["relationships"].append({"parent_level": parent_level, "parent_id": parent,
                                                  "child_level": level, "child_id": ident})
        time.sleep(max(args.delay, 0))
        return data
    counties = collect("counties", None)
    if args.max_counties > 0:
        counties = counties[:args.max_counties]
    for county in counties:
        for afo in collect("afos", county["id"], "counties"):
            for part in collect("parts", afo["id"], "afos"):
                collect("areas", part["id"], "parts")
    manifest["finished_at"] = utcnow()
    manifest["counts"] = {level: len(records) for level, records in seen.items()}
    manifest["complete"] = bool(manifest["requests"]) and not manifest["issues"] and args.max_counties == 0
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "counts": manifest["counts"],
                      "requests": len(manifest["requests"]), "issues": len(manifest["issues"]),
                      "complete": manifest["complete"]}, ensure_ascii=False, indent=2))
    return 0 if not manifest["issues"] else 1

if __name__ == "__main__":
    sys.exit(main())
