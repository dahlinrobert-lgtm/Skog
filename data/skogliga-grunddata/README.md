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
