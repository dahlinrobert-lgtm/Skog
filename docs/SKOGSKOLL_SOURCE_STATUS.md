# Skogskoll – automatisk status för datakällor

**Register kontrollerat:** 2026-11-14  
**Underlag:** data-platform/config/sources.yml

> Rapporten är maskinellt sammanställd från källregistret. Den är en operativ översikt, inte ett juridiskt godkännande. Saknat operations-block betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.

## Sammanfattning

- Registrerade datakällor: **47**
- Källor med operativ status: **11**
- Källor som ännu inte har operativ status: **36**
- Åtkomst: Auktoriserad åtkomst använd: 1, Delvis verifierad: 5, Ej verifierad: 1, Teknisk probe: 1, Verifierad: 3
- Snapshots: 30-dagars dagligt test: 1, Endast baslinje: 1, Inte startad: 2, Metadatabevakning behöver repareras: 1, Månadsarkiv planerat/pilot: 1, Pilot: 5
- Historik: Delvis historik: 5, Delvis historiskt arkiv: 1, Ej verifierad: 3, Endast metadataserie: 1, Ingen: 1
- Kommersiellt: Inväntar produktvillkor: 1, Verifierad med källhänvisning: 1, Villkorad: 4, Villkorad per handling/post: 1, Villkorad per produkt: 4
- Kundvisning: Inväntar dokumentgranskning: 1, Inväntar lagerkontroll: 2, Inväntar produktbedömning: 4, Inväntar produktbeskrivning: 1, Inväntar skriftligt/beställt scope: 1, Villkorad: 1, Villkorad av attribution/källomfattning: 1
- Uttryckligen godkända för kundvisning i registret: **0**

## Operativ status per datakälla

| Datakälla | Käll-ID | Åtkomst | Snapshots | Historik | Kommersiellt | Kundvisning | Senast verifierad |
|---|---|---|---|---|---|---|---|
| Skogsstyrelsen – avverkningsanmälningar | skogsstyrelsen.harvest_notifications | Verifierad | Pilot | Delvis historik | Villkorad | Inväntar lagerkontroll | 2026-11-15 |
| Skogsstyrelsen – Samråd point, line and area layers | skogsstyrelsen.samrad | Verifierad | Pilot | Delvis historik | Villkorad | Inväntar lagerkontroll | 2026-11-14 |
| Länsstyrelsen – offentliga diarier och ärendehandlingar | lansstyrelsen.public_diary | Delvis verifierad | Månadsarkiv planerat/pilot | Delvis historik | Villkorad per handling/post | Inväntar dokumentgranskning | 2026-11-14 |
| SLU Torvkarta 1.0 – klassad och kontinuerlig | slu.peat_map.v1 | Verifierad | Pilot | Endast metadataserie | Verifierad med källhänvisning | Villkorad av attribution/källomfattning | 2026-11-14 |
| Skogliga grunddata – Ståndortsindex SIS (gran och tall) | skogsstyrelsen.standortsindex_sis | Delvis verifierad | Metadatabevakning behöver repareras | Ej verifierad | Villkorad | Inväntar produktbeskrivning | 2026-11-14 |
| Trafikverket – öppna data | trafikverket.open_data | Ej verifierad | Inte startad | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Lantmäteriet – Fastighetsindelning Direkt (OAPIF) | lantmateriet.fastighetsindelning_direkt | Teknisk probe | Inte startad | Ingen | Inväntar produktvillkor | Inväntar skriftligt/beställt scope | 2026-11-14 |
| Nationella Viltolycksrådet – historiska och löpande viltolyckor | nvr.wildlife_collisions | Auktoriserad åtkomst använd | 30-dagars dagligt test | Delvis historiskt arkiv | Villkorad | Villkorad | 2026-11-15 |
| Trafikverket – Miljöwebb Landskap | trafikverket.miljoweb_landskap | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB Viltolyckor | trafikverket.nvdb.wildlife_collision_frequency | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB vägnät och Lastkajen | trafikverket.nvdb.road_network_lastkajen | Delvis verifierad | Endast baslinje | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |

