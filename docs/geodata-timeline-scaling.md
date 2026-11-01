# Skogsdatalabbet – sampling strategy and national scaling

## Current pilot
The weekly workflow samples a fixed 1 km × 1 km window around Gräsmyr in EPSG:3006 for Torvkarta and SIS. The sample is exported at the service's nominal pixel size, capped at 1024 pixels per side, and saved as compressed NPZ together with service metadata and hashes.

The 2026-11-01 09:40 UTC record is a metadata/hash-only baseline. The 10:24 UTC record is the first one with pixel arrays. It must not be counted as a pixel-comparable weekly pair. The next successful run can compare against the 10:24 sample, and the following weekly run is needed to verify two comparable weekly intervals.

## Stage 1 – Gräsmyr
Do not widen the collection area before at least two comparable weekly snapshots exist for both services. A comparable pair requires:
- both observations completed successfully for the same service;
- identical sample bounding box, array shape, dtype and band count;
- both compressed NPZ arrays are retained;
- valid-pixel and NoData handling are reported;
- metadata changes and pixel-content changes are reported separately.

A service error must never be represented as a valid weekly observation. A shape, resolution, extent or dtype change is reported as an incomparable sample, not as changed pixels.

## Stage 2 – geographically distributed pilot
After Gräsmyr verification, add a small set of fixed 1 km windows distributed across northern, central and southern Sweden. Select sites to span different regions and landscape contexts, not as a statistically representative sample.

For each location and service, collect the same bounded metadata and pixel sample. Record service response status, coverage, raster dimensions, pixel size, band count, NoData behavior and whether the service supports efficient change detection. Never download a nationwide raster as part of this test.

## Stage 3 – national architecture
Before scaling, probe service capabilities and limits:
- ImageServer exportImage support and maximum dimensions;
- identify/query support where applicable;
- catalog/version/update metadata;
- ETag, Last-Modified, version identifiers or other cache validators;
- service-side mosaic/raster function support and change/footprint metadata;
- tiled export and stable grid alignment;
- authentication, quotas, throttling and licensing/redistribution terms.

Prefer a hierarchy:
1. Cheap metadata/version check.
2. Spatially scoped change/footprint check, if supported.
3. Request only changed tiles/windows.
4. Compare normalized pixel arrays only for affected windows.
5. Persist immutable event records and periodic full checkpoints.
6. Retain source metadata, observation timestamps and quality flags with each delta.

Store data by service, grid/version and tile ID. Use compressed NPZ or a more suitable chunked format only after measuring access patterns. Avoid storing duplicate unchanged data. Keep latest state separate from append-only change events. Include checksums and reproducible tile bounds.

## Current constraints
- Weekly polling is a monitoring cadence, not a claim that the source updates weekly.
- A difference between observations does not reveal the exact edit time or cause.
- A fixed sample may miss changes outside its window.
- A pixel hash difference alone does not describe the magnitude or semantics of change.
- Nationwide collection is blocked until efficient change detection, service limits, data rights and storage costs are understood.
