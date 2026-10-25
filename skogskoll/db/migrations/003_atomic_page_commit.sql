-- Skogskoll migration 003: atomic, service-role-only page commits.
-- Apply only after db/schema.sql and migrations/002_observation_history.sql.
-- This migration installs persistence primitives but does not start a scan.

alter table public.scan_sessions
  add column if not exists poll_run_id uuid references public.poll_runs(id) on delete set null;

-- Prevent two workers from advancing separate sessions for the same source.
-- A failed session may be followed by a fresh one; a running session is unique.
create unique index if not exists scan_sessions_one_running_per_source_idx
  on public.scan_sessions(source)
  where status = 'running';

-- Allocate a session and corresponding poll_run in one transaction.
create or replace function public.skogskoll_start_scan(
  p_source text,
  p_source_count integer,
  p_page_size integer,
  p_mode text default 'baseline'
) returns table(scan_id uuid, poll_run_id uuid)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_scan_id uuid;
  v_run_id uuid;
begin
  if p_source is null or length(trim(p_source)) = 0 then
    raise exception 'source is required';
  end if;
  if p_source_count is null or p_source_count < 0 then
    raise exception 'source_count must be non-negative';
  end if;
  if p_page_size is null or p_page_size < 1 then
    raise exception 'page_size must be positive';
  end if;
  if p_mode is null or p_mode not in ('baseline','incremental') then
    raise exception 'mode must be baseline or incremental';
  end if;

  insert into public.poll_runs(source, status, diagnostics)
  values (p_source, 'running', jsonb_build_object('mode', p_mode, 'scan_kind', 'bounded_offset'))
  returning id into v_run_id;

  insert into public.scan_sessions(source, source_count, page_size, diagnostics, poll_run_id)
  values (p_source, p_source_count, p_page_size, jsonb_build_object('mode', p_mode), v_run_id)
  returning id into v_scan_id;

  return query select v_scan_id, v_run_id;
end;
$$;

-- Commit a whole page, the deduplication IDs, and the checkpoint atomically.
-- Records are normalized by src/observation-core.mjs.
create or replace function public.skogskoll_commit_page(
  p_scan_id uuid,
  p_expected_offset integer,
  p_expected_fetched integer,
  p_next_offset integer,
  p_next_fetched integer,
  p_records jsonb,
  p_ids jsonb,
  p_observed_at timestamptz
) returns table(inserted_count integer, changed_count integer, unchanged_count integer)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_scan public.scan_sessions%rowtype;
  v_record jsonb;
  v_id text;
  v_previous_hash text;
  v_event text;
  v_inserted integer := 0;
  v_changed integer := 0;
  v_unchanged integer := 0;
  v_expected_ids integer;
  v_inserted_ids integer;
  v_geom geometry;
  v_source text;
