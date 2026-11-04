# Kungjort pilot archive and synchronization

## Scope

The collector stores API document metadata and full-text/detail responses for the five pilot municipalities. It does not download original binary files. The archive is append-only: every fetched document detail and every deletion tombstone is stored as a compressed JSONL run file. The current pagination and change cursors are stored in `data/kungjort/state.json`.

The API's `/coverage` response is observational and explicitly does not guarantee complete coverage. Do not interpret absence from coverage as proof that a municipality, organ, year or document type has no records.

## Initial bootstrap

1. Run **Actions → Sync Kungjort pilot archive** with mode `bootstrap`.
2. The collector reads `/documents?limit=100` and follows `next_cursor`.
3. It saves the `changes_cursor` from the first page before proceeding, then fetches `/documents/{id}` for every list record.
4. Each invocation processes at most five pages by default and persists the next pagination cursor. Re-run bootstrap until the state reports `bootstrap_complete: true`.
5. Only after the historical export is complete may the changes mode run.

The first-page changes cursor is essential: after bootstrap, daily change replay starts from that original cursor so changes made during the historical export are not missed.

## Daily change sync

The scheduled run requests `/changes` using the saved cursor. Upserts trigger a fresh detail fetch; deletes are stored as tombstones and do not erase earlier records. Unknown change operations or missing/unchanged cursors fail closed rather than silently advancing the checkpoint.

The collector honours `Retry-After` for HTTP 429 and 503 responses and uses bounded exponential backoff when the header is absent. API credentials are read only from the `KUNGJORT_API_KEY` GitHub secret and are never written to the archive.

## Storage layout

- `data/kungjort/state.json`: bootstrap and change checkpoints.
- `data/kungjort/bootstrap/*.jsonl.gz`: immutable batches of historical document details.
- `data/kungjort/changes/*.jsonl.gz`: immutable batches of document updates and tombstones.

Each archive record contains a capture timestamp and the original API response. Keep the original document ID and revision; do not deduplicate distinct IDs solely because they share a diary number. Any later normalization should be a derived layer, not a mutation of the raw archive.

## Pilot and licensing safeguards

This workflow does not fetch original binary files or republish source documents. Before using the data in a commercial service, retaining it beyond the pilot, or exposing full text externally, obtain written clarification from Kungjort on permitted storage, derived analytics, retention and redistribution.

## Operational note

Bootstrap defaults to five pages (up to 500 documents) per run to limit load on the shared API quota. Continue with manual bootstrap runs until completion. The scheduled daily changes sync is intentionally blocked until the bootstrap is complete.
