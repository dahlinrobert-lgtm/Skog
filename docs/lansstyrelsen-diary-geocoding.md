# Matching diary clues to official protected areas

This stage matches extracted named-area/place-name clues against a GeoJSON export from Naturvårdsverket's official Nature Conservation Register.

Official source and service information:
- Naturvårdsverket public WFS: https://geodata.naturvardsverket.se/naturvardsregistret/wfs
- Metadata for open services and protected areas: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=50FE77C1-43A0-445A-B56C-6B729E21DC67_C
- The register includes national parks, nature reserves and several other protected-area types; the data is maintained by county administrative boards.

## Prepare official GeoJSON

Export/download the protected-area layer from Naturvårdsverket's open data service as GeoJSON and save it locally. Then run:

```bash
python scripts/lansstyrelsen_diary_geocoding.py
python scripts/lansstyrelsen_diary_protected_area_match.py --official-geojson path/to/official-protected-areas.geojson
python scripts/test_lansstyrelsen_diary_protected_area_match.py
```

The script discovers the name field from feature properties and fails closed if it cannot find one. It only assigns coordinates for a unique exact normalized name match. If multiple official areas share a name, or no match is found, it leaves coordinates and circle radius null.

For a unique polygon match, the coordinate is an interior representative point and the circle radius is the distance needed to enclose the whole official polygon. This is intentionally conservative: the circle communicates the matched area's extent, **not** the exact planned burn footprint. A later step should use case details/attachments to find a more precise burn polygon or location where available.

The output popup includes the matched official name, source, match method, clue source, confidence explanation, and the circle's meaning. Municipality and postort clues are not used to fabricate protected-area coordinates.
