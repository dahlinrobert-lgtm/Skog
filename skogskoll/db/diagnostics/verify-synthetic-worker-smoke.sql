-- Read-only audit of the live synthetic worker smoke test.
-- Run in Supabase SQL Editor against the dedicated skogskoll-test project only.
-- This script contains SELECT statements only. It does not mutate or delete data.

-- Fixed identifiers from GitHub Actions run #45259733480.
-- Expected source: skogskoll:synthetic:worker-smoke-test
-- Expected scan:   1a53c3b2-fad4-47d1-afb4-9340dc50f15c

-- 1) Scan session + linked poll run + snapshot registration marker.
select
  s.id as scan_id,
  s.source,
  s.source_count,
  s.page_size,
  s.next_offset,
  s.fetched_count,
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
where s.id = '1a53c3b2-fad4-47d1-afb4-9340dc50f15c'
  and s.source = 'skogskoll:synthetic:worker-smoke-test';

-- 2) Exact expected current-state observations.
select
  id, source, source_id, first_seen_at, last_seen_at,
  active, last_run_id, content_hash, attributes
from public.source_observations
where source = 'skogskoll:synthetic:worker-smoke-test'
  and source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')
order by source_id;

-- 3) Seen-ID ledger for the scan (must contain exactly the two fixture IDs).
select scan_id, source_id, first_offset
from public.scan_seen_ids
where scan_id = '1a53c3b2-fad4-47d1-afb4-9340dc50f15c'
order by first_offset, source_id;

-- 4) Immutable observation history rows for the fixture and linked poll run.
select
  h.id, h.source, h.source_id, h.event_type, h.observed_at,
  h.poll_run_id, h.content_hash
from public.source_observation_history h
where h.source = 'skogskoll:synthetic:worker-smoke-test'
  and h.source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')
order by h.source_id, h.observed_at, h.id;

-- 5) Snapshot envelope: expected status complete, customer_visibility not_assessed.
select
  snapshot_id, run_id, scan_session_id, source, product,
  captured_at, status, coverage_key, schema_version, identity_version,
  comparability_key, customer_visibility, rights_evidence_ref, created_at
from public.snapshot_envelopes
where scan_session_id = '1a53c3b2-fad4-47d1-afb4-9340dc50f15c'
   or source = 'skogskoll:synthetic:worker-smoke-test'
order by created_at desc;

-- 6) Compact count reconciliation for the exact scan.
select
  (select count(*) from public.scan_seen_ids
   where scan_id = '1a53c3b2-fad4-47d1-afb4-9340dc50f15c') as seen_id_count,
  (select count(*) from public.source_observations
   where source = 'skogskoll:synthetic:worker-smoke-test'
     and source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')) as observation_count,
  (select count(*) from public.source_observation_history
   where source = 'skogskoll:synthetic:worker-smoke-test'
     and source_id in ('worker-smoke-feature-001', 'worker-smoke-feature-002')) as history_row_count,
  (select count(*) from public.snapshot_envelopes
   where scan_session_id = '1a53c3b2-fad4-47d1-afb4-9340dc50f15c') as snapshot_envelope_count;
