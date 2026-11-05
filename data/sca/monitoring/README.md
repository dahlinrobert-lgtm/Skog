# SCA voluntary geometry change monitoring

## Purpose

The scheduled monitor refreshes an independent national z9 census of the SCA voluntary layer, expands the z12 plan when new positive z9 tiles appear, and checks all retained z12 tiles for changes. It detects new geometries, changed geometries, metadata changes and possible disappearances while retaining source observations.

Workflow: [Monitor SCA voluntary geometry changes](../../../.github/workflows/monitor-sca-voluntary-changes.yml)

- Schedule: Mondays at 02:17 UTC
- Manual start: GitHub Actions workflow_dispatch
- Initial plan: 12,420 globally unique z12 tiles; the plan can grow when new positive z9 tiles appear
- Discovery screen: independent z9 census of the broad Sweden bounding box (ownership and voluntary layers queried independently)
- Baseline: z12 expansion artifacts from run [41704577034](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41704577034)
- Tile source: `https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf`

## Stored data

- `tile-state.json.gz`: compact current tile/feature index with tile response hashes, geometry hashes, full properties, last-seen status and pending disappearance counters. Geometry is not duplicated in this frequently updated index.
- `baseline/source-features.jsonl.gz`: immutable decoded geometry and metadata snapshot from the original z12 collection. Written once during bootstrap.
- `events/YYYY-MM-DD-RUN.jsonl.gz`: append-only event deltas. New and changed geometries include their decoded MVT geometry and metadata; removals retain source tile, geometry hash and properties.
- Workflow artifact `sca-voluntary-change-monitor`: run summary and event delta, retained for 90 days.

Each feature observation is linked to its source z/x/y tile, layer, geometry SHA-256 and full properties. MVT feature IDs are retained only as source metadata; they are not treated as stable object IDs.

## Event types

- `geometry_added`: a geometry fingerprint appeared in a valid tile response; event includes geometry and properties.
- `geometry_changed_candidate`: one old and one new geometry in the same layer share the same properties; candidate only, not resolved identity.
- `metadata_changed`: geometry fingerprint unchanged while properties changed.
- `geometry_missing_candidate`: a previously observed feature is absent from a valid response once.
- `geometry_removed_confirmed`: absence observed in two consecutive successful tile observations.
- `tile_unavailable_candidate`: a tile returned HTTP 404 twice; previous feature data is retained.
- `tile_poll_error`: request, HTTP or decode failure; previous state is retained.

A 404, timeout or other request failure never deletes features. No source geometries are merged, dissolved or overwritten.

## Interpretation and limitations

- Geometry hashes are calculated from decoded MVT tile-local coordinates. They are stable comparison fingerprints within a tile, not global object IDs.
- The monitor retains the original z12 plan and expands it from each complete z9 census using positive voluntary tiles plus a one-tile z12 neighbor ring. Only successfully decoded MVT responses (empty or with features) are classified as known; 404, request, HTTP and decode errors are counted as unknown and never treated as empty. A census with incomplete tile coverage or pending/unknown states is rejected before the plan changes.
- z9 is a discovery screen, not proof of complete national SCA coverage; features not represented at z9 may still be missed until they become visible in the z9 layer.
- A tile response hash change triggers feature-level comparison. If the payload hash is unchanged, the previous feature content is reused.
- Candidate relationships must not be treated as confirmed object identity.
- The monitor currently persists a compact state index, one immutable baseline archive and compressed event deltas in the Git repository as an MVP. Before substantially increasing scan frequency or adding more layers, move high-volume geometry/event archives to durable object storage or a database.

## Operational next steps

1. Run the workflow manually once to bootstrap from the original z12 artifacts and establish the current comparison baseline.
2. Review the first summary for tile count, poll errors and event counts.
3. Verify a second successful weekly run before treating disappearance events as operational signals.
4. Integrate validated change events into the Skogskoll event feed and notification pipeline only after the baseline and repeatability are validated.
