# Skogskoll – automatisk status för datakällor

**Register kontrollerat:** 2026-11-14  
**Rapportunderlag sammanställt:** 2026-11-15  
**Underlag:** `data-platform/config/sources.yml`

> Detta är en ögonblicksbild av källregistrets operativa status. Den är inte ett juridiskt godkännande. Saknat operations-block betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning. Den maskinellt genererade versionen skapas även som GitHub Actions-artifact när källregistret valideras.

## Sammanfattning

- Registrerade datakällor: **47**
- Källor med operativ status: **11**
- Källor som ännu inte har operativ status: **36**
- Åtkomst: verifierad 3, delvis verifierad 5, teknisk probe 1, auktoriserad åtkomst använd 1, ej verifierad 1.
- Snapshots: pilot 5, metadatabevakning behöver repareras 1, månadsarkiv planerat/pilot 1, 30-dagars dagligt test 1, endast baslinje 1, inte startad 2.
- Historik: delvis historik 5, endast metadataserie 1, delvis historiskt arkiv 1, ej verifierad 3, ingen 1.
- Kommersiell användning: villkorad 3, villkorad per handling/post 1, verifierad med källhänvisning 1, villkorad per produkt 4, inväntar omfattningsbesked 1, inväntar produktvillkor 1.
- Uttryckligen godkända för kundvisning i registret: **0**.

## Operativ status per datakälla

| Datakälla | Käll-ID | Åtkomst | Snapshots | Historik | Kommersiellt | Kundvisning | Senast verifierad |
|---|---|---|---|---|---|---|---|
| Skogsstyrelsen – avverkningsanmälningar | `skogsstyrelsen.harvest_notifications` | Verifierad | Pilot | Delvis historik | Villkorad | Inväntar lagerkontroll | 2026-11-14 |
| Skogsstyrelsen – Samråd point, line and area layers | `skogsstyrelsen.samrad` | Verifierad | Pilot | Delvis historik | Villkorad | Inväntar lagerkontroll | 2026-11-14 |
| Länsstyrelsen – offentliga diarier och ärendehandlingar | `lansstyrelsen.public_diary` | Delvis verifierad | Månadsarkiv planerat/pilot | Delvis historik | Villkorad per handling/post | Inväntar dokumentgranskning | 2026-11-14 |
| SLU Torvkarta 1.0 – klassad och kontinuerlig | `slu.peat_map.v1` | Verifierad | Pilot | Endast metadataserie | Verifierad med källhänvisning | Villkorad av attribution/källomfattning | 2026-11-14 |
| Skogliga grunddata – Ståndortsindex SIS (gran och tall) | `skogsstyrelsen.standortsindex_sis` | Delvis verifierad | Metadatabevakning behöver repareras | Ej verifierad | Villkorad | Inväntar produktbeskrivning | 2026-11-14 |
| Trafikverket – öppna data (katalogpost) | `trafikverket.open_data` | Ej verifierad | Inte startad | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Lantmäteriet – Fastighetsindelning Direkt (OAPIF) | `lantmateriet.fastighetsindelning_direkt` | Teknisk probe | Inte startad | Ingen | Inväntar produktvillkor | Inväntar skriftligt/beställt scope | 2026-11-14 |
| Nationella Viltolycksrådet – historiska och löpande viltolyckor | `nvr.wildlife_collisions` | Auktoriserad åtkomst använd | 30-dagars dagligt test | Delvis historiskt arkiv | Inväntar omfattningsbesked | Inväntar omfattningsbesked | 2026-11-14 |
| Trafikverket – Miljöwebb Landskap | `trafikverket.miljoweb_landskap` | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB Viltolyckor | `trafikverket.nvdb.wildlife_collision_frequency` | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB vägnät och Lastkajen | `trafikverket.nvdb.road_network_lastkajen` | Delvis verifierad | Endast baslinje | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |

## Prioriterade nästa åtgärder

1. **Avverkningsanmälningar:** verifiera komplett paginering och minst två kompletta jämförbara körningar; skilj nya anmälningar från äldre baslinje och bortfall.
2. **Samråd:** verifiera fullständighet separat för punkt-, linje- och polygonlagren och fortsätt bevara dagliga snapshots.
3. **Länsstyrelsens diarier:** verifiera månatliga arkivkörningar och täckning per län; granska dokument/bilagor separat från metadata.
4. **Torvkartan:** fortsätt versions-/metadatasnapshots; spara SLU:s skriftliga besked och kontrollera den nya produktens licens vid publicering.
5. **SIS:** felsök misslyckade metadataövervakningskörningar 13–14 november och verifiera rasterhämtning samt produktvillkor.
6. **Trafikverkets katalogpost:** använd de tre separata produktposterna för faktisk åtkomst, snapshotstatus, historik och rättighetsbedömning.
7. **Fastighetsindelning Direkt:** hämta och granska beslut/villkor för LM2026/171963 och LM2026/171968; verifiera kundvisning, lagring, historik och kommersiell användning.
8. **NVR:** följ upp 30-dagarstestet, verifiera automatiska körningar/exportjämförelser/dagsarkiv och dokumentera skriftligt godkännande, ändamål och återkommande hämtning.
9. **Miljöwebb Landskap:** verifiera vilka lager som ingår i Gräsmyr-piloten, kontrollera antal/täckning och spara två kompletta snapshots med manifest och kontrollsummor.
10. **NVDB Viltolyckor:** verifiera definition, referensperiod, täckning och uppdateringsdatum; dokumentera om värden är frekvenser, antal eller klassningar.
11. **NVDB vägnät/Lastkajen:** dokumentera lokal produktversion, kontrollera beställnings-/licensvillkor och bygg ett versionsstyrt uppdateringsflöde.

## Viktiga tolkningsregler

- Teknisk åtkomst eller en begränsad probe är inte bevis på komplett data.
- En snapshot är en observation av källan vid en tidpunkt; den betyder inte att källan uppdaterats vid samma tidpunkt.
- Ofullständiga uttag får inte användas för att markera objekt som försvunna eller inaktiva.
- Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution ska bedömas var för sig.
- Trafikverkets NVDB Viltolyckor är aggregerad frekvens per vägsegment, inte individuella olyckor.
- NVR:s individuella olyckshändelser ska hållas åtskilda från Trafikverkets aggregerade NVDB-data.

## Källor och förvaltning

- Huvuddokumentation: [SKOGSKOLL_DATA_OVERVIEW.md](SKOGSKOLL_DATA_OVERVIEW.md)
- Överlämning för ny chatt: [AI_HANDOVER.md](AI_HANDOVER.md)
- Rättighetsbedömning: [open-data-and-commercial-use.md](open-data-and-commercial-use.md)
- Källregister: [sources.yml](../data-platform/config/sources.yml)
- Rapportgenerator: [build_source_status_report.py](../data-platform/scripts/build_source_status_report.py)

Generera rapporten lokalt:

```bash
python -m pip install PyYAML==6.0.2
python data-platform/scripts/build_source_status_report.py --write
python data-platform/scripts/build_source_status_report.py --check
```
