-- Skogskoll migration 005: persist source metadata with scan identity and register immutable envelopes.
-- Apply after migrations 002 and 003. Worker-only data; no customer-facing policies.

-- Replace the original four-argument RPC with a metadata-aware signature.
drop function if exists public.skogskoll_start_scan(text, integer, integer, text);

create or replace function public.skogskoll_start_scan(
  p_source text,
  p_source_count integer,
  p_page_size integer,
  p_mode text default 'baseline',
  p_snapshot_metadata jsonb default null
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
  if p_snapshot_metadata is not null and jsonb_typeof(p_snapshot_metadata) <> 'object' then
    raise exception 'snapshot_metadata must be a JSON object';
  end if;

  insert into public.poll_runs(source, status, diagnostics)
  values (
    p_source,
    'running',
    jsonb_build_object('mode', p_mode, 'scan_kind', 'bounded_offset') ||
      case when p_snapshot_metadata is null then '{}'::jsonb
           else jsonb_build_object('snapshot_metadata', p_snapshot_metadata) end
  )
  returning id into v_run_id;

  insert into public.scan_sessions(source, source_count, page_size, diagnostics, poll_run_id)
  values (
    p_source,
    p_source_count,
    p_page_size,
    jsonb_build_object('mode', p_mode) ||
      case when p_snapshot_metadata is null then '{}'::jsonb
           else jsonb_build_object('snapshot_metadata', p_snapshot_metadata) end,
    v_run_id
  )
  returning id into v_scan_id;

  return query select v_scan_id, v_run_id;
end;
$$;

create table if not exists public.snapshot_envelopes (
  snapshot_id text primary key,
  run_id uuid not null references public.poll_runs(id) on delete restrict,
  scan_session_id uuid not null unique references public.scan_sessions(id) on delete restrict,
  source text not null,
  product text not null,
  endpoint text not null,
  layer text not null,
  captured_at timestamptz not null,
  status text not null check (status in ('complete','partial','failed')),
  coverage_key text not null,
  schema_version text not null,
  identity_version text not null,
  comparability_key text not null,
  customer_visibility text not null default 'not_assessed',
  rights_evidence_ref text,
  envelope jsonb not null,
  created_at timestamptz not null default now(),
  constraint snapshot_envelopes_customer_visibility_check
    check (customer_visibility in ('not_assessed','approved','restricted','rejected'))
);

alter table public.snapshot_envelopes enable row level security;
-- Intentionally no public policies. Only trusted service-role workers may register/read envelopes.

create or replace function public.skogskoll_register_snapshot(
  p_scan_id uuid,
  p_envelope jsonb
) returns text
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_scan public.scan_sessions%rowtype;
  v_run public.poll_runs%rowtype;
  v_metadata jsonb;
  v_existing public.snapshot_envelopes%rowtype;
  v_snapshot_id text;
begin
  if p_scan_id is null or p_envelope is null or jsonb_typeof(p_envelope) <> 'object' then
    raise exception 'scan_id and snapshot envelope are required';
  end if;

  select * into v_scan from public.scan_sessions where id = p_scan_id for update;
  if not found then raise exception 'scan session not found'; end if;
  if v_scan.poll_run_id is null then raise exception 'scan session has no linked poll run'; end if;
  select * into v_run from public.poll_runs where id = v_scan.poll_run_id for update;
  if not found then raise exception 'poll run not found'; end if;

  if v_scan.status not in ('complete','failed','abandoned') then
    raise exception 'snapshot envelope requires a terminal scan session';
  end if;
  if v_run.status not in ('success','warning','failed') then
    raise exception 'snapshot envelope requires a terminal poll run';
  end if;

  v_metadata := v_scan.diagnostics->'snapshot_metadata';
  if v_metadata is null or jsonb_typeof(v_metadata) <> 'object' then
    raise exception 'persisted snapshot metadata is missing';
  end if;
  if p_envelope->>'run_id' is distinct from v_run.id::text
     or p_envelope->>'source' is distinct from v_scan.source
     or p_envelope->>'snapshot_id' is distinct from ('skogskoll-worker:' || v_run.id::text || ':' || v_scan.id::text) then
    raise exception 'snapshot envelope identity does not match persisted scan';
  end if;
  if p_envelope->>'product' is distinct from v_metadata->>'product'
     or p_envelope->>'endpoint' is distinct from v_metadata->>'endpoint'
     or p_envelope->>'layer' is distinct from v_metadata->>'layer'
     or p_envelope->>'query_definition' is distinct from v_metadata->>'query_definition'
     or p_envelope->>'coverage_key' is distinct from v_metadata->>'coverage_key'
     or p_envelope->>'schema_version' is distinct from v_metadata->>'schema_version'
     or p_envelope->>'identity_version' is distinct from v_metadata->>'identity_version' then
    raise exception 'snapshot envelope metadata differs from scan-start metadata';
  end if;
  if p_envelope->>'customer_visibility' is distinct from coalesce(v_metadata->>'customer_visibility','not_assessed')
     or coalesce(p_envelope->>'rights_evidence_ref','') <> coalesce(v_metadata->>'rights_evidence_ref','') then
    raise exception 'snapshot envelope rights metadata differs from scan-start metadata';
  end if;
  if p_envelope->>'status' not in ('complete','partial','failed') then
    raise exception 'invalid snapshot envelope status';
  end if;
  if (v_scan.status = 'complete' and (v_run.status <> 'success' or p_envelope->>'status' <> 'complete'))
     or (v_scan.status <> 'complete' and p_envelope->>'status' = 'complete') then
    raise exception 'snapshot completeness does not match terminal scan state';
  end if;

  v_snapshot_id := p_envelope->>'snapshot_id';
  select * into v_existing from public.snapshot_envelopes
  where scan_session_id = p_scan_id or snapshot_id = v_snapshot_id
  for update;
  if found then
    if v_existing.envelope = p_envelope then return v_existing.snapshot_id; end if;
    raise exception 'immutable snapshot envelope already exists with different content';
  end if;

  insert into public.snapshot_envelopes(
    snapshot_id, run_id, scan_session_id, source, product, endpoint, layer,
    captured_at, status, coverage_key, schema_version, identity_version,
    comparability_key, customer_visibility, rights_evidence_ref, envelope
  ) values (
    v_snapshot_id, v_run.id, v_scan.id, v_scan.source,
    p_envelope->>'product', p_envelope->>'endpoint', p_envelope->>'layer',
    (p_envelope->>'captured_at')::timestamptz, p_envelope->>'status',
    p_envelope->>'coverage_key', p_envelope->>'schema_version',
    p_envelope->>'identity_version', p_envelope->>'comparability_key',
    coalesce(p_envelope->>'customer_visibility','not_assessed'),
    p_envelope->>'rights_evidence_ref', p_envelope
  );
  return v_snapshot_id;
end;
$$;

revoke all on function public.skogskoll_start_scan(text,integer,integer,text,jsonb) from public, anon, authenticated;
revoke all on function public.skogskoll_register_snapshot(uuid,jsonb) from public, anon, authenticated;
grant execute on function public.skogskoll_start_scan(text,integer,integer,text,jsonb) to service_role;
grant execute on function public.skogskoll_register_snapshot(uuid,jsonb) to service_role;
