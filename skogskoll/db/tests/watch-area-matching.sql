-- PostGIS matching integration test; requires schema.sql and migrations 002-004.
-- Intended for a disposable database only. All fixtures are rolled back.

begin;

do $test$
declare
  v_user uuid := gen_random_uuid();
  v_radius_id uuid := gen_random_uuid();
  v_polygon_id uuid := gen_random_uuid();
  v_disabled_id uuid := gen_random_uuid();
  v_count integer;
begin
  insert into auth.users(id) values (v_user);

  insert into public.watch_areas(id, user_id, name, geom, radius_m, enabled)
  values
    (v_radius_id, v_user, 'radius test', st_setsrid(st_makepoint(0, 0), 4326), 2000, true),
    (v_polygon_id, v_user, 'polygon test',
      st_geomfromtext('POLYGON((-0.01 -0.01, 0.01 -0.01, 0.01 0.01, -0.01 0.01, -0.01 -0.01))', 4326), null, true),
    (v_disabled_id, v_user, 'disabled test', st_setsrid(st_makepoint(0, 0), 4326), 2000, false);

  insert into public.source_observations(source, source_id, attributes, geom, content_hash)
  values
    ('test', 'inside-radius', '{"name":"near"}', st_setsrid(st_makepoint(0.005, 0), 4326), repeat('a',64)),
    ('test', 'outside-radius', '{"name":"far"}', st_setsrid(st_makepoint(0.05, 0), 4326), repeat('b',64)),
    ('test', 'inside-polygon', '{"name":"polygon"}', st_setsrid(st_makepoint(0, 0), 4326), repeat('c',64)),
    ('test', 'null-geometry', '{"name":"no geometry"}', null, repeat('d',64)),
    ('test', 'inactive', '{"name":"inactive"}', st_setsrid(st_makepoint(0, 0), 4326), repeat('e',64));
  update public.source_observations set active = false where source_id = 'inactive';

  select count(*) into v_count from public.skogskoll_match_observations(v_radius_id, null);
  if v_count <> 2 then
    raise exception 'radius match expected 2 observations, got %', v_count;
  end if;
  if exists (select 1 from public.skogskoll_match_observations(v_radius_id, null) where source_id in ('outside-radius','null-geometry','inactive')) then
    raise exception 'radius match returned outside, null-geometry or inactive observation';
  end if;

  select count(*) into v_count from public.skogskoll_match_observations(v_polygon_id, null);
  if v_count <> 2 then
    raise exception 'polygon match expected 2 observations, got %', v_count;
  end if;
  if exists (select 1 from public.skogskoll_match_observations(v_disabled_id, null)) then
    raise exception 'disabled watch area must return no matches';
  end if;

  raise notice 'PostGIS watch-area matching integration test passed';
end;
$test$;

rollback;
