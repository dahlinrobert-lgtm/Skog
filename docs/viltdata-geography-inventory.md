# Viltdata – nationell geografiinventering

Read-only inventering av offentliga metadata för län → ÄFO → ÄFO-delområde → jakt-/skötselområde. Kopplad till issue #363.

## Körning

Kräver Python 3.10+ och inga externa paket.

```powershell
python scripts/viltdata_geography_inventory.py --max-counties 1
python scripts/viltdata_geography_inventory.py
```

Första kommandot är ett begränsat funktionstest, inte en nationell inventering. Andra kommandot hämtar samtliga län. Körningen kan ta tid beroende på antal underområden och API-svar. Ingen schemalagd hämtning aktiveras av denna PR.

## Utdata

Varje körning skapar en egen UTC-tidsstämplad katalog under `data/viltdata/geography-inventory/`. Där sparas oförändrade JSON-svar under `raw/<nivå>/<föräldra-ID>.json` samt `manifest.json` med URL, hämtningstid, SHA-256, antal poster, fel och föräldra–barn-relationer.

`complete=true` kräver full nationell körning utan registrerade fel. Ett HTTP-fel räknas aldrig som en tom lista. Processen ger exitkod 1 om fel registreras. Befintliga körningar skrivs inte över.

## Kvalitetskontroll av jaktområdesnamn

Efter en inventering kan en separat kontroll köras mot den tidsstämplade katalogen:

```powershell
python scripts/viltdata_area_duplicate_qa.py data/viltdata/geography-inventory/<UTC-katalog>
```

Rapporten sparas som `qa/duplicate-area-titles.json` i samma körningskatalog. Den flaggar grupper där flera olika jaktområdes-ID:n har samma normaliserade titel inom samma delområde (`part_id`) och samma `parentId`. Normaliseringen använder Unicode NFKC, komprimerar blanksteg och ignorerar skiftläge.

Kontrollen är avsiktligt konservativ:
- Alla råa API-svar lämnas oförändrade.
- Inga ID:n slås ihop eller tas bort.
- Samma titel under olika föräldrar eller olika delområden flaggas inte som samma kandidat.
- Träffarna är kandidater för manuell bedömning; API-fälten `id`, `parentId` och `title` avgör inte om objekten är legitima separata jaktområden eller källdubbletter.

Enhetstester körs med:

```powershell
python -m unittest discover -s tests -p "test_viltdata_area_duplicate_qa.py" -v
```

## Viktiga begränsningar

- Detta är endast metadata, inte historisk statistik eller observationer.
- Resultatens områdesidentiteter måste kontrolleras över tid. Samma ID kan återkomma under flera föräldrar; relationerna bevaras.
- `parentId=null` från jaktområdes-API:t är inte bevis för att geografisk relation saknas; föräldrarelationen kommer från frågeparametern.
- API-belastning ska följas upp innan schemaläggning eller fullskalig insamling.
