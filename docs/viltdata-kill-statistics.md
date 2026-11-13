# Viltdata – avskjutningssnapshots

Första statistikpiloten fokuserar på publik aggregerad avskjutning (`StatisticsReportType=kill`). Den hämtar inte privata jaktlagsuppgifter.

## Körning

Kräver Python 3.10+ och inga externa paket.

```powershell
# Snabbt API-test: två arter, nationellt + första länet
python scripts/viltdata_kill_statistics_snapshot.py --max-species 2 --max-counties 1

# Full pilot: alla arter i små batchar, nationellt + samtliga län
python scripts/viltdata_kill_statistics_snapshot.py
```

Skriptet hämtar `GetStatisticsModel`, väljer alla arter med `enableForKill=true`, hämtar länslistan och begär hela tillgängliga perioden. Artnamnen trimmas från inledande/avslutande blanktecken eftersom modellsvaret innehåller radbrytningar i vissa namn.

## Batchning

API-anropen görs som GET-anrop. För att hålla URL:erna korta skickas som standard två arter per statistikfråga. Med 49 arter blir det 25 batchar per geografiskt scope. `--species-batch-size` kan ändra batchstorleken efter verifiering. `--max-species` och `--max-counties` är avsedda för pilotkörningar och gör att körningen markeras `partial`.

## Lagring och validering

Varje körning får en egen UTC-tidsstämplad katalog under `data/viltdata/kill-statistics/`. Varje råsvar sparas separat med URL, hämtningstid, HTTP-status, Content-Type, SHA-256, filstorlek och valideringsräkningar.

- `null` bevaras och konverteras aldrig till noll.
- Svar måste vara JSON med icke-tomma `labels` och `dataSets`.
- Varje dataseries längd måste motsvara antalet etiketter.
- Ofullständiga körningar markeras `partial` och får inte användas som komplett jämförelsebas.
- Befintliga körningar skrivs aldrig över.

## Test

```powershell
python -m unittest discover -s tests -p "test_viltdata_kill_statistics_snapshot.py" -v
```

Ingen schemaläggning aktiveras innan full pilot och snapshot-jämförelse har verifierats.
