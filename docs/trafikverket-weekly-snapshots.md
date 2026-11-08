# Trafikverket weekly snapshots

The workflow `Trafikverket weekly geodata snapshots` downloads real feature geometries
from the public Trafikverket ArcGIS REST services for the Gräsmyr pilot envelope.

## Schedule and persistence
- Runs every Monday at 05:50 UTC and can be started manually.
- Stores dated, compressed GeoJSON files and a manifest under
  `data/trafikverket/snapshots/YYYY-MM-DD/`.
- Commits snapshots to the repository for durable history and also uploads a
  90-day GitHub Actions artifact for convenient retrieval.
- Same-day reruns are idempotent at the path level: they replace that date's
  snapshot rather than create duplicate date folders.

## Data model
Each service layer is stored separately as gzip-compressed GeoJSON in WGS84
(CRS84 longitude/latitude). The manifest records source URL, layer ID/name,
geometry type, source object-ID count, downloaded feature count, fields,
compressed size and SHA-256 checksum.

The collector uses ArcGIS object-ID queries followed by chunked feature
queries. It fails the run if a layer returns fewer features than its object-ID
list, or if the total snapshot is empty. This prevents a partial download from
being silently treated as a valid snapshot.

## Sources and limitations
- Miljöwebb Landskap MapServer.
- NVDB viltolyckor MapServer.
- The wildlife service contains aggregated road-link risk/frequency values,
  not individual accident records or event dates.
- The Gräsmyr envelope is an approximate discovery area, not a property boundary.
- These are weekly observations of the source services. A new snapshot does not
  imply that every source dataset is updated weekly.
- Before external/commercial redistribution, review current source terms and
  attribution requirements.

## Run locally
```bash
python scripts/snapshot_trafikverket.py
```
