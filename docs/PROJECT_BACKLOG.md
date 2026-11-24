# Skog/Skogskoll – prioriterad projektbacklogg

**Baslinje:** 2026-11-18  
**Ägare av beslut:** Användaren  
**Regler:** Se [PROJECT_MANAGER_RULES.md](PROJECT_MANAGER_RULES.md). Prioriteringar är förslag, inte godkända arbetsorder.

## Prioriterade arbetsområden

## Överordnad prioritering

**P0 – Dagligt snapshotinformationsflöde är projektets primära leverans.** En daglig sammanställning ska visa status för samtliga registrerade källor och separata produkter/lager: senaste kompletta snapshot, senaste körningsförsök, running/success/partial/failed, aktualitet, scope/täckning, antal, jämförbarhet, förändringar, blockerare och länkar till workflow/manifest/artifact/PR. Okända statusvärden ska förbli okända, aldrig visas som noll eller godkända.

Detta är en daglig informationsprodukt och driftkontroll – inte ett krav att alla källor hämtas varje dag. Varje källa behåller en dokumenterad lämplig kadens. Rapporten uppdateras dagligen och visar källans färskhet i förhållande till sin kadens.

**Backloggen ska vara långsiktig och heltäckande men sekundär.** Fånga framtida arbete i separata nivåer; skapa inte fler aktiva spår än kapaciteten medger. Vid konflikt prioriteras P0, därefter fel/fullständighet i befintliga snapshots och nationell täckning, därefter plattform och kundfunktioner.

### PM-027 – Dagligt snapshot- och källinformationsflöde (P0)

| Fält | Värde |
|---|---|
| Prioritet | P0 – högsta operativa prioritet |
| Status | Krav fastställt; inventering av befintliga rapporter/workflows återstår |
| Mål | Daglig read-only status över snapshots och insamlingsflöden för alla registrerade källor och separata produkter/lager |
| Ska visa | Senaste kompletta snapshot; senaste körningsförsök; running/success/partial/failed; stale-status; källans kadens; scope/täckning; antal; jämförbarhet; förändringar; blockerare; granskningsbehov; evidenslänkar |
| Acceptanskriterier | Daglig rapport; alla källor/lager med; senaste kompletta snapshot skild från senaste försök; okända statusar förblir okända; fel/partial synliggörs; read-only; inga kundwrites eller kundaviseringar |
| Beroenden | Källregister, workflow-run inventory, snapshotinventering, manifest/artifactlänkar, normaliserad statusmodell |
| Nästa steg | Inventera befintlig projektledarinventering och snapshot/change-feed-kontrakt; definiera minsta rapportfält och käll-/lagerkoppling utan parallell historikmodell |

### Backloggens långsiktiga täckningsområden

Backloggen ska successivt fånga följande områden. Detta är en planeringsram, inte en order att starta allt.

- **Källregister och nationell täckning:** varje källa/produkt/lager, nationell geografi, fullständighetsmetod, stabila ID:n och täckningsluckor.
- **Daglig drift och observability:** schemalagda körningar, freshness/SLA, felklassning, återhämtning, runbooks, kostnad och kapacitetsgränser.
- **Snapshots och historik:** gemensamt envelope, manifestschema, checksummor, append-only-arkiv, retention, deduplicering, checkpoints och restore.
- **Datakvalitet och geometri:** CRS, giltighet, topologi, precision, attribut, ID-stabilitet, dubbletter och scope-hash.
- **Källspecifika adaptrar:** ArcGIS/OGC API, raster, WMS, PxWeb/statistik, filhämtning, diarier och versionsstyrda geodata.
- **Analys och indikatorer:** förändringsdetektion, överlapp/union, arealberäkning, riskindikatorer, historiska jämförelser och osäkerhetsmått.
- **Skogskoll runtime:** auth, RLS, PostGIS, säker ingestion, bevakningsområden, matchning, API, testmiljö, backup och restore.
- **Kundupplevelse:** karta, historik, filter, sökning, förklaringar, proveniens, mobilanpassning och tillgänglighet.
- **Aviseringar:** tyst baslinje, opt-in, relevansfilter, deduplicering, transactional outbox, e-post/push och leveransstatus.
- **Rättigheter och regelefterlevnad:** teknisk åtkomst, lagring, bearbetning, derivat, kommersiell användning, kundvisning, redistribution, attribution, personuppgifter och sekretess per produkt/lager.
- **Kommersiell drift:** abonnemang, behörigheter, support, incidenter, kostnadsmodell, användningsvillkor och mätning av nytta.
- **Teknisk skuld och förvaltning:** beroendeuppdateringar, Node/Python-versioner, CI, dokumentation, kodägarskap, säkerhetsskanning, testtäckning och legacyavveckling.

