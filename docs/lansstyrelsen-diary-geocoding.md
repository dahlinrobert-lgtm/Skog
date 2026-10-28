# Länsstyrelsen diary geocoding pilot

This pipeline extracts geographic hints from saved Länsstyrelsen diary records and matches candidate names to official protected-area geometries. Coordinates are only assigned after a match to an official feature; the diary's `Kommun` and `Postort` columns are treated as metadata because they may identify the sender rather than the burn location.

## Official data

The pipeline downloads public ESRI Shape packages from Naturvårdsverket's official directory:

- Direct downloads: https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret/
- Service metadata: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=50FE77C1-43A0-445A-B56C-6B729E21DC67_C
- Open-data documentation: https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret/Naturvardsregistret_beskrivning_av_oppna_data.pdf

The current selection includes NR (nature reserves), NP (national parks), NVO (nature-conservation areas), KR (cultural reserves), DVO (animal/plant protection areas), LBSO (landscape protection areas), OBO (biotope-protection areas), IF (interim prohibitions), and VSO (water-protection areas). The source registers are updated regularly; the workflow downloads current packages on each run.

## Run locally

Install the dependencies and run extraction, official data matching, and tests:

```bash
python -m pip install "shapely>=2.0,<3" "pyproj>=3.6,<4" "pyshp>=2.3,<3" "pytest>=8,<9"
python scripts/lansstyrelsen_diary_geocoding.py
python scripts/lansstyrelsen_diary_fetch_protected_areas.py
python scripts/lansstyrelsen_diary_protected_area_match.py --official-geojson data/lansstyrelsen-diary/official-protected-areas.geojson
PYTHONPATH=scripts pytest -q scripts/test_lansstyrelsen_diary_geocoding.py scripts/test_lansstyrelsen_diary_protected_area_match.py scripts/test_lansstyrelsen_diary_fetch_protected_areas.py
```

The fetcher reads each archive's declared source CRS and reprojects matching features to WGS84. It filters official features down to names found in the diary clues to keep artifacts small. It fails rather than accepting a malformed archive, missing projection, or a source dataset with zero features.

The matching stage uses exact normalized names plus a narrowly defined Swedish genitive form (for example, a title that says "Fulufjällets nationalpark" and an official name "Fulufjället"). If the title names a protected-area type, that type is preferred. A municipality mentioned in the title can help disambiguate a duplicated place name. The `Kommun` and `Postort` metadata columns are not used to disambiguate the burn location.

## Coordinate and circle meaning

For a unique official feature, the point is an interior representative point of the official geometry. The circle radius encloses that whole official feature. It is **not** an asserted burn perimeter. A record naming multiple distinct areas can contain several independently described locations. If same-name features remain ambiguous after using title clues, that candidate remains unplaced rather than receiving a guessed point.

Each map-ready location carries its official name, data package, link to the source, matching method, title clue, confidence explanation, geometry and circle explanation. Official type disagreement is retained as a low-confidence warning instead of silently being treated as a perfect match.

## Current limits

- This is a protected-area matcher, not a complete geocoder for all Swedish place names.
- Dedicated Natura 2000 layers, general official place-name gazetteers, and municipality polygons are not yet integrated.
- Case detail pages and attachments may include the actual burn polygon or a more precise location; extracting those remains a follow-up phase.
- The output is an audit artifact. It is not yet wired into the public-facing map UI.
