-- Skogskoll schema. Run in Supabase SQL editor after reviewing.
create extension if not exists postgis;

create table if not exists public.watch_areas (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  geom geometry(Geometry, 4326) not null,
  radius_m integer,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint watch_area_name_nonempty check (length(trim(name)) > 0),
  constraint watch_area_radius_positive check (radius_m is null or radius_m between 100 and 100000)
);
create index if not exists watch_areas_geom_gix on public.watch_areas using gist (geom);
create index if not exists watch_areas_user_idx on public.watch_areas(user_id);

-- One row per source object, keyed by source + stable source identifier.
create table if not exists public.source_observations (
  id bigserial primary key,
  source text not null,
  source_id text not null,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  source_updated_at timestamptz,
  source_created_at timestamptz,
  attributes jsonb not null default '{}'::jsonb,
  geom geometry(Geometry, 4326),
  content_hash text not null,
  active boolean not null default true,
  last_run_id uuid,
  unique (source, source_id)
);
create index if not exists source_observations_geom_gix on public.source_observations using gist (geom);
create index if not exists source_observations_last_seen_idx on public.source_observations(last_seen_at desc);

-- Immutable record of each polling run and its diagnostics.
create table if not exists public.poll_runs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running','success','warning','failed')),
  fetched_count integer not null default 0,
  inserted_count integer not null default 0,
  updated_count integer not null default 0,
  error_count integer not null default 0,
  diagnostics jsonb not null default '{}'::jsonb
);

create table if not exists public.alert_events (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  watch_area_id uuid not null references public.watch_areas(id) on delete cascade,
  source_observation_id bigint not null references public.source_observations(id) on delete cascade,
  channel text not null check (channel in ('email','push')),
  event_type text not null default 'new_match',
  created_at timestamptz not null default now(),
  delivered_at timestamptz,
  delivery_status text not null default 'pending' check (delivery_status in ('pending','sent','failed','suppressed')),
  provider_message_id text,
  error text,
  unique (user_id, watch_area_id, source_observation_id, channel, event_type)
);

create table if not exists public.push_subscriptions (
  id bigserial primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  endpoint text not null unique,
  subscription jsonb not null,
  created_at timestamptz not null default now(),
  last_used_at timestamptz
);

alter table public.watch_areas enable row level security;
alter table public.alert_events enable row level security;
alter table public.push_subscriptions enable row level security;
alter table public.source_observations enable row level security;
alter table public.poll_runs enable row level security;

drop policy if exists "owners manage own watch areas" on public.watch_areas;
create policy "owners manage own watch areas" on public.watch_areas
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "owners read own alerts" on public.alert_events;
create policy "owners read own alerts" on public.alert_events
  for select using (auth.uid() = user_id);
drop policy if exists "owners manage own push subscriptions" on public.push_subscriptions;
create policy "owners manage own push subscriptions" on public.push_subscriptions
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
-- Source observations and poll runs are worker-managed only. Do not add public policies.
