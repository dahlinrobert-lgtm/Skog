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

Apply `db/schema.sql` first, then `db/migrations/002_observation_history.sql`, then `db/migrations/003_atomic_page_commit.sql` in the Supabase SQL editor.

Migration 002 adds:
- `source_observation_history`: append-only snapshots/change records, separate from the current-state row in `source_observations`.
- `scan_sessions`: persisted run count, page size, checkpoint, status and diagnostics.
- `scan_seen_ids`: per-scan unique source IDs to detect overlap/duplicate pages without a giant JSON checkpoint.
- A database trigger preventing a completed scan from being reopened and checkpoints from moving backwards.
- Migration 003 adds service-role-only RPCs to start a scan, commit a complete page atomically, finish only after full ID coverage, and record failed scans. The page transaction writes normalized IDs, current state, change history, and checkpoint together.

The migration deliberately creates no end-user policies for worker-owned tables. Use the service-role key only in a server-side worker. This migration does not itself run ingestion or send notifications. The scan worker must only set a scan to `complete` after the count, page coverage, transfer-limit and ID-integrity checks all pass. A source-count change invalidates an in-progress checkpoint; restart the scan rather than mixing different source snapshots.

## Production adapters and explicit manual entrypoint

`src/supabase-adapters.mjs` implements the ArcGIS source adapter and service-role Supabase REST/RPC store. It restores a compact checkpoint from `scan_sessions`; it does not download the full `scan_seen_ids` table on each resume. The database remains authoritative for cross-page duplicate detection through the unique `(scan_id, source_id)` key and the atomic page RPC. The pure in-memory planner retains full ID checking for deterministic unit tests. Adapter contract tests run in the normal test suite.

`scripts/run-scan.mjs` is deliberately not attached to the scheduled workflow. It exits before network/database access unless `SKOGSKOLL_ENABLE_INGESTION=YES`, `SKOGSKOLL_SCAN_MODE=baseline|incremental`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are explicitly provided. Default run budget is 10 pages of 500 records, to be resumed by a subsequent manual invocation. Use the service-role key only in a trusted server environment; never put it in the frontend or GitHub Pages. No secrets are configured by this commit.

Transient network and server errors preserve the last committed checkpoint; known source-integrity violations stop the session. A source count check cannot prove snapshot consistency when the source changes and its count coincidentally stays constant, so a completed scan is a validated offset-pagination pass, not a transactionally consistent snapshot of the external ArcGIS service.

## Recovering a stale running session

A process that is terminated without handling an exception may leave its database session in `running`, and the unique one-running-session-per-source index correctly blocks a second session. Migration 003 therefore provides the service-role-only RPC `skogskoll_recover_stale_scan(p_source, p_stale_before, p_reason)`. It returns no row unless a session for that source has an `updated_at` older than the supplied timestamp. It marks the matching session and its poll run failed for audit; it does **not** delete history or unseen records.

Use this only after independently confirming that no worker is still running for the source. The old seen-ID ledger belongs to the old scan ID, so recovery does not resume that offset into a new session: run a fresh bounded scan from offset 0. Previously committed observations remain idempotent: existing IDs are classified as unchanged or changed, not inserted as new records. The RPC does not activate alerts or deactivate observations.

## Bounded worker orchestration core

`src/scan-worker-core.mjs` coordinates one bounded batch using injected source and store adapters. It checks the source count before each page and again before completion, validates page IDs, and returns `in_progress` when the per-run page budget is reached. It never sends alerts.

The storage adapter is required to implement `commitPage()` as one database transaction: upsert current observations, append observation history, register each seen source ID, and persist the next checkpoint together. If that atomic contract is not available, do not run the worker against production data. The core alone does not connect to Supabase and does not claim to persist anything.

Current status: orchestration core and mock-adapter tests are in the repository. The transactional SQL primitives are now committed in migration 003. The production Supabase source/store adapter, SQL execution validation against a real Supabase project, and safe manual run entrypoint are still required before any full scan can run. Do not enable full import or alerts yet. Keep the existing source probe separate and keep alerts disabled.
