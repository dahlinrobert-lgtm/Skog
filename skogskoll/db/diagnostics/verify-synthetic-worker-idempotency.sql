-- Read-only idempotency audit for the second synthetic worker smoke run.
-- Run only in the dedicated skogskoll-test Supabase project, after the second
-- GitHub Actions dispatch has completed successfully.
-- SELECT-only: this script performs no inserts, updates, deletes or RPC calls.
--
-- Reuses the fixed source and fixture IDs from run #45259733480 and #45265602291.
-- Expected second-run outcome:
--   latest scan/poll run complete/success; fetched=2; inserted=0; updated=0
--   latest scan has exactly 2 seen IDs
--   exactly 2 current observations remain
--   exactly 2 immutable history rows remain (both baseline from the first run)
--   exactly 2 snapshot envelopes exist for the synthetic source (one per complete run)

-- 1) Latest scan and linked poll run. Confirm this is the new run, not the baseline run.
select
  s.id as scan_id,
  s.source,
  s.source_count,
  s.page_size,
  s.next_offset,
  s.fetched_count as scan_fetched_count,
  s.status as scan_status,
  s.completed_at,
  s.snapshot_registered_at,
  s.poll_run_id,
  p.status as poll_run_status,
  p.fetched_count as poll_run_fetched_count,
  p.inserted_count,
  p.updated_count,
  p.finished_at
from public.scan_sessions s
left join public.poll_runs p on p.id = s.poll_run_id
where s.source = 'skogskoll:synthetic:worker-smoke-test'
order by s.updated_at desc
limit 1;

-- 2) Reconcile current fixture state and all retained history/envelopes.
with latest_scan as (
  select id
  from public.scan_sessions
  where source = 'skogskoll:synthetic:worker-smoke-test'
  order by updated_at desc
  limit 1
)
select
  (select count(*) from public.scan_seen_ids
   where scan_id = (select id from latest_scan)) as latest_scan_seen_id_count,
  (select count(*) from public.source_observations
   where source = 'skogskoll:synthetic:worker-smoke-test'
     and source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')) as current_observation_count,
  (select count(*) from public.source_observation_history
   where source = 'skogskoll:synthetic:worker-smoke-test'
     and source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')) as total_history_row_count,
  (select count(*) from public.snapshot_envelopes
   where source = 'skogskoll:synthetic:worker-smoke-test') as total_snapshot_envelope_count;

-- 3) Current observations must remain exactly the two original fixture records.
select
  id, source, source_id, first_seen_at, last_seen_at,
  active, last_run_id, content_hash, attributes
from public.source_observations
where source = 'skogskoll:synthetic:worker-smoke-test'
  and source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')
order by source_id;

-- 4) No new history rows should have been appended by the unchanged second run.
select
  h.id, h.source_id, h.event_type, h.observed_at,
  h.poll_run_id, h.content_hash
from public.source_observation_history h
where h.source = 'skogskoll:synthetic:worker-smoke-test'
  and h.source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')
order by h.source_id, h.observed_at, h.id;

-- 5) Both complete runs should have their own immutable envelope.
select
  snapshot_id, run_id, scan_session_id, source, product,
  captured_at, status, coverage_key, schema_version, identity_version,
  comparability_key, customer_visibility, rights_evidence_ref, created_at
from public.snapshot_envelopes
where source = 'skogskoll:synthetic:worker-smoke-test'
order by created_at;
