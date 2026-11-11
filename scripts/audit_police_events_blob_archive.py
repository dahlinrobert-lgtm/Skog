from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "stskogkolldata")
CONTAINER = os.environ.get("POLICE_ARCHIVE_CONTAINER", "police-events")
CHUNK_SIZE = 1024 * 1024


def verify_gzip_blob(container, blob_name: str, expected_sha: str, expected_bytes: int) -> None:
    # Stream the compressed object to disk, then decompress and hash incrementally.
    with tempfile.TemporaryDirectory() as temp_dir:
        compressed_path = Path(temp_dir) / "archive.gz"
        downloader = container.download_blob(blob_name)
        with compressed_path.open("wb") as output:
            for chunk in downloader.chunks():
                output.write(chunk)
        digest = hashlib.sha256()
        size = 0
        with gzip.open(compressed_path, "rb") as source:
            for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
                digest.update(chunk)
                size += len(chunk)
        if digest.hexdigest() != expected_sha or size != expected_bytes:
            raise RuntimeError(
                f"Deep verification failed for {blob_name}: "
                f"sha256={digest.hexdigest()} bytes={size}; "
                f"expected sha256={expected_sha} bytes={expected_bytes}"
            )


def load_json(container, name: str) -> dict:
    try:
        value = json.loads(container.download_blob(name).readall())
    except Exception as exc:
        raise RuntimeError(f"Cannot read valid JSON manifest {name}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Manifest is not a JSON object: {name}")
    return value


def check_archive(container, manifest_name: str, expected_type: str, deep: bool) -> tuple[int, int]:
    manifest = load_json(container, manifest_name)
    required = ("blob", "raw_sha256", "raw_bytes", "compressed_bytes", "row_count")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise RuntimeError(f"{manifest_name} missing fields: {', '.join(missing)}")
    if manifest.get("schema_version") != 1 or manifest.get("archive_type") != expected_type:
        raise RuntimeError(f"{manifest_name} has unexpected schema/archive type")
    if manifest.get("verified") is not True:
        raise RuntimeError(f"{manifest_name} is not marked verified")

    blob_name = str(manifest["blob"])
    if expected_type == "legacy_raw_jsonl_backfill" and blob_name != "legacy/raw_events.jsonl.gz":
        raise RuntimeError(f"Unexpected legacy blob path in {manifest_name}: {blob_name}")
    if expected_type == "police_raw_run_segment":
        if not blob_name.startswith("runs/") or not blob_name.endswith("/raw_events.jsonl.gz"):
            raise RuntimeError(f"Unexpected run segment path in {manifest_name}: {blob_name}")
        if manifest_name != blob_name.removesuffix("raw_events.jsonl.gz") + "manifest.json":
            raise RuntimeError(f"Manifest/segment path mismatch: {manifest_name} -> {blob_name}")

    blob = container.get_blob_client(blob_name)
    props = blob.get_blob_properties()
    metadata = props.metadata or {}
    expected_metadata = {
        "raw_sha256": str(manifest["raw_sha256"]),
        "raw_bytes": str(manifest["raw_bytes"]),
        "compressed_bytes": str(manifest["compressed_bytes"]),
        "compressed_sha256": str(manifest["compressed_sha256"]),
    }
    if expected_type == "police_raw_run_segment":
        for key in ("run_id", "run_attempt"):
            if not manifest.get(key):
                raise RuntimeError(f"{manifest_name} missing {key}")
        expected_metadata.update({
            "run_id": str(manifest["run_id"]),
            "run_attempt": str(manifest["run_attempt"]),
            "row_count": str(manifest["row_count"]),
        })
    for key, value in expected_metadata.items():
        if metadata.get(key) != value:
            raise RuntimeError(
                f"Blob metadata mismatch for {blob_name}, field {key}: "
                f"manifest={value!r}, blob={metadata.get(key)!r}"
            )
    if props.size != int(manifest["compressed_bytes"]):
        raise RuntimeError(
            f"Compressed size mismatch for {blob_name}: "
            f"blob={props.size}, manifest={manifest['compressed_bytes']}"
        )
    if deep:
        verify_gzip_blob(container, blob_name, str(manifest["raw_sha256"]), int(manifest["raw_bytes"]))
    return int(manifest["row_count"]), int(manifest["raw_bytes"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the durable Azure police raw archive.")
    parser.add_argument(
        "--deep", action="store_true",
        help="Download, decompress and SHA-256 verify every archived raw object.",
    )
    args = parser.parse_args()

    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{ACCOUNT}.blob.core.windows.net",
        credential=credential,
    )
    try:
        container = service.get_container_client(CONTAINER)
        names = {item.name for item in container.list_blobs()}
        manifests = sorted(name for name in names if name.endswith("/manifest.json"))
        required_legacy = "legacy/manifest.json"
        if required_legacy not in names:
            raise RuntimeError("Required legacy/manifest.json is missing")
        run_manifests = [name for name in manifests if name.startswith("runs/")]
        if not run_manifests:
            raise RuntimeError("No run manifests found; refusing to report an empty archive as healthy")

        referenced: set[str] = set()
        total_rows = 0
        total_raw_bytes = 0
        checked = 0
        for name in [required_legacy, *run_manifests]:
            expected_type = (
                "legacy_raw_jsonl_backfill" if name == required_legacy
                else "police_raw_run_segment"
            )
            rows, raw_bytes = check_archive(container, name, expected_type, args.deep)
            manifest = load_json(container, name)
            blob_name = str(manifest["blob"])
            if blob_name in referenced:
                raise RuntimeError(f"Duplicate manifest reference to blob: {blob_name}")
            referenced.add(blob_name)
            total_rows += rows
            total_raw_bytes += raw_bytes
            checked += 1

        raw_objects = {
            name for name in names
            if name == "legacy/raw_events.jsonl.gz"
            or (name.startswith("runs/") and name.endswith("/raw_events.jsonl.gz"))
        }
        orphan_objects = sorted(raw_objects - referenced)
        missing_objects = sorted(referenced - raw_objects)
        if orphan_objects or missing_objects:
            raise RuntimeError(
                f"Archive inventory mismatch: orphan_objects={orphan_objects}; "
                f"missing_objects={missing_objects}"
            )

        print(
            f"archive_audit=passed manifests_checked={checked} "
            f"run_segments={len(run_manifests)} raw_rows_sum={total_rows} "
            f"raw_bytes_sum={total_raw_bytes} deep_verification={str(args.deep).lower()}"
        )
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
