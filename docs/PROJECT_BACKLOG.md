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

| PM-018 | Verifiera GitHub-skrivisolering för privat historikrepo | P1 | Blockerad – ruleset saknas | Privat repo skapat och verifierat. Rulesets API returnerar ännu `[]`; klassiskt branchskydd kan inte läsas av integrationen (403). Konfigurera/verifiera ruleset på `main`, därefter backup/restore och negativa tester. Ingen App, secret eller persistens. |

| PM-019 | Konfigurera och verifiera ruleset för privat historikrepo | P1 | Ej konfigurerat | Mål: exakt `main` i `skogskoll-project-manager-history`; active, block deletion och non-fast-forward/force push, ingen bypass för framtida automationsidentitet. Verifiera API/UI. Integrationens branch-protection GET gav 403; klassiskt skydd är okänt. |

| PM-020 | Separat privat Git-repository för projektledarhistorik | P1 | Klart – bootstrap verifierad | `skogskoll-project-manager-history` är skapat och verifierat privat, default branch `main`; bootstrapdokumentation finns. Nästa: ruleset, extern backup/restore och syntetiska negativa tester. Ingen App/secret/persistens. |
