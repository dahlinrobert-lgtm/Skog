-- Least-privilege API grants and RLS integration test.
-- Requires schema.sql and migrations 002-006. Disposable database only.
-- All fixtures and role-based writes are rolled back.

begin;

do $fixtures$
declare
  v_user_a uuid := '10000000-0000-4000-8000-000000000001';
  v_user_b uuid := '10000000-0000-4000-8000-000000000002';
  v_watch_a uuid := '20000000-0000-4000-8000-000000000001';
  v_watch_b uuid := '20000000-0000-4000-8000-000000000002';
  v_observation bigint;
  v_run uuid := gen_random_uuid();
  v_scan uuid := gen_random_uuid();
begin
  insert into auth.users(id) values (v_user_a), (v_user_b);

  insert into public.watch_areas(id, user_id, name, geom, radius_m)
  values
    (v_watch_a, v_user_a, 'RLS fixture A', st_setsrid(st_makepoint(0,0),4326), 1000),
    (v_watch_b, v_user_b, 'RLS fixture B', st_setsrid(st_makepoint(1,1),4326), 1000);

  insert into public.source_observations(source, source_id, attributes, geom, content_hash)
  values ('rls-test', 'rls-fixture', '{}'::jsonb, st_setsrid(st_makepoint(0,0),4326), repeat('a',64))
  returning id into v_observation;

  insert into public.alert_events(user_id, watch_area_id, source_observation_id, channel)
  values
    (v_user_a, v_watch_a, v_observation, 'email'),
    (v_user_b, v_watch_b, v_observation, 'email');

  insert into public.push_subscriptions(user_id, endpoint, subscription)
  values
    (v_user_a, 'https://push.example.test/a', '{"fixture":"a"}'),
    (v_user_b, 'https://push.example.test/b', '{"fixture":"b"}');

  insert into public.poll_runs(id, source, status) values (v_run, 'rls-test', 'running');
  insert into public.scan_sessions(id, source, source_count, page_size, poll_run_id)
  values (v_scan, 'rls-test', 0, 1, v_run);
end;
$fixtures$;

do $privileges$
begin
  if has_table_privilege('anon', 'public.watch_areas', 'SELECT')
     or has_table_privilege('anon', 'public.alert_events', 'SELECT')
     or has_table_privilege('anon', 'public.push_subscriptions', 'SELECT') then
    raise exception 'anon customer-table privilege matrix is incorrect';
  end if;

  if not has_table_privilege('authenticated', 'public.watch_areas', 'SELECT')
     or not has_table_privilege('authenticated', 'public.watch_areas', 'INSERT')
     or not has_table_privilege('authenticated', 'public.watch_areas', 'UPDATE')
     or not has_table_privilege('authenticated', 'public.watch_areas', 'DELETE') then
    raise exception 'authenticated watch_areas CRUD grants are incomplete';
  end if;
  if not has_table_privilege('authenticated', 'public.alert_events', 'SELECT')
     or has_table_privilege('authenticated', 'public.alert_events', 'INSERT')
     or has_table_privilege('authenticated', 'public.alert_events', 'UPDATE')
     or has_table_privilege('authenticated', 'public.alert_events', 'DELETE') then
    raise exception 'authenticated alert_events must be read-only';
  end if;
  if not has_table_privilege('authenticated', 'public.push_subscriptions', 'SELECT')
     or not has_table_privilege('authenticated', 'public.push_subscriptions', 'INSERT')
     or not has_table_privilege('authenticated', 'public.push_subscriptions', 'UPDATE')
     or not has_table_privilege('authenticated', 'public.push_subscriptions', 'DELETE')
     or not has_sequence_privilege('authenticated', 'public.push_subscriptions_id_seq', 'USAGE') then
    raise exception 'authenticated push_subscriptions grants are incomplete';
  end if;

  if has_table_privilege('authenticated', 'public.source_observations', 'SELECT')
     or has_table_privilege('authenticated', 'public.poll_runs', 'SELECT')
     or has_table_privilege('authenticated', 'public.source_observation_history', 'SELECT')
     or has_table_privilege('authenticated', 'public.scan_sessions', 'SELECT')
     or has_table_privilege('authenticated', 'public.scan_seen_ids', 'SELECT')
     or has_table_privilege('authenticated', 'public.snapshot_envelopes', 'SELECT') then
    raise exception 'authenticated must not read internal worker tables';
  end if;

  if not has_table_privilege('service_role', 'public.poll_runs', 'SELECT')
     or not has_table_privilege('service_role', 'public.scan_sessions', 'SELECT')
     or has_table_privilege('service_role', 'public.poll_runs', 'INSERT')
     or has_table_privilege('service_role', 'public.poll_runs', 'UPDATE')
     or has_table_privilege('service_role', 'public.poll_runs', 'DELETE')
     or has_table_privilege('service_role', 'public.scan_sessions', 'INSERT')
     or has_table_privilege('service_role', 'public.scan_sessions', 'UPDATE')
     or has_table_privilege('service_role', 'public.scan_sessions', 'DELETE') then
    raise exception 'service_role worker read-only table grants are incorrect';
  end if;

  if has_table_privilege('service_role', 'public.source_observations', 'SELECT')
     or has_table_privilege('service_role', 'public.source_observation_history', 'SELECT')
     or has_table_privilege('service_role', 'public.scan_seen_ids', 'SELECT')
     or has_table_privilege('service_role', 'public.snapshot_envelopes', 'SELECT') then
    raise exception 'service_role must not directly access protected worker tables';
  end if;
