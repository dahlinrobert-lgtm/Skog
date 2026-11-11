# Durable storage for the police-event raw archive

## Why this is required

The append-only `data/police_events/raw_events.jsonl` file exceeded GitHub's 100 MB per-file limit during the full-history workflow on 2026-11-11. The collector and quality-report steps completed; only the final Git push failed.

The raw JSONL is a version history, not a generated convenience file. It contains each newly observed event payload and subsequent changed payloads, with retrieval timestamp and SHA-256. It must therefore be retained append-only and must not be truncated or rewritten as part of this migration.

## Required target architecture

- Keep small, reproducible analysis outputs in Git: `events.csv`, `wildlife_candidates.csv`, `wildlife_incidents.csv`, and `run_quality_report.json`, subject to repository-size review.
- Move raw JSONL history to durable object storage (Azure Blob Storage) in a dedicated container/prefix for police events.
- Use GitHub Actions OIDC for Azure authentication; do not store storage account keys in the repository.
- Upload a new immutable daily/run segment rather than repeatedly replacing a single large JSONL object. Include run ID, retrieval timestamp, row count, byte count and SHA-256 in a small manifest.
- Maintain an append-only manifest/index that identifies every committed segment and its hash. A retry must be idempotent: same run segment/hash must not create duplicate logical history.
- Verify the uploaded blob by downloading it or checking provider-supported content length and hash metadata before marking a segment complete.
- Keep a local temporary working copy only for processing within the Actions job. Do not stage the full raw history in Git.
- Backfill the existing Git raw archive to object storage before removing it from tracked Git history. Verify source and destination SHA-256 and byte counts first.
- Do not delete or rewrite existing Git history as part of the first migration PR. Any later Git-history rewrite requires an explicit backup, verification and coordinated repository maintenance.

## Migration sequence

1. Confirm Azure container, OIDC role assignment and lifecycle/immutability settings.
2. Add a storage adapter with tests for deterministic segment naming, append-only behavior, retry idempotency, manifest generation and hash verification.
3. Backfill all currently tracked raw JSONL history and verify exact SHA-256/byte count.
4. Update the workflow so the collector writes new run segments to Azure and never commits raw JSONL.
5. Stop tracking the legacy raw JSONL in Git only after successful backfill verification. Add the path to `.gitignore`.
6. Keep event/candidate CSVs and the compact quality report in Git only while they remain below repository file-size limits; otherwise export them as versioned, compact artifacts as well.
7. Run a full-history test, verify the manifest and report, then a scheduled incremental test.

## Safety and interpretation

- Do not count a failed workflow as a successful archive publication.
- Do not infer complete API history from the number of records or a successful run.
- Wildlife extraction results remain candidates, not confirmed collisions.
- Preserve source event IDs, retrieval timestamps and payload hashes so later changes can be audited.
