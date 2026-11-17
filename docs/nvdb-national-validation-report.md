# NVDB – nationell valideringsrapport och granskningsurval

**Status:** första fristående rapportbyggare i utvecklingsbranch; inte produktionssatt.  
**Skript:** `scripts/build_nvdb_validation_report.py`  
**Indata:** CSV-utdata från `scripts/match_points_to_nvdb_roads.py`.  
**Utdata:** JSON-sammanfattning och separat CSV-kö för manuell granskning.

## Syfte och avgränsning

Rapportbyggaren gör matchningsresultatet granskningsbart i stor skala utan att skapa en nationell GeoJSON med alla geometrier. Den ändrar inte matchnings-CSV, originaldata, temporal evidens, kandidatlistor eller `geographic_match_used`. Inget vägobjekt bekräftas automatiskt.

## Funktion

- Räknar sökstatusar, källäsningsfel, avståndsfördelning (min, median, p90, p95, max) och kandidatantal.
- Flaggmarkerar statusar som inte är `completed_with_candidates`, långa avstånd och nära alternativa kandidater.
- Tar med samtliga flaggade poster i granskningskön.
- Tar dessutom ett deterministiskt stickprov av icke-flaggade poster per förekommande källfil. Samma indata och seed ger samma urval.
- Skriver JSON-rapport och gransknings-CSV separat. Granskningsstatus börjar som `pending`.

Källfilernas antal i rapporten beskriver kandidaters proveniens, inte geografisk täckning eller länsvis fullständighet.

## Exempel

```powershell
python scripts/build_nvdb_validation_report.py `
  --input "$Base\viltolycka_NVR\working\lulea-police-nvr\nvdb-nearest-road-review-zip-pilot.csv" `
  --report "$Base\viltolycka_NVR\working\lulea-police-nvr\nvdb-validation-report.json" `
  --review-queue "$Base\viltolycka_NVR\working\lulea-police-nvr\nvdb-review-queue.csv" `
  --sample-per-source 20
```

Om en stabil händelse-ID-kolumn finns kan den anges med `--event-id-field`. Trösklarna `--far-m`, `--very-far-m` och `--ambiguity-gap-m` är granskningsurval, inte automatiska kvalitetsgodkännanden.

## Nationell uppskalning

Innan nationell körning ska:
1. samma NVDB-produktversion och kompatibel källtäckning verifieras för samtliga län;
2. benchmark göras med representativa händelsevolymer och alla avsedda länsarkiv;
3. körtid, minne, antal lästa features och källfel mätas;
4. manuellt bedömda positiva, negativa och tvetydiga fall finnas i flera geografiska miljöer;
5. granskningsbeslut kunna kopplas till stabil händelseidentitet och NVDB-element-ID, inte enbart radnummer;
6. rapportens urvals- och avståndströsklar kalibreras mot det manuellt bedömda referensmaterialet.

Nuvarande rapport räknar avstånd och kandidater från matchnings-CSV. Den mäter inte precision/recall eller faktisk vägträffsäkerhet eftersom det kräver ett oberoende manuellt bedömt facit. Den härleder inte heller geografisk täckning från källfiler.

## Säkerhetsregler

- `partial_source_read` och andra icke kompletta statusar ska granskas; de får inte tolkas som att väg saknas.
- `completed_no_candidate_in_search_window` betyder endast att ingen kandidat hittades inom sökradien i de lästa källorna.
- Nära parallella vägar och ramper kan ge tvetydighet även vid mycket kort avstånd.
- Manuell granskning är separat från temporal matchning.
- Inga resultat är godkända för kundvisning genom denna rapportbyggare.
