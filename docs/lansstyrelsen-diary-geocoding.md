# Matching diary clues to official protected areas

This stage matches extracted named-area/place-name clues against Naturvårdsverket's official Nature Conservation Register.

Official source:
- WFS: https://geodata.naturvardsverket.se/naturvardsregistret/wfs
- Layer: `Naturvardsregistret_WFS:SkyddadeOmraden`
- Metadata: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=50FE77C1-43A0-445A-B56C-6B729E21DC67_C
- Open-data documentation: https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret/Naturvardsregistret_beskrivning_av_oppna_data.pdf

## Fetch and match

```bash
python scripts/lansstyrelsen_diary_geocoding.py
python scripts/lansstyrelsen_diary_fetch_protected_areas.py
python scripts/lansstyrelsen_diary_protected_area_match.py --official-geojson data/lansstyrelsen-diary/official-protected-areas.geojson
python -m pip install pytest
PYTHONPATH=scripts pytest -q scripts/test_lansstyrelsen_diary_geocoding.py scripts/test_lansstyrelsen_diary_protected_area_match.py scripts/test_lansstyrelsen_diary_fetch_protected_areas.py
```

The fetcher uses paginated WFS requests and writes atomically. It refuses to publish an empty dataset or malformed response. The official layer includes several protected-area types, so the matcher still checks exact names and only assigns coordinates for a unique match. If multiple official features share the name, or no match exists, coordinates and circle radius remain null.

For a unique polygon match, the coordinate is an interior representative point and the circle radius encloses the whole official polygon. The circle communicates the matched area's extent, **not** the exact planned burn footprint. The popup includes the official name, source, match method, clue source, confidence explanation, and circle meaning. Municipality and postort metadata alone cannot produce a protected-area coordinate.

## Known limitations

- This layer covers protected areas, not all geographic place names.
- Case details and attachments may identify a more precise planned burn area; harvesting that content is a later phase.
- Exact name matching is intentionally conservative. Fuzzy matching must be reviewed/audited before it can affect map coordinates.