| ID | Uppgift | Prioritet | Status | Beroenden / nästa steg |
|---|---|---|---|---|
| PM-001 | Bygg read-only projektinventering av issues, PR, workflows och dokumentstatus | P1 | v1/v2a verifierade; v2b Git + indefinite beslutat, design/implementation återstår | Användaren har valt separat skyddad Git-branch och indefinite retention. Teknisk design dokumenterad i `PROJECT_MANAGER_AGENT_V2B_TECHNICAL_DESIGN.md`. Offline-modulen är mergad via PR #440 och lokal restore-/round-trip-funktion via PR #441; PR #441:s samtliga checks passerade. Säkerhetsgranskningen finns i `PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md`: rulesets-endpointen gav tom lista, men klassiskt branchskydd för main kunde inte läsas (HTTP 403). Historikbranch saknas ännu. Detta blockerar livepersistens tills administrativ verifiering och separat permissionsmodell är klara. CI push-paths korrigeras för history-modul och tester. Ingen v2c ännu. |
| PM-002 | Etablera AI-baserad projektledarrapport och beslutslista | P1 | Väntar på separat beslut | LLM/API, datahantering, secret, kostnadsram och eventuell schedule kräver uttryckligt beslut. v2 ska först förbli deterministisk och read-only. |
| PM-003 | Utred och verifiera Lantmäteriets beslut/villkor för Fastighetsindelning Direkt | P1 | Öppen | Ärenden LM2026/171963 och LM2026/171968; rättighets- och produktomfattning måste dokumenteras. |
| PM-004 | Felsök Skogsstyrelsens SIS metadataövervakning | P1 | Öppen | Kontrollera misslyckade körningar 13–14 november, rasterhämtning och produktvillkor. |
| PM-005 | Följ upp NVR:s 30-dagars observationstest och fullständighetsmodell | P1 | Pågående | Kontrollera dagliga körningar, snapshots, manifest och jämförbarhet; partial får inte ge borttagningsslutsatser. |
| PM-006 | Slutför Rovbase geografiska kvalitetsgranskning | P1 | Pågående | Kör korrigerad full validering i separat output; utred 35 koordinatpar och bekräfta RT90-systemet med källägaren. |
| PM-007 | Verifiera Skogsstyrelsens avverkningsanmälningar med kompletta jämförbara körningar | P1 | Första kompletta Gräsmyr-observation verifierad; nationell täckning och observation 2 återstår | Run #8 (2026-11-22) och PR #524: 165/165 ID:n/geometrier, stabil ID-inventering, complete_scan=true, snapshot SHA-256 arkiverad. Nästa: andra kompletta jämförbara Gräsmyr-snapshoten; därefter nationell uttagsdesign och fullständighetsgrind. |
| PM-008 | Verifiera samråd separat per punkt-, linje- och polygonlager | P1 | Öppen | Fullständighet och snapshotmanifest per lager. |
| PM-009 | Fortsätt Torvkarta/SIS veckosnapshot och jämförbarhetstest | P1 | Pågående | Två jämförbara snapshots per tjänst innan geografisk breddning enligt issue #132. |
| PM-010 | Verifiera Viltdata rättigheter och beslut om Azure-arkivering | P1 | Blockerad | Invänta skriftligt besked om historisk lagring/arkivering och avsedda användningar; ingen riktig upload före beslut. |
| PM-011 | Granska NVDB nationell matchningspilot och bygg oberoende referensurval | P2 | Planerad | Benchmark, manuellt facit, täckning och prestanda; fortsatt review-only. |
| PM-012 | Fortsätt Länsstyrelsens diary discovery kontrollerat | P2 | Planerad | Kör en grupp åt gången; ingen schedule eller snapshotpublicering via discovery-workflow. |
| PM-013 | Registrera och bedöm Rovbase som separat källa | P2 | Blockerad | Rättighetsbesked och validerad datakvalitet före operativ källa/produktflöde. |
| PM-014 | Utvärdera SCA/Sveaskog-källspår | P3 | Öppen | Källåtkomst, fullständighet och rättigheter; ingen automatisk insamling före beslut. |
| PM-015 | Slutför Skogskoll produktionsberedskap för auth, RLS, PostGIS och ingestion | P2 | Planerad | Verifiera befintlig kod/CI och separat testprojekt; ingen produktionsaktivering ännu. |
| PM-016 | Implementera bevakningshistorik och aviseringar efter verifierad baslinje | P2 | Blockerad | Kräver PM-015, källgodkännande, användarsamtycke och tyst första baslinje. |
| PM-022 | Etablera Skogskolls snapshotbaserade dag-för-dag-flöde | P1 | Adapter, metadata-provider, workerintegration och snapshotregister mergade; isolerad Supabase-verifiering återstår | PR #531/#535 etablerade adapter och jämförbarhetskontrakt; PR #537 lade till ArcGIS-metadata från faktisk workerkonfiguration; PR #538 kopplade metadata till worker/store och införde migration 005 med `snapshot_envelopes`, immutabilitetsgrindar, idempotent registrering och återförsök. CI passerade med 85/85 UI-tester, begränsad source probe (300/300 unika ID:n) och migration/SQL-smoketest i disponibel PostgreSQL/PostGIS. Nästa steg: verifiera migration/RPC i separat Supabase-testmiljö och därefter live read-only metadatahämtning. Ingen produktionsmigration, kundfeed eller avisering utan separat godkännande. |

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
| Nästa steg | Bygg UI i små, reversibla vertikala iterationer: app-shell/navigation först, därefter flöde/kort, karta och historik. Testa varje steg med syntetiska data, länk-/sökvägstester, responsivitet och manuell UX-granskning. UI ska vara frikopplat från worker/DB via kontrakt och klientgräns. |
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


