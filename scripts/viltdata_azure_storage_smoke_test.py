#!/usr/bin/env python3
"""Verify GitHub OIDC access and immutable Blob write/readback for Viltdata.

Only synthetic test content is written. No Viltdata source payloads are uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "stskogkolldata")
CONTAINER = os.environ.get("VILTDATA_ARCHIVE_CONTAINER", "viltdata-kill-statistics")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_test_payload(run_id: str, run_attempt: str) -> bytes:
    document = {
        "schema_version": 1,
        "purpose": "synthetic Azure Blob write/readback smoke test",
        "source_id": "viltdata.kill_statistics",
        "run_id": str(run_id),
        "run_attempt": str(run_attempt),
        "synthetic": True,
        "source_data_included": False,
    }
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def upload_immutable(blob_client, payload: bytes, metadata: dict[str, str], content_type: str) -> bool:
    """Create a blob once; on retry, accept only an exact matching object."""
    try:
        blob_client.upload_blob(
            payload,
            overwrite=False,
            metadata=metadata,
            content_settings=ContentSettings(content_type=content_type),
        )
        return True
    except ResourceExistsError:
        properties = blob_client.get_blob_properties()
        existing_metadata = properties.metadata or {}
        for key, value in metadata.items():
            if existing_metadata.get(key) != value:
                raise RuntimeError(f"Existing immutable blob conflicts on metadata field {key}")
        existing_payload = blob_client.download_blob().readall()
        if existing_payload != payload:
            raise RuntimeError("Existing immutable blob content differs; refusing overwrite")
        return False


def run_smoke_test(run_id: str, run_attempt: str, account: str = ACCOUNT, container_name: str = CONTAINER) -> dict:
    if not run_id or not run_attempt:
        raise ValueError("run_id and run_attempt are required")

    payload = build_test_payload(run_id, run_attempt)
    digest = sha256_bytes(payload)
    prefix = f"smoke-tests/github-actions/{run_id}/attempt-{run_attempt}"
    payload_name = f"{prefix}/synthetic-payload.json"
    manifest_name = f"{prefix}/manifest.json"

    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{account}.blob.core.windows.net",
        credential=credential,
    )
    try:
        container = service.get_container_client(container_name)
        try:
            container.create_container()
            container_created = True
        except ResourceExistsError:
            container_created = False

        metadata = {
            "source_id": "viltdata.kill_statistics",
            "run_id": str(run_id),
            "run_attempt": str(run_attempt),
            "sha256": digest,
            "synthetic": "true",
        }
        payload_blob = container.get_blob_client(payload_name)
        payload_created = upload_immutable(payload_blob, payload, metadata, "application/json")

        downloaded = payload_blob.download_blob().readall()
        downloaded_sha = sha256_bytes(downloaded)
        if downloaded != payload or downloaded_sha != digest:
            raise RuntimeError("Azure readback failed exact-byte/SHA-256 verification")

        properties = payload_blob.get_blob_properties()
        if properties.size != len(payload):
            raise RuntimeError("Azure blob byte-count verification failed")
        for key, value in metadata.items():
            if (properties.metadata or {}).get(key) != value:
                raise RuntimeError(f"Azure blob metadata verification failed for {key}")

        manifest = {
            "schema_version": 1,
            "test_type": "viltdata_azure_blob_smoke_test",
            "source_id": "viltdata.kill_statistics",
            "storage_account": account,
            "container": container_name,
            "blob": payload_name,
            "run_id": str(run_id),
            "run_attempt": str(run_attempt),
            "synthetic": True,
            "source_data_included": False,
            "payload_bytes": len(payload),
            "payload_sha256": digest,
            "readback_bytes": len(downloaded),
            "readback_sha256": downloaded_sha,
            "verified": True,
            "verification": "exact bytes, byte count, SHA-256 and Blob metadata checked after download",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        manifest_metadata = {
            "source_id": "viltdata.kill_statistics",
            "run_id": str(run_id),
            "run_attempt": str(run_attempt),
            "payload_sha256": digest,
            "verified": "true",
            "synthetic": "true",
        }
        manifest_blob = container.get_blob_client(manifest_name)
        manifest_created = upload_immutable(manifest_blob, manifest_bytes, manifest_metadata, "application/json")

        saved_manifest = json.loads(manifest_blob.download_blob().readall())
        if (
            saved_manifest.get("verified") is not True
            or saved_manifest.get("payload_sha256") != digest
            or saved_manifest.get("payload_bytes") != len(payload)
            or saved_manifest.get("blob") != payload_name
        ):
            raise RuntimeError("Azure manifest readback validation failed")

        return {
            "status": "success",
            "container_created": container_created,
            "payload_created": payload_created,
            "manifest_created": manifest_created,
            "storage_account": account,
            "container": container_name,
            "payload_blob": payload_name,
            "manifest_blob": manifest_name,
            "payload_bytes": len(payload),
            "payload_sha256": digest,
            "readback_bytes": len(downloaded),
            "readback_sha256": downloaded_sha,
            "verified": True,
            "synthetic": True,
            "source_data_included": False,
        }
    finally:
        service.close()
        credential.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    parser.add_argument("--account", default=ACCOUNT)
    parser.add_argument("--container", default=CONTAINER)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.run_id:
        parser.error("--run-id or GITHUB_RUN_ID is required")

    report = run_smoke_test(args.run_id, args.run_attempt, args.account, args.container)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(serialized, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
