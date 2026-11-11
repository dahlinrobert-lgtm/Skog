from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings, ResourceExistsError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "police_events" / "raw_events.jsonl"
ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "stskogkolldata")
CONTAINER = os.environ.get("POLICE_ARCHIVE_CONTAINER", "police-events")


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def verify_gzip_blob(container_client, blob_name: str, expected_sha: str, expected_bytes: int) -> None:
    digest = hashlib.sha256()
    size = 0
    downloader = container_client.download_blob(blob_name)
    import io

    with gzip.GzipFile(fileobj=io.BytesIO(downloader.readall()), mode="rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    actual_sha = digest.hexdigest()
    if actual_sha != expected_sha or size != expected_bytes:
        raise RuntimeError(
            f"Azure verification failed: sha256={actual_sha} bytes={size}; "
            f"expected sha256={expected_sha} bytes={expected_bytes}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill the tracked police raw JSONL archive to Azure Blob Storage."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Raw archive not found: {source}")

    raw_sha, raw_bytes = sha256_file(source)
    if raw_bytes == 0:
        raise RuntimeError("Refusing to backfill an empty raw archive")

    with tempfile.TemporaryDirectory() as temp_dir:
        compressed = Path(temp_dir) / "raw_events.jsonl.gz"
        with source.open("rb") as src, gzip.open(compressed, "wb", compresslevel=6) as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)

        compressed_sha, compressed_bytes = sha256_file(compressed)
        row_count = sum(1 for _ in source.open("rb"))
        blob_name = "legacy/raw_events.jsonl.gz"
        manifest_name = "legacy/manifest.json"

        account_url = f"https://{ACCOUNT}.blob.core.windows.net"
        credential = DefaultAzureCredential()
        service = BlobServiceClient(account_url=account_url, credential=credential)
        container = service.get_container_client(CONTAINER)
        try:
            container.create_container()
            print(f"container_created={CONTAINER}")
        except ResourceExistsError:
            print(f"container_exists={CONTAINER}")

        metadata = {
            "archive_type": "legacy_raw_jsonl_backfill",
            "raw_sha256": raw_sha,
            "raw_bytes": str(raw_bytes),
            "compressed_sha256": compressed_sha,
            "compressed_bytes": str(compressed_bytes),
            "row_count": str(row_count),
        }

        blob = container.get_blob_client(blob_name)
        try:
            with compressed.open("rb") as data:
                blob.upload_blob(
                    data,
                    overwrite=False,
                    metadata=metadata,
                    content_settings=ContentSettings(content_type="application/gzip"),
                )
            print(f"blob_uploaded={blob_name}")
        except ResourceExistsError:
            properties = blob.get_blob_properties()
            existing = properties.metadata or {}
            for key, value in metadata.items():
                if existing.get(key) != value:
                    raise RuntimeError(
                        f"Existing blob differs from this source for metadata field {key}; "
                        "refusing to overwrite immutable archive data"
                    )
            print(f"blob_already_exists_matching={blob_name}")

        verify_gzip_blob(container, blob_name, raw_sha, raw_bytes)
        manifest = {
            "schema_version": 1,
            "archive_type": "legacy_raw_jsonl_backfill",
            "source_path": "data/police_events/raw_events.jsonl",
            "blob": blob_name,
            "container": CONTAINER,
            "storage_account": ACCOUNT,
            "verified": True,
            "verification": "downloaded, decompressed, and compared byte count plus SHA-256",
            "raw_sha256": raw_sha,
            "raw_bytes": raw_bytes,
            "compressed_sha256": compressed_sha,
            "compressed_bytes": compressed_bytes,
            "row_count": row_count,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        manifest_blob = container.get_blob_client(manifest_name)
        try:
            manifest_blob.upload_blob(manifest_bytes, overwrite=False, content_type="application/json")
            print(f"manifest_uploaded={manifest_name}")
        except ResourceExistsError:
            existing_manifest = json.loads(manifest_blob.download_blob().readall())
            if (
                existing_manifest.get("raw_sha256") != raw_sha
                or existing_manifest.get("raw_bytes") != raw_bytes
                or existing_manifest.get("blob") != blob_name
                or existing_manifest.get("verified") is not True
            ):
                raise RuntimeError("An existing legacy manifest conflicts with the verified source")
            print(f"manifest_already_exists_matching={manifest_name}")

        print(
            f"backfill_verified=true raw_bytes={raw_bytes} rows={row_count} "
            f"raw_sha256={raw_sha} compressed_bytes={compressed_bytes}"
        )
        credential.close()
        service.close()


if __name__ == "__main__":
    main()
