#!/usr/bin/env python3
"""Create immutable public Viltdata harvest (kill) statistics snapshots.

Fetches the statistics model, all kill-enabled species, one national series and
one series per county. Raw JSON is retained unchanged with a manifest and SHA-256.
Python 3.10+, standard library only.
"""
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
MODEL_URL = BASE + "/StatisticsApi/GetStatisticsModel"
COUNTIES_URL = BASE + "/StatisticsApi/GetCounties"
STATS_URL = BASE + "/StatisticsApi/GetStatistics"
USER_AGENT = "Skog-Viltdata-public-kill-snapshot/0.1"


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def request_json(url, timeout=60, attempts=3):
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    error = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "")
            if "json" not in content_type.lower():
                raise ValueError(f"Expected JSON, received Content-Type={content_type!r}")
            payload = json.loads(body.decode("utf-8-sig"))
            return body, payload, status, content_type
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            error = str(exc)
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed after {attempts} attempts: {url}: {error}")


def write_raw(run_dir, relative_path, body):
    path = run_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {
        "file": relative_path.as_posix(),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def get_start_year(start_years, keys, fallback):
    if not isinstance(start_years, dict):
        return fallback
    # GetStatisticsModel nests harvest start years under startYears.avskjutning.
    harvest_years = start_years.get("avskjutning", start_years)
    if not isinstance(harvest_years, dict):
        return fallback
    for key in keys:
        value = harvest_years.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return fallback


def build_statistics_url(species, start_year, end_year, county=None):
    params = [
        ("chartType", "line"),
        ("StartYear", str(start_year)),
        ("EndYear", str(end_year)),
        ("StatisticsReportType", "kill"),
        ("AfoDTOS", ""),
        ("PartAfos", ""),
        ("HuntAreas", ""),
        ("Krets", ""),
        ("ExcelReportTitle", "Avskjutning"),
        ("ShowIncompleteColumn", "true"),
    ]
    for index, item in enumerate(species):
        params.extend([
            (f"Species[{index}][ID]", str(item["id"])),
            (f"Species[{index}][Name]", item["name"]),
        ])
    if county is not None:
        params.extend([
            ("Counties[0][id]", str(county["id"])),
            ("Counties[0][name]", county["name"]),
        ])
    return STATS_URL + "?" + urllib.parse.urlencode(params)


def validate_statistics(payload):
    if not isinstance(payload, dict):
        raise ValueError("Statistics response must be a JSON object")
    labels = payload.get("labels")
    datasets = payload.get("dataSets")
    if not isinstance(labels, list):
        raise ValueError("Statistics response has no labels array")
    if not isinstance(datasets, list):
        raise ValueError("Statistics response has no dataSets array")
    if not labels or not datasets:
        raise ValueError("Statistics response has empty labels or dataSets")
    for dataset in datasets:
        if not isinstance(dataset, dict) or not isinstance(dataset.get("data"), list):
            raise ValueError("Invalid dataSets entry")
        if len(dataset["data"]) != len(labels):
            raise ValueError("Dataset length does not match labels length")
    return {"labels": len(labels), "datasets": len(datasets)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/viltdata/kill-statistics")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between statistics requests")
    parser.add_argument("--max-counties", type=int, default=0, help="Limit county requests for a pilot; 0 = all")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = pathlib.Path(args.output) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": utc_now(),
        "source": "Viltdata public StatisticsApi",
        "report_type": "kill",
        "status": "running",
        "complete": False,
        "requests": [],
        "species_count": 0,
        "county_count": 0,
        "errors": [],
        "notes": [
            "Reported harvest statistics; not a population census.",
            "Null values are preserved and are never converted to zero.",
            "Only public aggregate statistics are requested; no login-protected hunt-team data.",
        ],
    }

    try:
        model_body, model, model_status, model_type = request_json(MODEL_URL, args.timeout)
        model_file = write_raw(run_dir, pathlib.Path("raw/model/statistics-model.json"), model_body)
        manifest["requests"].append({
            "kind": "statistics_model", "url": MODEL_URL, "retrieved_at": utc_now(),
            "http_status": model_status, "content_type": model_type, **model_file,
        })
        if not isinstance(model, dict) or not isinstance(model.get("species"), list):
            raise ValueError("Statistics model has no species array")

        species = []
        for item in model["species"]:
            if not isinstance(item, dict):
                continue
            if item.get("enableForKill") is True and isinstance(item.get("id"), int) and isinstance(item.get("name"), str):
                species.append({"id": item["id"], "name": item["name"]})
        species.sort(key=lambda item: item["id"])
        if not species:
            raise ValueError("No kill-enabled species found in statistics model")
        manifest["species_count"] = len(species)
        manifest["species"] = species

        county_body, counties, county_status, county_type = request_json(COUNTIES_URL, args.timeout)
        county_file = write_raw(run_dir, pathlib.Path("raw/model/counties.json"), county_body)
        manifest["requests"].append({
            "kind": "counties", "url": COUNTIES_URL, "retrieved_at": utc_now(),
            "http_status": county_status, "content_type": county_type, **county_file,
        })
        if not isinstance(counties, list):
            raise ValueError("County response must be a JSON array")
        counties = [
            {"id": item["id"], "name": item.get("name", item.get("title"))}
            for item in counties
            if isinstance(item, dict) and isinstance(item.get("id"), int)
            and isinstance(item.get("name", item.get("title")), str)
        ]
        counties.sort(key=lambda item: item["id"])
        if args.max_counties > 0:
            counties = counties[:args.max_counties]
        manifest["county_count"] = len(counties)

        start_years = model.get("startYears", {})
        national_start = get_start_year(start_years, ["Nationellt", "National", "national"], 1939)
        county_start = get_start_year(start_years, ["Län", "Lan", "County", "county"], 1960)
        active_years = model.get("activeYears", [])
        end_year = max((year for year in active_years if isinstance(year, int)), default=dt.datetime.now(dt.timezone.utc).year)
        manifest["period"] = {"national_start_year": national_start, "county_start_year": county_start, "end_year": end_year}

        scopes = [{"scope": "national", "county": None, "start_year": national_start}]
        scopes.extend({"scope": f"county-{county['id']}", "county": county, "start_year": county_start} for county in counties)

        successes = 0
        for scope in scopes:
            url = build_statistics_url(species, scope["start_year"], end_year, scope["county"])
            entry = {
                "kind": "statistics", "scope": scope["scope"], "county": scope["county"],
                "url": url, "retrieved_at": utc_now(), "status": "pending",
            }
            try:
                body, payload, status, content_type = request_json(url, args.timeout)
                validation = validate_statistics(payload)
                relative = pathlib.Path("raw/statistics") / f"{scope['scope']}.json"
                file_info = write_raw(run_dir, relative, body)
                entry.update({
                    "status": "ok", "http_status": status, "content_type": content_type,
                    "labels_count": validation["labels"], "datasets_count": validation["datasets"],
                    **file_info,
                })
                successes += 1
            except Exception as exc:
                entry.update({"status": "error", "error": str(exc)})
                manifest["errors"].append({"scope": scope["scope"], "error": str(exc)})
            manifest["requests"].append(entry)
            time.sleep(max(args.delay, 0))

        expected = len(scopes)
        manifest["complete"] = successes == expected and not manifest["errors"] and args.max_counties == 0
        manifest["status"] = "complete" if manifest["complete"] else "partial"
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["errors"].append({"scope": "setup", "error": str(exc)})

    manifest["finished_at"] = utc_now()
    manifest["statistics_requests_ok"] = sum(
        1 for item in manifest["requests"] if item.get("kind") == "statistics" and item.get("status") == "ok"
    )
    manifest["statistics_requests_expected"] = 1 + manifest["county_count"]
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_dir": str(run_dir), "status": manifest["status"], "complete": manifest["complete"],
        "species_count": manifest["species_count"], "county_count": manifest["county_count"],
        "statistics_requests_ok": manifest["statistics_requests_ok"],
        "statistics_requests_expected": manifest["statistics_requests_expected"],
        "errors": manifest["errors"],
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
