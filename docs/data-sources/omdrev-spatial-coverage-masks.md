# Omdrev spatial coverage masks

This pilot produces a 2 km grid of valid-data coverage for matched volume rasters
from Omdrev 1, 2 and 3 (tile codes 12, 21 and 23).

## Method
- Reads the GeoTIFFs inside the nine OneDrive ZIP archives.
- Uses each GeoTIFF's NoData value; zero is retained as valid.
- Aggregates valid and NoData pixel counts into 2 km cells in EPSG:3006.
- Compares Omdrev 2 and 3 cell-by-cell after checking geographic cell bounds.
- Writes a CSV for GIS overlay and a JSON summary.

## Interpretation
This is a spatial distribution of valid raster cells, not a laser-flight footprint.
NoData does not prove that no laser scanning took place. It may reflect product
processing, masking, acquisition coverage, or another source limitation.

The next stage is to overlay these cells with Skogsstyrelsen's 2.5 km scan-index
metadata polygons, retaining survey round, scan date, flight block and leaf status.
If available and verified, the ImageServer UnixDay band can then provide
pixel-level scan-date attribution. Do not infer scan date from ZIP publication dates.

The script deliberately does not interpret raw volume values or their scale.
