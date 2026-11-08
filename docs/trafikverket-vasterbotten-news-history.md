# Trafikverket – Västerbotten news history pilot

## Purpose

Discover the most complete publicly accessible historical news series for
Västerbotten before implementing recurring collection and permanent storage.

Primary archive:
- https://www.trafikverket.se/om-oss/nyheter/?county=18
- County filter: `18` (Västerbotten)
- The archive showed 67 results when the pilot was initiated on 2026-11-08.

## Collection design

1. Inspect the archive's own pagination, forms, scripts and sitemap declarations.
2. Identify and document a supported public retrieval route; do not guess hidden
   paging parameters or treat the first ten results as a complete archive.
3. Collect article metadata and original URLs, preserving publication and update
   dates separately.
4. Keep a raw source record and a normalized event record.
5. Deduplicate by canonical article URL, retaining title/date changes as updates.
6. Geocode only when the article provides enough explicit place/project context.
   Never infer precise geometry from a vague regional reference.
7. Store immutable dated snapshots and a current index. Keep source attribution.

## Why discovery is a separate first PR

The archive is county-filtered and includes project news as well as county news.
Some project articles may live outside the `/lansnyheter/vasterbotten/` URL path.
A sitemap-only crawl could therefore omit relevant records. The discovery
workflow captures the archive's actual pagination and public sitemap structure
before a complete collector is implemented.

## Existing related data flows

The repository already has Trafikverket GIS inventory and weekly Gräsmyr
snapshots. This news pilot is a separate, non-spatial source intended to
contextualize environmental and landscape GIS observations.
