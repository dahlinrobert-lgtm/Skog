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


## Theoretical national linkage exercise

Because the two snapshot services are currently collected only for the Gräsmyr pilot envelope, a nationwide spatial join is not possible yet. This section defines a reproducible *theoretical* linkage assessment using national news and the schema/semantics of the pilot snapshots. It must not be presented as a measured national spatial match.

### What can be linked conceptually

| News evidence | Snapshot family | Theoretical link | What is still missing |
|---|---|---|---|
| Explicit wildlife collision and species (moose, wild boar, roe deer, reindeer, red deer, fallow deer) | NVDB Viltolyckor | Species-specific risk/frequency value on a road link | Exact road link ID or reliable event location; the layer is aggregated, not an event log |
| Wildlife collision without species | NVDB Viltolyckor | General ungulate frequency/risk layer | Location and species disambiguation |
| Fauna passage, fencing, ecological connectivity, species-rich road verge | Miljöwebb Landskap | Relevant landscape/environment feature by geometry and attributes | Article location/project extent and matching layer feature |
| Invasive species or species observation described in a news item | Miljöwebb Landskap, only where the corresponding feature type exists | Potential thematic relationship to an invasive-species feature | Exact species, observation location, date and compatible feature type |
| Cultural environment, water fauna/fish passage, nature or landscape value | Miljöwebb Landskap, if represented by a corresponding layer | Potential spatial context around an infrastructure event | Exact layer coverage, feature identity and article geometry |

The table describes possible relationships, not observed matches. An article can relate to more than one family.

### Matchability levels

Use separate fields rather than one opaque confidence score:

1. **Thematic candidate** — title or preamble contains a relevant species, environmental term or feature concept.
2. **Geographic clue** — article identifies a named place, municipality, road number, route or project. Store the clue verbatim and its extraction method.
3. **Spatial candidate** — an independently sourced point, line or polygon for the article/project can be compared with snapshot geometry.
4. **Verified feature link** — the spatial operation and identity are reproducible; store service URL, layer ID/name, feature identity field/value, geometry relation, distance/intersection measure and snapshot date.

Do not upgrade a record from level 1 or 2 to level 3 merely because it mentions E4, a municipality or an animal. A road number is a route clue, not an NVDB link ID.

### Suggested evidence fields

- `article_url`, `published_date`, `article_title`
- `snapshot_family`, `snapshot_service_url`, `snapshot_layer_id`, `snapshot_layer_name`
- `thematic_terms`, `species_terms`, `route_references`, `place_names`, `project_names`
- `matchability_level`, `match_method`, `match_evidence`
- `feature_identity_field`, `feature_identity_value`, `snapshot_date`
- `spatial_relation`, `distance_m`, `review_status`

Only populate feature identity and spatial fields after an actual geometry/attribute comparison. Missing values should remain null, not inferred.

### Illustrative scenarios (not observed articles)

- “Älgolycka på E4 vid [ort]”: thematic candidate for NVDB wildlife layers; E4 and the named place are geographic clues. No road-link match until the location is geocoded and intersected with a road link.
- “Ny faunapassage vid [plats]”: thematic candidate for Miljöwebb Landskap; a project point/line/polygon or a reliable location is needed to identify the corresponding feature.
- “Järnvägsarbeten i [kommun]”: excluded from this snapshot linkage exercise unless the story independently concerns a Miljöwebb Landskap feature or NVDB wildlife risk. A railway-only mention is not a candidate.

### Reporting requirements

The national report should publish:
- article counts per thematic family (overlapping categories clearly labelled);
- counts at each matchability level;
- counts of records with species, route, place and project clues;
- a short reviewed sample of candidate articles with explicit evidence;
- a separate list of limitations and unmatched records.

Do not calculate a national match rate against the Gräsmyr snapshot: its geographic envelope is not a representative national sample. It can validate the matching method only within the pilot area.
