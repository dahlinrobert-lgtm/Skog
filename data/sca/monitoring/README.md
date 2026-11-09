# SCA voluntary geometry change monitoring

## Purpose

The scheduled monitor refreshes an independent national z9 census, runs a stratified z8-z12 coverage diagnostic, expands the z12 plan from positive z9 and sampled z10-z12 tiles, and checks all retained z12 tiles for changes. It detects new geometries, changed geometries, metadata changes and possible disappearances while retaining source observations.

Workflow: [Monitor SCA voluntary geometry changes](../../../.github/workflows/monitor-sca-voluntary-changes.yml)

- Schedule: Mondays at 02:17 UTC
- Manual start: GitHub Actions workflow_dispatch
- Initial plan: 12,420 globally unique z12 tiles; the plan can grow when new positive z9 tiles appear
- Discovery screen: independent z9 census of the broad Sweden bounding box (ownership and voluntary layers queried independently)
- Multi-zoom diagnostic: 8 positive and 8 404 z9 tiles sampled; z8 parent plus z10-z12 descendants checked. This is a diagnostic sample, not a national completeness claim.
- Baseline: z12 expansion artifacts from run [41704577034](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41704577034)
- Tile source: `https://olga.scaskog.com/map/omraden/{z}/{x}/{y}.pbf`

## Stored data

- `tile-state.json.gz`: compact current tile/feature index with tile response hashes, geometry hashes, full properties, last-seen status and pending disappearance counters. Geometry is not duplicated in this frequently updated index.
- `baseline/source-features.jsonl.gz`: immutable decoded geometry and metadata snapshot from the original z12 collection. Written once during bootstrap.
- `events/YYYY-MM-DD-RUN.jsonl.gz`: append-only event deltas. New and changed geometries include their decoded MVT geometry and metadata; removals retain source tile, geometry hash and properties.
- Workflow artifact `sca-voluntary-change-monitor`: run summary, event delta, z9 census and multi-zoom coverage audit, retained for 90 days.
- `event-schema.json`: version 1 contract for downstream Skogskoll ingestion. Every event has a deterministic `event_id`, source system/tile/URL, category and `notification_candidate` flag.

Each feature observation is linked to its source z/x/y tile, layer, geometry SHA-256 and full properties. MVT feature IDs are retained only as source metadata; they are not treated as stable object IDs.

## Event types

- `geometry_added`: a geometry fingerprint appeared in a valid tile response; event includes geometry and properties.
- `geometry_changed_candidate`: one old and one new geometry in the same layer share the same properties; candidate only, not resolved identity.
- `metadata_changed`: geometry fingerprint unchanged while properties changed.
- `geometry_missing_candidate`: a previously observed feature is absent from a valid response once.
- `geometry_removed_confirmed`: absence observed in two consecutive successful tile observations.
- `tile_unavailable_candidate`: a tile returned HTTP 404 twice; previous feature data is retained.
- `tile_poll_error`: request, HTTP or decode failure; previous state is retained.

A 404, timeout or other request failure never deletes features. The monitor retains last-attempt HTTP status, response hash, byte count and content type separately from the last valid tile hash. Identical HTTP error signatures are grouped in the run summary with one representative short response-body preview, avoiding repeated error text in every tile-state record. No source geometries are merged, dissolved or overwritten.

## Interpretation and limitations

- Geometry hashes are calculated from decoded MVT tile-local coordinates. They are stable comparison fingerprints within a tile, not global object IDs.
- The monitor retains the original z12 plan and expands it from positive z9 tiles plus positive z10-z12 tiles found by the stratified multi-zoom audit, with a one-tile z12 neighbor ring. Only successfully decoded MVT responses (empty or with features) are classified as known; 404, request, HTTP and decode errors are counted as unknown and never treated as empty. A census with incomplete tile coverage or pending/unknown states is rejected before the plan changes.
- The multi-zoom audit samples 8 positive and 8 404 z9 tiles, probes each z8 parent and all z10-z12 descendants, and records response status, response hash, content type, server and a short error-body preview. Positive descendants at z10-z12 can expand the z12 plan. The sample diagnoses zoom-dependent gaps but does not establish national completeness.
- z9 is a discovery screen, not proof of complete national SCA coverage; features not represented at z9 may still be missed until they become visible in the z9 layer.
- A tile response hash change triggers feature-level comparison. If the payload hash is unchanged, the previous feature content is reused.
- Event archives use the versioned envelope in `event-schema.json`. `notification_candidate=true` is reserved for `geometry_added`, `metadata_changed` and `geometry_removed_confirmed`; ambiguous geometry changes, first-miss candidates and technical/source-availability events are not directly notification-eligible.
- Candidate relationships must not be treated as confirmed object identity.
- The monitor currently persists a compact state index, one immutable baseline archive and compressed event deltas in the Git repository as an MVP. Before substantially increasing scan frequency or adding more layers, move high-volume geometry/event archives to durable object storage or a database.

## Operational next steps

1. Run the workflow manually once to bootstrap from the original z12 artifacts and establish the current comparison baseline.
2. Review the first summary for tile count, poll errors and event counts.
3. Verify a second successful weekly run before treating disappearance events as operational signals.
4. Review the multi-zoom audit response signatures and positive descendants; adjust sample strategy only from observed evidence.
5. Integrate version 1 event archives into the Skogskoll event feed. Keep notification delivery disabled until a second comparable run verifies event repeatability.


## Cross-tile event matching (analysis layer)

The separate `scripts/analyze_sca_event_cross_tile_matches.py` utility compares polygon geometries carried by one event archive across adjacent tiles. It converts tile-local MVT coordinates to a common EPSG:3857 diagnostic coordinate space before calculating overlap. Only same-zoom, adjacent-tile observations from the same source layer are compared.

Example:

```bash
python scripts/analyze_sca_event_cross_tile_matches.py \
  --events output/sca-voluntary-change-events.jsonl.gz \
  --output output/sca-voluntary-cross-tile-candidates.json
```

The default candidate threshold is intersection area divided by the smaller polygon area >= 0.80. Results are classified as:
- `strong_geometry_and_attributes_candidate`: exact property equality plus strong overlap;
- `geometry_overlap_attributes_compatible`: same resolved class and motive but other property differences;
- `geometry_overlap_attribute_conflict_review`: strong overlap with class/motive disagreement or missing values.

The output retains event IDs and both source tile coordinates. It deliberately does not assign object IDs, merge geometries, deduplicate the event archive, or change notification eligibility. It is scoped to geometry observations in the supplied archive, not the full baseline or a national object census. Historical missing/removal observations are not interpreted as proof that a neighboring tile currently lacks the object.

The initial run #23 archive can be used as a pilot input. Its 591 events include multiple event types; technical events, tile-availability events and metadata-only events are excluded. A no-match result is inconclusive where the corresponding observation is absent from that archive.
