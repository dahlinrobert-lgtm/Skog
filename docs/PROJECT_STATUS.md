# Skog/Skogskoll – projektstatus

**Baslinjedatum:** 2026-11-18  
**Källa:** GitHub `main` och projektets tre obligatoriska nulägesdokument.  
**Status:** Första projektledarbaslinje – inte en fullständig kodrevision.

## Samlad bedömning

Skog har en etablerad dataplattform med flera fungerande insamlings-, snapshot-, analys- och valideringsflöden. Skogskoll som kundprodukt är däremot ännu inte produktionssatt. Den centrala förflyttningen är att gå från separata pilotflöden till en komplett, kvalitetssäkrad, rättighetsbedömd och driftbar plattform med användarbevakning och aviseringar.

## Verifierat i dokumentationen

- Källregistret `data-platform/config/sources.yml` innehåller 49 källposter; 12 har operativa statusblock och 37 saknar ännu sådan status.
- Den genererade källstatusrapporten anger 0 källor uttryckligen godkända för kundvisning.
- Skogskoll-prototypen har lokal bevakningsområdeshantering; den är inte en produktionsdatabas och synkar inte användardata mellan enheter.
- Ingestion-kärna, databasstruktur, historikmodell, scan-sessioner, atomisk sidcommit och PostGIS-matchnings-RPC har utvecklats och har teststöd. Liveinstallation i produktionsprojekt är inte verifierad.
- Kundaviseringar ska inte aktiveras innan ingestion, baslinje, historik, databas och källbeteende verifierats.
- Viltdata nationella manuella snapshot 2026-11-18 är dokumenterad som 49 arter, 21 län och 550/550 lyckade statistikförfrågningar. Azure-arkivverktyg finns i main; rättighetsbedömning och livearkivering av original återstår.
- NVR-material 2015–2026 har hämtats och arkiverats i arbetsflöde; ett 30-dagars dagligt observationstest pågår. Fullständighet/jämförbarhet måste fortsatt bedömas.
- Rovbase originaluttag och första geografiska validering finns dokumenterade. Korrigerad full körning, kvarvarande avvikelsegranskning, koordinatsystembekräftelse och rättighetsbedömning återstår.
- NVDB nationella metadata-/geometristickprov är genomfört för 21 län, men nationell matchningskvalitet och täckning är inte bevisad.
- Lantmäteriets Fastighetsindelning Direkt är en viktig extern beroendepunkt; faktiska beslut och villkor för ärendena LM2026/171963 och LM2026/171968 behöver granskas.
- SIS metadataövervakning hade dokumenterade misslyckade körningar 13–14 november och behöver felsökas.

## AI-projektledare – implementation v1 (2026-11-18)

- PR #431 (styrdokument) och PR #432 (agent v1) är mergade i `main`; agentens merge commit är `9c8be18276396f3c53ff30d0dbe91c57e69a293c`.
- Manuell livekörning #5, [Actions #44413951767](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44413951767), kördes på `main`; test- och inventory-jobben avslutades med `success`.
- Artifact #14479221503 innehåller `inventory.json` och `report.md`. Första rapporten visar 6 issues i insamlingsfönstret (5 öppna), 300 PR-poster (5 öppna, 292 mergade), 100 workflows och 50 workflowkörningar; 14 körningar markerades failed/cancelled.
- Samtliga nio projektledardokument hittades. Inventeringen är begränsad till högst tre sidor issues/PR och 50 workflowkörningar.
- Agenten har read-only-behörighet. Ingen schedule, LLM/API eller GitHub-skrivoperation ingår. Detta är en deterministisk inventerings-/rapportagent, inte ännu språkmodellbaserad analys eller autonom projektplanering.

## Kända öppna GitHub-issues vid baslinjen

Följande öppna issues returnerades av GitHub-sökningen 2026-11-18. De är kandidater till backloggen; kontrollera alltid aktuell status innan arbete startas.

