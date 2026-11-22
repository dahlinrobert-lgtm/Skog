# Skog/Skogskoll – prioriterad projektbacklogg

**Baslinje:** 2026-11-18  
**Ägare av beslut:** Användaren  
**Regler:** Se [PROJECT_MANAGER_RULES.md](PROJECT_MANAGER_RULES.md). Prioriteringar är förslag, inte godkända arbetsorder.

## Prioriterade arbetsområden

| ID | Uppgift | Prioritet | Status | Beroenden / nästa steg |
|---|---|---|---|---|
| PM-001 | Bygg read-only projektinventering av issues, PR, workflows och dokumentstatus | P1 | v1/v2a verifierade; v2b Git + indefinite beslutat, design/implementation återstår | Användaren har valt separat skyddad Git-branch och indefinite retention. Teknisk design dokumenterad i `PROJECT_MANAGER_AGENT_V2B_TECHNICAL_DESIGN.md`. Offline-modulen är mergad via PR #440 och lokal restore-/round-trip-funktion via PR #441; PR #441:s samtliga checks passerade. Säkerhetsgranskningen finns i `PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md`: rulesets-endpointen gav tom lista, men klassiskt branchskydd för main kunde inte läsas (HTTP 403). Historikbranch saknas ännu. Detta blockerar livepersistens tills administrativ verifiering och separat permissionsmodell är klara. CI push-paths korrigeras för history-modul och tester. Ingen v2c ännu. |
| PM-002 | Etablera AI-baserad projektledarrapport och beslutslista | P1 | Väntar på separat beslut | LLM/API, datahantering, secret, kostnadsram och eventuell schedule kräver uttryckligt beslut. v2 ska först förbli deterministisk och read-only. |
| PM-003 | Utred och verifiera Lantmäteriets beslut/villkor för Fastighetsindelning Direkt | P1 | Öppen | Ärenden LM2026/171963 och LM2026/171968; rättighets- och produktomfattning måste dokumenteras. |
| PM-004 | Felsök Skogsstyrelsens SIS metadataövervakning | P1 | Öppen | Kontrollera misslyckade körningar 13–14 november, rasterhämtning och produktvillkor. |
| PM-005 | Följ upp NVR:s 30-dagars observationstest och fullständighetsmodell | P1 | Pågående | Kontrollera dagliga körningar, snapshots, manifest och jämförbarhet; partial får inte ge borttagningsslutsatser. |
| PM-006 | Slutför Rovbase geografiska kvalitetsgranskning | P1 | Pågående | Kör korrigerad full validering i separat output; utred 35 koordinatpar och bekräfta RT90-systemet med källägaren. |
| PM-007 | Verifiera Skogsstyrelsens avverkningsanmälningar med kompletta jämförbara körningar | P1 | Öppen | Full paginering, checkpoint/retry, stabila ID:n och minst två kompletta jämförbara körningar. |
| PM-008 | Verifiera samråd separat per punkt-, linje- och polygonlager | P1 | Öppen | Fullständighet och snapshotmanifest per lager. |
| PM-009 | Fortsätt Torvkarta/SIS veckosnapshot och jämförbarhetstest | P1 | Pågående | Två jämförbara snapshots per tjänst innan geografisk breddning enligt issue #132. |
| PM-010 | Verifiera Viltdata rättigheter och beslut om Azure-arkivering | P1 | Blockerad | Invänta skriftligt besked om historisk lagring/arkivering och avsedda användningar; ingen riktig upload före beslut. |
| PM-011 | Granska NVDB nationell matchningspilot och bygg oberoende referensurval | P2 | Planerad | Benchmark, manuellt facit, täckning och prestanda; fortsatt review-only. |
| PM-012 | Fortsätt Länsstyrelsens diary discovery kontrollerat | P2 | Planerad | Kör en grupp åt gången; ingen schedule eller snapshotpublicering via discovery-workflow. |
| PM-013 | Registrera och bedöm Rovbase som separat källa | P2 | Blockerad | Rättighetsbesked och validerad datakvalitet före operativ källa/produktflöde. |
| PM-014 | Utvärdera SCA/Sveaskog-källspår | P3 | Öppen | Källåtkomst, fullständighet och rättigheter; ingen automatisk insamling före beslut. |
| PM-015 | Slutför Skogskoll produktionsberedskap för auth, RLS, PostGIS och ingestion | P2 | Planerad | Verifiera befintlig kod/CI och separat testprojekt; ingen produktionsaktivering ännu. |
| PM-016 | Implementera bevakningshistorik och aviseringar efter verifierad baslinje | P2 | Blockerad | Kräver PM-015, källgodkännande, användarsamtycke och tyst första baslinje. |
| PM-022 | Etablera Skogskolls snapshotbaserade dag-för-dag-flöde | P1 | Pågående – inventering klar; adapterkontrakt nästa | PR #483 kundskal och PR #484 change-feed-kontrakt är mergade; PR #486 dokumentationsstatus är också mergad. Snapshot-/historikinventering finns i docs/SKOGSKOLL_SNAPSHOT_INVENTORY.md. Nästa steg: ren adapter-mappning för befintlig Skogsstyrelsen-worker till snapshot-envelope och tester för fullständighet/täckning/rättighetsgrind. Ingen migration eller kundfeed är aktiverad. Ofullständiga körningar får aldrig skapa borttagningshändelser. |

