# Manual geometry conversion helper

This helper converts the downloaded JSON response from the Min karta geometry probe into a GeoJSON FeatureCollection in WGS84/EPSG:4326. It preserves multiple area geometries as MultiPolygon features.

## Important: verify the CRS first

The Min karta endpoint is undocumented and the response shown so far does not declare its coordinate reference system. Coordinate values that look like projected metres are not sufficient evidence to assume EPSG:3006. Lantmäteriet's public help says Min karta can show approximate boundary coordinates in SWEREF 99 TM. A local diagnostic conversion of the sample using EPSG:3006 placed the larger polygon in the expected Gräsmyr area and close to the project's known reference location. This is supporting evidence, but not a formal declaration from the endpoint. Before treating the CRS as production-verified, compare the converted outline visually against the selected property in Min karta or an authoritative layer.

Do **not** run a conversion until the source CRS has been independently verified against a known point or authoritative metadata. The required `--confirm-crs` flag is an intentional safety check, not automatic CRS detection.

## Usage

Install the dependency:

```bash
python -m pip install pyproj
```

After verification, for example if the source CRS is proven to be EPSG:3006:

```bash
python skogskoll/tools/convert-min-karta-geometry.py v1 skogskoll-geometry.geojson --source-crs EPSG:3006 --confirm-crs
```

Input should be the raw JSON file downloaded from the manual probe, not the HAR file. Output is standard GeoJSON in longitude/latitude order (WGS84). Each area has its own Feature and includes source identity and area number.

## Tests

From this directory, run:

```bash
python -m pip install pyproj
python -m unittest -v test_convert_min_karta_geometry.py
```

## Scope and limitations

- This is a local, manual diagnostic helper, not a production integration.
- It does not call Min karta, upload data, or infer the source CRS.
- It currently handles Polygon geometries in `enhetsutbredning[].yta[]`.
- Min karta's displayed property boundaries are indicative and are not legally authoritative.
- Production should use Lantmäteriet's authorized Fastighetsindelning Direkt API after access and usage approval.
