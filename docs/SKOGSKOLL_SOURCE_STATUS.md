# Skogskoll – automatisk status för datakällor

**Register kontrollerat:** 2026-11-18  
**Underlag:** data-platform/config/sources.yml

> Rapporten är maskinellt sammanställd från källregistret. Den är en operativ översikt, inte ett juridiskt godkännande. Saknat operations-block betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.

## Sammanfattning

- Registrerade datakällor: **52**
- Källor med operativ status: **15**
- Källor som ännu inte har operativ status: **37**
- Åtkomst: Auktoriserad åtkomst använd: 1, Delvis verifierad: 5, Ej verifierad: 2, Teknisk probe: 1, Verifierad: 6
- Snapshots: 30-dagars dagligt test: 1, Endast baslinje: 1, Inte startad: 4, Metadatabevakning behöver repareras: 1, Pilot: 8
- Historik: Delvis historik: 6, Delvis historiskt arkiv: 1, Ej verifierad: 4, Endast metadataserie: 1, Ingen: 3
- Kommersiellt: Inväntar produktvillkor: 1, Okänd: 2, Verifierad med källhänvisning: 2, Villkorad: 4, Villkorad av attribution/källomfattning: 1, Villkorad per handling/post: 1, Villkorad per produkt: 4
- Kundvisning: Ej bedömd: 2, Inväntar dokumentgranskning: 1, Inväntar lagerkontroll: 2, Inväntar produktbedömning: 4, Inväntar produktbeskrivning: 1, Inväntar skriftligt/beställt scope: 1, Villkorad: 1, Villkorad av attribution/källomfattning: 3
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
| Länsstyrelsernas Älgdata – avskjutning per älgförvaltningsområde | lansstyrelsen.elk_harvest_statistics | Verifierad | Pilot | Delvis historik | Verifierad med källhänvisning | Villkorad av attribution/källomfattning | 2026-11-25 |
| Länsstyrelserna – nationella älgförvaltningsområden (JaktAdm) | lansstyrelsen.elk_afo_boundaries | Verifierad | Inte startad | Ingen | Villkorad av attribution/källomfattning | Villkorad av attribution/källomfattning | 2026-11-16 |
| Trafikverket – Miljöwebb Landskap | trafikverket.miljoweb_landskap | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB Viltolyckor | trafikverket.nvdb.wildlife_collision_frequency | Delvis verifierad | Pilot | Delvis historik | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Trafikverket – NVDB vägnät och Lastkajen | trafikverket.nvdb.road_network_lastkajen | Delvis verifierad | Endast baslinje | Ej verifierad | Villkorad per produkt | Inväntar produktbedömning | 2026-11-14 |
| Viltdata.se – nationell avskjutningsstatistik | viltdata.kill_statistics | Verifierad | Pilot | Ej verifierad | Okänd | Ej bedömd | 2026-11-18 |
| Länsstyrelserna – eldningsförbud i skog och mark (EXT) | lansstyrelsen.fire_ban | Ej verifierad | Inte startad | Ingen | Okänd | Ej bedömd | 2026-11-24 |

## Nästa åtgärd

