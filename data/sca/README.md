# SCA voluntary set-asides – national tile collection

## Current verified collection

- Source tile harvest run: [41704577034](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41704577034)
- Geometry build run: [41714471371](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41714471371)
- Positive z9 census seeds: 183
- Globally unique z12 tiles in tile plan: 12,420
- Source feature records: 34,932
- Geometry types: 33,947 Polygon; 985 MultiPolygon
- Geometry parse/validity failures: 0
- Batch-local exact geometry repetitions: 285 extra representations in 285 groups (not yet a global cross-batch identity count)
- All source MVT tile records are retained with source tile, source layer, source feature index, source tile hash and URL in batch manifests.

## Cross-tile topology audit

- Audit run: [41724100628](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41724100628)
- Input: all 25 geometry batches; 34,932 source records across 2,915 source tiles.
- Globally unique exact geometry hashes: 34,604.
- Exact geometry repetition: 328 extra records across 328 duplicate hash groups.
- Candidate pairs flagged: 10,325 (328 exact duplicates; 157 near-duplicate candidates; 1,002 contained/nested; 6,908 partial overlaps; 1,930 nearby boundaries).
- No source observations were merged, deleted, or dissolved.

The 328 exact duplicate pairs are strong duplicate candidates, not confirmed duplicate objects. Five pairs have different resolved classes; 104 have different or missing motive values. Attribute disagreements must remain visible during reconciliation. Near-duplicate candidates require review of source provenance and attributes. Partial overlaps and nearby boundaries are deliberately broad review categories and must not be treated as object counts.

The audit is a candidate generator, not a national unique-object census. Its search covers exact geometry hashes globally and spatial relationships between distinct tiles no farther than one tile in either XYZ direction. The underlying z12 plan is still based on positive z9 seeds plus a one-tile neighbor ring, so completeness of national source coverage remains unproven.

## Candidate grouping run #1

- Run: [41725375000](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41725375000)
- Result: 475 candidate groups containing 954 source observations.
- Group sizes: 473 groups of 2 observations and 2 groups of 4 observations.
- Grouped high-confidence edges: 485 (328 exact geometry; 157 near duplicates).
- Class conflicts: 0 groups.
- Motive variation or missing motive: 142 groups.
- All 34,932 source records remain in the source geometry batches; only 954 currently participate in these high-confidence candidate groups.

Caution: these groups are connected components of exact/near-duplicate edges and are not confirmed source object IDs. The builder's first output summary counted only observations present in at least one topology edge when computing the previous `unassigned_candidate_edge_observations` field. That field did not represent all source records. The builder has been corrected to report edge-universe observations, source records with no candidate edge, and total source records not grouped separately; rerun it to produce the corrected summary.

## Classification snapshot

| SCA resolved class | Source records |
| --- | ---: |
| 51 Naturvård orörd (NO) | 29,449 |
| 60 Naturvård Skötsel utan virkesuttag | 3,143 |
| 59 Naturvård Skötsel med virkesuttag | 1,987 |
| 52 Överhålles (får ej nyregistreras) | 9 |
| Missing | 344 |

## Motive snapshot

| Motive | Source records |
| --- | ---: |
| 1 Eget värde | 18,022 |
| 2 Eget värde och läge | 6,691 |
| 3 Förstärkningsområde | 493 |
| 4 Skyddszon | 346 |
| 5 Läge med imp. | 1,084 |
| 6 Inom Värdetrakt | 196 |
| 7 Tvingande myndighetsbeslut | 43 |
| 8 Social Hänsyn, Övrigt | 18 |
| 9 Social Hänsyn, Rennäring | 49 |
| 11 Eget värde, vindkraftskompensation | 104 |
| 0 Ej bedömd | 227 |
| Missing | 7,659 |

## Interpretation and limitations

- 34,932 are source tile feature records, not unique voluntary set-aside objects.
- The 285 exact-geometry repetitions are summed from per-batch checks; cross-batch duplicates still require a global comparison. Do not discard source records; preserve provenance.
- Different clipped/generalized geometries for the same object will not be found by exact geometry hashing.
- Geometry reconstruction and object identity across tile edges are still pending.
- The z12 coverage plan is expanded from 183 z9 positive seed tiles and a one-tile neighbor ring. It does not prove complete national SCA coverage.
- HTTP 404 is not proof of no set-aside; the service may use sparse tile delivery.
- EPSG:3857 is a working geometry CRS. Use a suitable Swedish projected CRS for authoritative area calculations.
- The online service and its license/terms must be checked before external redistribution or commercial use.

## Next milestone

Reconstruct candidate objects by examining adjacency and overlap across tile boundaries, while retaining each source feature as an immutable observation. Validate candidate merges using geometry, class, motive and neighboring tile provenance. Publish unique object counts only after that review.
