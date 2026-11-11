from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

FIELDS = (
    "published_datetime", "type_original", "headline", "description", "content",
    "title_location", "location_string", "administrative_area_level_1",
    "administrative_area_level_2", "latitude", "longitude",
    "external_source_link", "permalink", "is_summary",
)


def iter_records(text: str) -> Iterator[dict]:
    """Decode concatenated JSON objects separated by whitespace or literal \\n."""
    decoder = json.JSONDecoder()
    position = 0
    while position < len(text):
        while position < len(text):
            if text[position].isspace():
                position += 1
            elif text.startswith(r"\\n", position):
                position += 2
            else:
                break
        if position >= len(text):
            return
        record, next_position = decoder.raw_decode(text, position)
        if not isinstance(record, dict):
            raise ValueError(f"Expected JSON object at character {position}")
        yield record
        if next_position <= position:
            raise ValueError("JSON decoder made no progress")
        position = next_position


def _first(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def normalize_record(record: dict) -> dict:
    event = record.get("event") if isinstance(record.get("event"), dict) else record
    event_id = str(_first(record.get("event_id"), event.get("id")))
    retrieved_at = str(record.get("retrieved_at") or "")
    if not event_id or not retrieved_at:
        raise ValueError("Record is missing event_id or retrieved_at")

    published = _first(
        event.get("pubdate_iso8601"), event.get("published_at"),
        event.get("published_datetime"), event.get("date"),
    )
    try:
        published_dt = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
        if published_dt.tzinfo is None:
            published_dt = published_dt.replace(tzinfo=timezone.utc)
        published = published_dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        published = str(published or "")

    payload_sha = str(record.get("payload_sha256") or "")
    if not payload_sha:
        canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    row = {
        "event_id": event_id,
        "retrieved_at": retrieved_at,
        "payload_sha256": payload_sha,
        "published_datetime": published,
        "type_original": _first(event.get("title_type"), event.get("type")),
        "headline": event.get("headline") or "",
        "description": _first(event.get("description"), event.get("content_teaser")),
        "content": event.get("content") or "",
        "title_location": event.get("title_location") or "",
        "location_string": _first(event.get("location_string"), event.get("locations")),
        "administrative_area_level_1": event.get("administrative_area_level_1") or "",
        "administrative_area_level_2": event.get("administrative_area_level_2") or "",
        "latitude": _first(event.get("lat"), event.get("latitude")),
        "longitude": _first(event.get("lng"), event.get("longitude")),
        "external_source_link": event.get("external_source_link") or "",
        "permalink": event.get("permalink") or "",
        "is_summary": str(
            str(_first(event.get("title_type"), event.get("type"))).casefold().startswith("sammanfattning")
        ).lower(),
    }
    # Legacy CSV snapshots already contain a normalized is_summary flag.
    if event.get("is_summary") not in (None, ""):
        row["is_summary"] = str(event["is_summary"]).lower()
    return {key: _csv_value(value) for key, value in row.items()}


def _csv_value(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "" if value is None else str(value)


def build_history(records: list[dict]) -> tuple[list[dict], list[dict], dict]:
    normalized = [normalize_record(record) for record in records]
    normalized.sort(key=lambda row: (
        row["event_id"], row["retrieved_at"], row["payload_sha256"]
    ))

    by_event: dict[str, list[dict]] = defaultdict(list)
    for row in normalized:
        by_event[row["event_id"]].append(row)

    version_rows: list[dict] = []
    change_rows: list[dict] = []
    version_histogram: Counter = Counter()
    duplicate_versions = 0

    for event_id in sorted(by_event):
        versions = by_event[event_id]
        previous = None
        seen_hashes: set[str] = set()
        version_number = 0
        for row in versions:
            if row["payload_sha256"] in seen_hashes:
                duplicate_versions += 1
                continue
            seen_hashes.add(row["payload_sha256"])
            version_number += 1
            version = {**row, "version_number": version_number}
            version_rows.append(version)

            if previous is None:
                change_rows.append({
                    "event_id": event_id,
                    "from_retrieved_at": "",
                    "to_retrieved_at": row["retrieved_at"],
                    "from_payload_sha256": "",
                    "to_payload_sha256": row["payload_sha256"],
                    "change_type": "first_seen",
                    "changed_fields": "first_observation",
                    "before_values_json": "{}",
                    "after_values_json": json.dumps(
                        {field: row[field] for field in FIELDS},
                        ensure_ascii=False, sort_keys=True,
                    ),
                })
            else:
                changed = [
                    field for field in FIELDS
                    if previous.get(field, "") != row.get(field, "")
                ]
                if previous["payload_sha256"] != row["payload_sha256"]:
                    before = {field: previous.get(field, "") for field in changed}
                    after = {field: row.get(field, "") for field in changed}
                    change_rows.append({
                        "event_id": event_id,
                        "from_retrieved_at": previous["retrieved_at"],
                        "to_retrieved_at": row["retrieved_at"],
                        "from_payload_sha256": previous["payload_sha256"],
                        "to_payload_sha256": row["payload_sha256"],
                        "change_type": "updated" if changed else "payload_changed_unmapped",
                        "changed_fields": ";".join(changed),
                        "before_values_json": json.dumps(before, ensure_ascii=False, sort_keys=True),
                        "after_values_json": json.dumps(after, ensure_ascii=False, sort_keys=True),
                    })
            previous = row
        version_histogram[len(seen_hashes)] += 1

    version_rows.sort(key=lambda row: (row["retrieved_at"], row["event_id"], row["version_number"]))
    change_rows.sort(key=lambda row: (row["to_retrieved_at"], row["event_id"]))
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_record_count": len(records),
        "unique_event_id_count": len(by_event),
        "distinct_event_version_count": len(version_rows),
        "duplicate_payload_version_count": duplicate_versions,
        "event_ids_with_multiple_versions": sum(1 for count in version_histogram.elements() if count > 1),
        "version_count_histogram": {str(k): v for k, v in sorted(version_histogram.items())},
        "change_transition_count": len(change_rows),
        "field_change_transition_count": sum(1 for row in change_rows if row["change_type"] == "updated"),
        "interpretation": (
            "Only changed/new versions written by the collector are represented. "
            "Absence from a later API response is not evidence that an event was deleted. "
            "Field changes are limited to the normalized fields listed in the version table."
        ),
    }
    return version_rows, change_rows, summary


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build event-version and field-change tables from a verified restore.")
    parser.add_argument("--input", type=Path, required=True, help="Verified restored_raw_events.jsonl.gz")
    parser.add_argument("--output-dir", type=Path, default=Path("police-event-history"))
    args = parser.parse_args()
    records = []
    with gzip.open(args.input, "rt", encoding="utf-8") as stream:
        for physical_line, line in enumerate(stream, start=1):
            try:
                records.extend(iter_records(line))
            except Exception as exc:
                raise RuntimeError(f"Cannot parse restored stream at physical line {physical_line}: {exc}") from exc
    versions, changes, summary = build_history(records)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    version_fields = ["event_id", "version_number", "retrieved_at", "payload_sha256", *FIELDS]
    change_fields = [
        "event_id", "from_retrieved_at", "to_retrieved_at",
        "from_payload_sha256", "to_payload_sha256", "change_type",
        "changed_fields", "before_values_json", "after_values_json",
    ]
    write_csv(args.output_dir / "event_versions.csv", versions, version_fields)
    write_csv(args.output_dir / "event_changes.csv", changes, change_fields)
    (args.output_dir / "history_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"history_analysis=passed source_records={summary['source_record_count']} "
        f"unique_event_ids={summary['unique_event_id_count']} "
        f"distinct_versions={summary['distinct_event_version_count']} "
        f"change_transitions={summary['change_transition_count']}"
    )


if __name__ == "__main__":
    main()
