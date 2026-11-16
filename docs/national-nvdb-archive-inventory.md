# NVDB – inventering av länsvisa GeoPackage-arkiv

**Senast uppdaterad:** 2026-11-16  
**Syfte:** Kontrollera att de 21 länsvisa NVDB-arkiven innehåller ett kompatibelt vägnummerlager innan nationell närmaste-vägmatchning körs.

## Verifierad OneDrive-baslinje

OneDrive-mappen `Skogskoll/Lastkajen/Länsfiler NVDB data` inventerades via Microsoft Graph 2026-11-16:

- 21 GeoPackage-ZIP-filer – ett arkiv för vart och ett av Sveriges län.
- Sammanlagd rapporterad storlek: 10 677 114 317 byte (cirka 10,68 GB).
- Filnamn, existens och storlek verifierades i molnmappen.
- Innehåll, lagerstruktur, CRS, attributschema, feature-antal och geografisk täckning har ännu inte verifierats.

Det finns också en separat uppladdad fil `Lastkajen/uploaded gpkg file/Norrbottens_län.gpkg` (1 203 462 144 byte). Den ska inte behandlas som auktoritativ ersättning för ZIP-originalet innan versions-/innehållsjämförelse har gjorts.

## Read-only-inspektör

Skript: `scripts/inventory_nvdb_county_archives.py`

Skriptet:
- letar efter `*_GeoPackage.zip` i angiven katalog,
- läser ZIP-medlemsmetadata utan att extrahera filer,
- använder GDAL `/vsizip/` via Pyogrio för att lista GeoPackage-lager,
- läser lagerdefinitioner, feature-antal (om källan rapporterar det), geometrityp, CRS och fält,
- kontrollerar att `NVDB_DK_O_111_Vagnummer` finns och innehåller `ELEMENT_ID`, `Europavag`, `Huvudnummer` och `Lankroll`,
- skriver en separat JSON-rapport.

Skriptet skannar inte samtliga feature-geometrier och validerar inte fullständig geografisk täckning. Det ändrar eller extraherar inte originalarkiven. Om en ZIP eller ett lager inte kan läsas markeras rapporten som `partial`; saknat lager eller fält redovisas separat. Ett misslyckat uttag får aldrig tolkas som att vägar saknas.

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

1. Kontrollera att samtliga 21 län har vägnummerlagret och samma obligatoriska fält.
2. Jämför CRS, geometrityper, feature-antal och eventuella skillnader i fälttyper.
3. Kontrollera gränsöverlapp mellan län och om samma `ELEMENT_ID` återkommer i flera arkiv.
4. Mät prestanda på ett representativt urval innan nationell körning.
5. Välj därefter mellan direkt fråga mot flera ZIP-arkiv och ett separat nationellt spatialt index.
6. Kör nationell kandidatmatchning som review-only; sätt inte automatiska gråzonsgränser innan fördelningen av avstånd och vägnummeravvikelser har analyserats.

## Rättigheter och dataskydd

Teknisk åtkomst och lokal filinventering är inte i sig ett besked om kommersiell lagring, bearbetning, kundvisning eller vidare distribution. Kontrollera villkoren för exakt Lastkajen-produkt innan materialet används i en extern tjänst.
