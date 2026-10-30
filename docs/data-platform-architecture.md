# Skog – data platform architecture

Status: initial architecture proposal; no production ingestion is enabled by this document.

## Purpose

Provide one repeatable way to ingest, preserve, validate, normalize and publish forest-related information from heterogeneous sources. The platform is forest-domain-specific. It is not intended to become a generic enterprise data platform.

The existing map and Skogskoll frontend must consume prepared datasets; they must not contain source-specific ingestion logic.

## Existing capabilities to reuse

- Skogskoll has a source-observation ingestion core with stable source identity, content hashes, baseline handling, append-only history, bounded scans and atomic page commits. Its current Supabase schema and worker are specifically designed for Skogsstyrelsen observations and user watch areas.
- The repository already downloads selected Skogsstyrelsen volume-raster archives from personal OneDrive using Microsoft Graph delegated access.
- Raster validation and analysis scripts read GeoTIFFs in windows, record CRS, dimensions, resolution, bounds, band and NoData, distinguish valid zero values from NoData, and calculate polygon statistics.
- Existing harvest-history pipelines preserve snapshots/deltas and reconstruct prior states.

These capabilities should be integrated by contract and shared utilities where appropriate. Do not force raster assets or municipal documents into the Skogskoll `source_observations` table. Do not replace the existing alert-safety invariants.

## Logical architecture

1. **Source registry** – source identity, owner, access method, cadence, licence/terms, geographic scope, data type and connector configuration. Secrets are environment variables/GitHub secrets, never stored in this registry.
2. **Connectors** – one adapter per source or source family. Responsible for authentication, pagination, download, source metadata and raw response capture.
3. **Raw zone** – immutable source payloads and original files, partitioned by source and retrieval date. Store checksums and retrieval manifests. Large rasters stay outside Git history.
4. **Validation** – structural, schema, identity, geometry, raster metadata, completeness and source-specific checks. A failed or partial run must not publish a complete dataset.
5. **Normalized zone** – source-neutral records with explicit source identity, source timestamps, observation/retrieval timestamps, CRS and units.
6. **Domain model** – forest objects, spatial areas, events, decisions, observations, raster assets and relationships.
7. **Curated outputs** – versioned GeoParquet/GeoJSON/JSON and raster assets/COGs where justified. These are consumed by the map, analysis jobs and future API.

## Storage decision for the first iteration

Start file-first and keep storage portable:
- JSON/JSONL for raw API payloads and manifests.
- GeoParquet for normalized vector tables and analysis-ready spatial data.
- Original GeoTIFF/ZIP archives retained unchanged; use COG or tiled derivatives only when they demonstrably improve access or size.
- Small catalogues and reports may remain JSON.
- Git stores code, schemas, small examples and documentation, not large source datasets or frequent snapshots.
- Keep the existing Supabase database for Skogskoll user-owned watch areas, source observations and alert workflow. A future shared spatial database can be considered when multi-user query patterns justify it.

## Common record envelope

Every normalized record should carry:
- `record_type`
- `record_id` (stable platform ID)
- `source_id` and `source_record_id`
- `source_url` or source locator when available
- `source_created_at`, `source_updated_at` (nullable; never inferred)
- `retrieved_at` and `valid_time` (nullable; distinguish transaction time from real-world validity)
- `geometry` and `geometry_crs` (when spatial)
- `attributes`
- `units` and `measurement_method` for measured/derived values
- `content_hash`, `schema_version`, `quality_status`

A source record is not automatically the same as a real-world event. Keep source records separate from canonical domain entities so that multiple sources can refer to one decision, event or area without losing provenance.

## Initial domain entities

- `source`: registered external data source.
- `source_record`: immutable reference to a record/file as supplied by a source.
- `forest_area`: a geographic area or management unit; do not assume it is a cadastral property.
- `property`: cadastral property reference, only where legally/technically supported.
- `forest_observation`: a measured or modelled forest attribute at a place and time.
- `raster_asset`: a raster dataset, version, band, unit, resolution, CRS, bounds, NoData and checksum.
- `forestry_event`: planned or completed forestry measure, e.g. notification, felling, thinning, fertilization or consultation.
- `authority_case`: authority diary case or municipal matter.
- `decision`: a formal decision linked to a case/meeting/document where evidence supports the link.
- `document`: original or derived document with checksum, URL, extraction status and text metadata.
- `relationship`: typed link between entities, with evidence and confidence where matching is uncertain.

## Identity, matching and history

- Source identity is always `source_id + source_record_id`; never deduplicate only by geometry, title or parcel name.
- Platform IDs identify canonical entities, not source records.
- Matching across sources must be explicit and auditable. Store match method, evidence, confidence and review status.
- Preserve raw payloads and append change history. A changed source record updates current state and adds a change event; it does not erase prior state.
- Missing records may be marked absent/inactive only after a complete, validated source scan whose scope matches the prior scan.
- Failed, partial, rate-limited or changed-snapshot runs must not deactivate or delete records.
- Baseline imports do not generate user alerts.

## Raster rules

- Keep source rasters immutable and identify each version by source, product, geography, source date/version and checksum.
- Store per-band metadata and explicit units/scaling. Never infer units from pixel values.
- Treat NoData separately from valid zero and other negative values.
- Read/process by windows or tiles; do not load county-wide or national rasters into memory.
- Keep display derivatives separate from analysis originals. Downsampled map overlays must never be used for measurements.
- Polygon summaries must record raster version, band, CRS transform, cell inclusion rule, valid-cell coverage and summary method.
- Do not describe modelled values as current field inventory unless the product source warrants it.

## Synchronization lifecycle

Each run records source, scope, start/end, status, source snapshot/count if available, cursor/checkpoint, fetched/inserted/updated/rejected counts, checksum and diagnostics. Publish a new curated version only after validation succeeds. Preserve the last known good output if a run fails.

## First pilots

1. **Sakfråga decisions** – test API pagination, title search limitations, stable decision/meeting IDs, source coverage and document linking. Search results are discovery candidates, not guaranteed complete decision registers.
2. **Skogsstyrelsen Omdrev 3 volume rasters** – test asset cataloguing, checksums, metadata, unit semantics, raster windows/tiles and polygon zonal statistics. Existing OneDrive downloader and raster scripts are the starting point.
3. **Existing forestry observations** – adapt shared provenance/manifest conventions without changing the production behavior or safety guarantees of the current Skogskoll ingestion worker.

## Non-goals for the foundation

- No automatic alerting from new source connectors.
- No assumption that all sources expose incremental cursors or reliable update timestamps.
- No destructive replacement of current data.
- No national completeness claim based on keyword search results.
- No conversion of every raster into vector features.

## Acceptance criteria

- A source can be registered without editing the central domain model.
- Every ingested record/file is traceable to its source and retrieval run.
- Failed/partial runs leave the last successful curated output intact.
- Re-running an unchanged source payload is idempotent.
- A record update preserves the previous version.
- Raster metadata and units are explicit, and NoData is not conflated with zero.
- At least one API/document source and one raster source pass end-to-end pilot tests.
