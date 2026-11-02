# Product concept: age of forest observations and event-aware context

## Product role
Skogskoll should not try to replace Skogsstyrelsen's Skogens karta or the SLU/Skogsstyrelsen Skogliga grunddata viewer. Those tools let a user inspect a mapped area and calculate estimated timber volume and other forest metrics for the acquisition time of the underlying laser scan.

Skogskoll's distinct value is to connect the same place to dated events and explain what has happened since that observation. The monitoring feed remains the primary product surface; the map is supporting context.

## User-facing insight: "Did you know?"
Examples:
- "The latest registered laser scan for this area was 6 years ago."
- "The forest-volume estimate is based on data acquired on 2020-08-09."
- "A completed-harvest event was registered after the scan."
- "The next available scan observation is from 2025; the interval between the reported harvest date and that observation is approximately 4 years."
- "Several changes have been registered in this area since the underlying forest data was acquired."

All statements must be generated from spatially matched source observations and show the relevant date/source. Avoid saying that a raster has been "updated" merely because its publication or service version changed.

## Core data model
Keep separate entities/records:
1. Scan observation: source, survey round, index tile, scan date, LAZ filename, leaf status, scanner model, block, geometry, source retrieval timestamp.
2. Forest metric observation: product/version, metric, raster code, raster acquisition/scan date if known, cell/polygon aggregation method, value/statistics, valid coverage, NoData count.
3. Forest event: event source, event ID, event type, reported event date (e.g. Avvdatum), date semantics/provenance, geometry, source retrieval/snapshot timestamp.
4. Spatial-temporal relationship: event-to-scan tile intersection, overlap area/share, nearest scan before/after event, day/year offsets, confidence/limitations.

Do not treat a 2.5 km metadata index tile as an aircraft trajectory or as proof every pixel was scanned on the stated date. Preserve multiple source records for the same tile and survey round. The published metadata may report only the latest scan date if several scans occurred within a tile.

## Recommended insight logic
- Latest scan age: use the latest verified scan date intersecting the monitored area. Make clear if the result is based on any-overlap versus area-weighted coverage.
- Forest-data age: calculate age from the scan date underlying the particular raster/product, not product publication date.
- Event-after-scan: flag events whose reported date is after the relevant scan date.
- Scan bracket: for each event, retain closest registered scan strictly before and after the event. Missing one side is an open interval, not zero.
- "Since scan" event count: count only events with geometrically meaningful overlap and a source date later than the scan observation.
- Confidence: distinguish exact date from source-reported date, index-tile date, estimated interval and incomplete flight history.

## Important distinction in wording
Skogliga grunddata are modelled estimates derived from laser data and field inventory, not direct measurements of every point. A user-facing "age" insight describes the age of the underlying observation, not necessarily the age of every individual attribute or the actual current forest condition.

## Initial scope
Use current Omdrev 3 volume rasters and the collected scan metadata for the existing test areas (raster codes 12, 21, 23). Keep Omdrev 1/2 metadata as scan-history context until comparable historical metric rasters are collected. Avoid presenting Omdrev 3 volume values as if they belonged to Omdrev 1 or 2.

## Product examples
A monitoring feed item could say:
"Did you know? The forest data used for this area was scanned on 9 August 2020. That observation is now 6 years old. Since then, one completed-harvest event has been registered within the area."

The interface should link the insight to the underlying observation, show the scan date and survey round, and allow the user to inspect the matched event(s).