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