end;
$privileges$;

-- Simulate an authenticated browser request for user A.
set local role authenticated;
select set_config('request.jwt.claim.sub', '10000000-0000-4000-8000-000000000001', true);

do $user_a$
declare
  v_count integer;
begin
  select count(*) into v_count from public.watch_areas;
  if v_count <> 1 then raise exception 'watch_areas RLS leaked rows or hid owner row'; end if;

  select count(*) into v_count from public.alert_events;
  if v_count <> 1 then raise exception 'alert_events RLS leaked rows or hid owner row'; end if;

  select count(*) into v_count from public.push_subscriptions;
  if v_count <> 1 then raise exception 'push_subscriptions RLS leaked rows or hid owner row'; end if;

  insert into public.watch_areas(user_id, name, geom, radius_m)
  values (auth.uid(), 'Own insert', st_setsrid(st_makepoint(2,2),4326), 1000);

  begin
    insert into public.watch_areas(user_id, name, geom, radius_m)
    values ('10000000-0000-4000-8000-000000000002', 'Foreign insert',
            st_setsrid(st_makepoint(3,3),4326), 1000);
    raise exception 'watch_areas RLS accepted another user owner_id';
  exception when insufficient_privilege then
    null;
  end;

  insert into public.push_subscriptions(user_id, endpoint, subscription)
  values (auth.uid(), 'https://push.example.test/own-insert', '{"fixture":"own"}');

  begin
    insert into public.push_subscriptions(user_id, endpoint, subscription)
    values ('10000000-0000-4000-8000-000000000002',
            'https://push.example.test/foreign-insert', '{"fixture":"foreign"}');
    raise exception 'push_subscriptions RLS accepted another user owner_id';
  exception when insufficient_privilege then
    null;
  end;
end;
$user_a$;

reset role;

-- service_role can perform the two direct REST reads used by the worker adapter.
set local role service_role;
do $worker_reads$
declare
  v_count integer;
begin
  select count(*) into v_count from public.scan_sessions where source = 'rls-test';
  if v_count <> 1 then raise exception 'service_role cannot read scan_sessions'; end if;
  select count(*) into v_count from public.poll_runs where source = 'rls-test';
  if v_count <> 1 then raise exception 'service_role cannot read poll_runs'; end if;
end;
$worker_reads$;

reset role;
rollback;
