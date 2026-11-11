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


def verify_blob(container, blob_name: str, expected_sha: str, expected_size: int) -> None:
    import io

    compressed = container.download_blob(blob_name).readall()
    digest = hashlib.sha256()
    size = 0
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if digest.hexdigest() != expected_sha or size != expected_size:
        raise RuntimeError("Downloaded Azure segment failed SHA-256/byte-count verification")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload one immutable police raw-event run segment.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    raw_sha, raw_bytes = file_hash(source)
    if raw_bytes == 0:
        print("segment_skipped=empty changed_or_new_versions=0")
        return
    with source.open("rb") as stream:
        row_count = sum(1 for _ in stream)

    with tempfile.TemporaryDirectory() as temp_dir:
        compressed = Path(temp_dir) / "segment.jsonl.gz"
        with source.open("rb") as src, gzip.open(compressed, "wb", compresslevel=6) as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
        compressed_sha, compressed_bytes = file_hash(compressed)

        segment_key = f"runs/{args.run_id}/attempt-{args.run_attempt}"
        blob_name = f"{segment_key}/raw_events.jsonl.gz"
        manifest_name = f"{segment_key}/manifest.json"
        metadata = {
            "archive_type": "police_raw_run_segment",
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
                    data,
                    overwrite=False,
                    metadata=metadata,
                    content_settings=ContentSettings(content_type="application/gzip"),
                )
            print(f"segment_uploaded={blob_name}")
        except ResourceExistsError:
            existing = blob.get_blob_properties().metadata or {}
            for key, value in metadata.items():
                if existing.get(key) != value:
                    raise RuntimeError(f"Existing immutable run segment conflicts on {key}; refusing overwrite")
            print(f"segment_already_exists_matching={blob_name}")

        verify_blob(container, blob_name, raw_sha, raw_bytes)
        manifest = {
            "schema_version": 1,
            "archive_type": "police_raw_run_segment",
            "storage_account": ACCOUNT,
            "container": CONTAINER,
            "blob": blob_name,
            "run_id": args.run_id,
            "run_attempt": args.run_attempt,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "row_count": row_count,
            "raw_bytes": raw_bytes,
            "raw_sha256": raw_sha,
            "compressed_bytes": compressed_bytes,
            "compressed_sha256": compressed_sha,
            "verified": True,
            "verification": "downloaded, decompressed, and compared byte count plus SHA-256",
        }
        manifest_data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        manifest_blob = container.get_blob_client(manifest_name)
        try:
            manifest_blob.upload_blob(
                manifest_data,
                overwrite=False,
                content_settings=ContentSettings(content_type="application/json"),
            )
            print(f"segment_manifest_uploaded={manifest_name}")
        except ResourceExistsError:
            current = json.loads(manifest_blob.download_blob().readall())
            if current.get("raw_sha256") != raw_sha or current.get("raw_bytes") != raw_bytes or current.get("verified") is not True:
                raise RuntimeError("Existing run manifest conflicts with verified segment")

        print(
            f"segment_verified=true rows={row_count} raw_bytes={raw_bytes} "
            f"raw_sha256={raw_sha} compressed_bytes={compressed_bytes}"
        )
        credential.close()
        service.close()


if __name__ == "__main__":
    main()
