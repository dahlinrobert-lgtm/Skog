#!/usr/bin/env python3
"""Audit Kungjort organ/publication_organ values; raw values remain private in Azure."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.kungjort_selection_inventory import build_inventory, encode_jsonl_gzip

ACCOUNT = "stskogkolldata"
METADATA_CONTAINER = "metadata"
SCHEMA_VERSION = 1


def normalize_organization(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def classify_organization(value: str) -> str:
    normalized = normalize_organization(value)
    if not normalized:
        return "empty"
    if re.search(r"\b(forvaltningen|forvaltning|forvaltningskontor)\b", normalized):
        return "administration_candidate"
    if re.search(r"\b(namnden|namnd|styrelsen|styrelse|utskott|beredning)\b", normalized):
        return "committee_or_board_candidate"
    if re.search(r"\b(fullmaktige|kommunfullmaktige)\b", normalized):
        return "municipal_assembly_candidate"
    if re.search(r"\bkommun\b", normalized):
        return "municipality_level_publisher"
    if re.search(r"\b(lansstyrelsen|region|myndighet|domstol)\b", normalized):
        return "other_public_authority"
    return "unclassified_organ"


def build_private_audit(records: list[dict], run_id: str) -> tuple[list[dict], dict]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    category_documents = Counter()
    field_documents = Counter()
    detail_coverage = Counter()
    for record in records:
        detail_coverage["documents"] += 1
        detail_coverage["with_detail"] += bool(record.get("has_detail_record"))
        detail_coverage["without_detail"] += not bool(record.get("has_detail_record"))
        identity = record.get("organizational_identity") or {}
        organ = identity.get("issuing_organ") or {}
        evidence = organ.get("evidence") or []
        seen_categories = set()
        for item in evidence:
            field = str(item.get("source") or "")
            value = item.get("value")
            if field not in {"organ", "publication_organ", "organ_name"}:
                continue
            if not isinstance(value, str) or not value.strip():
                continue
            normalized = normalize_organization(value)
            category = classify_organization(value)
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            key = (field, digest)
            if key not in grouped:
                grouped[key] = {
                    "record_type": "kungjort_organization_value",
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_id,
                    "source_field": field,
                    "normalized_value_sha256": digest,
                    "normalized_value": normalized,
                    "source_value": value.strip(),
                    "category": category,
                    "document_ids": set(),
                }
            grouped[key]["document_ids"].add(str(record.get("document_id") or ""))
            field_documents[field] += 1
            seen_categories.add(category)
        for category in seen_categories:
            category_documents[category] += 1

    private_rows = []
    unique_by_category = Counter()
    for item in grouped.values():
        ids = sorted(x for x in item.pop("document_ids") if x)
        item["document_count"] = len(ids)
        item["document_ids"] = ids
        private_rows.append(item)
        unique_by_category[item["category"]] += 1

    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "report_type": "kungjort_organization_value_audit",
        "run_id": run_id,
        "documents_reviewed": detail_coverage["documents"],
        "documents_with_detail": detail_coverage["with_detail"],
        "documents_without_detail": detail_coverage["without_detail"],
        "documents_with_organ_value_by_category": dict(sorted(category_documents.items())),
        "unique_organ_values_by_category": dict(sorted(unique_by_category.items())),
        "organ_field_document_occurrences": dict(sorted(field_documents.items())),
        "unique_organ_value_groups": len(private_rows),
        "privacy_note": "Aggregate counts only. Raw organization names, hashes, document IDs and source values are stored only in private Azure.",
    }
    return private_rows, aggregate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-batches", type=int, default=500)
    parser.add_argument("--output", default="organization-report-export/organization-summary.json")
    args = parser.parse_args()
    if not 1 <= args.max_batches <= 2000:
        parser.error("--max-batches must be between 1 and 2000")
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{ACCOUNT}.blob.core.windows.net",
        credential=credential,
    )
    try:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        selection, selection_summary = build_inventory(service, args.max_batches, run_id)
        rows, aggregate = build_private_audit(selection["records"], run_id)
        private_blob = f"kungjort/organization-audit/v{SCHEMA_VERSION}/{run_id}/organization-values.jsonl.gz"
        blob = service.get_blob_client(container=METADATA_CONTAINER, blob=private_blob)
        blob.upload_blob(
            encode_jsonl_gzip(rows),
            overwrite=False,
            content_settings=ContentSettings(content_type="application/gzip"),
            metadata={"schema_version": str(SCHEMA_VERSION), "selection_run_id": run_id},
        )
        aggregate["private_audit_blob"] = private_blob
        aggregate["selection_unique_documents"] = selection_summary["unique_documents"]
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Organization audit complete: " + "; ".join(
            f"{key}={value}" for key, value in aggregate["unique_organ_values_by_category"].items()
        ))
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
