# Skogskoll – automatisk status för datakällor

**Register kontrollerat:** 2026-11-23  
**Underlag:** data-platform/config/sources.yml

> Rapporten är maskinellt sammanställd från källregistret. Den är en operativ översikt, inte ett juridiskt godkännande. Saknat operations-block betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.

## Sammanfattning

- Registrerade datakällor: **51**
- Källor med operativ status: **14**
- Källor som ännu inte har operativ status: **37**
- Åtkomst: Auktoriserad åtkomst använd: 1, Delvis verifierad: 5, Ej verifierad: 1, Teknisk probe: 1, Verifierad: 6
- Snapshots: 30-dagars dagligt test: 1, Endast baslinje: 1, Inte startad: 2, Metadatabevakning behöver repareras: 1, Pilot: 8
- Historik: Delvis historik: 5, Delvis historiskt arkiv: 1, Ej verifierad: 4, Endast metadataserie: 1, Ingen: 3
- Kommersiellt: Inväntar produktvillkor: 1, Okänd: 1, Verifierad med källhänvisning: 2, Villkorad: 4, Villkorad av attribution/källomfattning: 1, Villkorad per handling/post: 1, Villkorad per produkt: 4
- Kundvisning: Ej bedömd: 1, Inväntar dokumentgranskning: 1, Inväntar lagerkontroll: 2, Inväntar produktbedömning: 4, Inväntar produktbeskrivning: 1, Inväntar skriftligt/beställt scope: 1, Villkorad: 1, Villkorad av attribution/källomfattning: 3
- Uttryckligen godkända för kundvisning i registret: **0**

## Operativ status per datakälla

| Datakälla | Käll-ID | Åtkomst | Snapshots | Historik | Kommersiellt | Kundvisning | Senast verifierad |
|---|---|---|---|---|---|---|---|
| Skogsstyrelsen – avverkningsanmälningar | skogsstyrelsen.harvest_notifications | Verifierad | Pilot | Delvis historik | Villkorad | Inväntar lagerkontroll | 2026-11-15 |
| Skogsstyrelsen – Samråd point, line and area layers | skogsstyrelsen.samrad | Verifierad | Pilot | Delvis historik | Villkorad | Inväntar lagerkontroll | 2026-11-14 |
| Länsstyrelsen – offentliga diarier och ärendehandlingar | lansstyrelsen.public_diary | Delvis verifierad | Pilot | Delvis historik | Villkorad per handling/post | Inväntar dokumentgranskning | 2026-11-16 |
| SLU Torvkarta 1.0 – klassad och kontinuerlig | slu.peat_map.v1 | Verifierad | Pilot | Endast metadataserie | Verifierad med källhänvisning | Villkorad av attribution/källomfattning | 2026-11-14 |
| Skogliga grunddata – Ståndortsindex SIS (gran och tall) | skogsstyrelsen.standortsindex_sis | Delvis verifierad | Metadatabevakning behöver repareras | Ej verifierad | Villkorad | Inväntar produktbeskrivning | 2026-11-14 |
| Trafikverket – öppna data | trafikverket.open_data | Ej verifierad | Inte startad | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Lantmäteriet – Fastighetsindelning Direkt (OAPIF) | lantmateriet.fastighetsindelning_direkt | Teknisk probe | Inte startad | Ingen | Inväntar produktvillkor | Inväntar skriftligt/beställt scope | 2026-11-14 |
| Nationella Viltolycksrådet – historiska och löpande viltolyckor | nvr.wildlife_collisions | Auktoriserad åtkomst använd | 30-dagars dagligt test | Delvis historiskt arkiv | Villkorad | Villkorad | 2026-11-15 |
| Länsstyrelsernas Älgdata – avskjutning per älgförvaltningsområde | lansstyrelsen.elk_harvest_statistics | Verifierad | Nationell 129/129 snapshot verifierad | Två nationella snapshots: 2026-11-21 och 2026-11-23; dashboarddifferens granskad, rå ÄJO-differens återstår | Verifierad med källhänvisning | Villkorad av attribution/källomfattning | 2026-11-23 |
| Länsstyrelserna – nationella älgförvaltningsområden (JaktAdm) | lansstyrelsen.elk_afo_boundaries | Verifierad | Inte startad | Ingen | Villkorad av attribution/källomfattning | Villkorad av attribution/källomfattning | 2026-11-16 |
| Trafikverket – Miljöwebb Landskap | trafikverket.miljoweb_landskap | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB Viltolyckor | trafikverket.nvdb.wildlife_collision_frequency | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB vägnät och Lastkajen | trafikverket.nvdb.road_network_lastkajen | Delvis verifierad | Endast baslinje | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Viltdata.se – nationell avskjutningsstatistik | viltdata.kill_statistics | Verifierad | Pilot | Ej verifierad | Okänd | Ej bedömd | 2026-11-18 |

## Nästa åtgärd

