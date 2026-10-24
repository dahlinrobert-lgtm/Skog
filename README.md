# Skog – Gräsmyr monitoring MVP

Monitor forestry notifications and imagery freshness around Gräsmyr, Nordmaling municipality.

## Initial area
Approximate centre: 63.74646 N, 19.66455 E. Default radius: 10 km. This is a search centre, not a cadastral boundary.

## Run
```bash
python -m pip install -r requirements.txt
python scripts/monitor.py
```

Outputs: `data/latest.json` and timestamped snapshots under `data/snapshots/`.

## Sources
- Skogsstyrelsen cutting notification layer: https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSkogsbruk/MapServer/5
- Copernicus Data Space STAC: https://catalogue.dataspace.copernicus.eu/stac/search
- Lantmäteriet GeoLex: https://geolex.lantmateriet.se/
- Lantmäteriet production plans: https://www.lantmateriet.se/sv/geodata/vara-produkter/produktsupport/planer-och-utfall-for-produktionen/

## Important limitations
- The Skogsstyrelsen layer is not a cadastral property register. Matching an application to a property such as Gräsmyr 6:43 requires a separate property-boundary source.
- A cutting notification is not proof that felling has started or occurred.
- Satellite scene cloud cover is a scene-level metric and may not describe the exact monitoring area.
- Commercial map services (e.g. Hitta.se) may not publish image acquisition dates. Website update dates must not be treated as image dates. Where no metadata is available, use manual verification or compare saved reference images and label the result as a detected visual change, not a known acquisition date.
- This is a first monitoring scaffold. Check source responses and data quality before relying on it for alerts.


## First live run — 2026-10-24
The scheduled run completed successfully. The run queried the Skogsstyrelsen service and both Copernicus STAC collections and committed a dated snapshot.

Observed run metrics:
- Skogsstyrelsen cutting-notification features returned in the 10 km bounding box: **253**.
- Sentinel-1 scenes returned: **100** (catalogue query limit).
- Sentinel-2 L2A scenes returned: **100** (catalogue query limit).
- Latest scene acquisition timestamps at the time of the run: Sentinel-1 **2026-10-24 04:56:56 UTC**; Sentinel-2 **2026-10-22 10:30:31 UTC**.
- The Sentinel-2 catalogue's newest returned item had **99.93% scene-level cloud cover**; this does not indicate cloud cover specifically over the Gräsmyr AOI.

### Interpretation and known issues after first run
- The 253 notification features are all features intersecting a rectangular bounding box, not a verified Gräsmyr-village or cadastral-property selection. Records include multiple municipalities and older cases. They must not be presented as 253 new notifications.
- The first run has no previous saved catalogue snapshot to compare against; consequently the 200 returned satellite items are **initially observed items**, not 200 scenes newly acquired since the previous run.
- Each catalogue query is capped at 100 scenes. This is enough to prove endpoint connectivity but is not a complete 550-day archive. Subsequent code should use STAC pagination or page tokens and retain indexed metadata for consistent delta detection.
- `published_at` is the catalogue's created/published metadata where available, while `acquired_at` is scene acquisition time. They describe different events and must remain separate.
- Before generating alerts, filter cutting notifications by the geometry of interest, distinguish truly new object IDs from older features, and alert only on newly observed records. Parcel-specific monitoring still needs a verified property-boundary layer.

Run details: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40082300173


## Monitoring logic update (2026-10-24)
- Cutting-notification search now uses a 10 km point-distance query around the configured centre rather than the rectangular bounding box. This narrows the search but still does not define the village or any cadastral parcel.
- Copernicus STAC requests follow `rel=next` links and persist compact scene metadata instead of full scene geometries.
- `data/scene_index.json` stores scene IDs and acquisition/publication timestamps for delta detection. When this index is first created, the run establishes a baseline and intentionally emits no satellite-scene alerts. This avoids treating the older archive as newly acquired imagery.
- The next scheduled run is needed to verify these changes against the live services. Until then, pagination and distance-query behavior are implemented but not yet live-run validated.

## Daily history of completed-harvest polygons

