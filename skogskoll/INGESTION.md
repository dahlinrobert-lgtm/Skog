# Ingestion and alert safety

The pure ingestion core is in `src/observation-core.mjs`; run tests with:

```sh
node --test skogskoll/tests/*.test.mjs
```

## Invariants
- Identity is `source + source_id`; never deduplicate solely by geometry or parcel name.
- Missing source IDs are rejected and counted; never invent random IDs.
- An unchanged record is a touch, not a new alert.
- Changed attributes or geometry should update the stored record and create an auditable change event later; they are not automatically a new-application alert.
- Initial baseline import must not alert on historical records. Alerting stays disabled until baseline is explicitly established.
- A failed or incomplete poll must never mark unseen records inactive. Reconciliation may only follow a complete successful scan.
- Preserve `Inkomdatum` as a source value until live metadata confirms its type and meaning.
- This pure core is database-agnostic. Supabase persistence and transactional alert-outbox handling are a later layer; no email or push notifications are sent here.

## Database groundwork (migration 002)

Apply `db/schema.sql` first, then `db/migrations/002_observation_history.sql` in the Supabase SQL editor.

Migration 002 adds:
- `source_observation_history`: append-only snapshots/change records, separate from the current-state row in `source_observations`.
- `scan_sessions`: persisted run count, page size, checkpoint, status and diagnostics.
- `scan_seen_ids`: per-scan unique source IDs to detect overlap/duplicate pages without a giant JSON checkpoint.
- A database trigger preventing a completed scan from being reopened and checkpoints from moving backwards.

The migration deliberately creates no end-user policies for worker-owned tables. Use the service-role key only in a server-side worker. This migration does not itself run ingestion or send notifications. The scan worker must only set a scan to `complete` after the count, page coverage, transfer-limit and ID-integrity checks all pass. A source-count change invalidates an in-progress checkpoint; restart the scan rather than mixing different source snapshots.
