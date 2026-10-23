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
