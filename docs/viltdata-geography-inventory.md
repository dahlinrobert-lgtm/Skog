# Viltdata – nationell geografiinventering

Read-only inventering av offentliga metadata för län → ÄFO → ÄFO-delområde → jakt-/skötselområde. Kopplad till issue #363.

## Körning

Kräver Python 3.10+ och inga externa paket.

```powershell
python scripts/viltdata_geography_inventory.py --max-counties 1
python scripts/viltdata_geography_inventory.py
```

Första kommandot är ett begränsat funktionstest, inte en nationell inventering. Andra kommandot hämtar samtliga län. Ingen schemalagd hämtning aktiveras av inventeringsskriptet.

## Utdata

Varje körning skapar en egen UTC-tidsstämplad katalog under `data/viltdata/geography-inventory/`. Där sparas oförändrade JSON-svar under `raw/<nivå>/<föräldra-ID>.json` samt `manifest.json` med URL, hämtningstid, SHA-256, antal poster, fel och föräldra–barn-relationer.

`complete=true` kräver full nationell körning utan registrerade fel. Ett HTTP-fel räknas aldrig som en tom lista. Processen ger exitkod 1 om fel registreras. Befintliga körningar skrivs inte över.

## Jämförelse mellan snapshots

När minst två inventeringar finns kan de jämföras:

```powershell
python scripts/viltdata_geography_snapshot_diff.py data/viltdata/geography-inventory/<baslinje> data/viltdata/geography-inventory/<ny-körning>
```

Rapporten skapas i `data/viltdata/geography-comparisons/`. Den identifierar tillkomna, ändrade och (när båda körningarna är kompletta) saknade ID:n samt ändrade föräldra–barn-relationer.

- Identitet baseras på nivå + API-ID, aldrig på titel.
- Råa JSON-svar ändras aldrig.
- Om någon körning är ofullständig undertrycks borttagningar och redovisas i stället som obekräftat saknade poster/relationer.
- Jaktområdets `parentId` är ett eget metadatafält. Delområdestillhörigheten kommer separat från inventeringens förfrågeparameter och manifestrelation.

Enhetstester:

```powershell
python -m unittest discover -s tests -p "test_viltdata_geography_snapshot_diff.py" -v
```

## Kvalitetskontroll av jaktområdesnamn

Efter en inventering kan en separat kontroll köras:

```powershell
python scripts/viltdata_area_duplicate_qa.py data/viltdata/geography-inventory/<UTC-katalog>
```

Rapporten sparas som `qa/duplicate-area-titles.json` i samma körningskatalog. Den flaggar grupper där flera olika jaktområdes-ID:n har samma normaliserade titel inom samma delområde (`part_id`) och samma `parentId`. Normaliseringen använder Unicode NFKC, komprimerar blanksteg och ignorerar skiftläge.

Kontrollen ändrar inte rådata, slår inte ihop ID:n och flaggar inte samma titel under olika föräldrar eller delområden. Träffarna är kandidater för manuell bedömning.

## Viktiga begränsningar

- Detta är metadata, inte historisk statistik eller observationer.
- En enda inventering är en baslinje, inte en tidsserie.
- API-belastning ska följas upp innan schemaläggning.
