-- Skogskoll migration 004: authoritative PostGIS watch-area matching.
-- Radius areas are represented by a POINT in geom plus radius_m.
-- Polygon areas use their polygon geometry and radius_m = NULL.
-- This is a read-only matching primitive; it does not create alerts or send notifications.

create or replace function public.skogskoll_match_observations(
  p_watch_area_id uuid,
  p_since timestamptz default null
) returns table (
  watch_area_id uuid,
  observation_id bigint,
  source text,
  source_id text,
  attributes jsonb,
  geom geometry(Geometry, 4326),
  last_seen_at timestamptz
)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_area public.watch_areas%rowtype;
begin
  if p_watch_area_id is null then
    raise exception 'watch_area_id is required';
  end if;

  select * into v_area
  from public.watch_areas
  where id = p_watch_area_id and enabled = true;

  if not found then
    return;
  end if;

  if v_area.radius_m is not null and geometrytype(v_area.geom) <> 'POINT' then
    raise exception 'radius watch area geometry must be a POINT';
  end if;
  if v_area.radius_m is null and geometrytype(v_area.geom) not in ('POLYGON', 'MULTIPOLYGON') then
    raise exception 'polygon watch area geometry must be POLYGON or MULTIPOLYGON';
  end if;

  return query
  select v_area.id, o.id, o.source, o.source_id, o.attributes, o.geom, o.last_seen_at
  from public.source_observations o
  where o.active = true
    and o.geom is not null
    and (p_since is null or o.first_seen_at >= p_since)
    and (
      (v_area.radius_m is not null and
        st_dwithin(o.geom::geography, v_area.geom::geography, v_area.radius_m))
      or
      (v_area.radius_m is null and st_intersects(o.geom, v_area.geom))
    )
  order by o.last_seen_at desc, o.id;
end;
$$;

revoke all on function public.skogskoll_match_observations(uuid,timestamptz) from public, anon, authenticated;
grant execute on function public.skogskoll_match_observations(uuid,timestamptz) to service_role;
