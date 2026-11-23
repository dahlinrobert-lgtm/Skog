-- Read-only audit for the controlled one-record-change synthetic worker run.
-- Run only in the dedicated skogskoll-test Supabase SQL Editor after the
-- workflow completes with fixture_variant=change_feature_001.
-- SELECT-only: no inserts, updates, deletes, RPC calls or cleanup.
--
-- Expected relative to the verified three-run baseline:
--   scan complete / poll success; fetched=2; inserted=0; updated=1
--   current observations remain 2; history rows become 3; envelopes become 4
--   exactly one new 'changed' history row for worker-smoke-feature-001
--   worker-smoke-feature-002 remains unchanged; both baseline rows remain

-- 1) Latest scan and poll run.
select
  s.id as scan_id, s.source, s.source_count, s.page_size,
  s.next_offset, s.fetched_count as scan_fetched_count,
  s.status as scan_status, s.completed_at, s.snapshot_registered_at,
  s.poll_run_id, p.status as poll_run_status,
  p.fetched_count as poll_run_fetched_count,
  p.inserted_count, p.updated_count, p.finished_at
from public.scan_sessions s
left join public.poll_runs p on p.id = s.poll_run_id
where s.source = 'skogskoll:synthetic:worker-smoke-test'
order by s.updated_at desc
limit 1;

-- 2) Aggregate counts after the changed-content run.
select
  (select count(*) from public.scan_seen_ids
   where scan_id = (
     select id from public.scan_sessions
     where source = 'skogskoll:synthetic:worker-smoke-test'
     order by updated_at desc limit 1
   )) as latest_scan_seen_id_count,
  (select count(*) from public.source_observations
   where source = 'skogskoll:synthetic:worker-smoke-test'
     and source_id in ('worker-smoke-feature-001','worker-smoke-feature-002')) as current_observation_count,
  (select count(*) from public.source_observation_history
   where source = 'skogskoll:synthetic:worker-smoke-test'
     and source_id in ('worker-smoke-feature-001','worker-smoke-feature-002')) as total_history_row_count,
  (select count(*) from public.snapshot_envelopes
   where source = 'skogskoll:synthetic:worker-smoke-test') as total_snapshot_envelope_count;

-- 3) Current state: feature 001 should have sequence=101; feature 002 stays sequence=2.
select id, source_id, first_seen_at, last_seen_at, active, last_run_id, content_hash, attributes
from public.source_observations
where source = 'skogskoll:synthetic:worker-smoke-test'
  and source_id in ('worker-smoke-feature-001','worker-smoke-feature-002')
order by source_id;

-- 4) Full history: exactly one 'changed' row should be added for feature 001.
select id, source_id, event_type, observed_at, poll_run_id, content_hash, attributes
from public.source_observation_history
where source = 'skogskoll:synthetic:worker-smoke-test'
  and source_id in ('worker-smoke-feature-001','worker-smoke-feature-002')
order by source_id, observed_at, id;

-- 5) Snapshot envelopes: four complete envelopes should now exist.
select snapshot_id, run_id, scan_session_id, source, product, captured_at,
       status, coverage_key, schema_version, identity_version,
       comparability_key, customer_visibility, rights_evidence_ref, created_at
from public.snapshot_envelopes
where source = 'skogskoll:synthetic:worker-smoke-test'
order by created_at;
