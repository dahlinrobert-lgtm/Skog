#!/usr/bin/env python3
"""Extract municipal work IDs and protocol decision references from Kungjort.

The source archive and document-level extraction stay private in Azure.
GitHub receives aggregate counts only. No matter/process links are finalized.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ACCOUNT = "stskogkolldata"
CONTAINER = "metadata"
SELECTION_PREFIX = "kungjort/selection/v1/"
DETAIL_SOURCES = (("kungjort-raw", "bootstrap-live/"), ("kungjort-raw", "bootstrap/"))
SCHEMA_VERSION = 1

# Deliberately conservative: municipal prefix + four-digit year + slash + serial.
WORK_ID_RE = re.compile(r"(?<![\w])([A-ZÅÄÖ]{2,12})\s*(\d{4})\s*/\s*(\d{1,8})(?!\w)", re.IGNORECASE)
WORK_ID_PREFIX_STOPWORDS = {"eller", "och", "med", "från", "för", "av", "till", "på", "i", "är"}
PROTOCOL_RE = re.compile(r"(?<!\d)(20\d{2}-\d{2}-\d{2})\s*\(\s*§\s*(\d{1,4}[a-z]?)\s*\)", re.IGNORECASE)
TEXT_KEYS = {
    "title", "rubrik", "subject", "summary", "sammanfattning", "description",
    "beskrivning", "case_title", "arende", "ärende", "heading", "name",
    "decision", "beslut", "text", "content",
}


def normalize_work_id(value: str) -> str:
    value = value.upper()
    value = re.sub(r"\s+", "", value)
    return value


def work_id_matches(text: str) -> list[str]:
    found = {normalize_work_id(m.group(0)) for m in WORK_ID_RE.finditer(text) if m.group(1).casefold() not in WORK_ID_PREFIX_STOPWORDS}
    return sorted(found)


def protocol_references(text: str) -> list[dict]:
    found = {}
    for match in PROTOCOL_RE.finditer(text):
        raw = match.group(0)
        key = (match.group(1), match.group(2).casefold())
        found[key] = {
            "raw": raw,
            "decision_date": match.group(1),
            "protocol_paragraph": match.group(2),
        }
    return [found[key] for key in sorted(found)]


def collect_semantic_text(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in TEXT_KEYS:
                if isinstance(child, str) and child.strip():
                    out.append(child.strip())
                elif isinstance(child, list):
                    out.extend(x.strip() for x in child if isinstance(x, str) and x.strip())
            if isinstance(child, (dict, list)):
                collect_semantic_text(child, out)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                collect_semantic_text(child, out)


def read_jsonl_gzip(payload: bytes) -> list[dict]:
    rows = []
    for line in gzip.decompress(payload).decode("utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def encode_jsonl_gzip(rows: list[dict]) -> bytes:
    import io
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as stream:
        for row in rows:
            stream.write((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
    return out.getvalue()


def latest_selection(service: Any) -> tuple[str, str]:
    container = service.get_container_client(CONTAINER)
    names = sorted(
        item.name for item in container.list_blobs(name_starts_with=SELECTION_PREFIX)
        if item.name.endswith("/document-selection.jsonl.gz")
    )
    if not names:
        raise RuntimeError("No private Kungjort selection index found")
    name = names[-1]
    return name.split("/")[3], name


def build_audit(service: Any, max_batches: int, run_id: str, audit_run_id: str) -> tuple[list[dict], dict]:
    selection_blob = service.get_blob_client(
        container=CONTAINER, blob=f"{SELECTION_PREFIX}{run_id}/document-selection.jsonl.gz"
    )
    selected = {
        str(row["document_id"]): row
        for row in read_jsonl_gzip(selection_blob.download_blob().readall())
        if row.get("document_id") is not None
    }
    if not selected:
        raise RuntimeError("Selection index is empty")

    details: dict[str, dict] = {}
    batch_available, batch_reviewed, truncated = {}, {}, {}
    for container_name, prefix in DETAIL_SOURCES:
        label = prefix.rstrip("/").replace("/", "_")
        container = service.get_container_client(container_name)
        names = sorted(
            item.name for item in container.list_blobs(name_starts_with=prefix)
            if item.name.endswith(".jsonl.gz")
        )
        batch_available[label] = len(names)
        truncated[label] = len(names) > max_batches
        names = names[:max_batches]
        batch_reviewed[label] = len(names)
        for name in names:
            payload = service.get_blob_client(container=container_name, blob=name).download_blob().readall()
            for record in read_jsonl_gzip(payload):
                doc_id = record.get("document_id") or record.get("id")
                if doc_id is None and isinstance(record.get("list_record"), dict):
                    doc_id = record["list_record"].get("id") or record["list_record"].get("document_id")
                detail = record.get("detail")
                if doc_id is not None and str(doc_id) in selected and isinstance(detail, dict) and detail:
                    details.setdefault(str(doc_id), detail)

    document_rows = []
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    work_id_occurrences = Counter()
    protocol_occurrences = Counter()
    docs_with_work_id = 0
    docs_with_protocol = 0
    docs_with_detail = 0
    docs_with_explicit_municipality = 0
    docs_with_resolved_authority = 0
    docs_with_conflicting_authority = 0
    docs_with_unknown_authority = 0
    work_ids_by_authority: dict[str, set[str]] = defaultdict(set)

    for doc_id, selection in sorted(selected.items()):
        detail = details.get(doc_id, {})
        docs_with_detail += bool(detail)
        text_parts = []
        collect_semantic_text(selection, text_parts)
        collect_semantic_text(detail, text_parts)
        combined = "\n".join(text_parts)
        work_ids = work_id_matches(combined)
        protocols = protocol_references(combined)
        resolution = selection.get("authority_resolution") or {}
        municipality = str(selection.get("municipality") or "").strip()
        # Backward compatibility for already-created private selection indexes.
        if not resolution and municipality:
            resolution = {"status": "resolved", "name": municipality, "method": "legacy_explicit_municipality", "evidence": []}
        authority = str(resolution.get("name") or "").strip()
        docs_with_explicit_municipality += bool(municipality)
        if authority and resolution.get("status") == "resolved":
            docs_with_resolved_authority += 1
        elif resolution.get("status") == "conflict":
            docs_with_conflicting_authority += 1
        else:
            docs_with_unknown_authority += 1
        docs_with_work_id += bool(work_ids)
        docs_with_protocol += bool(protocols)
        priority = str((selection.get("selection") or {}).get("priority", "unknown"))
        for work_id in work_ids:
            # Authority is part of the namespace. Never group identical IDs across authorities.
            authority_key = authority.casefold()
            if authority_key:
                groups[(authority_key, work_id)].append(doc_id)
                work_ids_by_authority[work_id].add(authority_key)
            work_id_occurrences[work_id] += 1
        for protocol in protocols:
            protocol_occurrences[(protocol["decision_date"], protocol["protocol_paragraph"])] += 1

        document_rows.append({
            "record_type": "kungjort_work_id_extraction",
            "schema_version": SCHEMA_VERSION,
            "audit_run_id": audit_run_id,
            "selection_run_id": run_id,
            "document_id": doc_id,
            "priority": priority,
            "municipality_authority": authority or None,
            "authority_resolution_status": resolution.get("status", "unknown"),
            "authority_resolution_method": resolution.get("method"),
            "authority_evidence": resolution.get("evidence", []),
            "has_detail_record": bool(detail),
            "work_ids": [
                {"raw": value, "normalized": value, "role": "detected_in_semantic_text"}
                for value in work_ids
            ],
            "protocol_decision_references": protocols,
        })

    group_rows = []
    multi_doc_groups = 0
    documents_in_multi_doc_groups = set()
    for (authority_key, work_id), members in sorted(groups.items()):
        unique_members = sorted(set(members))
        if len(unique_members) < 2:
            continue
        multi_doc_groups += 1
        documents_in_multi_doc_groups.update(unique_members)
        group_rows.append({
            "record_type": "kungjort_work_id_candidate_group",
            "schema_version": SCHEMA_VERSION,
            "audit_run_id": audit_run_id,
            "authority_key_hash": hashlib.sha256(authority_key.encode("utf-8")).hexdigest(),
            "work_id": work_id,
            "document_ids": unique_members,
            "document_count": len(unique_members),
            "link_status": "candidate_only",
        })

    rows = document_rows + group_rows
    private_blob = f"kungjort/work-id-audit/v{SCHEMA_VERSION}/{audit_run_id}/work-id-extraction.jsonl.gz"
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "kungjort_work_id_extraction",
        "selection_run_id": run_id,
        "selection_documents": len(selected),
        "documents_with_detail": docs_with_detail,
        "detail_source_batches_available": batch_available,
        "detail_source_batches_reviewed": batch_reviewed,
        "detail_source_scan_truncated": truncated,
        "documents_with_work_id": docs_with_work_id,
        "documents_with_explicit_municipality": docs_with_explicit_municipality,
        "documents_with_resolved_authority": docs_with_resolved_authority,
        "documents_with_conflicting_authority": docs_with_conflicting_authority,
        "documents_with_unknown_authority": docs_with_unknown_authority,
        "repeated_work_ids_across_resolved_authorities": sum(1 for authorities in work_ids_by_authority.values() if len(authorities) > 1),
        "documents_with_protocol_reference": docs_with_protocol,
        "distinct_work_ids": len(work_id_occurrences),
        "work_ids_found_in_multiple_documents": sum(1 for n in work_id_occurrences.values() if n > 1),
        "candidate_groups_same_authority_and_work_id": multi_doc_groups,
        "documents_in_multi_document_candidate_groups": len(documents_in_multi_doc_groups),
        "distinct_protocol_date_paragraph_pairs": len(protocol_occurrences),
        "private_document_audit_blob": private_blob,
        "privacy_note": "Aggregate only. No work IDs, protocol values, document IDs, titles, municipality values, URLs or text.",
    }
    return rows, aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=2000)
    parser.add_argument("--output", default="work-id-report-export/work-id-summary.json")
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 2000:
        parser.error("--max-batches must be between 1 and 2000")

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    credential = DefaultAzureCredential()
    service = BlobServiceClient(account_url=f"https://{ACCOUNT}.blob.core.windows.net", credential=credential)
    try:
        selection_run_id, _ = latest_selection(service)
        audit_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        rows, aggregate = build_audit(service, args.max_batches, selection_run_id, audit_run_id)
        blob = service.get_blob_client(container=CONTAINER, blob=aggregate["private_document_audit_blob"])
        blob.upload_blob(
            encode_jsonl_gzip(rows), overwrite=False,
            content_settings=ContentSettings(content_type="application/gzip"),
            metadata={"schema_version": str(SCHEMA_VERSION), "selection_run_id": selection_run_id},
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            "Work ID extraction complete: "
            f"documents={aggregate['selection_documents']}; "
            f"with_work_id={docs if (docs := aggregate['documents_with_work_id']) else 0}; "
            f"candidate_groups={aggregate['candidate_groups_same_authority_and_work_id']}"
        )
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
