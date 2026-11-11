# Durable storage for the police-event raw archive

## Migration status

The initial Azure migration and a subsequent incremental run have both been verified.

- Legacy backfill: `legacy/raw_events.jsonl.gz` and `legacy/manifest.json` were uploaded and verified against the original 20,000-row raw file (78,655,286 bytes; SHA-256 `33820ff172a0274ffe339b3676fbfeb3106ebf409cb608184eada494ff496ebd`).
- Incremental run: run `43041322803` uploaded and verified its immutable run segment in Azure.
- Follow-up run: run `43042048315` uploaded and verified 500 rows (2,038,197 raw bytes; SHA-256 `6711c51bf13b43d543b269ed514a30ca95304e201ac63c70ecad5e75045f498d`) and successfully published analysis outputs to Git.
- Azure account/container: `stskogkolldata` / `police-events`.
- The legacy raw JSONL is being removed from the current Git working tree only after the verified Azure backfill. This does not rewrite old Git commits.

## Required target architecture

- Keep small, reproducible analysis outputs in Git: `events.csv`, `wildlife_candidates.csv`, `wildlife_incidents.csv`, and `run_quality_report.json`, subject to repository-size review.
- Store raw JSONL history in Azure Blob Storage in the dedicated `police-events` container.
- Use GitHub Actions OIDC for Azure authentication; do not store storage account keys in the repository.
- Upload a new immutable daily/run segment rather than replacing a single large JSONL object. Include run ID, retrieval timestamp, row count, byte count and SHA-256 in a manifest.
- Keep each segment and manifest under its run/attempt-specific prefix. Do not overwrite an existing run segment.
- Verify uploaded blobs by downloading and checking raw byte count and SHA-256 before marking a segment complete.
- Keep a local temporary working copy only for processing within the Actions job. Never stage the full raw history in Git.
- The collector requires an explicit `--raw-output` path. The workflow supplies a unique temporary path for every run.

## Operational safeguards

- Do not delete Azure legacy or run segments as part of Git cleanup.
- Do not rewrite Git history as part of this migration. Old commits may still contain the historical raw file; removing it from the current tree prevents future commits from carrying it.
- Keep `data/police_events/raw_events.jsonl` in `.gitignore` as a guard against accidental reintroduction.
- A retry must remain isolated by run ID and attempt. Verify Azure upload and hash before publishing analysis outputs.
- Retain the normalized CSVs and compact quality report in Git only while they remain below repository file-size limits; otherwise export them as versioned compact artifacts as well.

## Safety and interpretation

- Do not count a failed workflow as a successful archive publication.
- Do not infer complete API history from the number of records or a successful run.
- Wildlife extraction results remain candidates, not confirmed collisions.
- Preserve source event IDs, retrieval timestamps and payload hashes so later changes can be audited.


## Independent Azure archive audit

The workflow `Police Azure archive audit` inventories the legacy object and all run segments from their manifests. It checks manifest schema and archive type, blob existence, blob size and metadata consistency, manifest-to-object pairing, and unreferenced or missing raw objects. The scheduled monthly run performs this metadata/inventory audit without downloading the full archive.

A manual run with `deep=true` additionally downloads each gzip object, decompresses it incrementally, and verifies the original raw byte count and SHA-256 against its manifest. This is the stronger end-to-end integrity check and may take longer as the archive grows.

The audit deliberately does not infer API-history completeness, event uniqueness across different runs, or collision truth from row counts. Repeated event versions across snapshots are expected; reconstruction and deduplication must use event IDs, retrieval timestamps, and payload hashes rather than summing segment row counts as unique events.


## Restore and reconstruction test

The manual workflow `Police Azure archive restore test` reconstructs a combined JSONL gzip from the verified legacy object and all run segments. It rechecks each manifest, Azure metadata, compressed-object SHA-256 and size, decompressed raw SHA-256 and size, and row count before accepting records.

Records are retained as original JSONL lines and ordered deterministically by retrieval timestamp, event ID, payload hash, and original line. No event versions are discarded. A SQLite temporary database is used for sorting so the workflow does not need to hold the complete archive in memory.

The restore report distinguishes:
- source rows from unique event IDs;
- event IDs with multiple archived versions;
- exact duplicate records;
- records missing payload hashes;
- output byte count and SHA-256.

The workflow is manual and read-only against Azure. It uploads the reconstructed gzip and report as a GitHub Actions artifact with 30-day retention. This is a restore test artifact, not a replacement for the durable Azure source archive. A successful run proves that the currently inventoried objects can be reconstructed and verified; it does not prove complete historical API coverage.
