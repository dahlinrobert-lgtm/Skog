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
        if status not in ALLOWED_ATTRIBUTION_STATUS:
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
    print(
        f"Source registry valid: {len(sources)} sources, "
        f"{with_provenance} with provenance/attribution metadata."
    )


if __name__ == "__main__":
    main()
