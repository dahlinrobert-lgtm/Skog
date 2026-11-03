# SCA voluntary set-asides – national tile collection

## Current verified collection

- Source tile harvest run: [41704577034](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41704577034)
- Geometry build run: [41714471371](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/41714471371)
- Positive z9 census seeds: 183
- Globally unique z12 tiles in tile plan: 12,420
- Source feature records: 34,932
- Geometry types: 33,947 Polygon; 985 MultiPolygon
- Geometry parse/validity failures: 0
- Exact geometry repetitions across source records: 285 extra representations in 285 groups
- All source MVT tile records are retained with source tile, source layer, source feature index, source tile hash and URL in batch manifests.

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
- 285 exact geometry duplicate representations have been detected. Do not discard source records; preserve provenance.
- Different clipped/generalized geometries for the same object will not be found by exact geometry hashing.
- Geometry reconstruction and object identity across tile edges are still pending.
- The z12 coverage plan is expanded from 183 z9 positive seed tiles and a one-tile neighbor ring. It does not prove complete national SCA coverage.
- HTTP 404 is not proof of no set-aside; the service may use sparse tile delivery.
- EPSG:3857 is a working geometry CRS. Use a suitable Swedish projected CRS for authoritative area calculations.
- The online service and its license/terms must be checked before external redistribution or commercial use.

## Next milestone

Reconstruct candidate objects by examining adjacency and overlap across tile boundaries, while retaining each source feature as an immutable observation. Validate candidate merges using geometry, class, motive and neighboring tile provenance. Publish unique object counts only after that review.
