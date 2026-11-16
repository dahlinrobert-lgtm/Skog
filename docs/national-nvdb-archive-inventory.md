# NVDB – inventering av länsvisa GeoPackage-arkiv

**Senast uppdaterad:** 2026-11-16  
**Syfte:** Kontrollera att de 21 länsvisa NVDB-arkiven innehåller ett kompatibelt vägnummerlager innan nationell närmaste-vägmatchning körs.

## Verifierad OneDrive-baslinje

OneDrive-mappen `Skogskoll/Lastkajen/Länsfiler NVDB data` inventerades via Microsoft Graph 2026-11-16:

- 21 GeoPackage-ZIP-filer – ett arkiv för vart och ett av Sveriges län.
- Sammanlagd rapporterad storlek: 10 677 114 317 byte (cirka 10,68 GB).
- Filnamn, existens och storlek verifierades i molnmappen.
- Innehållet har nu metadata-inspekterats i två län (Gotland och Västerbotten), men ännu inte i samtliga 21 län.

Det finns också en separat uppladdad fil `Lastkajen/uploaded gpkg file/Norrbottens_län.gpkg` (1 203 462 144 byte). Den ska inte behandlas som auktoritativ ersättning för ZIP-originalet innan versions-/innehållsjämförelse har gjorts.

## Read-only-inspektör

Skript: `scripts/inventory_nvdb_county_archives.py`

Skriptet:
- letar efter `*_GeoPackage.zip` i angiven katalog,
- läser ZIP-medlemsmetadata utan att extrahera filer,
- frågar GeoPackages `gpkg_contents` via GDAL/Pyogrio SQLite-dialekt för att kontrollera mållagrets förekomst,
- öppnar endast `NVDB_DK_O_111_Vagnummer` direkt med `pyogrio.read_info()`,
- rapporterar feature-antal, geometrityp, CRS och fält,
- kontrollerar obligatoriska fält `ELEMENT_ID`, `Europavag`, `Huvudnummer` och `Lankroll`,
- kontrollerar att lagrets CRS är EPSG:3006,
- skriver en separat JSON-rapport.

Skriptet använder avsiktligt inte `pyogrio.list_layers()`: den anropningen misslyckades för samtliga 21 arkiv med `Geometry type is not supported: -2147483648`, trots att det aktuella vägnummerlagret gick att öppna direkt i de två testade arkiven. Andra lager i GeoPackage-filerna behöver inte öppnas för att verifiera mållagret.

I Gotland och Västerbotten kunde både `gpkg_contents` och direktinspektionen av vägnummerlagret läsas. Båda hade EPSG:3006 och samtliga obligatoriska fält. Gotland rapporterade 6 203 objekt och Västerbotten 26 902. Båda rapporterade `geometry_type: Unknown`; detta registreras som metadata och är inte ensamt ett kompatibilitetsfel. Faktisk geometriinnehållsvalidering är fortfarande inte genomförd.

Skriptet skannar inte samtliga feature-geometrier och validerar inte fullständig geografisk täckning. Det ändrar eller extraherar inte originalarkiven. Om katalogfrågan eller direktläsningen misslyckas markeras arkivet som `partial`; saknat lager eller schema-/CRS-avvikelse redovisas separat. Ett misslyckat uttag får aldrig tolkas som att vägar saknas.

## Körning i Windows PowerShell

Kör från roten av Skog-repot efter att branchen har hämtats:

```powershell
python scripts/inventory_nvdb_county_archives.py `
  --directory "C:\Users\dahli\OneDrive\Skogskoll\Lastkajen\Länsfiler NVDB data" `
  --expected-archives 21 `
  --output "C:\Users\dahli\OneDrive\Skogskoll\Lastkajen\nvdb-county-archive-inventory-20261116.json"
```

Förväntat utfall vid full metadataåtkomst är `status: completed`, 21 arkiv och `compatible: 21`. Det är ett förväntat kriterium, inte ett redan uppnått resultat. En `partial`-rapport eller avvikande schema ska granskas innan nästa steg.

## Nästa steg efter inventeringen

1. Kör den uppdaterade inspektören mot alla 21 län.
2. Granska status, CRS, geometriuppgift, feature-antal och fält per län.
3. Undersök varför GeoPackage-lagren rapporterar `Unknown` och validera faktisk geometri på ett representativt urval.
4. Kontrollera gränsöverlapp mellan län och om samma `ELEMENT_ID` återkommer i flera arkiv.
5. Mät prestanda på ett representativt urval innan nationell körning.
6. Välj därefter mellan direkt fråga mot flera ZIP-arkiv och ett separat nationellt spatialt index.
7. Kör nationell kandidatmatchning som review-only; sätt inte automatiska gråzonsgränser innan fördelningen av avstånd och vägnummeravvikelser har analyserats.

## Rättigheter och dataskydd

Teknisk åtkomst och lokal filinventering är inte i sig ett besked om kommersiell lagring, bearbetning, kundvisning eller vidare distribution. Kontrollera villkoren för exakt Lastkajen-produkt innan materialet används i en extern tjänst.
