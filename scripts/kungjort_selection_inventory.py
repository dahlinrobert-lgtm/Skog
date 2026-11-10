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

try:
    from .kungjort_document_selection import classify_plan_scope
    from .kungjort_municipality_crosswalk import resolve_scb_municipality
except ImportError:  # direct script execution from the scripts directory
    from kungjort_document_selection import classify_plan_scope
    from kungjort_municipality_crosswalk import resolve_scb_municipality

ACCOUNT = "stskogkolldata"
METADATA_CONTAINER = "metadata"
SOURCES = (
    (METADATA_CONTAINER, "kungjort/index/reclassified-v2/", "reclassified_metadata", 1),
    (METADATA_CONTAINER, "kungjort/index/bootstrap-live/", "listing_metadata", 2),
    ("kungjort-raw", "bootstrap-live/", "document_details", 3),
    ("kungjort-raw", "bootstrap/", "legacy_document_details", 4),
)
SCHEMA_VERSION = 2


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


def resolve_authority(metadata: dict) -> dict:
    """Resolve municipality from explicit names, codes, IDs or municipal organs."""
    name_fields = ("municipality", "municipality_name", "kommun", "kommunnamn", "publication_municipality", "publication_municipality_name")
    code_fields = ("municipality_code", "municipalityCode", "kommun_kod", "kommunkod", "kommun_kod4")
    id_fields = ("municipality_id", "municipalityId", "kommun_id", "kommunid")
    organ_fields = ("organ", "organ_name", "publication_organ")
    def values(fields):
        return [(key, str(metadata[key]).strip()) for key in fields if metadata.get(key) is not None and str(metadata[key]).strip()]
    names = [(key, value.removesuffix(" kommun").strip()) for key, value in values(name_fields)]
    organs = [(key, value[:-len(" kommun")].strip()) for key, value in values(organ_fields) if value.casefold().endswith(" kommun")]
    codes = [(key, value.zfill(4) if value.isdigit() and len(value) <= 4 else value) for key, value in values(code_fields)]
    ids = values(id_fields)
    name_values = [value for _, value in names + organs if value]
    names_by_key = {value.casefold(): value for value in name_values}
    distinct_names = set(names_by_key)
    distinct_codes = {value for _, value in codes}
    distinct_ids = {value for _, value in ids}
    evidence = {
        "names": [{"source": key, "value": value} for key, value in names + organs],
        "codes": [{"source": key, "value": value} for key, value in codes],
        "ids": [{"source": key, "value": value} for key, value in ids],
    }
    if len(distinct_names) > 1 or len(distinct_codes) > 1 or len(distinct_ids) > 1:
        return {"status": "conflict", "name": None, "municipality_code": None, "municipality_id": None, "evidence": evidence, "method": "conflicting_metadata"}
    name = names_by_key[next(iter(distinct_names))] if distinct_names else None
    code = next(iter(distinct_codes), None)
    municipality_id = next(iter(distinct_ids), None)
    if name or code or municipality_id:
        methods = []
        if name: methods.append("explicit_name_or_municipal_organ")
        if code: methods.append("explicit_municipality_code")
        if municipality_id: methods.append("explicit_municipality_id")
        return {"status": "resolved", "name": name, "municipality_code": code, "municipality_id": municipality_id, "evidence": evidence, "method": "+".join(methods)}
    return {"status": "unknown", "name": None, "municipality_code": None, "municipality_id": None, "evidence": evidence, "method": None}
def _resolve_explicit_name(metadata: dict, keys: tuple[str, ...]) -> dict:
    evidence = []
    for key in keys:
        value = _first_text(metadata.get(key))
        if value:
            evidence.append({"source": key, "value": value})
    names = {item["value"].casefold() for item in evidence}
    if len(names) == 1:
        return {"status": "resolved", "name": evidence[0]["value"], "evidence": evidence}
    if len(names) > 1:
        return {"status": "conflict", "name": None, "evidence": evidence}
    return {"status": "unknown", "name": None, "evidence": []}


def resolve_organizational_identity(metadata: dict) -> dict:
    """Keep municipality, committee and administration as separate source-backed entities."""
    return {
        "municipality": resolve_authority(metadata),
        "committee": _resolve_explicit_name(
            metadata,
            ("committee", "committee_name", "issuing_committee", "namnd", "nämnd"),
        ),
        "administration": _resolve_explicit_name(
            metadata,
            ("administration", "administration_name", "forvaltning", "förvaltning", "department"),
        ),
        # Generic organ/sender labels are retained as evidence, never promoted to committee.
        "issuing_organ": _resolve_explicit_name(
            metadata,
            ("issuing_organ", "organ", "organ_name", "publication_organ", "sender", "sender_name"),
        ),
    }


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


