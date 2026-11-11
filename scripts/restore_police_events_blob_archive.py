from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "stskogkolldata")
CONTAINER = os.environ.get("POLICE_ARCHIVE_CONTAINER", "police-events")
CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def read_manifest(container, name: str) -> dict:
    value = json.loads(container.download_blob(name).readall())
    if not isinstance(value, dict):
        raise RuntimeError(f"Invalid manifest object: {name}")
    required = ("blob", "raw_sha256", "raw_bytes", "compressed_sha256", "compressed_bytes", "row_count")
    missing = [key for key in required if key not in value]
    if missing:
        raise RuntimeError(f"{name} missing fields: {', '.join(missing)}")
    if value.get("schema_version") != 1 or value.get("verified") is not True:
        raise RuntimeError(f"{name} has unsupported schema or is not verified")
    return value


def validate_blob_metadata(container, manifest: dict, expected_type: str) -> None:
    name = str(manifest["blob"])
    blob = container.get_blob_client(name)
    props = blob.get_blob_properties()
    metadata = props.metadata or {}
    expected = {
        "raw_sha256": str(manifest["raw_sha256"]),
        "raw_bytes": str(manifest["raw_bytes"]),
        "compressed_sha256": str(manifest["compressed_sha256"]),
        "compressed_bytes": str(manifest["compressed_bytes"]),
    }
    if expected_type == "police_raw_run_segment":
        expected.update({
            "run_id": str(manifest["run_id"]),
            "run_attempt": str(manifest["run_attempt"]),
            "row_count": str(manifest["row_count"]),
        })
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise RuntimeError(f"Metadata mismatch for {name}: {key}")
    if props.size != int(manifest["compressed_bytes"]):
        raise RuntimeError(f"Compressed size mismatch for {name}")


