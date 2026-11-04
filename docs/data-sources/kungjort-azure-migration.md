# Migrate the existing Kungjort archive to Azure

## Purpose

Move the already-collected append-only archive from the public Git repository into the private Azure Storage Account `stskogkolldata`. The migration does not delete or modify local Git files. It is safe to rerun.

## Destination layout

- `kungjort-raw/bootstrap/*.jsonl.gz`: historical full-text/detail batches.
- `kungjort-changes/changes/*.jsonl.gz`: updates and tombstones.
- `metadata/kungjort/state.json`: bootstrap and changes cursors.

Each uploaded blob receives SHA-256 metadata. Existing blobs are accepted only if both SHA-256 metadata and byte size match. Conflicting content fails closed; the script never overwrites a different blob. The state checkpoint is uploaded last.

## Runbook

1. Merge the migration PR.
2. Open Actions → **Migrate Kungjort archive to Azure Blob Storage**.
3. Run once with `dry_run=true`; inspect the manifest for expected batches and total bytes.
4. Run again with `dry_run=false`.
5. Confirm the workflow reports every archive batch uploaded or already present and the checkpoint uploaded last.
6. Verify blob counts and hashes before enabling Azure-native ingestion.

## Security

The workflow uses GitHub OIDC and the `Storage Blob Data Contributor` role. No account key or client secret is used. The containers must remain private.

## Important

This migration copies the data into Azure but does not erase copies already committed to the public Git repository or its history. Do not delete the source until Azure validation is complete. Public Git history cleanup is a separate, coordinated operation.
