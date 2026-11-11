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


## Verified restore baseline — 2026-11-11

The first complete end-to-end reconstruction passed in GitHub Actions run
[43050217200](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43050217200)
(workflow run #9, commit `59e5c7d06802d929d76ada6d14512fd0862c656c`).

Verified results from the uploaded `restore_report.json`:

- Status: `passed`; inventory match: `true`; all source segments verified: `true`.
- Four source objects reconstructed: one legacy object and three immutable run segments.
- 22,000 parsed records from 21,500 physical source lines; the legacy object contains 20,500 parsed records over 20,000 physical lines.
- 10,000 unique event IDs; all 10,000 have multiple archived versions.
- Version histogram: 9,499 IDs with 2 versions, 1 with 3, 1 with 5, and 499 with 6.
- Exact duplicate records: 0; records missing payload SHA-256: 0.
- Restored raw stream: 83,031,377 bytes; SHA-256
  `7aa212adf851502aa70e39b6ac3cebca7bffbcd32afe0fe9d0bf48d1dfe55196`.
- Restored gzip: 11,944,071 bytes; SHA-256
  `2c13a2411e823a8ea0dbea96c86762ec30e866125b2b58677c86be204293017a`.

The legacy manifest's `row_count=20,000` records physical lines, whereas the
restore parser identifies 20,500 JSON records in that object. This distinction
is intentional and is reported separately; raw bytes and SHA-256 still match
the legacy manifest exactly.

The run artifact contains `restored_raw_events.jsonl.gz` and
`restore_report.json` and is retained by GitHub Actions for 30 days. The
durable source remains the immutable Azure archive. The report's summary and
hashes are recorded here as the long-lived operational checkpoint.

## Recurring restore verification

The restore workflow runs automatically once per quarter (January, April,
July and October) and remains manually dispatchable. Each run performs the
same read-only reconstruction and verification against the current Azure
inventory. Review the workflow result and retain the run URL and report
summary in this document when a scheduled run completes.

A successful restore verifies integrity and reconstructability of the
currently inventoried archive objects. It does not prove that the upstream
API supplied a complete history or that event IDs represent distinct real
incidents.


## Historical version analysis — first run 2026-11-11

The first history analysis completed successfully in
[workflow run 43051685265](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43051685265).
Its artifact is police-event-history-43051685265.

The generated tables contained:

- 22,000 archived source observations.
- 10,000 unique event IDs.
- 10,024 distinct payload versions after collapsing 11,976 repeated observations with identical payload hashes.
- 22 event IDs with more than one distinct payload version: 20 with two versions and 2 with three versions.
- 10,000 first-observation rows and 24 payload-change transitions.
- No detected changes in the selected normalized fields during those 24 payload transitions. The initial analysis did not compare every nested source JSON field, so those transitions were marked payload_changed_unmapped, not as unchanged content.

This first run covers only the observations currently present in the four archived source objects. Most observations share a single collection timestamp from the legacy backfill, so they do not establish a long-term trend.

The next analysis revision compares nested source JSON paths as well as the normalized reporting fields. It will report exact changed paths and before/after values, while retaining payload-hash changes with no identifiable JSON-field diff as an explicit diagnostic category.


## Source-level change analysis — run #2, 2026-11-11

The refined history analysis completed in
[workflow run 43053147153](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43053147153).
The artifact is `police-event-history-43053147153`.

- 22,000 observations; 10,000 event IDs; 10,024 distinct payload versions.
- 11,976 observations repeat a payload hash already seen for the same event ID.
- 9,978 event IDs have one distinct version; 20 have two; 2 have three.
- 24 payload-change transitions were found across 22 event IDs.
- The normalized reporting fields did not change in these transitions, but source-level comparison found a difference in the original JSON for all 24 transitions.
- Payload changes without an identifiable source-field difference: 0.

The earlier summary counted the 10,000 first-observation rows as change transitions. The next builder revision separates first observations from actual subsequent transitions; until that correction is applied, use 24 as the verified number of actual payload-change transitions.

This remains a small set of source observations and is not a representative time series of all incidents. Missing events in later API responses are not classified as deletions.
