-- Skogskoll migration 002: auditable observation history and resumable scan state.
-- Apply after db/schema.sql. Worker-only tables: no end-user RLS policies are added.

create table if not exists public.source_observation_history (
  id bigserial primary key,
  source text not null,
  source_id text not null,
  observed_at timestamptz not null default now(),
  event_type text not null check (event_type in ('baseline','inserted','changed','unchanged')),
  content_hash text not null,
  source_received_at jsonb,
  attributes jsonb not null default '{}'::jsonb,
  geom geometry(Geometry, 4326),
  poll_run_id uuid references public.poll_runs(id) on delete set null,
  constraint source_observation_history_source_id_nonempty check (length(trim(source_id)) > 0)
);
create index if not exists source_observation_history_source_time_idx
  on public.source_observation_history(source, source_id, observed_at desc);
create index if not exists source_observation_history_run_idx
  on public.source_observation_history(poll_run_id);

-- A scan is resumable only when source count and page size still match.
create table if not exists public.scan_sessions (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  source_count integer not null check (source_count >= 0),
  page_size integer not null check (page_size > 0),
  next_offset integer not null default 0 check (next_offset >= 0),
  fetched_count integer not null default 0 check (fetched_count >= 0),
  status text not null default 'running' check (status in ('running','complete','abandoned','failed')),
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  diagnostics jsonb not null default '{}'::jsonb,
  constraint scan_session_offsets_within_count check (next_offset <= source_count and fetched_count <= source_count)
);
create index if not exists scan_sessions_source_status_idx
  on public.scan_sessions(source, status, updated_at desc);

-- Separate normalized ID table avoids storing a huge JSON array in each checkpoint.
create table if not exists public.scan_seen_ids (
  scan_id uuid not null references public.scan_sessions(id) on delete cascade,
  source_id text not null,
  first_offset integer not null check (first_offset >= 0),
  primary key (scan_id, source_id)
);
create index if not exists scan_seen_ids_source_id_idx on public.scan_seen_ids(source_id);

alter table public.source_observation_history enable row level security;
alter table public.scan_sessions enable row level security;
alter table public.scan_seen_ids enable row level security;
-- Intentionally no public policies: service-role worker access only.

-- Guardrail: prevent a completed scan from being silently reopened or advanced.
create or replace function public.guard_skogskoll_scan_session()
returns trigger language plpgsql as $$
begin
  if old.status = 'complete' and (
    new.status <> old.status or
    new.next_offset <> old.next_offset or
    new.fetched_count <> old.fetched_count
  ) then
    raise exception 'completed Skogskoll scan sessions are immutable';
  end if;
  if new.next_offset < old.next_offset or new.fetched_count < old.fetched_count then
    raise exception 'Skogskoll scan checkpoint cannot move backwards';
  end if;
  if new.next_offset <> new.fetched_count then
    raise exception 'Skogskoll scan offset and fetched count must advance together';
  end if;
  if new.status = 'complete' and new.next_offset <> new.source_count then
    raise exception 'Skogskoll scan cannot complete before reaching source count';
  end if;
  if new.status = 'complete' and new.completed_at is null then
    new.completed_at := now();
  end if;
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_guard_skogskoll_scan_session on public.scan_sessions;
create trigger trg_guard_skogskoll_scan_session
before update on public.scan_sessions
for each row execute function public.guard_skogskoll_scan_session();
