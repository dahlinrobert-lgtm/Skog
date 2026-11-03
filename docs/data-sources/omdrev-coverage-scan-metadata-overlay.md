# Omdrev coverage and scan-metadata overlay

This workflow combines the 2 km valid-data coverage masks for Omdrev 1-3 with
Skogsstyrelsen's 2.5 km laser scan index polygons.

It retains raster round and metadata survey round separately, together with
scan date, index tile, source file, leaf status, flight block, scanner model
and geographic overlap fraction.

The join is a spatial association. It does not establish the exact acquisition
flight for each raster pixel. NoData does not prove absence of laser scanning,
and metadata dates may not represent complete flight-by-flight history.

The workflow downloads the same nine pilot rasters from OneDrive, collects
scan-index metadata for the actual Omdrev 3 raster extents, then overlays those
metadata polygons against 2 km coverage cells from all three rounds.
