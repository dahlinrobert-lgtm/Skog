-- Skogskoll migration 006: explicit least-privilege API grants.
-- Apply after migrations 002-005. RLS policies from schema.sql remain the row-level boundary.
-- Worker writes continue through SECURITY DEFINER RPCs; direct REST reads are limited
-- to the two tables currently reloaded by supabase-adapters.mjs.

-- Customer-owned data: authenticated users receive only the operations already
-- constrained by the owner policies created in schema.sql.
revoke all privileges on table public.watch_areas
  from public, anon, authenticated, service_role;
grant select, insert, update, delete on table public.watch_areas to authenticated;

revoke all privileges on table public.alert_events
  from public, anon, authenticated, service_role;
grant select on table public.alert_events to authenticated;

revoke all privileges on table public.push_subscriptions
  from public, anon, authenticated, service_role;
grant select, insert, update, delete on table public.push_subscriptions to authenticated;

-- BIGSERIAL sequence access is separate from table privileges.
revoke all privileges on sequence public.push_subscriptions_id_seq
  from public, anon, authenticated, service_role;
grant usage, select on sequence public.push_subscriptions_id_seq to authenticated;

-- Internal worker data remains unavailable to browser roles and is not directly
-- writable by service_role. The current adapter performs REST SELECTs only on
-- poll_runs and scan_sessions; all mutations use the SECURITY DEFINER RPCs.
revoke all privileges on table
  public.source_observations,
  public.poll_runs,
  public.source_observation_history,
  public.scan_sessions,
  public.scan_seen_ids,
  public.snapshot_envelopes
  from public, anon, authenticated, service_role;

grant select on table public.poll_runs, public.scan_sessions to service_role;

-- Do not expose internal BIGSERIAL sequences through API roles.
revoke all privileges on sequence
  public.source_observations_id_seq,
  public.source_observation_history_id_seq,
  public.alert_events_id_seq
  from public, anon, authenticated, service_role;

-- No grants are added to anon. No new RLS policies are created, and the existing
-- owner policies remain the sole row-level authorization for customer tables.