## Nästa åtgärd

- **Skogsstyrelsen – avverkningsanmälningar:** Verifiera komplett paginering och minst två kompletta jämförbara körningar; skilj nya anmälningar från äldre baslinje och bortfall.
- **Skogsstyrelsen – Samråd point, line and area layers:** Verifiera fullständighet separat för punkt-, linje- och polygonlagren och fortsätt bevara dagliga snapshots.
- **Länsstyrelsen – offentliga diarier och ärendehandlingar:** Verifiera månatliga arkivkörningar och dokumentera täckning per län; granska dokument/bilagor separat från metadata.
- **SLU Torvkarta 1.0 – klassad och kontinuerlig:** Fortsätt versions-/metadatasnapshots; spara SLU:s skriftliga besked och kontrollera den nya produktens licens vid publicering.
- **Skogliga grunddata – Ståndortsindex SIS (gran och tall):** Felsök misslyckade metadataövervakningskörningar 13–14 november och verifiera rasterhämtning samt produktvillkor.
- **Trafikverket – öppna data:** Använd de tre separata produktposterna nedan för faktisk åtkomst, snapshotstatus, historik och rättighetsbedömning; uppdatera denna post endast om Trafikverket inför en ny gemensam produkt eller tjänst.
- **Lantmäteriet – Fastighetsindelning Direkt (OAPIF):** Hämta och granska beslut/villkor för ärendena LM2026/171963 och LM2026/171968; verifiera kundvisning, lagring, historik och kommersiell användning.
- **Nationella Viltolycksrådet – historiska och löpande viltolyckor:** Följ upp 30-dagarstestet och etablera en kontrollerad, skrivskyddad publiceringsendpoint för NVR-händelser med manifest, fullständighetsstatus och källhänvisning. Rådata får inte publiceras direkt från OneDrive eller GitHub Pages utan separat publiceringskontroll.
- **Trafikverket – Miljöwebb Landskap:** Verifiera vilka lager som ingår i Gräsmyr-piloten, kontrollera antal/geografisk täckning och spara senaste två kompletta snapshots med manifest och kontrollsummor.
- **Trafikverket – NVDB Viltolyckor:** Verifiera produktens exakta definition, referensperiod, geografiska täckning och uppdateringsdatum; spara jämförbara snapshots och dokumentera om värdena är frekvenser, antal eller klassningar.
- **Trafikverket – NVDB vägnät och Lastkajen:** Dokumentera vilken NVDB-produktversion som finns lokalt, kontrollera Lastkajens beställnings- och licensvillkor och bygg ett versionsstyrt uppdateringsflöde innan vägnätsförändringar används i kundhistorik.

## Tolkning och begränsningar

- En tekniskt fungerande endpoint/probe visar inte att hela datamängden har hämtats.
- En snapshotserie är inte automatiskt en komplett eller jämförbar historisk tidsserie.
- partial, failed eller annan ofullständig insamling får inte användas för att dra slutsatser om att objekt har försvunnit.
- Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution ska bedömas separat.
- Statusen approved för kundvisning måste ha konkret produkt-/lagerunderlag och dokumenterad evidens.
- Den här rapporten läser endast registret; den startar inga insamlingsflöden och ändrar inte källstatus.

## Källor och förvaltning

- Huvuddokumentation: [SKOGSKOLL_DATA_OVERVIEW.md](SKOGSKOLL_DATA_OVERVIEW.md)
- Rättighetsbedömning: [open-data-and-commercial-use.md](open-data-and-commercial-use.md)
- Källregister: [sources.yml](../data-platform/config/sources.yml)
- Validering: [validate_source_registry.py](../data-platform/scripts/validate_source_registry.py)
- Rapportgenerator: [build_source_status_report.py](../data-platform/scripts/build_source_status_report.py)

Generera lokalt med:

    python -m pip install PyYAML==6.0.2
    python data-platform/scripts/build_source_status_report.py --write

Kontrollera att rapporten är aktuell med:

    python data-platform/scripts/build_source_status_report.py --check
