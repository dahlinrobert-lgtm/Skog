#!/usr/bin/env python3
"""Build a private, conservative Kungjort document-hierarchy audit.

GitHub receives aggregate coverage and candidate counts only. Document IDs,
source values, reference values and node memberships remain in private Azure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Running this file directly adds scripts/ rather than the repository root
# to sys.path. Add the root explicitly so shared helpers import in Actions.
import sys
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from scripts.kungjort_relationship_audit import (
    ACCOUNT, METADATA_CONTAINER, SELECTION_PREFIX, DETAIL_SOURCES,
    read_jsonl_gzip, encode_jsonl_gzip, document_id,
)

SCHEMA_VERSION = 1


def _resolved_name(value: Any) -> str | None:
    if not isinstance(value, dict) or value.get("status") != "resolved":
        return None
    name = value.get("name")
    return str(name).strip() if isinstance(name, str) and name.strip() else None


def _hash_key(parts: tuple[str, ...]) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def build_hierarchy_audit(service: Any, max_batches: int, selection_run_id: str, audit_run_id: str):
    selection_blob = service.get_blob_client(
        container=METADATA_CONTAINER,
        blob=f"{SELECTION_PREFIX}{selection_run_id}/document-selection.jsonl.gz",
    )
    selected = {
        str(row["document_id"]): row
        for row in read_jsonl_gzip(selection_blob.download_blob().readall())
        if row.get("document_id") is not None
    }
    if not selected:
        raise RuntimeError("Private selection index contains no document rows")

    details: dict[str, dict] = {}
    batches_available, batches_reviewed, truncated = {}, {}, {}
    for container_name, prefix, kind, _precedence in DETAIL_SOURCES:
        container = service.get_container_client(container_name)
        names = sorted(
            item.name for item in container.list_blobs(name_starts_with=prefix)
            if item.name.endswith(".jsonl.gz")
        )
        batches_available[kind] = len(names)
        truncated[kind] = len(names) > max_batches
        names = names[:max_batches]
        batches_reviewed[kind] = len(names)
        for name in names:
            payload = service.get_blob_client(container=container_name, blob=name).download_blob().readall()
            for record in read_jsonl_gzip(payload):
                doc = document_id(record)
                detail = record.get("detail")
                if doc in selected and isinstance(detail, dict) and detail:
                    details.setdefault(doc, detail)

    coverage = Counter()
    meeting_members: dict[str, set[str]] = defaultdict(set)
    case_members: dict[tuple[str, str], set[str]] = defaultdict(set)
    private_rows = []
    for doc_id, selection in sorted(selected.items()):
        detail = details.get(doc_id, {})
        identity = selection.get("organizational_identity") or {}
        municipality = _resolved_name(identity.get("municipality"))
        committee = _resolved_name(identity.get("committee"))
        administration = _resolved_name(identity.get("administration"))
        organ = str(detail.get("organ") or "").strip() or None
        meeting_date = str(detail.get("meeting_date") or "").strip() or None
        sections = detail.get("sections") if isinstance(detail.get("sections"), list) else []
        paragraphs = set()
        case_refs = set()
        for section in sections:
            if not isinstance(section, dict):
                continue
            paragraph = str(section.get("paragraf") or "").strip()
            if paragraph:
                paragraphs.add(paragraph)
            cases = section.get("cases") if isinstance(section.get("cases"), list) else []
            for case in cases:
                if not isinstance(case, dict):
                    continue
                for field in ("case_id", "normalized_dnr", "dnr"):
                    value = case.get(field)
                    if isinstance(value, (str, int)) and str(value).strip():
                        case_refs.add((field, " ".join(str(value).casefold().split())))
        coverage["documents"] += 1
        coverage["with_detail"] += bool(detail)
        coverage["with_resolved_municipality"] += bool(municipality)
        coverage["with_resolved_committee"] += bool(committee)
        coverage["with_resolved_administration"] += bool(administration)
        coverage["with_source_organ"] += bool(organ)
        coverage["with_meeting_date"] += bool(meeting_date)
        coverage["with_organ_and_date"] += bool(organ and meeting_date)
        coverage["with_sections"] += bool(sections)
        coverage["with_paragraph"] += bool(paragraphs)
        coverage["with_case_reference"] += bool(case_refs)

        # Meeting candidate key is intentionally not a committee inference:
        # municipality + source organ + date must all be present.
        if municipality and organ and meeting_date:
            meeting_key = _hash_key((municipality.casefold(), organ.casefold(), meeting_date))
            meeting_members[meeting_key].add(doc_id)
        for field, value in case_refs:
            case_members[(field, value)].add(doc_id)

        private_rows.append({
            "record_type": "kungjort_hierarchy_document",
            "schema_version": SCHEMA_VERSION,
            "audit_run_id": audit_run_id,
            "selection_run_id": selection_run_id,
            "document_id": doc_id,
            "municipality_name": municipality,
            "committee_name": committee,
            "administration_name": administration,
            "source_organ": organ,
            "meeting_date": meeting_date,
            "paragraphs": sorted(paragraphs),
            "case_reference_hashes": sorted(_hash_key((field, value)) for field, value in case_refs),
            "has_detail_record": bool(detail),
        })

    meeting_groups = [members for members in meeting_members.values() if len(members) > 1]
    case_groups = [(key, members) for key, members in case_members.items() if len(members) > 1]
    private_rows.extend({
        "record_type": "kungjort_meeting_candidate_group",
        "schema_version": SCHEMA_VERSION,
        "audit_run_id": audit_run_id,
        "meeting_key_hash": key,
        "document_ids": sorted(members),
        "document_count": len(members),
        "link_status": "candidate_only",
    } for key, members in sorted(meeting_members.items()) if len(members) > 1)
    private_rows.extend({
        "record_type": "kungjort_case_candidate_group",
        "schema_version": SCHEMA_VERSION,
        "audit_run_id": audit_run_id,
        "reference_field": field,
        "reference_hash": _hash_key((value,)),
        "document_ids": sorted(members),
        "document_count": len(members),
        "link_status": "candidate_only",
    } for (field, value), members in sorted(case_groups))

    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "kungjort_document_hierarchy_audit",
        "selection_run_id": selection_run_id,
        "selection_documents": len(selected),
        "detail_source_batches_available": batches_available,
        "detail_source_batches_reviewed": batches_reviewed,
        "detail_source_scan_truncated": truncated,
        "coverage": dict(sorted(coverage.items())),
        "candidate_groups": {
            "meeting_groups": len(meeting_groups),
            "documents_in_meeting_groups": len(set().union(*meeting_groups) if meeting_groups else set()),
            "case_reference_groups": len(case_groups),
            "documents_in_case_reference_groups": len(set().union(*(members for _, members in case_groups)) if case_groups else set()),
            "status": "candidate_only",
        },
        "hierarchy_policy": {
            "municipality": "resolved identity only",
            "committee": "resolved identity only; not inferred from source organ",
            "administration": "separate resolved identity",
            "meeting": "municipality + source organ + meeting date",
            "paragraph": "section paragraph values retained privately",
            "case": "structured case_id/DNR references; candidate links only",
        },
        "private_audit_blob": f"kungjort/hierarchy-audit/v{SCHEMA_VERSION}/{audit_run_id}/document-hierarchy.jsonl.gz",
        "privacy_note": "Aggregate only; no document IDs, names, reference values, titles, URLs or text.",
    }
    return private_rows, aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=2000)
    parser.add_argument("--output", default="hierarchy-report-export/hierarchy-summary.json")
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 2000:
        parser.error("--max-batches must be between 1 and 2000")
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings
    credential = DefaultAzureCredential()
    service = BlobServiceClient(account_url=f"https://{ACCOUNT}.blob.core.windows.net", credential=credential)
    try:
        container = service.get_container_client(METADATA_CONTAINER)
        names = sorted(item.name for item in container.list_blobs(name_starts_with=SELECTION_PREFIX)
                       if item.name.endswith("/document-selection.jsonl.gz"))
        if not names:
            raise RuntimeError("No private Kungjort selection index found")
        selection_run_id = names[-1].split("/")[3]
        audit_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        rows, aggregate = build_hierarchy_audit(service, args.max_batches, selection_run_id, audit_run_id)
        blob = service.get_blob_client(container=METADATA_CONTAINER, blob=aggregate["private_audit_blob"])
        blob.upload_blob(encode_jsonl_gzip(rows), overwrite=False,
                         content_settings=ContentSettings(content_type="application/gzip"),
                         metadata={"schema_version": str(SCHEMA_VERSION), "selection_run_id": selection_run_id})
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Hierarchy audit complete: " + "; ".join(f"{k}={v}" for k, v in aggregate["candidate_groups"].items()))
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