| Issue | Ämne | Första bedömning |
|---|---|---|
| [#363](https://github.com/dahlinrobert-lgtm/Skog/issues/363) | Viltdata snapshot-pilot | Följ upp status och nästa steg efter manuell snapshot/Azure-smoketest. |
| [#177](https://github.com/dahlinrobert-lgtm/Skog/issues/177) | SCA inkrementell geometri- och metadataövervakning | Fortsätt endast efter kontroll av beroenden och källvillkor. |
| [#173](https://github.com/dahlinrobert-lgtm/Skog/issues/173) | SCA partiella överlapp och inneslutna relationer | Teknisk analys; kontrollera om senare arbete redan löst delar. |
| [#171](https://github.com/dahlinrobert-lgtm/Skog/issues/171) | SCA kandidatgrupper och attribut-QA | Issue-texten beskriver genomförda ändringar; kontrollera om den bör stängas/uppdateras. |
| [#170](https://github.com/dahlinrobert-lgtm/Skog/issues/170) | SCA regressionstest och tomma grupper | Issue-texten beskriver verifierad körning och uppföljningshärdning; kontrollera kvarvarande kriterier. |
| [#132](https://github.com/dahlinrobert-lgtm/Skog/issues/132) | Nationell täckningsprobe för Skogsdatalabbet | Blockerad av Stage 1 med två jämförbara veckosnapshots för båda tjänsterna. |
| [#119](https://github.com/dahlinrobert-lgtm/Skog/issues/119) | Skogsindustriernas Skyddad skog | Käll- och rättighetsutredning; ingen schemalagd insamling före klartecken. |
| [#110](https://github.com/dahlinrobert-lgtm/Skog/issues/110) | Sveaskog geodata | Käll- och rättighetsutredning; ingen veckosnapshot före klartecken. |

## Viktiga osäkerheter

- Denna baslinje är dokument- och issuebaserad; ingen fullständig kod-/workflowinventering har ännu genomförts av projektledaren.
- Sökresultat för öppna issues kan ändras efter baslinjedatumet.
- Öppna PR-sökningen gav äldre PR-poster som inte säkert kunde klassas som öppna i denna connectorvy. Ingen PR-status ska därför härledas från den sökningen.
- Exakta aktuella resultat för alla schemalagda workflows behöver hämtas vid nästa inventeringskörning.
- Kommersiella rättigheter och kundvisning är inte automatiskt godkända genom teknisk åtkomst eller genomförda tester.

## Rekommenderad ordning

1. Skapa en komplett read-only inventering av issues, PR, workflows och dokumenterade nästa steg.
2. Kontrollera blockerande externa rättigheter och driftproblem.
3. Slutför datakvalitet och historik för befintliga prioriterade källor.
4. Fortsätt produktionsarkitektur och integration först när källornas krav och baslinjer är klara.
5. Förbered kundproduktens flöden men håll användarlarm avstängda tills samtliga skyddsvillkor passerar.


## AI-projektledare – v2a implementerad och liveverifierad (2026-11-19)

PR #436 är sammanslagen i `main` (merge commit `fffad6fd9ccb9af356c89e7c486bdbac7ee53ce5`). Projektledartester och Snapshot storage tests passerade efter merge. Manuell workflowkörning #10 [passerade](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44456582601) och producerade artifact `skogskoll-project-manager-report` med `inventory.json` och `report.md`. Issues-endpointen hämtade 436 poster på 5 sidor; 11 var issues efter filtrering av PR-poster. PR-endpointen hämtade 425 poster på 5 sidor. Båda listorna hade status `complete`, utan trunkering. Artifact SHA-256: `de613fbcc54d2f1567f5c8f5bab75b65a09b1e4a797d9dfb0e4a30cfa85c6dbb`, retention till 2026-12-03 04:12:41 UTC. Rapporten omfattade 100 workflows, 50 workflow runs och 100 senaste commits; 13 av de 50 workflowkörningarna hade failure/cancelled vid inventeringstidpunkten. Dessa är granskningssignaler, inte automatiska felbeslut; de senaste korrigerade PR-kontrollerna och liveinventeringen passerade. Ingen historisk baslinjelagring, jämförelse, schedule, LLM/API eller skrivbehörighet införs.


## Uppdaterad produktstyrning och verifieringsläge (2026-11-22)

Projektets slutmål är en kundklar Skogskoll-tjänst för privata skogsägare, inte enbart en samling fungerande datainsamlingsflöden. Tjänsten ska stödja bevakningsområden/fastigheter, kvalitetssäkrade händelser, geografisk matchning, spårbar historik och valbara aviseringar. Kundvisning och aviseringar förblir avstängda tills respektive datakälla, rättigheter, baslinje och drift är verifierade.

Källstatusrapporten som hämtats från `main` anger 51 registrerade källor, 14 med operativ status och 0 uttryckligen godkända för kundvisning. Äldre siffror i denna baslinjes ursprungliga avsnitt (49/12) ska betraktas som historiska; den aktuella rapporten har kontrollstämpel 2026-11-18.

### Fyra aktiva huvudspår
1. Kärnbevakning: fullständig och jämförbar insamling av planerade avverkningar samt verifiering av Samråd och utförda avverkningar.
2. Gemensam historik: standardiserade snapshots, manifest, coverage-gates, proveniens och restore.
3. Skogskoll runtime: liveverifiera Supabase/Postgres/PostGIS, auth/RLS och serverbaserad ingestion i separat testmiljö.
4. Rättigheter: avgör per exakt produkt/lager vad som får lagras, bearbetas, kommersialiseras och visas för kund.

### Driftuppföljning – Gräsmyr 2026-11-22
Monitor-run [#45041585086](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45041585086) före optimeringen och [#45044260811](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044260811) efter PR #509 avslutades båda med `success`. I båda passerade analyssteget och skapandet/uppdateringen av data-PR. Den senare körningen läste 382 planerade snapshots utan oläsbara filer och analyserade 165 planerade samt 1 631 genomförda objekt. Data-PR [#512](https://github.com/dahlinrobert-lgtm/Skog/pull/512) mergades 17:02:10 UTC i commit `051aad8d41a6749766011cec2ac9af629407ea01`.

PR [#514](https://github.com/dahlinrobert-lgtm/Skog/pull/514) rättade rekonstruktionen så att varje delta följer sin uttryckliga `base_snapshot`-referens. Riktade arkiv-/evidenstester, full testsvit och audit passerade. Main-monitor-run [#45048859162](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45048859162) avslutades `success` efter 30m22s; samtliga steg inklusive analys och data-PR-publicering passerade. Data-PR [#515](https://github.com/dahlinrobert-lgtm/Skog/pull/515) mergades i `db4aca33642812ee69a6bff5cf7083b50f320de6`.

Den nya analysen läste 383 planerade snapshots utan oläsbara filer och rekonstruerade 381 genomförda arkiv; 370 övergångar var jämförbara, 10 äldre övergångar exkluderades på grund av saknat/ändrat query scope och 702 unika `new_completed_detection_overlap`-händelser återfanns. Händelserna är satellitbaserade överlappskandidater för manuell granskning, inte bevis för utförd avverkning. Planerade ID:n var exakt samma 165 i observationerna 16:42 och 17:20 UTC. Båda observationerna innehöll 1 631 genomförda objekt, men fullständig ID-/manifestjämförelse för genomförda polygoner återstår. Ingen frånvaroklassning eller kundavisering aktiveras.


## Gräsmyr – uppföljning efter PR #516 (2026-11-22)

En separat read-only-jämförelse av `data/completed_latest.json` mellan commit `2ee3159902e70b6dc8c92598d852178d620a6ee5` (16:42:36 UTC) och aktuell `main` efter data-PR #515 (17:21:11 UTC) är genomförd.

- Query-scope SHA-256 var identisk: `35078c26165a03b506f0cd0c7c32ed8dca9beab6ddc10413447d01b47a17bbca`.
- Båda observationerna innehöll 1 631 genomförda polygoner.
- Samtliga ID:n jämfördes: 0 tillagda, 0 saknade.
- Samtliga geometrihashar (`geometry_sha256`) jämfördes: 0 ändrade.
- Samtliga objektproperties jämfördes: 0 ändrade.

Detta verifierar identisk genomförd polygonmängd mellan de två observationerna inom samma 10 km-scope. Det är inte en oberoende kontrollsummeverifiering av varje historisk gzip-fil eller samtliga 381 arkivfiler.

De 10 äldre övergångarna från 2026-10-24 förblir exkluderade eftersom query-scope saknas i äldre metadata (för nio par saknas scope i båda ändar; i det tionde saknas äldre scope). Ingen retrospektiv scope får antas. Bevara arkiven och sök endast efter oberoende historisk evidens.

Monitor-run [#45048859162](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45048859162) var push-utlöst och lyckades; den var inte schemalagd. `.github/workflows/monitor.yml` har daglig cron `17 5 * * *` UTC. Nästa cron-körning ska verifieras separat. Ingen kundavisering eller frånvaroklassning aktiveras.


## Skogskoll Operations Center – daglig projektinventering (2026-11-22)

PR [#43](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/43) i det privata projektledarrepot är mergad (`30052942d061c32fb41615328af60895b0384823`). Inventeringen är schemalagd dagligen kl. 07:00 svensk tid via UTC-trigger 05:00/06:00 och en testad `Europe/Stockholm`-tidsgrind som hanterar sommar-/vintertid.

- Read-only-insamling mot registrerade aktiva projekt.
- Ett centralt GitHub Issue i privata historikrepot vid fel; samma ärende uppdateras och stängs först efter full lyckad återhämtning.
- 14-dagars artifact för felsökning; partiella resultat betraktas inte som kompletta.
- PR-CI: `unit-tests` och `synthetic-append-only` passerade.
- Ingen skrivbehörighet till inventerade källrepon, ingen Azure-publicering och ingen kundavisering.

Uppföljande PR [#44](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/44) är mergad och gör även misslyckad artifact-uppladdning larmbar.

PR [#45](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/45) är mergad. Registervalideringen stoppar nu felaktiga, dubblerade eller okända projektposter före insamling; kandidater förblir exkluderade. PR-CI passerade.

PR [#46](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/46) är mergad: saknad inventeringsartefakt ger nu ett fel i stället för att ignoreras. PR [#47](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/47) är mergad: KPI:n för olösta avvikelser inkluderar nu även olösta schemalagda fel. Båda PR:ernas CI-kontroller passerade.

**Status:** Mergad och konfigurerad, men första schemalagda körningen har ännu inte verifierats. Nästa kontroll är 2026-11-23 kl. 07:00 svensk tid.


## Projektledarsidan – automatisk latest-snapshot-koppling (2026-11-25)

Den publika GitHub Pages-sidan `docs/project-manager/` var fortfarande konfigurerad med en fast Azure-blob för inventeringskörning `45002255351` (2026-11-22). Detta gjorde att sidan inte följde senare publiceringar trots att projektledarrepots separata inventory- och Azure-publisher-flöden hade uppdaterats.

Verifierad senaste kedja vid felsökningen:
- Read-only inventory #16: [Actions 45644895332](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45644895332), `success`, 2026-11-25.
- Azure publisher #6: [Actions 45645047499](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45645047499), `success`, 2026-11-25.
- Publishern validerar källkörning och artifact, skriver run-scopad snapshot och manifest, gör read-back-kontroll och uppdaterar `latest.json` efter verifiering.

**Åtgärd i PR:** ändra Pages-klienten till att först läsa `latest.json`, validera att den pekar på förväntad run-scopad blob i samma Azure-container och därefter kontrollera payloadens byteantal och SHA-256 innan data renderas. Sidan visar även källkörning och publiceringstid. JavaScript-syntaxkontroll läggs till i projektledarworkflowet.

Denna ändring återanvänder befintlig inventory → Azure publisher → `latest.json`-arkitektur; ingen ny lagrings- eller publiceringskomponent införs. Liveverifiering av webbläsarens Microsoft-inloggning, Azure CORS och läsning av aktuell `latest.json` krävs efter merge. Ingen skrivbehörighet eller kundpublicering införs.


## Projektledarsidan – prioriterad PM-backlogg (2026-11-25)

PR [#633](https://github.com/dahlinrobert-lgtm/Skog/pull/633) och privata projektledarrepo PR [#73](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/73) är mergade. Den befintliga read-only inventory-kedjan hämtar nu strukturerade PM-uppgifter från Skogs auktoritativa `docs/PROJECT_BACKLOG.md` och skickar dem vidare i den run-scopade Azure-snapshoten. Den autentiserade Pages-sidan visar uppgift, prioritet, status och nästa steg. Dubbla PM-ID:n visas separat med varning.

CI verifierat före merge: private Project manager tests #132, private Synthetic append-only tests #114, Skog Website JavaScript syntax #307, Snapshot storage tests #562 och Skogskoll AI project manager run #26 – samtliga success.

Livepublicering av ny payload och autentiserad browser-rendering återstår att verifiera. Backloggen förblir enda sanningskällan; ingen ny lagrings- eller behörighetsmodell infördes.
