# Round-aware Omdrev scan metadata analysis

The first spatial overlay repeats the same scan-index metadata against each
raster round. This is useful for spatial comparison, but its row counts must not
be interpreted as separate metadata coverage for each raster round.

This follow-up deduplicates source records by ArcGIS object ID and produces:
- a metadata inventory by metadata survey round and raster tile;
- a 2 km-cell summary of spatial intersections against the Omdrev 3 reference
  grid, with raster valid fraction retained as a separate attribute;
- a JSON summary explicitly marking Omdrev 3 as ongoing.

A metadata polygon is a 2.5 km index area, not an exact aircraft flight
footprint. Spatial intersection does not attribute a raster pixel to an
individual scan. Omdrev 3 counts describe a current partial snapshot, not final
coverage.
