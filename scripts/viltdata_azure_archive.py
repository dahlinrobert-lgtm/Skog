#!/usr/bin/env python3
"""Immutable Azure archive for complete Viltdata kill-statistics snapshots.

Subcommands:
  upload  Validate and archive an existing local snapshot without rewriting it.
  audit   Inventory and deeply verify every archived snapshot.
  restore Rebuild one snapshot's exact file layout into a new local directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "stskogkolldata")
CONTAINER = os.environ.get("VILTDATA_ARCHIVE_CONTAINER", "viltdata-kill-statistics")
CHUNK_SIZE = 1024 * 1024
SNAPSHOT_RE = re.compile(r"^\d{8}T\d{6}Z$")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or not value or "\\" in value or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"Unsafe manifest file path: {value!r}")
    return path.as_posix()


def validate_snapshot(snapshot_dir: Path) -> tuple[dict, bytes, dict[str, Path]]:
    snapshot_dir = snapshot_dir.resolve()
    manifest_path = snapshot_dir / "manifest.json"
    if not snapshot_dir.is_dir() or not manifest_path.is_file():
        raise RuntimeError("Snapshot directory and manifest.json are required")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    if not isinstance(manifest, dict):
        raise RuntimeError("Snapshot manifest must be a JSON object")
    if manifest.get("status") != "complete" or manifest.get("complete") is not True:
        raise RuntimeError("Refusing to archive a snapshot that is not explicitly complete")
    snapshot_id = str(manifest.get("run_id") or snapshot_dir.name)
    if not SNAPSHOT_RE.fullmatch(snapshot_id) or snapshot_id != snapshot_dir.name:
        raise RuntimeError("Snapshot directory name must match manifest run_id (YYYYMMDDTHHMMSSZ)")

    requests = manifest.get("requests")
    if not isinstance(requests, list) or not requests:
        raise RuntimeError("Manifest request inventory is missing")
    files: dict[str, Path] = {}
    seen_kinds = set()
    stats = []
    for item in requests:
        if not isinstance(item, dict) or item.get("status", "ok") not in ("ok", "complete"):
            raise RuntimeError("Manifest contains a failed, pending, or invalid request")
        kind = item.get("kind")
        if kind in ("statistics_model", "counties"):
            seen_kinds.add(kind)
        elif kind == "statistics":
            stats.append(item)
            if item.get("status") != "ok":
                raise RuntimeError("Manifest contains a non-successful statistics request")
        else:
            raise RuntimeError(f"Unexpected request kind in manifest: {kind!r}")
        relative = _safe_relative(str(item.get("file") or ""))
        if relative == "manifest.json" or relative in files:
            raise RuntimeError(f"Duplicate or reserved manifest path: {relative}")
        path = snapshot_dir.joinpath(*PurePosixPath(relative).parts)
        if not path.is_file():
            raise RuntimeError(f"Manifest-listed raw file is missing: {relative}")
        sha, size = digest_file(path)
        if sha != item.get("sha256") or size != item.get("bytes"):
            raise RuntimeError(f"Raw file integrity mismatch: {relative}")
        files[relative] = path

    if seen_kinds != {"statistics_model", "counties"}:
        raise RuntimeError("Manifest must contain exactly the model and counties inventories")
    expected = manifest.get("statistics_requests_expected")
    successful = manifest.get("statistics_requests_ok")
    if not isinstance(expected, int) or not isinstance(successful, int):
        raise RuntimeError("Manifest statistics request totals are missing")
    if expected <= 0 or successful != expected or len(stats) != expected:
        raise RuntimeError("Statistics request inventory is incomplete")
    if manifest.get("errors"):
        raise RuntimeError("Manifest contains errors; refusing archive")
    actual = {
        p.relative_to(snapshot_dir).as_posix()
        for p in snapshot_dir.rglob("*") if p.is_file() and p.name != "manifest.json"
    }
    if actual != set(files):
        raise RuntimeError(
            f"Snapshot raw-file inventory mismatch: unlisted={sorted(actual-set(files))}, "
            f"missing={sorted(set(files)-actual)}"
        )
    return manifest, manifest_bytes, files



def validate_manifest_inventory(manifest: dict) -> dict[str, dict]:
    requests = manifest.get("requests")
    if not isinstance(requests, list) or not requests:
        raise RuntimeError("Manifest request inventory is missing")
    inventory = {}
    kinds = set()
    statistics = []
    for item in requests:
        if not isinstance(item, dict):
            raise RuntimeError("Invalid request inventory entry")
        kind = item.get("kind")
        if kind not in ("statistics_model", "counties", "statistics"):
            raise RuntimeError(f"Unexpected request kind: {kind!r}")
        if item.get("status", "ok") not in ("ok", "complete"):
            raise RuntimeError("Manifest contains a failed or pending request")
        if kind == "statistics" and item.get("status") != "ok":
            raise RuntimeError("Statistics request is not marked successful")
        relative = _safe_relative(str(item.get("file") or ""))
        if relative == "manifest.json" or relative in inventory:
            raise RuntimeError(f"Duplicate or reserved manifest path: {relative}")
        if not isinstance(item.get("bytes"), int) or item["bytes"] < 0:
            raise RuntimeError(f"Invalid byte count for {relative}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256") or "")):
            raise RuntimeError(f"Invalid SHA-256 for {relative}")
        inventory[relative] = item
        kinds.add(kind)
        if kind == "statistics":
            statistics.append(item)
    expected = manifest.get("statistics_requests_expected")
    successful = manifest.get("statistics_requests_ok")
    if kinds != {"statistics_model", "counties", "statistics"}:
        raise RuntimeError("Manifest must include model, counties and statistics requests")
    species_count = manifest.get("species_count")
    batch_count = manifest.get("species_batch_count")
    county_count = manifest.get("county_count")
    species = manifest.get("species")
    if (
        not isinstance(species_count, int) or species_count <= 0
        or not isinstance(batch_count, int) or batch_count <= 0
        or not isinstance(county_count, int) or county_count < 0
        or not isinstance(species, list) or len(species) != species_count
    ):
        raise RuntimeError("Manifest species/county inventory totals are invalid")
    if (
        not isinstance(expected, int) or expected <= 0 or successful != expected
        or len(statistics) != expected or expected != (1 + county_count) * batch_count
    ):
        raise RuntimeError("Statistics request inventory is incomplete")
    if manifest.get("errors"):
        raise RuntimeError("Manifest contains errors")
    return inventory

def upload_immutable(blob, payload: bytes, metadata: dict[str, str], content_type: str) -> bool:
    try:
        blob.upload_blob(
            payload, overwrite=False, metadata=metadata,
            content_settings=ContentSettings(content_type=content_type),
        )
        return True
    except ResourceExistsError:
        props = blob.get_blob_properties()
        existing_metadata = props.metadata or {}
        for key, value in metadata.items():
            if existing_metadata.get(key) != value:
                raise RuntimeError(f"Immutable Azure object conflicts on metadata {key}")
        existing = blob.download_blob().readall()
        if existing != payload:
            raise RuntimeError("Immutable Azure object differs in bytes; refusing overwrite")
        return False


def _connect():
    credential = DefaultAzureCredential()
    service = BlobServiceClient(
        account_url=f"https://{ACCOUNT}.blob.core.windows.net", credential=credential
    )
    return credential, service


def upload_snapshot(snapshot_dir: Path) -> dict:
    manifest, manifest_bytes, files = validate_snapshot(snapshot_dir)
    snapshot_id = str(manifest["run_id"])
    prefix = f"snapshots/{snapshot_id}"
    credential, service = _connect()
    uploaded = 0
    try:
        container = service.get_container_client(CONTAINER)
        for relative, path in sorted(files.items()):
            payload = path.read_bytes()
            sha = digest_bytes(payload)
            name = f"{prefix}/{relative}"
            metadata = {
                "source_id": "viltdata.kill_statistics",
                "snapshot_id": snapshot_id,
                "sha256": sha,
                "bytes": str(len(payload)),
                "object_type": "raw_source_json",
            }
            if upload_immutable(container.get_blob_client(name), payload, metadata, "application/json"):
                uploaded += 1
        manifest_name = f"{prefix}/manifest.json"
        manifest_sha = digest_bytes(manifest_bytes)
        manifest_meta = {
            "source_id": "viltdata.kill_statistics",
            "snapshot_id": snapshot_id,
            "sha256": manifest_sha,
            "bytes": str(len(manifest_bytes)),
            "object_type": "source_manifest",
        }
        if upload_immutable(
            container.get_blob_client(manifest_name), manifest_bytes, manifest_meta, "application/json"
        ):
            uploaded += 1
        # Read back every object, not just the manifest.
        for relative, path in sorted(files.items()):
            blob = container.get_blob_client(f"{prefix}/{relative}")
            body = blob.download_blob().readall()
            sha, size = digest_bytes(body), len(body)
            expected_sha, expected_size = digest_file(path)
            props = blob.get_blob_properties()
            metadata = props.metadata or {}
            if (
                sha != expected_sha or size != expected_size or props.size != expected_size
                or metadata.get("sha256") != expected_sha
                or metadata.get("snapshot_id") != snapshot_id
                or metadata.get("object_type") != "raw_source_json"
            ):
                raise RuntimeError(f"Azure readback verification failed: {relative}")
        saved_manifest = container.download_blob(manifest_name).readall()
        manifest_props = container.get_blob_client(manifest_name).get_blob_properties()
        if (
            saved_manifest != manifest_bytes
            or manifest_props.size != len(manifest_bytes)
            or (manifest_props.metadata or {}).get("sha256") != manifest_sha
            or (manifest_props.metadata or {}).get("snapshot_id") != snapshot_id
        ):
            raise RuntimeError("Azure manifest readback or metadata verification failed")
        return {
            "status": "verified", "snapshot_id": snapshot_id,
            "container": CONTAINER, "raw_file_count": len(files),
            "objects_created": uploaded, "manifest_sha256": manifest_sha,
            "source_status": manifest["status"], "complete": True,
        }
    finally:
        service.close()
        credential.close()


def audit_archive() -> dict:
    credential, service = _connect()
    try:
        container = service.get_container_client(CONTAINER)
        names = {item.name for item in container.list_blobs(name_starts_with="snapshots/")}
        manifests = sorted(n for n in names if n.endswith("/manifest.json"))
        if not manifests:
            raise RuntimeError("No Viltdata snapshot manifests found")
        referenced: set[str] = set()
        checked = 0
        total_bytes = 0
        for manifest_name in manifests:
            parts = manifest_name.split("/")
            if len(parts) != 3 or parts[0] != "snapshots" or not SNAPSHOT_RE.fullmatch(parts[1]):
                raise RuntimeError(f"Unexpected manifest path: {manifest_name}")
            snapshot_id = parts[1]
            raw_manifest = container.download_blob(manifest_name).readall()
            manifest = json.loads(raw_manifest.decode("utf-8-sig"))
            if manifest.get("run_id") != snapshot_id or manifest.get("complete") is not True or manifest.get("status") != "complete":
                raise RuntimeError(f"Archived manifest is not a complete matching snapshot: {manifest_name}")
            # Reuse the exact manifest inventory checks without creating local files.
            request_files = validate_manifest_inventory(manifest)
            expected_names = {manifest_name}
            for relative, item in request_files.items():
                name = f"snapshots/{snapshot_id}/{relative}"
                expected_names.add(name)
                blob = container.get_blob_client(name)
                props = blob.get_blob_properties()
                body = blob.download_blob().readall()
                sha = digest_bytes(body)
                if sha != item.get("sha256") or len(body) != item.get("bytes") or props.size != len(body):
                    raise RuntimeError(f"Blob content differs from manifest: {name}")
                metadata = props.metadata or {}
                if metadata.get("sha256") != sha or metadata.get("snapshot_id") != snapshot_id:
                    raise RuntimeError(f"Blob metadata mismatch: {name}")
                total_bytes += len(body)
            mblob = container.get_blob_client(manifest_name)
            mprops = mblob.get_blob_properties()
            mmeta = mprops.metadata or {}
            if (
                mprops.size != len(raw_manifest)
                or mmeta.get("sha256") != digest_bytes(raw_manifest)
                or mmeta.get("snapshot_id") != snapshot_id
                or mmeta.get("object_type") != "source_manifest"
            ):
                raise RuntimeError(f"Manifest blob metadata/size mismatch: {manifest_name}")
            referenced.update(expected_names)
            checked += 1
        actual = {n for n in names if n.startswith("snapshots/")}
        if actual != referenced:
            raise RuntimeError(
                f"Archive inventory mismatch: unreferenced={sorted(actual-referenced)}, missing={sorted(referenced-actual)}"
            )
        return {"status": "passed", "snapshots_checked": checked, "objects_checked": len(referenced), "raw_bytes_verified": total_bytes}
    finally:
        service.close()
        credential.close()


def restore_snapshot(snapshot_id: str, output_dir: Path) -> dict:
    if not SNAPSHOT_RE.fullmatch(snapshot_id):
        raise ValueError("snapshot_id must use YYYYMMDDTHHMMSSZ")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing restore directory: {output_dir}")
    credential, service = _connect()
    try:
        container = service.get_container_client(CONTAINER)
        prefix = f"snapshots/{snapshot_id}"
        manifest_name = f"{prefix}/manifest.json"
        manifest_bytes = container.download_blob(manifest_name).readall()
        manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
        if manifest.get("run_id") != snapshot_id or manifest.get("status") != "complete" or manifest.get("complete") is not True:
            raise RuntimeError("Archived snapshot manifest is not a complete matching baseline")
        entries = validate_manifest_inventory(manifest)
        payloads = {}
        for relative, item in entries.items():
            name = f"{prefix}/{relative}"
            body = container.download_blob(name).readall()
            if digest_bytes(body) != item.get("sha256") or len(body) != item.get("bytes"):
                raise RuntimeError(f"Restore integrity check failed: {name}")
            props = container.get_blob_client(name).get_blob_properties()
            if (props.metadata or {}).get("sha256") != item.get("sha256"):
                raise RuntimeError(f"Restore metadata check failed: {name}")
            payloads[relative] = body
        output_dir.mkdir(parents=True, exist_ok=False)
        try:
            for relative, body in payloads.items():
                target = output_dir.joinpath(*PurePosixPath(relative).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
            (output_dir / "manifest.json").write_bytes(manifest_bytes)
        except Exception:
            # Keep partial output visible for manual inspection; never delete user data.
            raise
        return {"status": "restored", "snapshot_id": snapshot_id, "output_dir": str(output_dir), "raw_file_count": len(payloads), "manifest_sha256": digest_bytes(manifest_bytes)}
    finally:
        service.close()
        credential.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("upload")
    up.add_argument("--snapshot-dir", type=Path, required=True)
    sub.add_parser("audit")
    restore = sub.add_parser("restore")
    restore.add_argument("--snapshot-id", required=True)
    restore.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "upload":
        result = upload_snapshot(args.snapshot_dir)
    elif args.command == "audit":
        result = audit_archive()
    else:
        result = restore_snapshot(args.snapshot_id, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
