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


## Pixelvärden och täckning

Skriptet `scripts/analyse_skogliga_grunddata.py` analyserar rasterfilerna inuti ZIP-arkiven fönster för fönster. Det räknar giltiga pixlar och NoData, min/max, medelvärde, standardavvikelse och exakta percentiler via histogram. Det jämför också rasterfilernas geografiska begränsningsrutor.

Kör arbetsflödet **Analyse Skogsstyrelsen volume rasters** manuellt under Actions. Resultatet publiceras som artefakten `skogliga-grunddata-pixel-analysis` och innehåller `pixel-analysis-report.json`.

Obs: jämförelsen av täckning använder rasterfilernas begränsningsrutor, inte en fullständig pixel-för-pixel-analys av giltig täckning. Enhet och eventuell skalfaktor härleds inte från pixelvärdena; verifiera dessa mot produktdokumentationen innan värdena används i beräkningar.


### Tolkning av pixelvärden

Skogsstyrelsens produktbeskrivning anger att volym uttrycks i m³sk/ha och att celler där den grundytevägda medelhöjden är under 3 meter får värdet 0 i samtliga kartprodukter. Därför ska nollor inte behandlas som NoData. Analysrapportens procentandel giltiga pixlar betyder endast andelen celler som inte är markerade med NoData (-1); den är inte i sig ett mått på skogstäckning.

Efter den första analysen har skriptet uppdaterats så att nollceller och positiva celler redovisas separat. Se produktbeskrivningen hos [Skogsstyrelsen](https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-skogliga-grunddata---produktbeskrivning.pdf).


## Pixelanalys – resultat 2026-10-26

Arbetsflödet **Analyse Skogsstyrelsen volume rasters** har körts med separat redovisning för nollvärden och positiva värden. Se artefakten från [körning 3](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40391104595).

| Raster | Giltiga celler (0 eller positivt) | Nollvärden | Positiva värden | NoData |
|---|---:|---:|---:|---:|
| `sks_Volym_omdrev3_07.tif` | 4 393 500 | 775 058 | 3 618 442 | 370 606 500 |
| `sks_Volym_omdrev3_10.tif` | 2 212 906 | 1 446 061 | 766 845 | 222 787 094 |
| `sks_Volym_omdrev3_13.tif` | 17 795 154 | 6 924 322 | 10 870 832 | 382 204 846 |

Värdena är i m³sk/ha enligt produktbeskrivningen. Giltiga nollceller är inte NoData och ska inte kastas bort.

## Pixelvis kontroll av överlapp

Arbetsflödet [Compare Skogsstyrelsen raster overlap](https://github.com/dahlinrobert-lgtm/Skog/actions/workflows/compare-skogliga-grunddata-overlap.yml) jämförde cellerna i de geografiska överlappen, blockvis. Rapportartefakten finns i [körning 2](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40391418611).

| Rasterpar | Överlapp | Båda har giltigt värde | Samma värde där båda är giltiga |
|---|---:|---:|---:|
| 07 och 10 | 15 000 km² i begränsningsrutorna | 0 celler | Ej tillämpligt |
| 07 och 13 | 15 000 km² i begränsningsrutorna | 9 683 celler | 9 683 av 9 683 (100 %) |
| 10 och 13 | Inget rektangulärt överlapp | 0 celler | Ej tillämpligt |

Det stora rektangelöverlappet mellan 07 och 10 innehåller inga celler med giltigt värde i båda filer. Mellan 07 och 13 finns 9 683 celler med data i båda, och samtliga har identiska värden. Det talar för att filerna kan kombineras utan konflikt i just det kontrollerade överlappet, men det bevisar inte att de kommer från samma version eller att de täcker hela Sverige.

### Geografisk relevans

Filnamnens länskoder är 07 Kronobergs län, 10 Blekinge län och 13 Hallands län. De här tre testfilerna täcker därför inte Luleå/Norrbotten (länskod 25). För Skogskoll i norra Sverige behöver vi senare lägga till rätt geografiska leveranser; analysflödet kan återanvändas på dem.


## Visuell täckningskontroll

Arbetsflödet [Create Skogsstyrelsen raster overview](https://github.com/dahlinrobert-lgtm/Skog/actions/workflows/create-skogliga-grunddata-overview.yml) skapar en nedskalad PNG-karta och en JSON-rapport som Actions-artifakt. [Lyckad körning 1](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40392838901).

Översikten visar att giltiga celler ligger i mindre, sammanhängande eller uppdelade områden inom varje stor rasterutbredning. Den grå ytan är NoData, gult är giltigt nollvärde och grönt är positiv volym. Kartan är avsedd för snabb visuell kontroll, inte mätning eller beräkning. Den använder närmaste granne för nedskalning; exakta statistikvärden ska tas från originalraster och pixelanalysrapporter.

Norrbotten är inte inkluderat i dessa provfiler avsiktligt. Det är rimligt att testa flödet med mindre län först; för ett stort län bör vi sedan hämta/hantera data i delområden eller rastertiles i stället för att kräva att hela länet hanteras som en enda fil.