- **Skogsstyrelsen – avverkningsanmälningar:** Verifiera komplett paginering och minst två kompletta jämförbara körningar; skilj nya anmälningar från äldre baslinje och bortfall.
- **Skogsstyrelsen – Samråd point, line and area layers:** Verifiera fullständighet separat för punkt-, linje- och polygonlagren och fortsätt bevara dagliga snapshots.
- **Länsstyrelsen – offentliga diarier och ärendehandlingar:** Upprepa en avgränsad, manuell månadskörning för att verifiera reproducerbarhet; dokumentera läns-/frasomfattning och utred Länsstyrelsens tekniska begränsningar innan återkommande drift. Granska dokument/bilagor separat från metadata.
- **SLU Torvkarta 1.0 – klassad och kontinuerlig:** Fortsätt versions-/metadatasnapshots; spara SLU:s skriftliga besked och kontrollera den nya produktens licens vid publicering.
- **Skogliga grunddata – Ståndortsindex SIS (gran och tall):** Felsök misslyckade metadataövervakningskörningar 13–14 november och verifiera rasterhämtning samt produktvillkor.
- **Trafikverket – öppna data:** Använd de tre separata produktposterna nedan för faktisk åtkomst, snapshotstatus, historik och rättighetsbedömning; uppdatera denna post endast om Trafikverket inför en ny gemensam produkt eller tjänst.
- **Lantmäteriet – Fastighetsindelning Direkt (OAPIF):** Hämta och granska beslut/villkor för ärendena LM2026/171963 och LM2026/171968; verifiera kundvisning, lagring, historik och kommersiell användning.
- **Nationella Viltolycksrådet – historiska och löpande viltolyckor:** Följ upp 30-dagarstestet och etablera en kontrollerad, skrivskyddad publiceringsendpoint för NVR-händelser med manifest, fullständighetsstatus och källhänvisning. Rådata får inte publiceras direkt från OneDrive eller GitHub Pages utan separat publiceringskontroll.
- **Länsstyrelsernas Älgdata – avskjutning per älgförvaltningsområde:** Slutför rå ÄJO-rad-för-rad-jämförelse mellan 2026-11-21 och 2026-11-23 med stabila registreringsnummer. Dashboardjämförelsen visar +972 kumulativa fällda (109 ÄFO ökade, 20 oförändrade, inga minskade) och oförändrat mål 79 704. Tolka inte differensen som dagliga fälthändelser. Utred separat rättigheter för historisk lagring, bearbetning och kundvisning innan produktintegration.
- **Länsstyrelserna – nationella älgförvaltningsområden (JaktAdm):** Retrieve the exact geodata metadata record when available and check for layer-specific restrictions; keep Länsstyrelsen attribution and do not offer raw geometry downloads.
- **Trafikverket – Miljöwebb Landskap:** Verifiera vilka lager som ingår i Gräsmyr-piloten, kontrollera antal/geografisk täckning och spara senaste två kompletta snapshots med manifest och kontrollsummor.
- **Trafikverket – NVDB Viltolyckor:** Verifiera produktens exakta definition, referensperiod, geografiska täckning och uppdateringsdatum; spara jämförbara snapshots och dokumentera om värdena är frekvenser, antal eller klassningar.
- **Trafikverket – NVDB vägnät och Lastkajen:** Dokumentera vilken NVDB-produktversion som finns lokalt, kontrollera Lastkajens beställnings- och licensvillkor och bygg ett versionsstyrt uppdateringsflöde innan vägnätsförändringar används i kundhistorik.
- **Viltdata.se – nationell avskjutningsstatistik:** Fortsätt manuella kompletta snapshots med tidsbegränsad GitHub Actions-artifact. Invänta skriftligt besked om historisk lagring/arkivering av exakt avskjutningsstatistikprodukt och avsedda användningar. Azure-region är verifierad som swedencentral; GitHub OIDC-identiteten har Storage Blob Data Contributor på Storage Account-scope. Efter dokumenterat rättighetsbesked: besluta om arkivering och eventuell separat least-privilege-identitet, kör därefter upload, audit och restore live. Ingen schemaläggning eller kundvisning före separat bedömning.


### Länsstyrelsernas Älgdata – nationell ÄFO-avskjutning (verifierad 2026-11-23)

- Full nationell körning #13 i alg-grasmyr är `completed/success` på main och har arkiverat 129/129 aktuella ÄFO för säsong 2026/2027.
- Artifactkontroll: 3 237 råa ÄJO-rader; `ShotTotal` summerar till 57 687 och `AssignedTotal` till 79 704, med exakt överensstämmelse mot dashboarden.
- Daterade snapshots finns för 2026-11-21 och 2026-11-23. Detta ger två nationella observationer, men jämförbar förändringsanalys ska först göras efter kontroll av stabila ID:n, säsong och gränssättning samt snapshoternas faktiska innehåll.
- Dashboard är uppdaterad till 2026-11-23. Äldre snapshotfiler bevarades.
- Kumulativa säsongssummor är inte individuella fälldatum/händelser. Kundvisning är fortsatt villkorad av attribution/källomfattning; lagring, bearbetning och kommersiell användning ska bedömas separat.

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


### Nationell ÄFO-differens 2026-11-21 till 2026-11-23

Dashboardjämförelsen omfattar 129/129 samma ÄFO-ID:n och samma säsong 2026/2027. Kumulativt rapporterat fälltal ökade från 56 715 till 57 687 (+972); 109 områden ökade, 20 var oförändrade och inget minskade. Avskjutningsmålet var oförändrat 79 704. Antalet råa ÄJO-rader per område var oförändrat i dashboardmetadata. Antalet färdigrapporterande ÄJO ändrades i 10 områden, inklusive en minskning i 14-005. Full rad-för-rad-jämförelse av råa ÄJO-rader återstår och krävs före slutsatser om nytillkomna/förändrade poster. Differenserna är kumulativa rapportförändringar, inte exakta dagliga händelser.
