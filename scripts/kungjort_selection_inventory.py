#!/usr/bin/env python3
"""Build a read-only-derived Kungjort planning selection index in private Azure.

Original source blobs are only read. The derived document-level index is written
to a versioned private prefix in the metadata container. GitHub artifacts contain
aggregate counts only.
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

try:\n    from .kungjort_document_selection import classify_plan_scope\nexcept ImportError:  # direct script execution from the scripts directory\n    from kungjort_document_selection import classify_plan_scope

ACCOUNT = "stskogkolldata"
METADATA_CONTAINER = "metadata"
SOURCES = (
    (METADATA_CONTAINER, "kungjort/index/reclassified-v2/", "reclassified_metadata", 1),
    (METADATA_CONTAINER, "kungjort/index/bootstrap-live/", "listing_metadata", 2),
    ("kungjort-raw", "bootstrap-live/", "document_details", 3),
    ("kungjort-raw", "bootstrap/", "legacy_document_details", 4),
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


def _document_id(record: dict) -> str | None:
    value = record.get("document_id")
    if value is None:
        value = record.get("id")
    if value is None and isinstance(record.get("metadata"), dict):
        value = record["metadata"].get("id") or record["metadata"].get("document_id")
    if value is None and isinstance(record.get("list_record"), dict):
        value = record["list_record"].get("id") or record["list_record"].get("document_id")
    return str(value) if value is not None and str(value).strip() else None


def _metadata(record: dict, kind: str) -> dict:
    if kind in {"reclassified_metadata", "listing_metadata"}:
        value = record.get("metadata")
        return value if isinstance(value, dict) else {}
    value = record.get("list_record")
    return value if isinstance(value, dict) else {}


def _detail(record: dict, kind: str) -> dict:
    if kind not in {"document_details", "legacy_document_details"}:
        return {}
    value = record.get("detail")
    return value if isinstance(value, dict) else {}


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]
    return None


def _detail_has_case_reference(detail: dict) -> bool:
    sections = detail.get("sections")
    if not isinstance(sections, list):
        return False
    for section in sections:
        if not isinstance(section, dict):
            continue
        cases = section.get("cases")
        if isinstance(cases, list):
            for case in cases:
                if isinstance(case, dict) and any(case.get(k) for k in ("dnr", "normalized_dnr", "case_id")):
                    return True
        if section.get("dnr") or section.get("decision_id"):
            return True
    return False


def build_inventory(service: BlobServiceClient, max_batches: int, run_id: str) -> tuple[dict, dict]:
    # Canonical record per source document. Metadata precedence is explicit:
    # current reclassification > live listing index > available detail records.
    documents: dict[str, dict] = {}
    source_batch_counts = Counter()
    source_batches_available = Counter()
    source_scan_truncated = {}
    source_record_counts = Counter()
    missing_id_counts = Counter()
    duplicate_records = 0

    for container_name, prefix, kind, precedence in SOURCES:
        container = service.get_container_client(container_name)
        names = sorted(
            blob.name for blob in container.list_blobs(name_starts_with=prefix)
            if blob.name.endswith(".jsonl.gz")
        )
        source_batches_available[kind] = len(names)
        source_scan_truncated[kind] = len(names) > max_batches
        names = names[:max_batches]
        source_batch_counts[kind] = len(names)
        for name in names:
            payload = service.get_blob_client(container=container_name, blob=name).download_blob().readall()
            records = read_jsonl_gzip(payload)
            source_record_counts[kind] += len(records)
            for record in records:
                doc_id = _document_id(record)
                if not doc_id:
                    missing_id_counts[kind] += 1
                    continue
                existing = documents.get(doc_id)
                if existing is None:
                    existing = {
                        "document_id": doc_id,
                        "metadata": {},
                        "detail": {},
                        "metadata_precedence": 999,
                        "sources": set(),
                    }
                    documents[doc_id] = existing
                else:
                    duplicate_records += 1
                existing["sources"].add(kind)
                metadata = _metadata(record, kind)
                if metadata and precedence < existing["metadata_precedence"]:
                    existing["metadata"] = metadata
                    existing["metadata_precedence"] = precedence
                detail = _detail(record, kind)
                if detail and not existing["detail"]:
                    existing["detail"] = detail

    selection_records = []
    class_counts = Counter()
    priority_counts = Counter()
    source_membership_counts = Counter()
    detail_count = 0
    case_reference_count = 0
    missing_metadata_count = 0

    for doc_id, item in sorted(documents.items()):
        metadata = item["metadata"]
        detail = item["detail"]
        if detail:
            detail_count += 1
        if _detail_has_case_reference(detail):
            case_reference_count += 1
        if not metadata:
            missing_metadata_count += 1

        # Include both listing and detail semantic fields in the classifier.
        classification = classify_plan_scope({"metadata": metadata, "detail": detail})
        class_counts[classification["selection_class"]] += 1
        priority_counts[classification["priority"]] += 1
        for source in item["sources"]:
            source_membership_counts[source] += 1

        selection_records.append({
            "record_type": "kungjort_planning_selection",
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "document_id": doc_id,
            "selection": classification,
            "has_detail_record": bool(detail),
            "has_case_reference_in_detail": _detail_has_case_reference(detail),
            "source_kinds": sorted(item["sources"]),
            "title": _first_text(metadata.get("title"), metadata.get("rubrik"), metadata.get("subject")),
            "municipality": _first_text(metadata.get("municipality"), metadata.get("municipality_name")),
            "document_type": _first_text(metadata.get("doc_type"), metadata.get("document_type"), metadata.get("type")),
        })

    private_blob = f"kungjort/selection/v{SCHEMA_VERSION}/{run_id}/document-selection.jsonl.gz"
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "kungjort_planning_selection_inventory",
        "run_id": run_id,
        "source_batches_available": dict(sorted(source_batches_available.items())),
        "source_batches_reviewed": dict(sorted(source_batch_counts.items())),
        "source_scan_truncated": dict(sorted(source_scan_truncated.items())),
        "source_records_reviewed": dict(sorted(source_record_counts.items())),
        "unique_documents": len(selection_records),
        "duplicate_source_records": duplicate_records,
        "records_missing_document_id": dict(sorted(missing_id_counts.items())),
        "records_missing_metadata": missing_metadata_count,
        "selection_class_counts": dict(sorted(class_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "documents_with_detail": detail_count,
        "documents_with_case_reference_in_detail": case_reference_count,
        "source_membership_counts": dict(sorted(source_membership_counts.items())),
        "private_index_blob": private_blob,
        "privacy_note": "Aggregate counts only. No document IDs, titles, municipality values, URLs, text, examples or source records.",
    }
    return {"records": selection_records, "blob": private_blob}, aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=500,
                        help="Maximum archive batches per source prefix (1-2000)")
    parser.add_argument("--output", default="selection-report-export/selection-summary.json")
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 2000:
        parser.error("--max-batches must be between 1 and 2000")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{ACCOUNT}.blob.core.windows.net",
        credential=credential,
    )
    try:
        result, aggregate = build_inventory(service, args.max_batches, run_id)
        if aggregate["unique_documents"] == 0:
            raise RuntimeError("No Kungjort source documents found in the selected archive prefixes")

        # The detailed index is written only to the private Azure metadata container.
        payload = encode_jsonl_gzip(result["records"])
        blob = service.get_blob_client(container=METADATA_CONTAINER, blob=result["blob"])
        blob.upload_blob(
            payload,
            overwrite=False,
            content_settings=ContentSettings(content_type="application/gzip"),
            metadata={"schema_version": str(SCHEMA_VERSION), "run_id": run_id},
        )

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Selection inventory complete: unique_documents={aggregate['unique_documents']}; "
            f"P1={aggregate['priority_counts'].get('P1', 0)}; "
            f"P2={aggregate['priority_counts'].get('P2', 0)}; "
            f"P3={aggregate['priority_counts'].get('P3', 0)}; "
            f"P4={aggregate['priority_counts'].get('P4', 0)}"
        )
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