def build_inventory(service: Any, max_batches: int, run_id: str) -> tuple[dict, dict]:
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
    municipality_status_counts = Counter()
    municipality_method_counts = Counter()
    municipality_name_documents = 0
    municipality_code_documents = 0
    municipality_id_documents = 0
    municipality_conflict_documents = 0
    municipality_distribution = Counter()
    municipality_evidence_sources = Counter()
    municipality_crosswalk_status_counts = Counter()
    municipality_crosswalk_distribution = Counter()

    for doc_id, item in sorted(documents.items()):
        metadata = item["metadata"]
        detail = item["detail"]
        authority = resolve_authority(metadata)
        municipality_status_counts[authority["status"]] += 1
        if authority.get("method"):
            municipality_method_counts[authority["method"]] += 1
        municipality_name_documents += bool(authority.get("name"))
        municipality_code_documents += bool(authority.get("municipality_code"))
        municipality_id_documents += bool(authority.get("municipality_id"))
        municipality_conflict_documents += authority["status"] == "conflict"
        if authority["status"] == "resolved" and authority.get("name"):
            municipality_distribution[authority["name"]] += 1
            crosswalk = resolve_scb_municipality(authority["name"])
            municipality_crosswalk_status_counts[crosswalk["status"]] += 1
            if crosswalk["status"] == "matched":
                municipality_crosswalk_distribution[(crosswalk["municipality_code"], crosswalk["municipality_name"])] += 1
            else:
                municipality_crosswalk_distribution[(None, authority["name"])] += 1
        for evidence in authority.get("evidence", {}).get("names", []):
            source_key = evidence.get("source", "")
            if source_key in ("municipality", "municipality_name", "kommun", "kommunnamn",
                              "publication_municipality", "publication_municipality_name"):
                municipality_evidence_sources["explicit_municipality_field"] += 1
            elif source_key in ("organ", "organ_name", "publication_organ"):
                municipality_evidence_sources["municipal_organ_label"] += 1
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
            "municipality": resolve_authority(metadata).get("name"),
            "municipality_code": resolve_authority(metadata).get("municipality_code"),
            "scb_municipality_code": (resolve_scb_municipality(authority["name"]).get("municipality_code") if authority.get("name") else None),
            "municipality_id": resolve_authority(metadata).get("municipality_id"),
            "authority_resolution": resolve_authority(metadata),
            "provenance_scope": "source_metadata_record",
            "organizational_identity": resolve_organizational_identity(metadata),
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
        "municipality_attribution": {
            "status_counts": dict(sorted(municipality_status_counts.items())),
            "method_counts": dict(sorted(municipality_method_counts.items())),
            "documents_with_municipality_name": municipality_name_documents,
            "documents_with_municipality_code": municipality_code_documents,
            "documents_with_municipality_id": municipality_id_documents,
            "documents_with_conflicting_municipality_evidence": municipality_conflict_documents,
            "documents_without_municipality_evidence": municipality_status_counts.get("unknown", 0),
            "municipality_distribution": [
                {"municipality_name": name, "documents": count}
                for name, count in sorted(municipality_distribution.items(), key=lambda item: (-item[1], item[0].casefold()))
            ],
            "scb_crosswalk": {
                "reference_year": 2026,
                "source": "Statistics Sweden (SCB), municipalities in numerical order",
                "source_url": "https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/lan-och-kommuner-i-kodnummerordning/",
                "coverage_scope": "Curated crosswalk for municipality names observed in the 2026-11-10 selection inventory; not yet the complete national list of 290 municipalities",
                "status_counts": dict(sorted(municipality_crosswalk_status_counts.items())),
                "distribution": [
                    {"municipality_code": code, "municipality_name": name, "documents": count}
                    for (code, name), count in sorted(municipality_crosswalk_distribution.items(), key=lambda item: (-item[1], item[0][1].casefold()))
                ],
            },
            "municipality_evidence_source_counts": dict(sorted(municipality_evidence_sources.items())),
            "provenance_scope": "canonical source metadata record only; parent-container inheritance not yet assessed; names are candidates pending SCB crosswalk validation",
        },
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

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient, ContentSettings

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
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
