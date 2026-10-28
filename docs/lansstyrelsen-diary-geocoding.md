# Länsstyrelsen diary geocoding pilot

This pilot extracts geographic clues from the persisted Länsstyrelsen diary records. It does **not** assign coordinates based only on municipality, postort, or a place-name guess.

## Run

```bash
python scripts/lansstyrelsen_diary_geocoding.py
python scripts/test_lansstyrelsen_diary_geocoding.py
```

The generated `data/lansstyrelsen-diary/geocoding-candidates.json` is an audit-friendly intermediate dataset. Each record contains candidate clues, their source, a confidence category, and popup text intended for a future map.

## Confidence interpretation

- `medium`: a named protected area appears in the case title; it still needs an authoritative polygon match.
- `low`: a municipality or candidate place name is present, but the exact burn location is not established.
- `very_low`: only postort metadata is available; it may describe the sender rather than the burn site.
- `unresolved`: no usable clue was extracted.

Coordinates, circle radius, and geometry remain null until an authoritative place/protected-area match is made. Once a location is verified, the map can display a circle/point and the click popup can explain the evidence, source, method, confidence, and uncertainty. The circle should represent geocoding uncertainty or the area of the matched feature—not an invented burn boundary.
