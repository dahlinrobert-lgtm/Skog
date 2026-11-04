#!/usr/bin/env python3
"""Idempotently copy the existing Kungjort Git archive into private Azure Blob Storage.

The archive is copied without modifying source files. The checkpoint is uploaded
last so it never advertises a state whose archive batches have not been copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
from pathlib import Path

from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.identity import DefaultAzureCredential


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(source: Path) -> list[tuple[Path, str, str]]:
    state_path = source / "state.json"
    if not state_path.is_file():
        raise RuntimeError(f"Missing required checkpoint: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1 or not state.get("changes_cursor"):
        raise RuntimeError("Checkpoint schema or initial changes_cursor is invalid")

    files: list[tuple[Path, str, str]] = []
    for folder, container in (("bootstrap", "kungjort-raw"), ("changes", "kungjort-changes")):
        directory = source / folder
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.jsonl.gz")):
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"Empty or invalid archive file: {path}")
            files.append((path, container, f"{folder}/{path.name}"))
    if not files:
        raise RuntimeError("No JSONL.GZ archive batches found; refusing to migrate an empty archive")
    # State is intentionally last.
    files.append((state_path, "metadata", "kungjort/state.json"))
    return files


def migrate(account_name: str, source: Path, dry_run: bool) -> None:
    files = collect_files(source)
    print(f"Source: {source}")
    print(f"Archive files: {len(files) - 1}")
    total_bytes = 0
    for path, container, blob_name in files:
        size = path.stat().st_size
        digest = sha256_file(path)
        total_bytes += size
        print(json.dumps({
            "container": container,
            "blob": blob_name,
            "bytes": size,
            "sha256": digest,
            "checkpoint": blob_name == "kungjort/state.json",
        }))
    print(f"Total bytes including checkpoint: {total_bytes}")
    if dry_run:
        print("Dry run only; no Azure blobs were written.")
        return

    service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    uploaded = 0
    skipped = 0
    try:
        for path, container, blob_name in files:
            digest = sha256_file(path)
            client = service.get_blob_client(container=container, blob=blob_name)
            try:
                props = client.get_blob_properties()
                remote_digest = (props.metadata or {}).get("sha256")
                if remote_digest != digest or props.size != path.stat().st_size:
                    raise RuntimeError(
                        f"Remote blob differs from local source; refusing overwrite: "
                        f"{container}/{blob_name}"
                    )
                skipped += 1
                print(f"Already present and verified: {container}/{blob_name}")
                continue
            except ResourceNotFoundError:
                pass

            content_type = "application/gzip" if path.suffix == ".gz" else "application/json"
            try:
                with path.open("rb") as stream:
                    client.upload_blob(
                        stream,
                        overwrite=False,
                        metadata={"sha256": digest},
                        content_settings=ContentSettings(content_type=content_type),
                    )
            except ResourceExistsError:
                # Handle a concurrent/retried upload by verifying the winner.
                props = client.get_blob_properties()
                if (props.metadata or {}).get("sha256") != digest or props.size != path.stat().st_size:
                    raise RuntimeError(f"Concurrent blob upload differs: {container}/{blob_name}")
                skipped += 1
                continue
            props = client.get_blob_properties()
            if (props.metadata or {}).get("sha256") != digest or props.size != path.stat().st_size:
                raise RuntimeError(f"Post-upload verification failed: {container}/{blob_name}")
            uploaded += 1
            print(f"Uploaded and verified: {container}/{blob_name}")

        print(json.dumps({
            "result": "success",
            "uploaded": uploaded,
            "already_present": skipped,
            "archive_batches": len(files) - 1,
            "checkpoint_uploaded_last": True,
            "total_bytes": total_bytes,
        }))
    finally:
        service.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--source", type=Path, default=Path("data/kungjort"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    migrate(args.account_name, args.source, args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
