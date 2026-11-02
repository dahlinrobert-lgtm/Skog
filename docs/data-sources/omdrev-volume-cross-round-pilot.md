# Omdrev volume raster inventory and cross-round pilot

Screening date: 2026-11-03

## Confirmed OneDrive inventory

The personal OneDrive `/Skogskoll` contains three separate folders of volume raster ZIP archives:

| Survey round | Folder | ZIP archives listed |
|---|---|---:|
| Omdrev 1 | Skogliga grunddata - Volym (omdrev 1, 2008-2016) | 20 |
| Omdrev 2 | Skogliga grunddata - Volym (omdrev 2, 2018-2025) | 21 |
| Omdrev 3 | Skogliga grunddata – Volym (omdrev 3, 2025-) | 9 |

The same raster tile codes 12, 21 and 23 are present in all three folders. This provides a controlled cross-round pilot using identical geographic footprints.

### Selected pilot files

| Omdrev | File | Size (bytes) |
|---|---|---:|
| 1 | sks_Volym_omdrev1_12.zip | 57,574,654 |
| 1 | sks_Volym_omdrev1_21.zip | 158,550,346 |
| 1 | sks_Volym_omdrev1_23.zip | 349,536,784 |
| 2 | sks_Volym_omdrev2_12.zip | 90,905,837 |
| 2 | sks_Volym_omdrev2_21.zip | 247,234,548 |
| 2 | sks_Volym_omdrev2_23.zip | 561,991,613 |
| 3 | sks_Volym_omdrev3_12.zip | 85,539,457 |
| 3 | sks_Volym_omdrev3_21.zip | 30,278,128 |
| 3 | sks_Volym_omdrev3_23.zip | 30,459,479 |

The nine pilot archives total approximately 1.61 GB (decimal). Omdrev 1 and 2 archives are already stored in OneDrive; they are not yet wired into the existing GitHub Actions downloader.

## Product and service facts

Skogsstyrelsen's technical specification describes the Skogliga grunddata image service as a 10-band image:
1. Volume (m3sk/ha)
2. Basal-area-weighted mean height (dm)
3. Basal area (m2/ha)
4. Basal-area-weighted mean diameter (cm)
5. Biomass (tonnes dry matter/ha)
6. P95 height (dm)
7. Vegetation ratio (%)
8. Laser acquisition date as UnixDay (days since 1970-01-01)
9. Leaf-on/leaf-off indicator
10. NMD forest productivity class

The same specification describes a laser-scan date WMS per 2.5 km tile and says Omdrev 1 and 2 are in the same image service, with a mosaic rule/query to select a survey round. The published service also documents a growth raster function comparing Omdrev 1 and 2. The current download portal lists separate downloadable raster products for Omdrev 1, 2 and 3, including volume, height, P95, vegetation ratio, diameter, basal area and biomass.

Sources:
- https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/teknisk-beskrivning/skogliga-grunddata---teknisk-beskrivning.pdf
- https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/ladda-ner-geodata/
- https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/skogliga-grunddata/

## Critical technical distinction

There are two complementary scan-date pathways:
- 2.5 km scan-index polygons with LAZ filename and flight metadata;
- scan-date pixels in band 8 (UnixDay) of the 10-band Skogliga grunddata image service.

The pixel date band is potentially more spatially precise than assigning one date to an entire 2.5 km tile. It should be investigated and compared with the LAZ/index metadata. Do not assume that the downloaded single-product volume ZIP archives contain all 10 bands; inspect each GeoTIFF's band count, descriptions, tags, CRS, resolution and NoData before interpreting it.

The existing Omdrev 3 join computes valid-pixel statistics for a volume raster under metadata tile polygons. It does not establish that the raster itself contains the scan-date band or prove that a metadata record is the exact acquisition date of every pixel.

## Pilot objective

Use the identical tile codes 12, 21 and 23 across Omdrev 1, 2 and 3 to:
1. Inspect ZIP/GeoTIFF structure and verify CRS, resolution, transform, bounds, data type, NoData, band count and tags.
2. Compare footprints and valid-data coverage between rounds.
3. Join each volume raster only to scan observations belonging to the corresponding survey round, retaining tile ID, scan date, LAZ filename, leaf status and scan block.
4. Where possible, query the 10-band image service for UnixDay and compare pixel-level scan dates to tile metadata.
5. Calculate per-tile and per-pixel volume change only where both rounds have valid, spatially aligned cells; report coverage and alignment diagnostics.
6. Keep source acquisition date, product publication/version date and retrieval timestamp as distinct fields.

## Reusable data model

A raster asset should be identified by `survey_round + product + tile_code + source_version`, not just tile code. The common metadata layer is linked through spatial tile geometry and survey round. The raster-pixel scan-date band, if available, is stored as a separate observation layer rather than copied from the 2.5 km polygon.

## Next implementation step

Create a separate Actions workflow for the nine-file pilot, without changing the existing Omdrev 3 collection workflow. It should download the six Omdrev 1/2 archives from OneDrive, reuse the existing Omdrev 3 archives, inspect all nine GeoTIFFs and emit a machine-readable manifest plus coverage/alignment diagnostics. Only after this passes should the generic multi-product/multi-round join replace the current Omdrev 3-only script.
