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

En kontrollpunkt kvarstår: `completed_evidence_transition_events` var 486 i körningen före optimeringen och 0 i körningen efter. Det kan bero på ändrad jämförelselogik och att inga nya/ändrade objekt fanns i den senare snapshoten, men detta är ännu inte bevisat. Händelsemängdernas semantik och historiska täckning ska jämföras innan vi betraktar evidenshistoriken som fullt verifierad. Den separata andra kompletta körningen av Gräsmyr 10 km-pilotflödet med manifest- och ID-jämförelse återstår. Ingen frånvaroklassning eller kundavisering aktiveras.