def restore_one(container, manifest_name: str, expected_type: str, db: sqlite3.Connection, temp_dir: Path) -> dict:
    manifest = read_manifest(container, manifest_name)
    if manifest.get("archive_type") != expected_type:
        raise RuntimeError(f"Unexpected archive type in {manifest_name}")
    blob_name = str(manifest["blob"])
    if expected_type == "legacy_raw_jsonl_backfill":
        if blob_name != "legacy/raw_events.jsonl.gz":
            raise RuntimeError("Unexpected legacy blob path")
    else:
        if not blob_name.startswith("runs/") or not blob_name.endswith("/raw_events.jsonl.gz"):
            raise RuntimeError(f"Unexpected run segment path: {blob_name}")
        if manifest_name != blob_name.removesuffix("raw_events.jsonl.gz") + "manifest.json":
            raise RuntimeError(f"Manifest path mismatch: {manifest_name}")
        if not manifest.get("run_id") or not manifest.get("run_attempt"):
            raise RuntimeError(f"Missing run identity in {manifest_name}")

    validate_blob_metadata(container, manifest, expected_type)
    compressed_path = temp_dir / (hashlib.sha256(blob_name.encode()).hexdigest() + ".gz")
    downloader = container.download_blob(blob_name)
    with compressed_path.open("wb") as output:
        for chunk in downloader.chunks():
            output.write(chunk)
    compressed_sha, compressed_bytes = sha256_file(compressed_path)
    if compressed_sha != manifest["compressed_sha256"] or compressed_bytes != int(manifest["compressed_bytes"]):
        raise RuntimeError(f"Compressed object hash/size mismatch: {blob_name}")

    raw_digest = hashlib.sha256()
    raw_bytes = 0
    rows = 0
    with gzip.open(compressed_path, "rb") as source:
        for line in source:
            raw_digest.update(line)
            raw_bytes += len(line)
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL record in {blob_name}, row {rows + 1}") from exc
            if not isinstance(record, dict):
                raise RuntimeError(f"Non-object JSONL record in {blob_name}, row {rows + 1}")
            event = record.get("event") if isinstance(record.get("event"), dict) else {}
            event_id = str(record.get("event_id") or event.get("id") or "")
            retrieved_at = str(record.get("retrieved_at") or "")
            payload_sha = str(record.get("payload_sha256") or "")
            if not retrieved_at or not event_id:
                raise RuntimeError(
                    f"Record missing retrieved_at/event_id in {blob_name}, row {rows + 1}"
                )
            db.execute(
                "INSERT INTO records(retrieved_at,event_id,payload_sha256,line) VALUES(?,?,?,?)",
                (retrieved_at, event_id, payload_sha, line),
            )
            rows += 1
    if raw_digest.hexdigest() != manifest["raw_sha256"] or raw_bytes != int(manifest["raw_bytes"]):
        raise RuntimeError(f"Raw content SHA-256/byte-count mismatch: {blob_name}")
    if rows != int(manifest["row_count"]):
        raise RuntimeError(f"Row-count mismatch for {blob_name}: read={rows}, manifest={manifest['row_count']}")
    compressed_path.unlink()
    return {
        "manifest": manifest_name,
        "blob": blob_name,
        "rows": rows,
        "raw_bytes": raw_bytes,
        "raw_sha256": raw_digest.hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a verified JSONL archive from Azure police raw segments.")
    parser.add_argument("--output-dir", type=Path, default=Path("police-archive-restore"))
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = output_dir / "restored_raw_events.jsonl.gz"
    report_path = output_dir / "restore_report.json"
    if output_jsonl.exists() or report_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing restore output in {output_dir}")

    credential = DefaultAzureCredential()
    service = BlobServiceClient(account_url=f"https://{ACCOUNT}.blob.core.windows.net", credential=credential)
    try:
        container = service.get_container_client(CONTAINER)
        names = {item.name for item in container.list_blobs()}
        legacy_manifest = "legacy/manifest.json"
        if legacy_manifest not in names:
            raise RuntimeError("Required legacy manifest is missing")
        run_manifests = sorted(
            name for name in names if name.startswith("runs/") and name.endswith("/manifest.json")
        )
        if not run_manifests:
            raise RuntimeError("No run manifests found")
        raw_objects = {
            name for name in names
            if name == "legacy/raw_events.jsonl.gz"
            or (name.startswith("runs/") and name.endswith("/raw_events.jsonl.gz"))
        }

        with tempfile.TemporaryDirectory(prefix="police-restore-") as temp:
            temp_dir = Path(temp)
            db = sqlite3.connect(temp_dir / "restore.sqlite")
            db.execute("""
                CREATE TABLE records (
                    retrieved_at TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    line BLOB NOT NULL
                )
            """)
            restored = []
            referenced = set()
            for manifest_name, expected_type in [
                (legacy_manifest, "legacy_raw_jsonl_backfill"),
                *((name, "police_raw_run_segment") for name in run_manifests),
            ]:
                item = restore_one(container, manifest_name, expected_type, db, temp_dir)
                if item["blob"] in referenced:
                    raise RuntimeError(f"Duplicate manifest reference: {item['blob']}")
                referenced.add(item["blob"])
                restored.append(item)
            if referenced != raw_objects:
                raise RuntimeError(
                    f"Azure inventory mismatch: unreferenced={sorted(raw_objects - referenced)} "
                    f"missing={sorted(referenced - raw_objects)}"
                )
            db.commit()

            total_rows = db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            unique_ids = db.execute("SELECT COUNT(DISTINCT event_id) FROM records").fetchone()[0]
            versions_by_id = db.execute(
                "SELECT event_id, COUNT(*) AS n FROM records GROUP BY event_id"
            ).fetchall()
            version_histogram = Counter(count for _, count in versions_by_id)
            duplicate_rows = db.execute("""
                SELECT COALESCE(SUM(n - 1), 0) FROM (
                    SELECT COUNT(*) AS n FROM records
                    GROUP BY retrieved_at, event_id, payload_sha256, line
                    HAVING COUNT(*) > 1
                )
            """).fetchone()[0]
            missing_payload_hash = db.execute(
                "SELECT COUNT(*) FROM records WHERE payload_sha256 = ''"
            ).fetchone()[0]

            output_digest = hashlib.sha256()
            output_bytes = 0
            with gzip.open(output_jsonl, "wb", compresslevel=6) as output:
                cursor = db.execute("""
                    SELECT line FROM records
                    ORDER BY retrieved_at COLLATE BINARY, event_id COLLATE BINARY,
                             payload_sha256 COLLATE BINARY, line
                """)
                for (line,) in cursor:
                    output.write(line)
                    output_digest.update(line)
                    output_bytes += len(line)
            db.close()

        output_compressed_sha, output_compressed_bytes = sha256_file(output_jsonl)
        report = {
            "schema_version": 1,
            "status": "passed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "storage_account": ACCOUNT,
            "container": CONTAINER,
            "ordering": ["retrieved_at", "event_id", "payload_sha256", "original_line"],
            "preserves_all_versions": True,
            "source_objects": restored,
            "source_manifest_count": len(restored),
            "source_row_count_sum": sum(item["rows"] for item in restored),
            "restored_record_count": total_rows,
            "unique_event_id_count": unique_ids,
            "event_ids_with_multiple_versions": sum(1 for _, count in versions_by_id if count > 1),
            "version_count_histogram": {str(k): v for k, v in sorted(version_histogram.items())},
            "exact_duplicate_record_count": duplicate_rows,
            "records_missing_payload_sha256": missing_payload_hash,
            "restored_raw_bytes": output_bytes,
            "restored_raw_sha256": output_digest.hexdigest(),
            "restored_gzip_bytes": output_compressed_bytes,
            "restored_gzip_sha256": output_compressed_sha,
            "inventory_match": True,
            "all_source_segments_verified": True,
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"restore_test=passed source_objects={len(restored)} records={total_rows} "
            f"unique_event_ids={unique_ids} multi_version_event_ids={report['event_ids_with_multiple_versions']} "
            f"exact_duplicate_records={duplicate_rows} restored_raw_sha256={output_digest.hexdigest()}"
        )
    finally:
        service.close()
        credential.close()


if __name__ == "__main__":
    main()