## Kända externa GitHub-issues att synka

- [#363 Viltdata snapshot-pilot](https://github.com/dahlinrobert-lgtm/Skog/issues/363)
- [#177 SCA inkrementell geometri/metadata](https://github.com/dahlinrobert-lgtm/Skog/issues/177)
- [#173 SCA överlapp/inneslutning](https://github.com/dahlinrobert-lgtm/Skog/issues/173)
- [#171 SCA kandidatgrupper/QA](https://github.com/dahlinrobert-lgtm/Skog/issues/171)
- [#170 SCA regression/tomma grupper](https://github.com/dahlinrobert-lgtm/Skog/issues/170)
- [#132 Skogsdatalabbet nationell täckningsprobe](https://github.com/dahlinrobert-lgtm/Skog/issues/132)
- [#119 Skogsindustriernas Skyddad skog](https://github.com/dahlinrobert-lgtm/Skog/issues/119)
- [#110 Sveaskog geodata](https://github.com/dahlinrobert-lgtm/Skog/issues/110)

## Backloggskrav

Varje ny uppgift ska innehålla:
- konkret mål och motivering,
- evidenslänk (issue, kod, workflow-run, dokument eller beslut),
- status och senaste verifieringsdatum,
- prioritet och uppskattad insats,
- beroenden/blockerare,
- acceptanskriterier,
- nästa konkreta steg,
- rättighets-/dataskyddsbedömning där relevant.

Avsluta inte en uppgift enbart för att en PR mergats. Kontrollera acceptanskriterier och faktisk drift/verifiering.


| PM-017 | Separat skrividentitet för privat historikrepo | P1 | Ej påbörjad / spärrad | Först efter ruleset, backup/restore och syntetiska negativa tester: utforma separat GitHub App installerad endast på `skogskoll-project-manager-history`, minsta Contents read/write + Metadata read. Ingen App/secret eller livepersistens före separat godkännande. |

- [ ] Kör och verifiera PR-CI för syntetiskt Git-append-test i feature/project-manager-v2b-synthetic-git-append. Testet ska visa isolerad lokal historikbranch, oförändrad main, exakt filinnehåll, idempotens och konflikt utan overwrite. Detta ersätter inte GitHub ruleset-/tokenverifiering.

| PM-018 | Verifiera GitHub-skrivisolering för privat historikrepo | P1 | Delvis verifierad – konfiguration klar | Ruleset `Protect history main` ID 27761134 är active, target exakt `refs/heads/main`, deletion/non_fast_forward blockerade, tom bypass-lista och current_user_can_bypass=never. Negativa operationstester återstår; därefter backup/restore och syntetiska tester. Ingen App, secret eller persistens. |

| PM-019 | Konfigurera och verifiera ruleset för privat historikrepo | P1 | Konfiguration verifierad | Ruleset ID 27761134: active, exakt `refs/heads/main`, deletion och non_fast_forward, ingen bypass. Klassisk branch protection endpoint ger 403; negativtester av faktisk push/deletion saknas. |

| PM-020 | Separat privat Git-repository för projektledarhistorik | P1 | Klart – bootstrap verifierad | `skogskoll-project-manager-history` är skapat och verifierat privat, default branch `main`; bootstrapdokumentation finns. Nästa: extern backup/restore och syntetiska negativa tester; ruleset verifierat (ID 27761134). Ingen App/secret/persistens. |


## PM-021 – Renodla Skogskoll kundwebb

| Fält | Värde |
|---|---|
| Prioritet | P1 |
| Status | Arkitekturgranskning dokumenterad; första UI-steget ej påbörjat |
| Mål | Skogskoll blir enda kundprodukt med separat navigation, gemensamt designsystem och tydlig gräns mot Skogs interna vyer |
| Evidens | [SKOGSKOLL_WEB_ARCHITECTURE.md](SKOGSKOLL_WEB_ARCHITECTURE.md) |
| Beroenden | Behåll befintliga domän-/worker-moduler och databasbeslut; verifiera publiceringssökvägar före flytt |
| Acceptanskriterier | Kundnavigationen länkar inte till interna Skog-sidor; relativa länkar fungerar; testläge förblir tydligt; befintliga Skog-sidor och tester påverkas inte |
| Nästa steg | Separat UI-PR för app-shell, navigation och grundläggande design tokens samt länk-/sökvägstester |
| Rättighets-/driftgrind | Ingen källa eller datatyp blir kundsynlig utan verifierat godkännande; ingen auth, ingestion eller avisering aktiveras i UI-steget |


## PM-023 – Skogsstyrelsens ärendebaserade förändringskontroll

| Fält | Värde |
|---|---|
| Prioritet | P1 |
| Status | Första månatliga pilotkörning och PR-baserad snapshotpublicering verifierade; planned-harvest fullscan återstår |
| Mål | Fånga nya/ändrade ärenden löpande och kontrollera historikens fullständighet med periodiska snapshots för planerade avverkningar, Samråd och utförda avverkningar |
| Evidens | [SKOGSSTYRELSEN_CASE_CHANGE_MONITORING.md](SKOGSSTYRELSEN_CASE_CHANGE_MONITORING.md); workflow [skogsstyrelsen-monthly-source-audit.yml](../.github/workflows/skogsstyrelsen-monthly-source-audit.yml) |
| Scope | Gräsmyr pilotområde, 10 km radie. Planerade avverkningsanmälningar är endast bounded probe i första versionen. |
| Acceptanskriterier | Månatligt workflow lyckas; Samråd tre lager hämtas komplett; utförda avverkningar arkiveras med scope-hash; probe för planerade anmälningar sparas; fel/partial ger ingen giltig kontrollpunkt eller borttagningsslutsats |
| Beroenden | ArcGIS metadata/edit tracking-verifiering; full paginerad planned-harvest snapshot; jämförbara månadssnapshots |
| Nästa steg | Verifiera ArcGIS edit tracking/datumfält och implementera fullständig paginerad snapshot för planerade anmälningar; följ upp jämförbarhet vid nästa månadskörning |
| Rättigheter/drift | Endast teknisk pilotkontroll; ingen kundvisning eller kundavisering aktiveras |

## PM-023 uppföljning – publiceringsflöde behöver korrigeras

Första manuella månadskörningen verifierade insamlingarna men publicering misslyckades eftersom workflowet försökte pusha direkt till skyddad main. Korrigering på separat branch ska skapa en granskningsbar data-PR via peter-evans/create-pull-request. Status för PM-023 är därför: **insamling verifierad i första pilotkörning; beständig publicering inväntar korrigering och ny körning**.


## PM-023 – status efter publiceringskorrigering

PR #489 är mergad. PR-check run #5 passerade teststeget, men källinsamling och snapshot-PR skapades inte i denna körning eftersom de är avsiktligt avstängda vid `pull_request`. PM-023 är därför fortfarande **delvis verifierad**. Nästa acceptanssteg är en manuell `workflow_dispatch` från main och verifiering av att snapshot-PR skapas och kan granskas.


### PM-023 – uppdaterad verifieringsstatus 2026-11-22

Run #6 (workflow_dispatch) lyckades och skapade data-PR #491. Den PR-baserade publiceringsvägen är därmed driftverifierad. Snapshotdata väntar fortfarande på manuell granskning/merge. Samråd och utförda avverkningar har samlats in inom Gräsmyr 10 km-piloten. Planerade avverkningsanmälningar är fortsatt endast en 300-radersprobe av cirka 132 594 poster, inte en fullständig snapshot. PM-023 är **delvis verifierad** tills data-PR:n granskats och planerade anmälningar fått en fullständig, auditerbar insamlingslösning.


### PM-023 – slutstatus efter första snapshot-merge (2026-11-22)

Run #6 lyckades och skapade snapshot-PR #491, som därefter mergades till `main`. Dokumentations-PR #492 är också mergad. Därmed är första pilotens insamling och PR-baserade publiceringskedja verifierade. PM-023 är fortfarande delvis klar: planerade avverkningsanmälningar täcks endast av 300-radersprobe av cirka 132 594 poster; fullständig paginerad insamling, edit tracking och jämförbarhet mellan flera månadssnapshots återstår.


## PM-024 – Återställ säker PR-publicering för Samråd och Life2Taiga (2026-11-22)

**Status: teknisk publiceringskedja verifierad efter merge; schemalagd drift och data-PR-granskning återstår.**

- Samråd-fix #494 och Life2Taiga-fix #495 är mergade till `main`.
- Efterföljande push-utlösta körningar lyckades hela vägen och skapade data-PR #496 respektive #497.
- Båda data-PR:erna är öppna och kräver manuell granskning; ingen automatisk merge.
- Nästa acceptanssteg: granska data/manifest/täckning i #496 och #497, och verifiera därefter att nästa cron-körning för respektive workflow också skapar eller uppdaterar PR utan direktpush till `main`.
- Teknisk insamling innebär inte att datan är godkänd för kundvisning.