begin
  if p_records is null or jsonb_typeof(p_records) <> 'array'
     or p_ids is null or jsonb_typeof(p_ids) <> 'array' then
    raise exception 'records and ids must be JSON arrays';
  end if;
  if p_observed_at is null then raise exception 'observed_at is required'; end if;
  if jsonb_array_length(p_records) <> jsonb_array_length(p_ids) then
    raise exception 'record and ID array lengths differ';
  end if;

  select * into v_scan
  from public.scan_sessions
  where id = p_scan_id
  for update;
  if not found then raise exception 'scan session not found'; end if;
  if v_scan.status <> 'running' then raise exception 'scan session is not running'; end if;
  if v_scan.next_offset <> p_expected_offset or v_scan.fetched_count <> p_expected_fetched then
    raise exception 'stale checkpoint; reload scan session';
  end if;
  if p_next_offset <> p_next_fetched then
    raise exception 'next offset and fetched count must match';
  end if;
  if p_next_offset <= p_expected_offset or p_next_fetched <= p_expected_fetched
     or p_next_offset > v_scan.source_count or p_next_fetched > v_scan.source_count then
    raise exception 'invalid checkpoint advance';
  end if;
  if p_next_offset - p_expected_offset <> jsonb_array_length(p_records) then
    raise exception 'checkpoint advance must equal page length';
  end if;

  select count(*) into v_expected_ids
  from (select value #>> '{}' as id from jsonb_array_elements(p_ids)) ids
  where id is not null and length(trim(id)) > 0;
  if v_expected_ids <> jsonb_array_length(p_ids) then raise exception 'source IDs must be non-empty'; end if;
  if (select count(distinct value #>> '{}') from jsonb_array_elements(p_ids)) <> jsonb_array_length(p_ids) then
    raise exception 'duplicate IDs within page';
  end if;
  if (
    select count(*) from (
      (select value->>'source_id' as id from jsonb_array_elements(p_records))
      except
      (select value #>> '{}' as id from jsonb_array_elements(p_ids))
    ) diff
  ) > 0 or (
    select count(*) from (
      (select value #>> '{}' as id from jsonb_array_elements(p_ids))
      except
      (select value->>'source_id' as id from jsonb_array_elements(p_records))
    ) diff
  ) > 0 then
    raise exception 'record IDs and page IDs do not match exactly';
  end if;

  insert into public.scan_seen_ids(scan_id, source_id, first_offset)
  select p_scan_id, ids.id, p_expected_offset + ids.ordinality::integer - 1
  from jsonb_array_elements_text(p_ids) with ordinality as ids(id, ordinality)
  on conflict (scan_id, source_id) do nothing;
  get diagnostics v_inserted_ids = row_count;
  if v_inserted_ids <> jsonb_array_length(p_ids) then
    raise exception 'duplicate ID across scan pages';
  end if;

  for v_record in select value from jsonb_array_elements(p_records)
  loop
    v_source := v_record->>'source';
    v_id := v_record->>'source_id';
    if v_source is distinct from v_scan.source then
      raise exception 'record source does not match scan source';
    end if;
    if v_id is null or length(trim(v_id)) = 0 then raise exception 'record has no source_id'; end if;
    if not (p_ids @> jsonb_build_array(v_id)) then raise exception 'record ID absent from page ID list'; end if;
    if v_record->>'content_hash' is null then raise exception 'record has no content_hash'; end if;

    v_previous_hash := null;
    select content_hash into v_previous_hash
    from public.source_observations
    where source = v_source and source_id = v_id
    for update;

    if not found then
      v_event := case when coalesce(v_scan.diagnostics->>'mode', 'baseline') = 'baseline' then 'baseline' else 'inserted' end;
      v_inserted := v_inserted + 1;
    elsif v_previous_hash is distinct from v_record->>'content_hash' then
      v_event := 'changed';
      v_changed := v_changed + 1;
    else
      v_event := 'unchanged';
      v_unchanged := v_unchanged + 1;
    end if;

    v_geom := null;
    if v_record->'geometry' is not null and v_record->'geometry' <> 'null'::jsonb then
      v_geom := st_setsrid(st_geomfromgeojson((v_record->'geometry')::text), 4326);
    end if;

    if v_event in ('baseline','inserted') then
      insert into public.source_observations(
        source, source_id, first_seen_at, last_seen_at, attributes, geom, content_hash, active, last_run_id
      ) values (
        v_source, v_id, p_observed_at, p_observed_at,
        coalesce(v_record->'attributes','{}'::jsonb), v_geom, v_record->>'content_hash', true, v_scan.poll_run_id
      );
    else
      update public.source_observations
      set last_seen_at = p_observed_at,
          attributes = coalesce(v_record->'attributes','{}'::jsonb),
          geom = v_geom,
          content_hash = v_record->>'content_hash',
          active = true,
          last_run_id = v_scan.poll_run_id
      where source = v_source and source_id = v_id;
    end if;

    -- The current-state change and immutable history row share this transaction.
    if v_event <> 'unchanged' then
      insert into public.source_observation_history(
        source, source_id, observed_at, event_type, content_hash, source_received_at, attributes, geom, poll_run_id
      ) values (
        v_source, v_id, p_observed_at, v_event, v_record->>'content_hash',
        v_record->'source_received_at', coalesce(v_record->'attributes','{}'::jsonb), v_geom, v_scan.poll_run_id
      );
    end if;
  end loop;

  update public.scan_sessions
  set next_offset = p_next_offset,
      fetched_count = p_next_fetched,
      diagnostics = diagnostics || jsonb_build_object('last_page_at', p_observed_at, 'last_page_size', jsonb_array_length(p_records))
  where id = p_scan_id;

  update public.poll_runs
  set fetched_count = p_next_fetched,
      inserted_count = public.poll_runs.inserted_count + v_inserted,
      updated_count = public.poll_runs.updated_count + v_changed,
      diagnostics = diagnostics || jsonb_build_object('last_page_at', p_observed_at)
  where id = v_scan.poll_run_id;

  return query select v_inserted, v_changed, v_unchanged;
end;
$$;

-- Only complete scans may be finalized; compare count, checkpoint and seen-ID count.
create or replace function public.skogskoll_finish_scan(p_scan_id uuid)
returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_scan public.scan_sessions%rowtype;
  v_seen_count integer;
begin
  select * into v_scan from public.scan_sessions where id = p_scan_id for update;
  if not found then raise exception 'scan session not found'; end if;
  if v_scan.status = 'complete' then return; end if;
  if v_scan.status <> 'running' then raise exception 'scan session is not running'; end if;
  if v_scan.next_offset <> v_scan.source_count or v_scan.fetched_count <> v_scan.source_count then
    raise exception 'cannot finish incomplete scan';
  end if;
  select count(*) into v_seen_count from public.scan_seen_ids where scan_id = p_scan_id;
  if v_seen_count <> v_scan.source_count then
    raise exception 'seen source-ID count does not match source count';
  end if;

  update public.scan_sessions set status = 'complete', completed_at = now() where id = p_scan_id;
  update public.poll_runs set status = 'success', finished_at = now(), fetched_count = v_scan.fetched_count
  where id = v_scan.poll_run_id;
end;
$$;

-- Failed/incomplete scans remain visible. No inactive reconciliation occurs here.
create or replace function public.skogskoll_fail_scan(p_scan_id uuid, p_reason text, p_details jsonb default '{}'::jsonb)
returns void
language plpgsql
security definer
set search_path = public, extensions
as $$
declare v_scan public.scan_sessions%rowtype;
begin
  if p_scan_id is null then return; end if;
  select * into v_scan from public.scan_sessions where id = p_scan_id for update;
  if not found or v_scan.status = 'complete' then return; end if;
  update public.scan_sessions
  set status = 'failed',
      diagnostics = diagnostics || jsonb_build_object('failure_reason', left(coalesce(p_reason,'unknown'), 500), 'failure_details', coalesce(p_details,'{}'::jsonb))
  where id = p_scan_id;
  update public.poll_runs
  set status = 'failed', finished_at = now(),
      diagnostics = diagnostics || jsonb_build_object('failure_reason', left(coalesce(p_reason,'unknown'), 500))
  where id = v_scan.poll_run_id;
end;
$$;

-- The worker may only be invoked with the Supabase service role from a trusted server.
revoke all on function public.skogskoll_start_scan(text,integer,integer,text) from public, anon, authenticated;
revoke all on function public.skogskoll_commit_page(uuid,integer,integer,integer,integer,jsonb,jsonb,timestamptz) from public, anon, authenticated;
revoke all on function public.skogskoll_finish_scan(uuid) from public, anon, authenticated;
revoke all on function public.skogskoll_fail_scan(uuid,text,jsonb) from public, anon, authenticated;
grant execute on function public.skogskoll_start_scan(text,integer,integer,text) to service_role;
grant execute on function public.skogskoll_commit_page(uuid,integer,integer,integer,integer,jsonb,jsonb,timestamptz) to service_role;
grant execute on function public.skogskoll_finish_scan(uuid) to service_role;
grant execute on function public.skogskoll_fail_scan(uuid,text,jsonb) to service_role;

-- Recover stale worker sessions after a process is killed or the host loses power.
-- Run only after verifying no worker is actively processing this source.
-- The prior session is marked failed for audit; the next scan starts from offset 0
-- because seen-ID coverage is scoped to a scan session.
create or replace function public.skogskoll_recover_stale_scan(
  p_source text,
  p_stale_before timestamptz,
  p_reason text default 'stale_worker_recovery'
) returns table(recovered_scan_id uuid, recovered_offset integer)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_scan public.scan_sessions%rowtype;
begin
  if p_source is null or length(trim(p_source)) = 0 then
    raise exception 'source is required';
  end if;
  if p_stale_before is null or p_stale_before >= now() then
    raise exception 'stale_before must be in the past';
  end if;

  select * into v_scan
  from public.scan_sessions
  where source = p_source and status = 'running' and updated_at < p_stale_before
  order by updated_at asc
  limit 1
  for update;

  if not found then
    return;
  end if;

  update public.scan_sessions
  set status = 'failed',
      diagnostics = diagnostics || jsonb_build_object(
        'failure_reason', left(coalesce(p_reason, 'stale_worker_recovery'), 500),
        'recovered_at', now(),
        'recovery_note', 'Prior session retained for audit; start a fresh scan from offset 0.'
      )
  where id = v_scan.id;

  update public.poll_runs
  set status = 'failed',
      finished_at = now(),
      diagnostics = diagnostics || jsonb_build_object(
        'failure_reason', left(coalesce(p_reason, 'stale_worker_recovery'), 500),
        'recovered_scan_id', v_scan.id
      )
  where id = v_scan.poll_run_id;

  return query select v_scan.id, v_scan.next_offset;
end;
$$;

revoke all on function public.skogskoll_recover_stale_scan(text,timestamptz,text) from public, anon, authenticated;
grant execute on function public.skogskoll_recover_stale_scan(text,timestamptz,text) to service_role;