- **Skogsstyrelsen – avverkningsanmälningar:** Verifiera komplett paginering och minst två kompletta jämförbara körningar; skilj nya anmälningar från äldre baslinje och bortfall.
- **Skogsstyrelsen – Samråd point, line and area layers:** Verifiera fullständighet separat för punkt-, linje- och polygonlagren och fortsätt bevara dagliga snapshots.
- **Länsstyrelsen – offentliga diarier och ärendehandlingar:** Upprepa en avgränsad, manuell månadskörning för att verifiera reproducerbarhet; dokumentera läns-/frasomfattning och utred Länsstyrelsens tekniska begränsningar innan återkommande drift. Granska dokument/bilagor separat från metadata.
- **SLU Torvkarta 1.0 – klassad och kontinuerlig:** Fortsätt versions-/metadatasnapshots; spara SLU:s skriftliga besked och kontrollera den nya produktens licens vid publicering.
- **Skogliga grunddata – Ståndortsindex SIS (gran och tall):** Felsök misslyckade metadataövervakningskörningar 13–14 november och verifiera rasterhämtning samt produktvillkor.
- **Trafikverket – öppna data:** Använd de tre separata produktposterna nedan för faktisk åtkomst, snapshotstatus, historik och rättighetsbedömning; uppdatera denna post endast om Trafikverket inför en ny gemensam produkt eller tjänst.
- **Lantmäteriet – Fastighetsindelning Direkt (OAPIF):** Hämta och granska beslut/villkor för ärendena LM2026/171963 och LM2026/171968; verifiera kundvisning, lagring, historik och kommersiell användning.
- **Nationella Viltolycksrådet – historiska och löpande viltolyckor:** Följ upp 30-dagarstestet och etablera en kontrollerad, skrivskyddad publiceringsendpoint för NVR-händelser med manifest, fullständighetsstatus och källhänvisning. Rådata får inte publiceras direkt från OneDrive eller GitHub Pages utan separat publiceringskontroll.
- **Länsstyrelsernas Älgdata – avskjutning per älgförvaltningsområde:** Continue immutable national snapshots in alg-grasmyr, link exact Actions run IDs for later complete batches in PM-027, and validate future comparable batches. Keep the row-level audit read-only; assess exact product scope and attribution before any Skog/Skogskoll integration.
- **Länsstyrelserna – nationella älgförvaltningsområden (JaktAdm):** Retrieve the exact geodata metadata record when available and check for layer-specific restrictions; keep Länsstyrelsen attribution and do not offer raw geometry downloads.
- **Trafikverket – Miljöwebb Landskap:** Verifiera vilka lager som ingår i Gräsmyr-piloten, kontrollera antal/geografisk täckning och spara senaste två kompletta snapshots med manifest och kontrollsummor.
- **Trafikverket – NVDB Viltolyckor:** Verifiera produktens exakta definition, referensperiod, geografiska täckning och uppdateringsdatum; spara jämförbara snapshots och dokumentera om värdena är frekvenser, antal eller klassningar.
- **Trafikverket – NVDB vägnät och Lastkajen:** Dokumentera vilken NVDB-produktversion som finns lokalt, kontrollera Lastkajens beställnings- och licensvillkor och bygg ett versionsstyrt uppdateringsflöde innan vägnätsförändringar används i kundhistorik.
- **Viltdata.se – nationell avskjutningsstatistik:** Fortsätt manuella kompletta snapshots med tidsbegränsad GitHub Actions-artifact. Invänta skriftligt besked om historisk lagring/arkivering av exakt avskjutningsstatistikprodukt och avsedda användningar. Azure-region är verifierad som swedencentral; GitHub OIDC-identiteten har Storage Blob Data Contributor på Storage Account-scope. Efter dokumenterat rättighetsbesked: besluta om arkivering och eventuell separat least-privilege-identitet, kör därefter upload, audit och restore live. Ingen schemaläggning eller kundvisning före separat bedömning.
- **Länsstyrelserna – eldningsförbud i skog och mark (EXT):** Kör den manuella metadata-only-inspektionen, verifiera lager, fält, täckning, objektidentitet och tjänstegränser. Planera separat beslut om första baslinje och schemaläggning tidigast 2027-01-24.

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


## Trafikverket – verifierad körning #33 (2026-11-25)

