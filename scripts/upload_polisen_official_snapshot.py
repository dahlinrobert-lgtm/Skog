from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "stskogkolldata")
CONTAINER = os.environ.get("POLICE_ARCHIVE_CONTAINER", "police-events")


def file_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload and verify an immutable official Police API snapshot.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    raw_sha, raw_bytes = file_hash(source)
    if raw_bytes == 0:
        raise RuntimeError("Refusing to archive an empty snapshot")
    with source.open("r", encoding="utf-8") as stream:
        snapshot = json.load(stream)
    if snapshot.get("source_id") != "polisen.events_official_api":
        raise ValueError("Unexpected source_id in snapshot")
    row_count = int(snapshot.get("record_count", -1))
    if row_count <= 0 or row_count != len(snapshot.get("records", [])):
        raise ValueError("Snapshot record_count does not match records")

    with tempfile.TemporaryDirectory() as temp_dir:
        compressed = Path(temp_dir) / "official-events.json.gz"
        with source.open("rb") as src, gzip.open(compressed, "wb", compresslevel=6) as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
        compressed_sha, compressed_bytes = file_hash(compressed)
        key = f"polisen-official/runs/{args.run_id}/attempt-{args.run_attempt}"
        blob_name = f"{key}/snapshot.json.gz"
        manifest_name = f"{key}/manifest.json"
        metadata = {
            "archive_type": "polisen_official_api_snapshot",
            "source_id": "polisen.events_official_api",
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "raw_sha256": raw_sha,
            "raw_bytes": str(raw_bytes),
            "compressed_sha256": compressed_sha,
            "compressed_bytes": str(compressed_bytes),
            "row_count": str(row_count),
        }

        credential = DefaultAzureCredential()
        service = BlobServiceClient(
            account_url=f"https://{ACCOUNT}.blob.core.windows.net",
            credential=credential,
        )
        container = service.get_container_client(CONTAINER)
        blob = container.get_blob_client(blob_name)
        try:
            with compressed.open("rb") as data:
                blob.upload_blob(
                    data, overwrite=False, metadata=metadata,
                    content_settings=ContentSettings(content_type="application/gzip"),
                )
            print(f"snapshot_uploaded={blob_name}")
        except ResourceExistsError:
            existing = blob.get_blob_properties().metadata or {}
            if any(existing.get(k) != v for k, v in metadata.items()):
                raise RuntimeError("Existing immutable snapshot conflicts; refusing overwrite")
            print(f"snapshot_already_exists_matching={blob_name}")

        downloaded = container.download_blob(blob_name).readall()
        digest = hashlib.sha256()
        size = 0
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(downloaded), mode="rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
        if digest.hexdigest() != raw_sha or size != raw_bytes:
            raise RuntimeError("Downloaded snapshot failed SHA-256/byte-count verification")

        manifest = {
            "schema_version": 1,
            "archive_type": "polisen_official_api_snapshot",
            "source_id": "polisen.events_official_api",
            "storage_account": ACCOUNT,
            "container": CONTAINER,
            "blob": blob_name,
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "retrieved_at": snapshot["retrieved_at"],
            "row_count": row_count,
            "norrbotten_record_count": snapshot["norrbotten_record_count"],
            "raw_bytes": raw_bytes,
            "raw_sha256": raw_sha,
            "compressed_bytes": compressed_bytes,
            "compressed_sha256": compressed_sha,
            "verified": True,
            "verification": "downloaded, decompressed, and compared byte count plus SHA-256",
        }
        manifest_blob = container.get_blob_client(manifest_name)
        manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        try:
            manifest_blob.upload_blob(
                manifest_data, overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
            )
        except ResourceExistsError:
            current = json.loads(manifest_blob.download_blob().readall())
            if current.get("raw_sha256") != raw_sha or current.get("verified") is not True:
                raise RuntimeError("Existing manifest conflicts with verified snapshot")
        print(
            f"snapshot_verified=true records={row_count} norrbotten_records={snapshot['norrbotten_record_count']} "
            f"raw_bytes={raw_bytes} raw_sha256={raw_sha}"
        )
        credential.close()
        service.close()


if __name__ == "__main__":
    main()
