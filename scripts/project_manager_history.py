#!/usr/bin/env python3
"""Deterministic, offline helpers for v2b project-manager history manifests.

This module deliberately performs no Git, GitHub API, network, or credential
operations. Persistence orchestration is a separate, not-yet-enabled concern.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

MANIFEST_SCHEMA_VERSION = 1
EXPECTED_REPOSITORY = "dahlinrobert-lgtm/Skog"
EXPECTED_ARTIFACT_NAME = "skogskoll-project-manager-report"
_REQUIRED_COVERAGE_STATUSES = {"complete", "truncated"}


class HistoryValidationError(ValueError):
    """Raised when an inventory cannot safely be prepared for archiving."""


class ExistingRunConflict(HistoryValidationError):
    """Raised when a run directory exists with different content."""


def _utc_timestamp(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise HistoryValidationError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryValidationError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HistoryValidationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coverage(inventory: Mapping[str, Any], key: str) -> dict[str, Any]:
    raw = (inventory.get("collection_limits") or {}).get(key)
    if not isinstance(raw, dict):
        raise HistoryValidationError(f"Missing coverage metadata: {key}")
    status = raw.get("status")
    if status not in _REQUIRED_COVERAGE_STATUSES:
        raise HistoryValidationError(f"Unknown coverage status for {key}: {status!r}")
    pages = raw.get("pages_fetched")
    items = raw.get("items_fetched")
    if not isinstance(pages, int) or pages < 1 or not isinstance(items, int) or items < 0:
        raise HistoryValidationError(f"Invalid coverage counts for {key}")
    truncated = bool(raw.get("truncated"))
    if (status == "truncated") != truncated:
        raise HistoryValidationError(f"Inconsistent truncation metadata for {key}")
    return {
        "status": status,
        "pages_fetched": pages,
        "items_fetched": items,
        "page_size": raw.get("page_size"),
        "max_pages": raw.get("max_pages"),
        "truncated": truncated,
    }


def build_manifest(
    inventory_bytes: bytes,
    report_bytes: bytes,
    *,
    run_id: str,
    run_attempt: int,
    repository: str,
    source_branch: str,
    source_commit_sha: str,
    archived_at: str,
    artifact_name: str = EXPECTED_ARTIFACT_NAME,
) -> bytes:
    """Validate source files and return deterministic manifest JSON bytes."""
    if not isinstance(inventory_bytes, bytes) or not isinstance(report_bytes, bytes):
        raise HistoryValidationError("Inventory and report must be supplied as exact bytes")
    if not inventory_bytes or not report_bytes:
        raise HistoryValidationError("Inventory and report must not be empty")
    try:
        inventory = json.loads(inventory_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryValidationError("inventory.json is not valid UTF-8 JSON") from exc
    if not isinstance(inventory, dict):
        raise HistoryValidationError("inventory.json root must be an object")
    if repository != EXPECTED_REPOSITORY:
        raise HistoryValidationError("Repository identity does not match the approved repository")
    if (inventory.get("repository") or {}).get("full_name") != repository:
        raise HistoryValidationError("Inventory repository identity mismatch")
    if not re.fullmatch(r"[0-9]+", str(run_id)):
        raise HistoryValidationError("run_id must contain only decimal digits")
    if not isinstance(run_attempt, int) or run_attempt < 1:
        raise HistoryValidationError("run_attempt must be a positive integer")
    if not source_branch or not source_commit_sha:
        raise HistoryValidationError("source_branch and source_commit_sha are required")
    if artifact_name != EXPECTED_ARTIFACT_NAME:
        raise HistoryValidationError("Unexpected artifact name")

    generated_at = _utc_timestamp(inventory.get("generated_at"), "generated_at")
    archived_at_utc = _utc_timestamp(archived_at, "archived_at")
    issues = _coverage(inventory, "issues")
    pulls = _coverage(inventory, "pull_requests")
    comparison_eligible = issues["status"] == "complete" and pulls["status"] == "complete"

    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": str(run_id),
        "run_attempt": run_attempt,
        "repository": repository,
        "source_branch": source_branch,
        "source_commit_sha": source_commit_sha,
        "generated_at": generated_at,
        "archived_at": archived_at_utc,
        "artifact_name": artifact_name,
        "files": {
            "inventory_json": {
                "path": "inventory.json",
                "size_bytes": len(inventory_bytes),
                "sha256": hashlib.sha256(inventory_bytes).hexdigest(),
            },
            "report_md": {
                "path": "report.md",
                "size_bytes": len(report_bytes),
                "sha256": hashlib.sha256(report_bytes).hexdigest(),
            },
        },
        "coverage": {"issues": issues, "pull_requests": pulls},
        "comparison_eligible": comparison_eligible,
    }
    return (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def check_append_only(existing_dir: Path, expected_files: Mapping[str, bytes]) -> bool:
    """Return False for an exact duplicate; raise on any conflicting existing run.

    This check is intentionally read-only. A later writer must perform an
    exclusive/atomic create and re-check the branch head before committing.
    """
    if not existing_dir.exists():
        return True
    if not existing_dir.is_dir():
        raise ExistingRunConflict("Existing run path is not a directory")
    for name, expected in expected_files.items():
        path = existing_dir / name
        if not path.is_file() or path.read_bytes() != expected:
            raise ExistingRunConflict(f"Existing run differs or is incomplete: {name}")
    actual_names = {p.name for p in existing_dir.iterdir()}
    if actual_names != set(expected_files):
        raise ExistingRunConflict("Existing run contains missing or unexpected files")
    return False


def restore_run_files(
    manifest_bytes: bytes,
    source_files: Mapping[str, bytes],
    destination: Path,
) -> dict[str, str]:
    """Restore a verified run into a new local directory (never overwrite).

    This is an offline recovery primitive only. It does not access Git or GitHub
    and must not be wired to production persistence without separate approval.
    """
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HistoryValidationError("manifest.json is not valid UTF-8 JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        raise HistoryValidationError("Unsupported or invalid manifest schema")
    expected = manifest.get("files")
    if not isinstance(expected, dict) or set(expected) != {"inventory_json", "report_md"}:
        raise HistoryValidationError("Manifest must describe exactly inventory.json and report.md")
    if set(source_files) != {"inventory.json", "report.md"}:
        raise HistoryValidationError("Restore input must contain exactly inventory.json and report.md")
    verified: dict[str, str] = {}
    for key, filename in (("inventory_json", "inventory.json"), ("report_md", "report.md")):
        metadata = expected.get(key)
        payload = source_files[filename]
        if not isinstance(metadata, dict) or not isinstance(payload, bytes):
            raise HistoryValidationError(f"Invalid restore metadata or bytes for {filename}")
        if metadata.get("path") != filename:
            raise HistoryValidationError(f"Unexpected manifest path for {filename}")
        if metadata.get("size_bytes") != len(payload):
            raise HistoryValidationError(f"Size mismatch for {filename}")
        digest = hashlib.sha256(payload).hexdigest()
        if metadata.get("sha256") != digest:
            raise HistoryValidationError(f"SHA-256 mismatch for {filename}")
        verified[filename] = digest

    if destination.exists():
        raise ExistingRunConflict("Restore destination already exists; refusing to overwrite")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for filename, payload in source_files.items():
            (destination / filename).write_bytes(payload)
        for filename, digest in verified.items():
            restored = (destination / filename).read_bytes()
            if hashlib.sha256(restored).hexdigest() != digest:
                raise HistoryValidationError(f"Readback SHA-256 mismatch for {filename}")
    except Exception:
        # Do not leave a partially restored directory that could look complete.
        import shutil
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return verified