### PM-024 – uppdatering efter data-PR-merge (2026-11-22)

Samråd snapshot-PR #496 och Life2Taiga data-PR #497 är nu båda mergade till `main`. Deras merge commits är `f442d6a24832a347319bd7c70fa08e331b2a0674` respektive `467322df3f1c591717e58b0f650717471d2b80cc`.

**Återstående acceptanssteg:** verifiera en faktisk schemalagd körning efter ändringarna för vardera workflow och kontrollera att respektive automation skapar/uppdaterar en granskningsbar PR. Ingen automatisk merge. Ingen kundvisningsrätt följer av publiceringen.


### PM-024 – slutstatus för dokumentations- och data-PR:er (2026-11-22)

PR #498 är mergad (merge commit `21cfa30af358588eb6889d27f78b4e8bffc1fa9a`) och kund-UI-test efter merge passerade. Data-PR #496 (Samråd) och #497 (Life2Taiga) är också mergade. Återstående acceptanspunkt är faktisk schemalagd körning efter workflowfixarna #494/#495; push-utlösta körningar räcker inte som cron-verifiering. Därefter fortsätter fullständig paginering för planerade avverkningsanmälningar.


## PM-025 – Styr Skog/Skogskoll mot sammanhållen kundprodukt

| Fält | Värde |
|---|---|
| Prioritet | P1 |
| Status | Planen samordnad i dokumentation; implementation och acceptans sker stegvis |
| Mål | Säkerställa att dataplattformens arbete leder till en driftsäker, rättighetsklar och användbar Skogskoll-tjänst |
| Slutmål | Privat skogsägare kan registrera fastighet/bevakningsområde, få kvalitetssäkrade och geografiskt matchade skogshändelser, följa spårbar historik och välja aviseringar |
| Evidens | `PROJECT_ROADMAP.md`, `PROJECT_STATUS.md`, `SKOGSKOLL_DATA_OVERVIEW.md`, `skogskoll/README.md`, `skogskoll/INGESTION.md` |
| Nästa steg | Prioritera fyra huvudspår: (1) kärnbevakning, (2) gemensamt snapshot-/historikflöde, (3) liveverifiering av auth/RLS/PostGIS/ingestion i testmiljö, (4) källspecifika rättighetsbesked |
| Acceptanskriterier | End-to-end-flöde verifierat från källinsamling till kundens historik; fullständighets- och rättighetsgrindar passerar; ingen historisk baslinje aviseringas; partial kan inte skapa borttagning; aviseringar kräver opt-in; drift och återställning är testade |
| Säkerhetsgrind | Ingen kundvisning, fastighetskoppling eller avisering aktiveras innan rättigheter och tekniska kontroller är uttryckligen verifierade |

