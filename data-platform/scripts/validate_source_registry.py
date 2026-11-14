#!/usr/bin/env python3
"""Validate the Skog source and rights registry without changing it."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REGISTRY = Path(__file__).resolve().parents[1] / "config" / "sources.yml"
ALLOWED_ATTRIBUTION_STATUS = {
    "required",
    "recommended",
    "not_required",
    "unknown",
    "pending_dataset_review",
}
OPERATIONAL_ALLOWED = {
    "access_status": {
        "verified", "partial", "technical_probe", "authorised_access_used",
        "not_verified", "planned",
    },
    "snapshot_status": {
        "recurring", "pilot", "partial", "baseline_only", "not_started",
        "metadata_monitoring_needs_repair", "pilot_for_selected_layers",
        "monthly_archive_planned_or_pilot", "30_day_daily_observation_test",
    },
    "history_status": {
        "time_series", "partial", "metadata_series_only", "not_verified",
        "none", "historical_archive_partial",
    },
    "commercial_use_status": {
        "verified", "verified_with_attribution", "conditional",
        "conditional_per_product", "pending_product_terms",
        "pending_scope_confirmation", "restricted", "unknown",
    },
    "customer_display_status": {
        "approved", "conditional", "conditional_on_attribution_and_source_scope",
        "pending_product_layer_check", "pending_layer_check",
        "pending_product_description_check", "pending_per_product",
        "pending_per_document_review", "pending_written_or_ordered_scope",
        "pending_scope_confirmation", "not_assessed",
    },
}
OPERATIONAL_REQUIRED = {
    "access_status", "snapshot_status", "history_status",
    "commercial_use_status", "customer_display_status", "last_verified",
    "next_action", "evidence_reference",
}

PROVENANCE_REQUIRED = {
    "producer_name",
    "distributor_name",
    "dataset_identity",
    "attribution_status",
    "attribution_text",
    "attribution_url",
    "attribution_scope",
    "evidence_reference",
    "reviewed_on",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> None:
    if not REGISTRY.is_file():
        fail(f"Registry file not found: {REGISTRY}")

    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fail(f"Invalid YAML: {exc}")

    if not isinstance(data, dict):
        fail("Registry root must be a YAML mapping.")
    if data.get("schema_version") != 2:
        fail("Expected schema_version: 2.")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("'sources' must be a non-empty list.")

    seen: set[str] = set()
    errors: list[str] = []

    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be a mapping")
            continue

        source_id = source.get("source_id")
        if not non_empty(source_id):
            errors.append(f"{label} is missing a non-empty source_id")
            source_id = label
        elif source_id in seen:
            errors.append(f"duplicate source_id: {source_id}")
        else:
            seen.add(source_id)

        for key in ("name", "source_type", "provider"):
            if not non_empty(source.get(key)):
                errors.append(f"{source_id}: missing non-empty '{key}'")

        rights = source.get("rights")
        if not isinstance(rights, dict):
            errors.append(f"{source_id}: 'rights' must be a mapping")
            continue

        operations = source.get("operations")
        if operations is not None:
            if not isinstance(operations, dict):
                errors.append(f"{source_id}: 'operations' must be a mapping")
            else:
                missing_operations = sorted(OPERATIONAL_REQUIRED - operations.keys())
                if missing_operations:
                    errors.append(
                        f"{source_id}: operations missing required fields: "
                        f"{', '.join(missing_operations)}"
                    )
                for field, allowed in OPERATIONAL_ALLOWED.items():
                    value = operations.get(field)
                    if value is not None and value not in allowed:
                        errors.append(
                            f"{source_id}: unsupported operations.{field} {value!r}"
                        )
                for field in ("last_verified", "next_action", "evidence_reference"):
                    if not non_empty(operations.get(field)):
                        errors.append(
                            f"{source_id}: operations.{field} must be a non-empty string"
                        )
                last_verified = operations.get("last_verified")
                if non_empty(last_verified) and not __import__("re").fullmatch(
                    r"\\d{4}-\\d{2}-\\d{2}", last_verified
                ):
                    errors.append(
                        f"{source_id}: operations.last_verified must use YYYY-MM-DD"
                    )

        provenance = source.get("provenance")
        if provenance is None:
            continue
        if not isinstance(provenance, dict):
            errors.append(f"{source_id}: 'provenance' must be a mapping")
            continue

        missing = sorted(PROVENANCE_REQUIRED - provenance.keys())
        if missing:
            errors.append(
                f"{source_id}: provenance missing required fields: {', '.join(missing)}"
            )
            continue

        status = provenance.get("attribution_status")
        if not isinstance(status, str) or status not in ALLOWED_ATTRIBUTION_STATUS:
            errors.append(
                f"{source_id}: unsupported attribution_status {status!r}"
            )
        if not non_empty(provenance.get("producer_name")):
            errors.append(f"{source_id}: provenance.producer_name must be non-empty")
        if not non_empty(provenance.get("distributor_name")):
            errors.append(f"{source_id}: provenance.distributor_name must be non-empty")
        if not non_empty(provenance.get("dataset_identity")):
            errors.append(f"{source_id}: provenance.dataset_identity must be non-empty")
        if not non_empty(provenance.get("attribution_scope")):
            errors.append(f"{source_id}: provenance.attribution_scope must be non-empty")
        if not non_empty(provenance.get("evidence_reference")):
            errors.append(f"{source_id}: provenance.evidence_reference must be non-empty")
        if not non_empty(provenance.get("reviewed_on")):
            errors.append(f"{source_id}: provenance.reviewed_on must be non-empty")

        attribution_text = provenance.get("attribution_text")
        attribution_url = provenance.get("attribution_url")
        if status in {"required", "recommended"} and not non_empty(attribution_text):
            errors.append(
                f"{source_id}: {status} attribution requires attribution_text"
            )
        if status == "required" and not non_empty(attribution_url):
            errors.append(
                f"{source_id}: required attribution requires attribution_url"
            )
        if non_empty(attribution_url) and not attribution_url.startswith(
            ("https://", "http://")
        ):
            errors.append(f"{source_id}: attribution_url must be an HTTP(S) URL")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    with_provenance = sum(isinstance(s, dict) and "provenance" in s for s in sources)
    with_operations = sum(isinstance(s, dict) and "operations" in s for s in sources)
    print(
        f"Source registry valid: {len(sources)} sources, "
        f"{with_provenance} with provenance/attribution metadata, "
        f"{with_operations} with operational status."
    )


if __name__ == "__main__":
    main()
