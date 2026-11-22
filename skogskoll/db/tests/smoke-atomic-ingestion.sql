-- Skogskoll PostgreSQL smoke test.
-- Run ONLY against a disposable Supabase test project after applying:
--   db/schema.sql
--   db/migrations/002_observation_history.sql
--   db/migrations/003_atomic_page_commit.sql
--   db/migrations/005_snapshot_envelope_registry.sql
-- All data inserted by this script is deleted before the transaction rolls back.
-- The whole test runs inside a transaction and ends with ROLLBACK.

begin;

do $test$
declare
  v_source text := 'skogskoll:sql-smoke-test-' || gen_random_uuid()::text;
  v_scan uuid;
  v_run uuid;
  v_result record;
  v_seen integer;
  v_history integer;
  v_obs integer;
  v_recovered integer;
  v_feature jsonb;
  v_changed_feature jsonb;
  v_scan2 uuid;
  v_run2 uuid;
  v_scan3 uuid;
  v_run3 uuid;
  v_metadata jsonb;
  v_envelope jsonb;
  v_snapshot_id text;
  v_ids jsonb;
  v_hash text := repeat('a', 64);
  v_now timestamptz := now();
begin
  -- Start a bounded scan over a one-record test source.
  select scan_id, poll_run_id into v_scan, v_run
  from public.skogskoll_start_scan(v_source, 3, 1, 'baseline');

  if v_scan is null or v_run is null then
    raise exception 'start_scan did not allocate IDs';
  end if;

  v_feature := jsonb_build_array(jsonb_build_object(
    'source', v_source,
    'source_id', 'smoke-1',
    'content_hash', v_hash,
    'source_received_at', '2026-10-25',
    'attributes', jsonb_build_object('test', true, 'label', 'baseline smoke test'),
    'geometry', null
  ));
  v_ids := jsonb_build_array('smoke-1');

  select * into v_result
  from public.skogskoll_commit_page(
    v_scan, 0, 0, 1, 1, v_feature, v_ids, v_now
  );
  if v_result.inserted_count <> 1 or v_result.changed_count <> 0 or v_result.unchanged_count <> 0 then
    raise exception 'unexpected baseline page counts: %', row_to_json(v_result);
  end if;

  select count(*) into v_seen from public.scan_seen_ids
  where scan_id = v_scan and source_id = 'smoke-1';
  select count(*) into v_obs from public.source_observations
  where source = v_source and source_id = 'smoke-1';
  select count(*) into v_history from public.source_observation_history
  where source = v_source and source_id = 'smoke-1' and poll_run_id = v_run;
  if v_seen <> 1 or v_obs <> 1 or v_history <> 1 then
    raise exception 'page transaction did not persist ID/current/history together (seen %, obs %, hist %)', v_seen, v_obs, v_history;
  end if;

  -- Duplicate IDs within a page must be rejected without leaking ledger rows.
  begin
    perform * from public.skogskoll_commit_page(
      v_scan, 1, 1, 3, 3,
      jsonb_build_array(
        jsonb_build_object('source', v_source, 'source_id', 'smoke-2', 'content_hash', v_hash, 'attributes', '{}'::jsonb, 'geometry', null),
        jsonb_build_object('source', v_source, 'source_id', 'smoke-3', 'content_hash', v_hash, 'attributes', '{}'::jsonb, 'geometry', null)
      ),
      jsonb_build_array('smoke-2', 'smoke-2'),
      v_now + interval '1 minute'
    );
    raise exception 'duplicate IDs within a page were unexpectedly accepted';
  exception
    when others then
      if sqlerrm = 'duplicate IDs within a page were unexpectedly accepted' then raise; end if;
      if position('duplicate IDs within page' in sqlerrm) = 0 then raise; end if;
  end;

  select count(*) into v_seen from public.scan_seen_ids where scan_id = v_scan;
  if v_seen <> 1 then raise exception 'rejected duplicate page leaked into seen-ID ledger'; end if;

  -- Commit the two remaining distinct IDs to complete the 3-record baseline.
  select * into v_result
  from public.skogskoll_commit_page(
    v_scan, 1, 1, 3, 3,
    jsonb_build_array(
      jsonb_build_object('source', v_source, 'source_id', 'smoke-2', 'content_hash', repeat('c',64), 'attributes', '{}'::jsonb, 'geometry', null),
      jsonb_build_object('source', v_source, 'source_id', 'smoke-3', 'content_hash', repeat('d',64), 'attributes', '{}'::jsonb, 'geometry', null)
    ),
    jsonb_build_array('smoke-2', 'smoke-3'),
    v_now + interval '1 minute'
  );
  if v_result.inserted_count <> 2 then raise exception 'valid second page was not committed'; end if;

  -- Finish the first scan before starting another session for the same source.
  perform public.skogskoll_finish_scan(v_scan);

  -- A changed payload on a new scan must update current state and append history.
  -- The source observation ID is stable across scans; run IDs are not.
  select scan_id, poll_run_id into v_scan2, v_run2
  from public.skogskoll_start_scan(v_source, 1, 1, 'incremental');

  v_changed_feature := jsonb_build_array(jsonb_build_object(
    'source', v_source,
    'source_id', 'smoke-1',
    'content_hash', repeat('b', 64),
    'source_received_at', '2026-10-25',
    'attributes', jsonb_build_object('test', true, 'label', 'changed payload'),
    'geometry', null
  ));
  select * into v_result from public.skogskoll_commit_page(
    v_scan2, 0, 0, 1, 1, v_changed_feature, v_ids, v_now + interval '2 minutes'
  );
  if v_result.changed_count <> 1 or v_result.inserted_count <> 0 then
    raise exception 'changed payload did not classify as changed: %', row_to_json(v_result);
  end if;
  if not exists (
    select 1 from public.source_observation_history
    where source = v_source and source_id = 'smoke-1'
      and poll_run_id = v_run2 and event_type = 'changed'
  ) then raise exception 'changed payload history event missing'; end if;
  perform public.skogskoll_finish_scan(v_scan2);

  -- Current committed offset is complete; finish must verify ledger coverage.
  perform public.skogskoll_finish_scan(v_scan);
  if not exists (select 1 from public.scan_sessions where id = v_scan and status = 'complete') then
    raise exception 'finish_scan did not complete a fully covered scan';
  end if;
  if not exists (select 1 from public.poll_runs where id = v_run and status = 'success') then
    raise exception 'finish_scan did not mark poll run successful';
  end if;

  -- A terminal complete run with persisted metadata registers one immutable envelope.
  v_metadata := jsonb_build_object(
    'product', 'harvest_notifications',
    'endpoint', 'https://example.test/MapServer/0',
    'layer', '0',
    'query_definition', 'where=1=1',
    'coverage_key', 'unfiltered-layer-query-v1',
    'schema_version', 'schema-v1',
    'identity_version', 'oid-v1',
    'customer_visibility', 'not_assessed',
    'rights_evidence_ref', null
  );
  select scan_id, poll_run_id into v_scan3, v_run3
  from public.skogskoll_start_scan(v_source || ':snapshot', 0, 1, 'baseline', v_metadata);

  -- Metadata is immutable on both run and scan records after allocation.
  begin
    update public.scan_sessions
    set diagnostics = diagnostics || jsonb_build_object(
      'snapshot_metadata', jsonb_set(v_metadata, '{schema_version}', '"tampered"')
    )
    where id = v_scan3;
    raise exception 'scan snapshot metadata was unexpectedly changed';
  exception
    when others then
      if sqlerrm = 'scan snapshot metadata was unexpectedly changed' then raise; end if;
      if position('snapshot metadata is immutable' in sqlerrm) = 0 then raise; end if;
  end;
  begin
    update public.poll_runs
    set diagnostics = diagnostics || jsonb_build_object(
      'snapshot_metadata', jsonb_set(v_metadata, '{schema_version}', '"tampered"')
    )
    where id = v_run3;
    raise exception 'run snapshot metadata was unexpectedly changed';
  exception
    when others then
      if sqlerrm = 'run snapshot metadata was unexpectedly changed' then raise; end if;
      if position('snapshot metadata is immutable' in sqlerrm) = 0 then raise; end if;
  end;

  perform public.skogskoll_finish_scan(v_scan3);

  select jsonb_build_object(
    'snapshot_id', 'skogskoll-worker:' || v_run3::text || ':' || v_scan3::text,
    'run_id', v_run3::text,
    'source', v_source || ':snapshot',
    'product', v_metadata->>'product',
    'endpoint', v_metadata->>'endpoint',
    'layer', v_metadata->>'layer',
    'query_definition', v_metadata->>'query_definition',
    'captured_at', to_char(now(), 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    'status', 'complete',
    'coverage_key', v_metadata->>'coverage_key',
    'schema_version', v_metadata->>'schema_version',
    'identity_version', v_metadata->>'identity_version',
    'comparability_key', 'smoke-comparability-key',
    'customer_visibility', 'not_assessed',
    'rights_evidence_ref', null,
    'diagnostics', jsonb_build_object('scan_session_id', v_scan3)
  ) into v_envelope;

  v_snapshot_id := public.skogskoll_register_snapshot(v_scan3, v_envelope);
  if v_snapshot_id <> v_envelope->>'snapshot_id' then
    raise exception 'snapshot registration returned unexpected identity';
  end if;
  -- A retry with identical content returns the same immutable row.
  if public.skogskoll_register_snapshot(v_scan3, v_envelope) <> v_snapshot_id then
    raise exception 'idempotent snapshot registration returned a different ID';
  end if;
  if not exists (
    select 1 from public.snapshot_envelopes
    where scan_session_id = v_scan3 and status = 'complete'
      and customer_visibility = 'not_assessed'
  ) then raise exception 'complete snapshot envelope was not persisted'; end if;
  if not exists (
    select 1 from public.scan_sessions
    where id = v_scan3 and snapshot_registered_at is not null
  ) then raise exception 'snapshot registration timestamp was not recorded'; end if;

  -- Even a privileged direct update cannot rewrite a registered snapshot.
  begin
    update public.snapshot_envelopes set status = 'partial' where scan_session_id = v_scan3;
    raise exception 'immutable snapshot envelope was unexpectedly updated';
  exception
    when others then
      if sqlerrm = 'immutable snapshot envelope was unexpectedly updated' then raise; end if;
      if position('snapshot envelopes are immutable' in sqlerrm) = 0 then raise; end if;
  end;

  -- Recovery should mark an intentionally stale running session failed.
  select scan_id, poll_run_id into v_scan, v_run
  from public.skogskoll_start_scan(v_source || ':stale', 2, 1, 'incremental');

  -- The checkpoint trigger deliberately refreshes updated_at on updates.
  -- Disable it only for this synthetic stale-session fixture, then restore it immediately.
  alter table public.scan_sessions disable trigger trg_guard_skogskoll_scan_session;
  update public.scan_sessions set updated_at = now() - interval '2 days' where id = v_scan;
  alter table public.scan_sessions enable trigger trg_guard_skogskoll_scan_session;
  select count(*) into v_recovered
  from public.skogskoll_recover_stale_scan(v_source || ':stale', now() - interval '1 day', 'sql_smoke_recovery');

  if v_recovered <> 1 then raise exception 'stale recovery did not return exactly one recovered session'; end if;
  if not exists (select 1 from public.scan_sessions where id = v_scan and status = 'failed') then
    raise exception 'stale recovery did not fail the session';
  end if;
  if not exists (select 1 from public.poll_runs where id = v_run and status = 'failed') then
    raise exception 'stale recovery did not fail the poll run';
  end if;

  raise notice 'Skogskoll SQL smoke test passed: atomic page, duplicate guard, finish coverage, immutable snapshot registration and stale recovery';
end;
$test$;

rollback;