PM-025 är en styrningspost, inte ett påstående om att produkten är färdig. Datakällor som inte bidrar till prioriterade kundflöden ska inte automatiskt tränga undan blockerande kärnarbete.

## PM-026 – Nationell insamling per relevant datakälla

| Fält | Värde |
|---|---|
| Prioritet | P1 – övergripande programkrav |
| Status | Mål fastställt; källvisa nationella acceptansbevis återstår |
| Mål | Etablera verifierad nationell insamling för varje relevant datakälla och separat produkt/lager, där källans täckning, tekniska villkor och rättigheter medger det |
| Evidens | PROJECT_ROADMAP.md; SKOGSKOLL_DATA_OVERVIEW.md; Gräsmyr fullscan run #8 och arkiv-PR #524 |
| Omfattning | Samtliga relevanta källor i data-platform/config/sources.yml, prioriterade efter kundnytta, kvalitet, teknisk möjlighet, kostnad och rättigheter. Ingen automatisk utvidgning till kundproduktens scope. |
| Acceptanskriterier | Dokumenterad nationell omfattning per källa/lager; verifierad fullständig uttagsmetod; stabila ID:n och count reconciliation; snapshots/manifest/checksummor; fail-closed hantering; minst två kompletta jämförbara observationer; återkommande drift och restore; separat rättighetsbedömning. |
| Nästa steg | Slutför observation 2 för Skogsstyrelsens avverkningsanmälningar i Gräsmyr; utforma därefter nationell uttagsarkitektur. Fortsätt Samråd med separat täckningsbevis för punkt, linje och polygon. |
| Stoppregler | Regional pilot är inte nationell täckning. Katalogpost, karta, probe eller delmängd räknas inte som fullständig insamling. Partial/failed får aldrig skapa borttagning eller ersätta komplett snapshot. Ingen kundvisning/kommersiell användning utan källspecifikt stöd. |

### PM-022 uppdatering 2026-11-23

PR #531 och #532 är mergade och adaptern mappar befintliga `poll_runs` + `scan_sessions` till snapshot-envelope. PR #535 är också mergad (merge commit `429c15a000bdbe22f80275b2e55c042c82b30400`); CI `Skogskoll customer UI tests` passerade för head `cf5e8286b1cf57f78c812f94cf16bd83bfa6ef9f`. Adaptern kräver nu uttrycklig metadata för produkt, endpoint, lager, query-definition, coverage, schema och identitetsversion och skapar en deterministisk `comparability_key`. Ändring i någon av dessa dimensioner skapar en separat jämförelsebas. Saknad metadata kan inte ge `complete`; `partial/failed` fail-closed och kundvisning är fortsatt `not_assessed`.

**Nästa steg:** verifiera den mergade worker-/snapshotregisterintegrationen i en disponibel Supabase-testmiljö och kontrollera därefter ArcGIS metadatahämtning read-only. Inga produktionsmigrationer, fulla nationella körningar, kundfeeds eller aviseringar ingår utan separat beslut.


## PM-028 – Etablera designagent för Skogskolls webb och app

