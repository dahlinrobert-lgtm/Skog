# Trafikverket – miljö- och viltdata

This integration starts with a read-only inventory. It does not yet ingest source geometries into the production map or create alerts.

## Public ArcGIS services

| Source | Service | Contents |
|---|---|---|
| Miljöwebb Landskap | [MWLEXGEO MapServer](https://vektor.trafikverket.se/gis/rest/services/MWLEXGEO/MiljowebbGeo/MapServer) | Environmental features such as wildlife passages, species-rich road/rail environments, invasive species, cultural features and water fauna passages |
| NVDB wildlife accidents | [Viltolyckor MapServer](https://vektor.trafikverket.se/gis/rest/services/NVDB_p%C3%A5_karta/Viltolyckor_NVDBpakarta/MapServer) | Seven road-link accident-frequency layers: ungulates total, moose, wild boar, roe deer, reindeer, red deer and fallow deer |

Both services use SWEREF 99 TM (EPSG:3006) and advertise JSON/GeoJSON/PBF query formats. The inventory script requests counts using a WGS84 envelope and does not download geometries.

## Gräsmyr pilot scope

The initial coverage check uses centre 63.74646 N, 19.66455 E and an approximate 75 km × 75 km envelope. The envelope is a discovery window only; it is not a cadastral boundary and its degree-based approximation is not a precise geodesic square.

Run locally:

```bash
python scripts/inventory_trafikverket.py
```

Output: `artifacts/trafikverket-inventory.json`.

The GitHub Actions workflow `.github/workflows/trafikverket-inventory.yml` runs manually and weekly, then publishes the JSON as a 30-day artifact. The probe is read-only and uses only Python's standard library.

## Important interpretation limits

- The wildlife accident service contains aggregated accident frequency per road link, not individual accident reports with dates and exact event coordinates.
- A count in the Gräsmyr envelope is a spatial coverage diagnostic, not a count of accidents in Gräsmyr village or on a particular property.
- Group layers and non-feature layers are catalogued but not queried for feature counts.
- A successful metadata/count probe does not establish permission to redistribute source data commercially. Check Trafikverket's current terms and source-specific metadata before publishing or selling derived datasets.
- Miljöwebb's public WMS/MapServer catalogue is not the same as authenticated access to the full Miljöwebb application. Trafikverket states that downloadable basic geographic data are available via Lastkajen, while access to the application itself requires an external account and assignment.
- This initial workflow stores its report as an Actions artifact, not as an append-only historical database. A later ingestion phase must preserve immutable source observations and explicit observation timestamps before alerts are considered.

## Source documentation

- [Trafikverket – Miljöwebb Landskap](https://bransch.trafikverket.se/tjanster/system-och-verktyg/forvaltning-och-underhall/miljowebb-landskap/)
- [Miljöwebb Landskap – ArcGIS REST](https://vektor.trafikverket.se/gis/rest/services/MWLEXGEO/MiljowebbGeo/MapServer)
- [NVDB wildlife accidents – ArcGIS REST](https://vektor.trafikverket.se/gis/rest/services/NVDB_p%C3%A5_karta/Viltolyckor_NVDBpakarta/MapServer)
