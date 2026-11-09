#!/usr/bin/env python3
"""Audit Kungjort case-reference coverage by planning-selection class.

Reads the latest private selection index and archived detail records. It writes
per-document diagnostics only to private Azure storage; GitHub receives aggregate
coverage and cross-document reference-frequency counts only.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACCOUNT = "stskogkolldata"
METADATA_CONTAINER = "metadata"
SELECTION_PREFIX = "kungjort/selection/v1/"
DETAIL_SOURCES = (
    ("kungjort-raw", "bootstrap-live/", "document_details", 1),
    ("kungjort-raw", "bootstrap/", "legacy_document_details", 2),
)
REFERENCE_FIELDS = (
    "case_id", "case_dnr", "normalized_dnr", "section_dnr",
    "decision_id", "diarieplan_kod", "section_id",
)
SCHEMA_VERSION = 1


def read_jsonl_gzip(payload: bytes) -> list[dict]:
    rows = []
    for line in gzip.decompress(payload).decode("utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def encode_jsonl_gzip(records: list[dict]) -> bytes:
    import io
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0) as stream:
        for record in records:
            stream.write((json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
    return output.getvalue()


def document_id(record: dict) -> str | None:
    value = record.get("document_id") or record.get("id")
    if value is None and isinstance(record.get("metadata"), dict):
        value = record["metadata"].get("id") or record["metadata"].get("document_id")
    if value is None and isinstance(record.get("list_record"), dict):
        value = record["list_record"].get("id") or record["list_record"].get("document_id")
    return str(value) if value is not None and str(value).strip() else None


def normalize_reference(value: Any) -> str | None:
    if not isinstance(value, (str, int)):
        return None
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    return " ".join(text.split()) or None


def _add(values: dict[str, set[str]], field: str, value: Any) -> None:
    normalized = normalize_reference(value)
    if normalized:
        values[field].add(normalized)


def extract_reference_values(detail: dict) -> dict[str, set[str]]:
    """Extract only known structured reference fields; no free-text search."""
    values = {field: set() for field in REFERENCE_FIELDS}
    sections = detail.get("sections")
    if not isinstance(sections, list):
        return values
    for section in sections:
        if not isinstance(section, dict):
            continue
        cases = section.get("cases")
        if isinstance(cases, list):
            for case in cases:
                if not isinstance(case, dict):
                    continue
                _add(values, "case_id", case.get("case_id"))
                _add(values, "case_dnr", case.get("dnr"))
                _add(values, "normalized_dnr", case.get("normalized_dnr"))
        section_dnrs = section.get("dnr")
        if isinstance(section_dnrs, list):
            for value in section_dnrs:
                _add(values, "section_dnr", value)
        else:
            _add(values, "section_dnr", section_dnrs)
        for field in ("decision_id", "diarieplan_kod", "section_id"):
            _add(values, field, section.get(field))
    return values


def _latest_selection_blob(service: Any) -> tuple[str, str]:
    container = service.get_container_client(METADATA_CONTAINER)
    names = sorted(
        item.name for item in container.list_blobs(name_starts_with=SELECTION_PREFIX)
        if item.name.endswith("/document-selection.jsonl.gz")
    )
    if not names:
        raise RuntimeError("No private Kungjort selection index found")
    name = names[-1]
    parts = name.split("/")
    if len(parts) < 5:
        raise RuntimeError("Unexpected private selection index path")
    return parts[3], name


def build_reference_audit(service: Any, max_batches: int, run_id: str) -> tuple[list[dict], dict]:
    selection_container = service.get_blob_client(container=METADATA_CONTAINER, blob=SELECTION_PREFIX + run_id + "/document-selection.jsonl.gz")
    selection_rows = read_jsonl_gzip(selection_container.download_blob().readall())
    selected = {
        str(row["document_id"]): row
        for row in selection_rows
        if row.get("document_id") is not None
    }
    if not selected:
        raise RuntimeError("Private selection index contains no document rows")

    details: dict[str, dict] = {}
    source_batches_available = Counter()
    source_batches_reviewed = Counter()
    source_scan_truncated = {}
    for container_name, prefix, kind, _precedence in DETAIL_SOURCES:
        container = service.get_container_client(container_name)
        names = sorted(
            item.name for item in container.list_blobs(name_starts_with=prefix)
            if item.name.endswith(".jsonl.gz")
        )
        source_batches_available[kind] = len(names)
        source_scan_truncated[kind] = len(names) > max_batches
        names = names[:max_batches]
        source_batches_reviewed[kind] = len(names)
        for name in names:
            payload = service.get_blob_client(container=container_name, blob=name).download_blob().readall()
            for record in read_jsonl_gzip(payload):
                doc_id = document_id(record)
                detail = record.get("detail")
                if doc_id in selected and isinstance(detail, dict) and detail:
                    # Sources are visited in precedence order; preserve the first detail.
                    details.setdefault(doc_id, detail)

    per_document = []
    class_totals: dict[str, Counter] = defaultdict(Counter)
    reference_documents: dict[str, Counter] = defaultdict(Counter)
    reference_frequency: dict[str, Counter] = defaultdict(Counter)
    for doc_id, selection in sorted(selected.items()):
        priority = str((selection.get("selection") or {}).get("priority", "unknown"))
        detail = details.get(doc_id, {})
        values = extract_reference_values(detail)
        counts = {field: len(found) for field, found in values.items()}
        totals = class_totals[priority]
        totals["documents"] += 1
        totals["documents_with_detail"] += bool(detail)
        totals["documents_with_any_reference"] += any(values.values())
        for field, found in values.items():
            if found:
                reference_documents[priority][field] += 1
                reference_frequency[field].update(found)
        per_document.append({
            "record_type": "kungjort_reference_coverage",
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "document_id": doc_id,
            "priority": priority,
            "selection_class": (selection.get("selection") or {}).get("selection_class"),
            "has_detail_record": bool(detail),
            "reference_value_counts": counts,
            "has_any_reference": any(values.values()),
        })

    by_priority = {}
    for priority in sorted(class_totals):
        totals = class_totals[priority]
        by_priority[priority] = {
            "documents": totals["documents"],
            "documents_with_detail": totals["documents_with_detail"],
            "detail_coverage_pct": round(100 * totals["documents_with_detail"] / totals["documents"], 2) if totals["documents"] else 0,
            "documents_with_any_reference": totals["documents_with_any_reference"],
            "reference_coverage_pct": round(100 * totals["documents_with_any_reference"] / totals["documents"], 2) if totals["documents"] else 0,
            "documents_with_reference_by_field": dict(sorted(reference_documents[priority].items())),
        }

    shared = {}
    for field in REFERENCE_FIELDS:
        frequencies = reference_frequency[field]
        repeated = [count for count in frequencies.values() if count >= 2]
        shared[field] = {
            "unique_reference_values": len(frequencies),
            "reference_values_shared_by_multiple_documents": len(repeated),
            "documents_in_shared_reference_groups": sum(count for count in repeated),
            "maximum_documents_per_reference": max(frequencies.values(), default=0),
        }

    private_blob = f"kungjort/relationship-audit/v{SCHEMA_VERSION}/{run_id}/document-reference-coverage.jsonl.gz"
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "kungjort_planning_reference_coverage",
        "selection_run_id": run_id,
        "selection_documents": len(selected),
        "documents_with_detail_any_class": len(details),
        "detail_source_batches_available": dict(sorted(source_batches_available.items())),
        "detail_source_batches_reviewed": dict(sorted(source_batches_reviewed.items())),
        "detail_source_scan_truncated": dict(sorted(source_scan_truncated.items())),
        "coverage_by_priority": by_priority,
        "cross_document_reference_frequency": shared,
        "private_document_audit_blob": private_blob,
        "privacy_note": "Aggregate only. No document IDs, reference values, titles, municipality values, URLs, text or examples.",
    }
    return per_document, aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=2000)
    parser.add_argument("--output", default="relationship-report-export/reference-coverage-summary.json")
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 2000:
        parser.error("--max-batches must be between 1 and 2000")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    credential = DefaultAzureCredential()
    service = BlobServiceClient(account_url=f"https://{ACCOUNT}.blob.core.windows.net", credential=credential)
    try:
        run_id, _ = _latest_selection_blob(service)
        records, aggregate = build_reference_audit(service, args.max_batches, run_id)
        audit_payload = encode_jsonl_gzip(records)
        audit_blob = service.get_blob_client(container=METADATA_CONTAINER, blob=aggregate["private_document_audit_blob"])
        audit_blob.upload_blob(
            audit_payload,
            overwrite=False,
            content_settings=ContentSettings(content_type="application/gzip"),
            metadata={"schema_version": str(SCHEMA_VERSION), "selection_run_id": run_id},
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            "Reference coverage complete: "
            + "; ".join(f"{key}={value['documents_with_any_reference']}/{value['documents']}" for key, value in aggregate["coverage_by_priority"].items())
        )
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