| Fält | Värde |
|---|---|
| Prioritet | P1 – möjliggör kvalitetssäkrad iterativ produktutveckling |
| Status | Mandat och arbetssätt dokumenteras; agenten är ännu inte tekniskt automatiserad |
| Mål | Ge Skogskoll en kontinuerlig produktdesigner/UX-granskare som analyserar gränssnitt, föreslår förbättringar och granskar iterationer |
| Omfattning | Webb och mobil webb först; PWA/native app bedöms först när användarbehov motiverar det |
| Evidens | PROJECT_MANAGER_RULES.md avsnitt 4C; PM-021; SKOGSKOLL_WEB_ARCHITECTURE.md |
| Acceptanskriterier | Agentinstruktion med tydligt uppdrag, granskningsformat, mandatgränser, evidenskrav och tillgänglighets-/responsivitetsgrind; designförslag ska vara små, reversibla och kopplade till testbara användaruppgifter |
| Nästa steg | Använd designagentens instruktion vid nästa PM-021 UI-iteration; välj första konkreta vy/flöde och granska nuläget innan kodändring |
| Stoppregler | Agenten får inte själv merge:a, publicera eller ändra datakontrakt; heuristisk granskning får inte beskrivas som användartest; prototypdata ska vara tydligt märkt |


### PM-022 implementation update 2026-11-22 – ArcGIS metadata provider

På branchen `feat/skogskoll-arcgis-snapshot-metadata` utökas befintlig `createArcGisSource` med en read-only `getSnapshotMetadata()`. Den hämtar lagerdefinitionen via samma ArcGIS-endpoint som källadaptern använder och bygger:
- produkt-ID från explicit worker-konfiguration,
- endpoint och lagernummer från den konfigurerade URL:en,
- query-definition från samma feature-parametrar som `getPage`, utan offset/sidlängd,
- coverage-identitet som uttryckligen betyder ofiltrerad lagerquery (inte nationell geografi),
- schema-version som SHA-256 av kanoniserade fält-/geometrimetadata,
- identitetsversion från ArcGIS OID-fältet och aktuell GeoJSON-ID-normalisering.

Källans metadata cachelagras per adapterinstans. Saknat fältschema, geometri-typ, OID-fält eller explicit lagernummer stoppar metadataframtagningen. Kundvisning är fortsatt `not_assessed`. Funktionen är ännu inte kopplad till snapshot-envelope eller persistens; inga migrationer eller livekörningar har gjorts. PR #537:s customer UI-test passerade 78/78 tester (run 45078075239). Read-only source-probe passerade (run 45078075046): 300/300 unika ID:n, noll dubbletter/saknade ID:n, men avsiktligt inte komplett. Liveanrop av den nya metadatafunktionen och fullständig scan återstår.

### PM-022 implementation update 2026-11-23 – worker integration and snapshot registry

PR #537 är mergad (merge commit 8ad923d9d4f5b2ef3b4e995c0b9aa15035e8256a). Integrationsarbetet fortsätter i PR på branchen feat/skogskoll-worker-snapshot-envelope-integration.

- Worker hämtar och fail-closed-validerar metadata före scan-start.
- Samma metadata sparas i run- och scan-sessionens diagnostics. Återupptagning kräver identisk kanoniserad metadata; metadata-/schema-/querydrift får inte blandas in i en befintlig scan.
- Ny migration 005 inför worker-only snapshot_envelopes med unik scan-session och oföränderlig envelope. Registrerings-RPC kontrollerar terminala statusar, kopplade run-/scan-ID:n, metadataöverensstämmelse och att complete endast kan registreras för fullständigt avslutad scan.
- Store mappar terminala poster genom befintlig snapshot-envelope-adapter och registrerar dem idempotent. Migrationen markerar registreringstidpunkt och en pending-RPC gör att oregistrerade terminala sessioner kan återförsökas vid nästa workerstart utan att skriva om en befintlig envelope.
- CI-utökning applicerar migration 005 och SQL-smoketestet täcker registrering. Inga live DB-/ArcGIS-anrop, produktionsmigrationer, alerts eller kundvisning ingår.

**Status efter merge:** PR #538 mergad i `main` med commit `38f2474ff75fc5d34dc491da059178c266590b58`. Slutliga PR-checkar passerade på kodhead `72c02f9`: UI 85/85, begränsad source probe 300/300 unika ID:n och database tests med migration 005 + PostGIS/SQL-smoketest. Ingen live Supabase eller live ArcGIS metadatahämtning ingick. Källstatus och rättighetsgrindar är oförändrade. Nästa steg är separat verifiering i disponibel Supabase-testmiljö.


