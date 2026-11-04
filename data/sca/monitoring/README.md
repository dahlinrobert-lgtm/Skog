# SCA voluntary geometry change monitoring

## Purpose

The scheduled monitor checks the existing national z12 tile plan for changes in the SCA voluntary set-aside MVT layer. It is intended to detect new geometries, changed geometries, metadata changes and possible disappearances while retaining source observations.

Workflow: [Monitor SCA voluntary geometry changes](../../.github/workflows/monitor-sca-voluntary-changes.yml)

- Schedule: Mondays at 02:17 UTC
- Manual start: GitHub Actions workflow_dispatch
- Current plan: 12,420 globally unique z12 tiles
- Baseline: z12 expansion artifacts from run [41704577034](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41704577034)
- Tile source: `https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf`

## Stored data

- `tile-state.json.gz`: current tile and feature state, including tile response hashes, decoded geometries, geometry hashes, properties and pending-missing observations.
- `events/YYYY-MM-DD-RUN.jsonl.gz`: append-only event deltas for each monitor run.
- Workflow artifact `sca-voluntary-change-monitor`: run summary and event delta, retained for 90 days.

Each feature observation includes its source tile, layer, tile-local decoded geometry, geometry SHA-256 and full properties. The MVT feature ID is retained only as source metadata; it is not treated as a stable object ID.

## Event types

- `geometry_added`: a geometry fingerprint appeared in a valid tile response.
- `geometry_changed_candidate`: one old and one new geometry in the same layer share the same properties; this is a candidate relationship, not resolved identity.
- `metadata_changed`: geometry fingerprint unchanged while properties changed.
- `geometry_missing_candidate`: a previously observed feature is absent from a valid response once.
- `geometry_removed_confirmed`: absence observed in two consecutive successful tile observations.
- `tile_unavailable_candidate`: a tile returned HTTP 404 twice; previous feature data is retained.
- `tile_poll_error`: request, HTTP or decode failure; previous state is retained.

A 404, timeout or other request failure never deletes features. No source geometries are merged, dissolved or overwritten.

## Interpretation and limitations

- Geometry hashes are calculated from decoded MVT tile-local coordinates. They are stable comparison fingerprints within a tile, not global object IDs.
- The monitor scans the current 12,420-tile z12 plan. This does not establish complete national SCA coverage beyond the original seed and neighbor-ring design.
- A tile response hash change triggers feature-level comparison. If the payload hash is unchanged, the previous feature content is reused.
- Candidate relationships must not be treated as confirmed object identity.
- The monitor currently persists state and compressed event deltas in the Git repository as an MVP. Before substantially increasing scan frequency or adding more layers, move high-volume state and geometry archives to durable object storage or a database.

## Operational next steps

1. Run the workflow manually once to bootstrap from the original z12 artifacts and establish the current comparison baseline.
2. Review the first summary for tile count, poll errors and event counts.
3. Verify a second successful weekly run before treating disappearance events as operational signals.
4. Add downstream notification/event-feed integration only after the baseline and repeatability are validated.
