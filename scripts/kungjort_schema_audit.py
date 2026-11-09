#!/usr/bin/env python3
"""Export a value-free schema inventory from private Kungjort Azure batches."""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

ACCOUNT = "stskogkolldata"
SOURCES = (
    ("metadata", "kungjort/index/bootstrap-live/", "listing_metadata"),
    ("metadata", "kungjort/index/reclassified-v2/", "reclassified_metadata"),
    ("kungjort-raw", "bootstrap-live/", "document_details"),
    ("kungjort-raw", "bootstrap/", "legacy_document_details"),
    ("kungjort-changes", "changes-live/", "change_records"),
)
SAFE_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def safe_key(key: object) -> str:
    value = str(key)
    return value if SAFE_KEY.fullmatch(value) else "<dynamic-key>"


def value_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "other"


def summarize_records(records: list[dict], source: str) -> dict:
    fields = defaultdict(Counter)
    records_with_field = Counter()
    record_types = Counter()

    def visit(value: object, path: str, seen: set[str]) -> None:
        kind = value_type(value)
        fields[path][kind] += 1
        seen.add(path)
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{safe_key(key)}" if path else safe_key(key)
                visit(child, child_path, seen)
        elif isinstance(value, list):
            for child in value:
                visit(child, f"{path}[]", seen)

    for record in records:
        if not isinstance(record, dict):
            continue
        record_types[str(record.get("record_type", "unknown"))] += 1
        seen_fields: set[str] = set()
        visit(record, "", seen_fields)
        records_with_field.update(seen_fields)

    return {
        "source": source,
        "records_reviewed": sum(record_types.values()),
        "record_type_counts": dict(sorted(record_types.items())),
        "fields": [
            {
                "path": path,
                "records_with_field": records_with_field[path],
                "value_occurrences": sum(counts.values()),
                "observed_types": dict(sorted(counts.items())),
            }
            for path, counts in sorted(fields.items())
        ],
    }


def read_jsonl_gzip(payload: bytes) -> list[dict]:
    rows = []
    for line in gzip.decompress(payload).decode("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_report(service: BlobServiceClient, max_batches: int) -> dict:
    sections = []
    total_batches = 0
    for container, prefix, label in SOURCES:
        client = service.get_container_client(container)
        names = sorted(
            blob.name for blob in client.list_blobs(name_starts_with=prefix)
            if blob.name.endswith(".jsonl.gz")
        )
        selected = names[:max_batches]
        records = []
        for name in selected:
            payload = service.get_blob_client(container=container, blob=name).download_blob().readall()
            records.extend(read_jsonl_gzip(payload))
        sections.append(summarize_records(records, label))
        total_batches += len(selected)

    return {
        "schema_version": 1,
        "report_type": "kungjort_value_free_schema_inventory",
        "batches_reviewed": total_batches,
        "sections": sections,
        "privacy_note": (
            "Schema only: field paths, observed JSON types and counts. "
            "No field values, IDs, titles, URLs, text, examples or source records."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=20)
    parser.add_argument("--output", default="schema-report-export/schema-inventory.json")
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 500:
        parser.error("--max-batches must be between 1 and 500")

    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{ACCOUNT}.blob.core.windows.net",
        credential=credential,
    )
    try:
        report = build_report(service, args.max_batches)
        if not report["sections"] or not any(s["records_reviewed"] for s in report["sections"]):
            raise RuntimeError("No readable Kungjort records found in the selected Azure prefixes")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        print(
            f"Schema inventory exported: batches={report['batches_reviewed']}, "
            f"sections={len(report['sections'])}, records="
            f"{sum(s['records_reviewed'] for s in report['sections'])}"
        )
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
