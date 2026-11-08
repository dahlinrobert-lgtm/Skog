# Trafikverket news and GIS linkage inventory

## Purpose

Use the national news feed as an event-discovery layer and identify which Trafikverket geodata products may provide spatial context. A news article is not itself a GIS feature and a keyword match is not a verified spatial join.

## Candidate layers — restricted to the snapshot pilot

This implementation deliberately matches only the two Trafikverket services already included in
`scripts/snapshot_trafikverket.py`:

| Snapshot service | Layer family | News themes that justify a candidate |
|---|---|---|
| `MWLEXGEO/MiljowebbGeo/MapServer` | **Miljöwebb Landskap** | Wildlife/fauna passages, species-rich road verges, invasive species, cultural environments, water fauna passages, nature values and ecological connections |
| `NVDB_på_karta/Viltolyckor_NVDBpakarta/MapServer` | **NVDB Viltolyckor** | Wildlife collisions and species/risk references covered by the seven road-link frequency layers: ungulates total, moose, wild boar, roe deer, reindeer, red deer and fallow deer |

The seven NVDB layers describe aggregated accident frequency per road link, not dated individual
collision events. A news item about an elk collision is therefore a thematic candidate, not proof
that the collision appears as an event in the snapshot.

Explicit road numbers (for example E4 or road 95) are retained as **textual route clues**. They
are not treated as matches to an NVDB road segment because the news record does not supply a
stable NVDB link identifier or verified geometry.

Railway networks, general real-time traffic information, traffic volume/speed products and generic
project-planning data are intentionally excluded from this inventory. They are not part of the
snapshot layer scope requested for this analysis.

## Inventory output

The probe emits a per-article candidate list based on title, preamble, category and URL. It extracts explicit route references where possible and counts overlapping thematic matches. This is a screening aid only.

## Matching workflow

1. Resolve article to a candidate project, named route, station, bridge or locality.
2. Verify against the appropriate authoritative GIS layer and its metadata.
3. Use spatial intersection or network referencing only after a feature geometry/route reference is available.
4. Store match method, confidence, source layer ID, feature ID, source URL and retrieval date.
5. Keep unmatched articles in the news archive; do not force a geometry.

## Important limitations

- Keyword classification is not semantic validation and may overcount broad terms.
- Many project news articles describe planning or consultation without a published project geometry.
- A project URL/category may identify a project but not a unique physical location.
- Confirm product-specific licence, API terms, attribution and redistribution rights before customer-facing use.
