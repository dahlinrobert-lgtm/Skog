# Viltdata – avskjutningssnapshots

Första statistikpiloten fokuserar på publik aggregerad avskjutning (`StatisticsReportType=kill`). Den är separat från geografiinventeringen och hämtar inte privata jaktlagsuppgifter.

## Körning

Kräver Python 3.10+ och inga externa paket.

```powershell
# Begränsat test: nationellt + första länet
python scripts/viltdata_kill_statistics_snapshot.py --max-counties 1

# Full pilot: nationellt + samtliga län
python scripts/viltdata_kill_statistics_snapshot.py
```

Skriptet hämtar `GetStatisticsModel`, väljer alla arter med `enableForKill=true`, hämtar länslistan och begär en nationell serie samt en serie per län. Hela tillgängliga perioden hämtas från modellens startår till dess aktiva år. Modellen och länslistan sparas också som rå JSON.

## Lagring och validering

Varje körning får en egen UTC-tidsstämplad katalog under `data/viltdata/kill-statistics/`. Råsvaret sparas oförändrat per scope. Manifestet innehåller URL/parametrar, hämtningstid, HTTP-status, Content-Type, SHA-256, filstorlek, antal årsetiketter och antal dataserier.

- `null` behålls som null; det konverteras aldrig till noll.
- Ett svar måste vara JSON och innehålla icke-tomma `labels` och `dataSets`.
- Varje dataseries längd måste motsvara antalet etiketter.
- En ofullständig körning markeras `partial` och får inte användas som komplett jämförelsebas.
- Befintliga körningar skrivs aldrig över.

## Test

```powershell
python -m unittest discover -s tests -p "test_viltdata_kill_statistics_snapshot.py" -v
```

## Avsiktlig begränsning i första piloten

Detta är rapporterad avskjutning, inte en inventering eller skattning av viltbestånd. Första piloten omfattar nationell nivå och länsnivå. ÄFO, delområden, jaktområden och kretsar samt andra statistiktyper hanteras i senare steg efter att anropsmönster och datavolymer verifierats.

Ingen schemaläggning aktiveras av denna implementation. Först ska en full pilotkörning verifieras och jämförelselogiken byggas/testas.
