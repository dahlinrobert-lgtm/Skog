# Manual geometry conversion helper

This helper converts a manually saved Min karta geometry response to GeoJSON in WGS84/EPSG:4326. It preserves separate area geometries. The undocumented endpoint is for manual diagnostics only, not production integration.

## Important: source CRS is unverified

The source response does not declare its coordinate reference system. Coordinates that look like projected metres are not sufficient evidence to assume EPSG:3006. Lantmäteriet says Min karta can show approximate boundary coordinates in SWEREF 99 TM, but that does not prove this particular endpoint uses EPSG:3006.

Do **not** run the production-style converter until the source CRS has been independently verified against authoritative metadata or a suitable control point. The required `--confirm-crs` flag is an intentional safety check, not automatic CRS detection.

## Actual Gräsmyr sample: diagnostic results

The saved raw JSON was inspected (two `enhetsutbredning` Polygon records). A separate diagnostic calculation tested the **hypothesis** EPSG:3006 and compared the resulting locations to the project's approximate Gräsmyr reference point (19.66455 E, 63.74646 N). These are diagnostic calculations, not confirmation of the CRS.

| Diagnostic under EPSG:3006 hypothesis | Area 1 | Area 2 |
|---|---:|---:|
| Positions in outer ring, including closure | 39 | 11 |
| Unique outer-ring vertices | 38 | 10 |
| Ring closed | Yes | Yes |
| Polygon valid in source coordinate plane | Yes | Yes |
| Approximate planar area | 571,767 m² | 44,622 m² |
| WGS84 bounding box (longitude, latitude) | 19.639193–19.709164 E; 63.738586–63.758744 N | 19.710105–19.717691 E; 63.757029–63.761363 N |
| Distance to approximate reference point, in hypothesized source CRS | 32.68 m | 2,547.79 m |
| Reference point inside polygon | No | No |

### Interpretation

- Both rings are closed and both polygons are valid under the tested coordinate-plane interpretation.
- Under EPSG:3006, area 1 lands in the expected general Gräsmyr region, but the approximate project reference point is about 33 m outside its polygon. Since that point is not a surveyed control point, this alone neither proves nor disproves the CRS.
- Area 2 lies about 2.55 km from that same reference point. This may represent a separate area, but its relationship to the intended property needs visual or authoritative confirmation.
- The source CRS remains **unverified**. These results do not establish that the polygons match the correct property or any legally valid boundary.

## Diagnostic audit tool

The new `audit-geometry-sample.py` tool runs these checks reproducibly against a manually saved JSON file and deliberately keeps `source_crs_verified` and `authoritative_boundary_verified` false.

Install dependencies:

```bash
python -m pip install pyproj shapely
```

Example, explicitly testing a CRS hypothesis (not asserting that it is correct):

```bash
python skogskoll/tools/audit-geometry-sample.py v1 grasmyr-audit.json --hypothesis-crs EPSG:3006 --reference-lon 19.66455 --reference-lat 63.74646
```

Input is the raw JSON response, not a HAR file. The tool does not call Min karta, infer CRS, upload geometry, or certify cadastral boundaries.

## Converter usage (only after independent CRS verification)

```bash
python skogskoll/tools/convert-min-karta-geometry.py v1 skogskoll-geometry.geojson --source-crs EPSG:3006 --confirm-crs
```

Output is GeoJSON in longitude/latitude order (WGS84). Each area is retained as a separate feature with source identity and area number.

## Geometry QA report

After conversion, `validate-geojson-report.py` checks GeoJSON structure, geometry validity, ring closure, and coordinate bounds. Such checks do not verify the source CRS or authoritative boundary.

```bash
python skogskoll/tools/validate-geojson-report.py skogskoll-geometry.geojson skogskoll-geometry-report.json
```

## Independent verification: next step

The preferred independent comparison is the authorized Lantmäteriet **Fastighetsindelning Direkt** API after access and usage approval. It provides property and joint-property geometries, but the product page notes legal review and specific usage conditions. The paid Fastighetsindelning Visning WMS can be a visual reference if licensed; it is a display service, not editable vector geometry.

Until one of those comparisons is completed, keep the CRS and authoritative-boundary verification flags false and do not use this sample as a production boundary source.