### PM-015 uppdatering 2026-11-23 – Supabase-test och behörighetsmigration

Användaren har skapat den separata Supabase-testinstansen `skogskoll-test` (West EU/Ireland, Free/Nano) och rapporterat installation av grundschema samt migrationerna 002–005. I testinstansen visade read-only kontroll att sju tabeller och åtta RPC-funktioner finns och att RLS är aktiverat på de sju tabellerna. Användaren visade lyckade resultat för PostGIS-matchningstestet och atomiskt ingestion/snapshot-smoketest. Behörighetsrevisionen visade dock att API-rollerna saknade direkta tabellprivilegier. Kodgranskning visade att workern behöver direkta REST-SELECT på `scan_sessions` och `poll_runs`.

PR #540 är mergad och migration 006 är installerad i `skogskoll-test`. PR #541 dokumenterade verifieringen och är också mergad. Användarens 27-raders tabellprivilegiekontroll bekräftade: authenticated får CRUD på egna `watch_areas`/`push_subscriptions` och SELECT på egna `alert_events`; service_role får endast SELECT på `scan_sessions`/`poll_runs`; övriga interna tabeller är direkt oåtkomliga. Åtta worker-RPC:er är EXECUTE-begränsade till service_role. CI och manuella SQL-smoketester är godkända. Ingen worker är ännu ansluten; ingen produktionskoppling, kundfeed eller avisering är aktiverad.

**Nästa steg:** etablera en explicit manuell worker smoke-test-väg mot `skogskoll-test`, utan schedule. Den ska först verifiera live ArcGIS metadata read-only och därefter endast köra en uttryckligt avgränsad teknisk testbatch när testhemligheter är konfigurerade. Bekräfta att befintlig `run-scan.mjs` och adapter återanvänds; inga parallella ingestionimplementationer. Secrets ska vara worker-only och aldrig exponeras i logs eller frontend.


## PM-024 – Förbered publicering av Skogskoll som mobilapp

| Fält | Värde |
|---|---|
| Prioritet | P2 – efter stabilisering av kundwebb och produktionsförutsättningar |
| Status | Planerad – krav och arbetsmoment registrerade; teknisk inventering återstår |
| Evidens | [GitHub issue #573](https://github.com/dahlinrobert-lgtm/Skog/issues/573) |
| Mål | Förbereda en gemensam och förvaltningsbar mobilapp för Google Play och Apple App Store utan att skapa parallell backend eller kringgå befintliga rättighets-/säkerhetsgrindar |
| Omfattning | Ägarskap och utvecklarkonton; inventering av befintlig frontend; jämförelse PWA/Capacitor/React Native; butikarnas metadata-, integritets-, behörighets-, konto- och granskningskrav; testning; drift, signering, release och support |
| Kostnad | Preliminärt 25 USD engångsavgift för Google Play Console och 99 USD/år för Apple Developer Program. Beloppen är inte verifierade för beslut och ska kontrolleras mot officiella prisuppgifter, kontoform, moms och valutaväxling före registrering |
| Viktiga beroenden | PM-021 kundwebb; verifierad auth-/kontomodell; mobilanpassning; notifieringsdesign; beslutad juridisk utgivare |
| Acceptanskriterier | Aktuell kodbas inventerad; teknikval motiverat; kontoägare beslutad; aktuella butikskrav och avgifter verifierade; komplett checklista för integritet, behörigheter, kontoradering, granskaråtkomst, metadata, testning och drift; tids-/kostnadsestimat framtaget |
| Säkerhets-/rättighetsgrind | Ingen kontoregistrering/betalning före ägarbeslut. Ingen kundvisning, datakälleaktivering eller avisering som bieffekt. Källrättigheter bedöms fortsatt separat |
| Nästa steg | Read-only inventera befintlig frontend, mobilanpassning, autentisering, kartor och notifieringsflöden; jämför därefter tekniska alternativ och skapa butiksspecifik kravmatris |

