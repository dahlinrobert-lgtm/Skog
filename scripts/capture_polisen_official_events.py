from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

API_URL = "https://polisen.se/api/events"
APP_NAME = "Skogskoll-Police-Source-Evaluation/1.0"
SOURCE_ID = "polisen.events_official_api"


def validate_payload(payload: object) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError("Unexpected Police API schema: expected a JSON array")
    if not payload:
        raise ValueError("Police API returned an empty array; refusing to create a misleading baseline")
    seen: set[str] = set()
    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} is not a JSON object")
        event_id = record.get("id")
        if event_id is None or str(event_id).strip() == "":
            raise ValueError(f"Record {index} has no event id")
        key = str(event_id)
        if key in seen:
            raise ValueError(f"Duplicate event id in one response: {key}")
        seen.add(key)
    return payload


def build_snapshot(payload: object, retrieved_at: str, request_url: str) -> dict:
    records = validate_payload(payload)
    county_counts: dict[str, int] = {}
    for record in records:
        location = record.get("location")
        county = location.get("name") if isinstance(location, dict) else None
        if county:
            county_counts[str(county)] = county_counts.get(str(county), 0) + 1
    return {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "source_name": "Polismyndigheten – officiellt API över polisens händelser",
        "retrieved_at": retrieved_at,
        "request_url": request_url,
        "record_count": len(records),
        "norrbotten_record_count": county_counts.get("Norrbottens län", 0),
        "county_counts": dict(sorted(county_counts.items())),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture one immutable evaluation snapshot from the official Police events API."
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    headers = {
        "Accept": "application/json",
        "User-Agent": f"{APP_NAME} (GitHub Actions scheduled source evaluation)",
    }
    response = requests.get(API_URL, headers=headers, timeout=45)
    response.raise_for_status()
    payload = response.json()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    snapshot = build_snapshot(payload, retrieved_at, response.url or API_URL)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"source_id={SOURCE_ID} status=complete records={snapshot['record_count']} "
        f"norrbotten_records={snapshot['norrbotten_record_count']} retrieved_at={retrieved_at}"
    )


if __name__ == "__main__":
    main()
