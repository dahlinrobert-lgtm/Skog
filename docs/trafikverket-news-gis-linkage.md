# Trafikverket news and GIS linkage inventory

## Purpose

Use the national news feed as an event-discovery layer and identify which Trafikverket geodata products may provide spatial context. A news article is not itself a GIS feature and a keyword match is not a verified spatial join.

## Candidate layer families

| News theme | Candidate Trafikverket data | Potential linkage |
|---|---|---|
| Roads, numbered roads, bridges, tunnels and road facilities | NVDB road network and relevant road features | Route number, road name, municipality, project/segment |
| Railways, stations, track works and level crossings | NJDB railway network and relevant railway features | Railway line, station, track section, project |
| Closures, roadworks, diversions and disruptions | Trafikverket real-time road/rail traffic information API; Datex II where relevant | Event coordinates, route reference, start/end time |
| Traffic volume, speed and capacity | Road traffic and speed data | Road segment and measurement location |
| Noise, wildlife passages, water and environmental impacts | Surrounding geodata and relevant infrastructure/environment products | Project area, point/line/polygon geometry |
| Consultation, permits and planned construction | Project-specific planning material and project geometries, if openly available | Project name, route corridor, municipality and project ID |

Trafikverket groups its data into road data, road traffic data, railway data, surrounding geodata and traffic information. NVDB contains the road network and associated road features; NJDB is the railway reference network. The real-time traffic API is a separate service and requires registration and acceptance of its API licence. Lastkajen is the download channel for road and railway datasets.

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
