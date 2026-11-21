# Trafikverket news and GIS linkage inventory

## Purpose

Use the national Trafikverket news feed as an event-discovery layer and screen articles for possible thematic relationships to geodata already included in the Skog snapshot pilot. A news article is not itself a GIS feature, and a keyword match is not a verified spatial join.

## Scope

This implementation deliberately screens only two existing snapshot families:

| Snapshot service | Layer family | Candidate themes |
|---|---|---|
| `MWLEXGEO/MiljowebbGeo/MapServer` | Miljöwebb Landskap | Wildlife/fauna passages, species-rich road verges, invasive species, cultural environments, water fauna passages, nature values and ecological connections |
| `NVDB_på_karta/Viltolyckor_NVDBpakarta/MapServer` | NVDB Viltolyckor | Wildlife collisions and species/risk references represented by the seven road-link frequency layers: ungulates total, moose, wild boar, roe deer, reindeer, red deer and fallow deer |

The NVDB layers describe aggregated accident frequency per road link, not dated individual collision events. A news item about an elk collision is therefore a thematic candidate, not proof that the collision appears as an event in the snapshot.

Railway networks, general real-time traffic information, traffic volume/speed products and generic project-planning data are excluded from this pilot linkage inventory. Explicit road numbers (for example E4 or road 95) are retained as textual route clues; they are not matches to NVDB road segments because news text does not provide a stable NVDB link identifier or verified geometry.

## Output and method

The probe adds `national_news_gis_linkage_inventory` to its JSON report. It screens article title, preamble, category and URL using conservative keyword rules and extracts explicit route references.

Categories are overlapping: one article may match both candidate layer families. Records without a keyword match remain in the output as `unclassified`. A match is labelled `thematic_candidate_only`; it must not be interpreted as a verified geographic match.

The monthly national news inventory is collected once and reused for this thematic screening and the corresponding report field. This avoids a duplicate monthly collection.

## Matchability levels for future work

1. **Thematic candidate** — title or preamble contains a relevant species, environmental term or feature concept.
2. **Geographic clue** — article identifies a named place, municipality, road number, route or project. Store the clue verbatim and its extraction method.
3. **Spatial candidate** — an independently sourced point, line or polygon for the article/project can be compared with snapshot geometry.
4. **Verified feature link** — the spatial operation and identity are reproducible; store service URL, layer ID/name, feature identity field/value, geometry relation, distance/intersection measure and snapshot date.

Do not upgrade a record from level 1 or 2 to level 3 merely because it mentions E4, a municipality or an animal. A road number is a route clue, not an NVDB link ID.

## Suggested evidence fields for a future spatial linkage stage

- `article_url`, `published_date`, `article_title`
- `snapshot_family`, `snapshot_service_url`, `snapshot_layer_id`, `snapshot_layer_name`
- `thematic_terms`, `species_terms`, `route_references`, `place_names`, `project_names`
- `matchability_level`, `match_method`, `match_evidence`
- `feature_identity_field`, `feature_identity_value`, `snapshot_date`
- `spatial_relation`, `distance_m`, `review_status`

Populate feature identity and spatial fields only after an actual geometry/attribute comparison. Missing values remain null, not inferred.

## Limitations and reporting

- Keyword classification is not semantic validation and may overcount broad terms.
- Project news may describe planning or consultation without a published project geometry.
- A project URL/category may identify a project but not a unique physical location.
- The current two snapshot services are collected only for the Gräsmyr pilot envelope. A nationwide spatial join is therefore not possible from these snapshots.
- Do not calculate a national match rate against the Gräsmyr snapshot; its geographic envelope is not a representative national sample.
- Confirm product-specific licence, API terms, attribution and redistribution rights before customer-facing use.

The national report should publish overlapping article counts per thematic family, counts of records with route clues, and a clear warning that the results are thematic candidates only. Unmatched articles must remain in the inventory.
