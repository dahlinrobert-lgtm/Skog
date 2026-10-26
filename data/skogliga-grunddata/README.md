# Skogliga grunddata – volym (omdrev 3)

Här läggs små provfiler från Skogsstyrelsens volymraster för att verifiera att data går att hämta, läsa och använda i Skog.

## Syfte
- Testa rasterformat, CRS, upplösning och pixelvärden.
- Dokumentera källa och hämtningstid för varje provfil.
- Använda REST-tjänsten om möjligt; annars dokumentera nedladdningslänk och geografiskt område.

## Viktigt
- Lägg bara in små provfiler här till att börja med.
- Filer över 50 MB ger Git-varning och filer över 100 MB blockeras normalt av GitHub. Uppladdning via webbläsaren är begränsad till 25 MiB per fil.
- Stora eller ofta uppdaterade raster bör senare hämtas automatiskt eller lagras utanför vanlig Git-historik.
- Behåll metadata för källa, datum, område, koordinatsystem, cellstorlek och licens/villkor.

## Filnamn
Använd gärna: `volym_omdrev3_<område>_<datum>.<ext>`

Ingen rasterfil är ännu incheckad i den här mappen.


## Automatisk validering

GitHub Actions kör `scripts/validate_skogliga_grunddata.py` när ZIP-filerna ändras eller vid manuell start. Rapporten `validation-report.json` innehåller arkivinventering, SHA-256, ZIP-kontroll och metadata för läsbara raster (dimensioner, CRS, upplösning, utbredning, band och NoData).

Kör lokalt efter att ha installerat Rasterio:

```bash
python -m pip install rasterio
python scripts/validate_skogliga_grunddata.py
```

Skriptet packar bara rastermedlemmar till temporära mappar för metadataavläsning; ZIP-originalen ändras inte.


## Senaste valideringsresultat

Körningen 2026-10-26 kunde läsa alla tre raster utan fel. Se [validation-report.json](validation-report.json) för fullständiga metadata och SHA-256-kontroller.

| Fil | Rasterstorlek | Upplösning | CRS | Utbredning (SWEREF 99 TM) |
|---|---:|---:|---|---|
| `sks_Volym_omdrev3_07.tif` | 25 000 × 15 000 | 10 m | EPSG:3006 | E 350000–600000, N 6200000–6350000 |
| `sks_Volym_omdrev3_10.tif` | 15 000 × 15 000 | 10 m | EPSG:3006 | E 450000–600000, N 6150000–6300000 |
| `sks_Volym_omdrev3_13.tif` | 20 000 × 20 000 | 10 m | EPSG:3006 | E 250000–450000, N 6200000–6400000 |

Alla tre är GeoTIFF med ett `int16`-band och NoData-värdet `-1`. Rasterdimensioner/utbredning är metadata; rapporten bekräftar inte ännu enhet eller tolkning av övriga pixelvärden.

Arbetsflödet laddar nu rapporten upp som ett GitHub Actions-artifakt i stället för att försöka pusha direkt till `main`. Det undviker samtidighetskonflikt med andra commits.