The scheduled workflow now also runs `scripts/snapshot_completed.py` against Skogsstyrelsen's public completed-harvest layer.

- `data/completed_latest.json` stores the latest feature attributes, geometry hashes, and ID-level change diagnostics.
- `data/snapshots/completed_YYYYMMDDTHHMMSSZ.geojson.gz` stores the full daily GeoJSON geometry in compressed form.
- The first successful run establishes a baseline; it does not label all existing polygons as new.
- Later runs report IDs newly present, IDs no longer returned by the query, and IDs whose geometry changed.

**Interpretation:** a missing ID is not proof that Skogsstyrelsen deleted a case or that felling occurred. It means only that the ID was not returned in the current query. Changes can also reflect source revisions, service/query behavior, or spatial filtering. The completed-harvest product is based on satellite change detection and Skogsstyrelsen cautions that it is a guidance layer, not a direct statistical ground truth.

The daily archive lets us compare full polygon geometries across observation dates. The existing notification snapshots and these completed-layer snapshots can then be used to investigate whether a planned polygon disappears around the time a nearby completed polygon appears.

## Change diagnostics: planned vs completed

The workflow now runs `scripts/analyze_changes.py` after saving both source layers.

- Writes `data/change_analysis.json`.
- Compares planned IDs across available notification snapshots and reports newly appearing IDs and IDs not returned later.
- Intersects current planned polygons with the current completed polygons after projecting to SWEREF99 TM (EPSG:3006).
- Stores each planned object’s best spatial candidates with overlap area, share of both polygons, completed-date metadata and Forebild/Efterbild identifiers.

The threshold (intersection at least 0.02 ha and at least 15% of either polygon) is a working diagnostic threshold, not a validated definition of an executed case. The report expressly treats spatial overlap as candidate evidence, not proof. An ID not returned by a later query is not automatically labelled deleted, expired or felled.

The project currently has a limited set of snapshots from the initial setup on 2026-10-24. That same-day history is not a sufficiently long time series to estimate typical register turnover. The report will become more informative as daily snapshots accumulate.


## Notification history quality guard (2026-10-24)

The notification-history builder compares the complete query scope, including spatial geometry/type and relevant ArcGIS query filters, rather than only the endpoint and configured centre/radius.

- IDs omitted just after a query-scope change are labelled `scope_changed`; they are not counted as source `not_returned` events.
- `record_changed` events compare tracked attributes and geometry only across consecutive successful snapshots with a matching query scope.
- `data/notification_history_events.jsonl` is rebuilt from the saved successful snapshots each run. The dated snapshots are the source of truth, allowing stale derived events from older comparison logic to be corrected rather than preserved indefinitely.
- A query-scope transition does not establish that an application was removed, expired, cancelled, or felled.


## Planned snapshot storage optimization

New planned-notification snapshots use a backwards-compatible mixed archive:

- `data/latest.json` remains the complete current state for the dashboard and other direct consumers.
- Historical `data/snapshots/YYYYMMDDTHHMMSSZ.json` files are full checkpoints when establishing a baseline, when the query scope changes, or at least every 30 days.
- Between checkpoints, the snapshot stores only added, updated, and no-longer-returned feature IDs. Unchanged features are omitted; for an attribute-only update, the geometry is omitted and reused from the base snapshot. Geometry and attribute hashes are stored separately for changed features.
- `scripts/snapshot_store.py` reconstructs legacy full snapshots and new delta snapshots for the notification-history and change-analysis pipelines.
- Failed notification queries are rejected before snapshot persistence. A query-scope change forces a full checkpoint rather than a delta, so IDs from different search areas are not compared as if the source register changed.
- `python scripts/audit_snapshots.py` reports current stored bytes, reconstructable snapshots, unchanged-feature share and a reconstructed full-snapshot equivalent. The equivalent is an estimate and does not measure Git's historical object storage.
- `python -m unittest discover -s tests -v` validates delta reconstruction and the main safety cases.

This reduces repetition in future commits, but it does **not** erase bytes already stored in Git history. Existing full snapshots are intentionally retained for auditability; historical compaction should only be considered separately after measuring repository growth and agreeing how to preserve the old history.