Teknisk körning verifierad: [Actions #33](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340), status complete, 34 lager och 7 674 features inom Gräsmyr-pilotens ungefärliga 75 × 75 km-envelope. Data-PR [#660](https://github.com/dahlinrobert-lgtm/Skog/pull/660) mergades 2026-11-25 21:44:22 UTC (merge commit `5ed1a0b62373b1e78a2f994f384a5e4c24506ef0`); manifest och båda produktkatalogerna är verifierade i `main`. Detta är en första baslinje, inte en jämförbar historikserie. Rättigheter/kundvisning är oförändrade och villkorade per produkt/lager.


## Projektledarens read-only inventory #25 (2026-11-26)

[Inventory #25](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45866881837) kördes 2026-11-26 17:20 UTC efter merge av PM PR #81 och #82. Körningen avslutades success med 3/3 repositories och 0 insamlingsfel. Artifact ID `15141206837`, digest `sha256:d055bee4f6e4a163e7536ca2b2a9e7434c78eacef365c02e6fe10849cfd1604b`. Read-only-säkerhetsfält visar att inga käll-featuredata hämtades och inga källrepositorier skrevs.

Inventory-artifactens `source_snapshot_evidence` för Skog innehåller fem separata adapterposter: avverkningsanmälningar, Samråd, Länsstyrelsernas Älgdata, Trafikverket Miljöwebb Landskap och Trafikverket NVDB Viltolyckor. Älgdata-dashboarden är daterad 2026-11-26 (report 3, säsong 2026/2027, current boundaries, 129/129 ÄFO) med senaste exakta workflowförsök [45837084941](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45837084941). Samråds senaste attempt är [45864838781](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45864838781), success; senaste kompletta manifest är 2026-11-25 inom konfigurerat 10 km-scope.

Trafikverkets separata produktposter validerar manifestet 2026-11-25: Miljöwebb 27 lager/2 396 features och NVDB Viltolyckor 7 lager/5 278 features. Båda är baseline inom Gräsmyrs ungefärliga 75 × 75 km-envelope; nationell täckning och global källtotal är inte verifierade. NVDB Viltolyckor avser aggregerad frekvens per vägsegment, inte individuella olyckor.

**Kvarstående teknisk avvikelse:** båda Trafikverket-posternas `latest_attempt` är `unknown`, eftersom sökvägen `.github/workflows/trafikverket-weekly-snapshots.yml` inte återfinns i GitHub Actions workflow inventory trots att YAML-filen finns i Skogs `main`. PR #82 gör felorsaken explicit och regressionstestad; run-ID får inte härledas från manifest eller commit. Utred workflowregistreringen och kör därefter ny inventory. Teknisk snapshotkompletthet ändrar inte kommersiella villkor, lagringsrätt, kundvisning eller vidare distributionsrätt.


## Projektledarens read-only inventory #26 – 2026-11-26

[Inventory #26](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45869038578) avslutades `completed/success` den 2026-11-26 17:35:53 UTC efter merge av PM PR #83. Körningen rapporterade 3/3 repositories och 0 insamlingsfel. Artifact ID `15141926416` har granskats. Fem adapterposter finns i `source_snapshot_evidence`; inventeringen är read-only och hämtade inga source feature collections.

För både `trafikverket.miljoweb_landskap` och `trafikverket.nvdb.wildlife_collision_frequency` är `latest_attempt` run [45705661340](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340), `completed/success`, med exakt workflow path `.github/workflows/trafikverket-weekly-snapshots.yml` och `workflow_discovery=repository_run_history_exact_path_fallback`. Den tidigare matchande körningen är [45705067474](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705067474). Fallbacken är därmed live-verifierad. GitHubs workflow inventory listar fortfarande inte workflowfilen; `workflows_not_found` redovisar den registreringsluckan trots att exakt sökvägsmatchning hittats i run history.

Senaste kompletta produktmanifest är fortsatt 2026-11-25: Miljöwebb 27 lager/2 396 features och NVDB Viltolyckor 7 lager/5 278 features inom det ungefärliga Gräsmyr 75 × 75 km-envelope. En ny latest-attempt-verifiering skapar inte en ny snapshot. Varje produkt har fortsatt endast en verifierad komplett baseline; run #32 är inte här verifierad som en andra komplett jämförbar snapshot. Ingen uppgradering till återkommande driftstatus görs. Global källtotal, nationell täckning, kommersiell användning, historisk lagring, kundvisning och vidare distribution är fortsatt ej verifierade/godkända genom denna inventering.

Källregistret lästes från `data-platform/config/sources.yml` på `main` med källregisterdatum 2026-11-18: 52 source_id, 15 med operations-block, 37 utan. Det är registerinventering, inte bevis på att alla 52 källor har en adapter eller aktuell snapshotstatus.
