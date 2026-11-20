# AI-projektledare v2b – säkerhetsgranskning av GitHub-lagring

**Granskningsdatum:** 2026-11-19  
**Omfattning:** Read-only kontroll av repository, rulesets, branchskydd, befintlig workflow och planerad historikbranch.  
**Status:** Delvis verifierad. Persistens får inte aktiveras.

## 1. Verifierade observationer

| Kontroll | Resultat | Betydelse |
|---|---|---|
| Repository | `dahlinrobert-lgtm/Skog`, default branch `main`, public repository | Bekräftad metadata |
| Repository rulesets API | `GET /repos/dahlinrobert-lgtm/Skog/rulesets` returnerade `[]` | Inga repository rulesets returnerades av endpointen |
| Klassisk branch protection för `main` | `GET /branches/main/protection` returnerade HTTP 403 `Resource not accessible by integration` | Kan inte avgöra om klassiskt branchskydd finns; kräver administrativ kontroll |
| Planerad historikbranch | `GET /branches/project-manager-history` returnerade 404 | Branchen finns inte, förväntat före aktivering |
| Nuvarande project-manager-workflow | YAML har workflow-nivå `contents: read`, `issues: read`, `pull-requests: read`, `actions: read` | Inget `contents: write` i inventeringsworkflowet |
| Nuvarande workflow-jobb | `tests` och `inventory`; inventory körs endast vid `workflow_dispatch` och behöver `tests` | Ingen persistenskomponent finns |
| Artifact | `skogskoll-project-manager-report`, retention 14 dagar | Tillfällig transport/granskning, inte beständig historik |

## 2. Slutsatser

1. Nuvarande inventeringsworkflow är fortsatt read-only enligt granskad version.
2. Ingen separat persistence-workflow eller historikbranch finns.
3. Rulesets-endpointen returnerade en tom lista, men klassisk branch protection kunde inte läsas på grund av integrationsbehörighet. Det går därför **inte** att bevisa att `main` är skyddad mot direkt push från en framtida skrivande workflow-identitet.
4. GitHubs vanliga `GITHUB_TOKEN` med `contents: write` är inte i sig en branch-specifik token. En workflow-`if`-kontroll är inte en säkerhetsgräns mot felaktig workflow-kod.
5. Separat jobbnivå med `permissions: contents: write` isolerar behörigheten från inventeringsjobbet, men tokenen har fortfarande repository-omfattande contents-write inom de regler GitHub tillämpar. Branchskydd måste verifieras, inte antas.

## 3. Blockerande verifieringar före livepilot

Kontrollera i GitHubs webbgränssnitt som repository-administratör:
- `Settings → Rules → Rulesets`: aktiva rulesets och branch targets.
- `Settings → Branches`: klassiskt branchskydd för `main`.
- Säkerställ att `main` kräver pull request och att GitHub Actions/GITHUB_TOKEN inte kan kringgå skyddet.
- Bestäm hur historikbranchen skyddas mot force-push och deletion. Om ruleset inte kan rikta sig till historikbranchen utan att blockera avsedd append-commit måste designen justeras.
- Kontrollera repository Actions policy och vilka workflows som får använda `GITHUB_TOKEN` med write-behörighet.
- Verifiera att persistensjobbet endast körs efter betrodd `workflow_dispatch`/`workflow_run`-kedja och aldrig med skrivbehörighet i `pull_request`-kontext eller från forks.

Skärmbilder/export av inställningarna eller administrativt åtkomlig API-verifiering behövs. Inga inställningar ändras i denna PR.

## 4. Rekommenderad säkerhetsmodell

- Behåll inventeringsworkflowets read-only-permissions.
- Lägg inte till `contents: write` på workflow-nivå.
- Vid framtida godkänd pilot ska write endast deklareras på separat persistence-jobb.
- Persistensjobbet ska endast ta emot artifact från samma betrodda workflow-run och validera filuppsättning, repoidentitet, run-ID, coverage och checksummor på nytt.
- Använd ingen PAT som genväg.
- Om branchskyddet inte kan hindra oavsiktlig skrivning till `main`: stoppa GitHub-branchalternativet och utred separat GitHub App-installation med snäva permissions eller Azure Blob med separat container-scope-identitet.

## 5. CI-triggerkorrigering

`pull_request.paths` omfattar `scripts/project_manager_history.py` och `tests/test_project_manager_history.py`, men `push.branches: [main].paths` omfattade inte dessa filer. Lägg till dem så att ändringar i offline-historikmodulen också kör tester efter merge till `main`.

## 6. Aktiveringsbeslut

**Inte godkänt / inte aktiverat.** Denna granskning ändrar inte behörigheter, skapar inte historikbranch och inför inte persistensworkflow. En framtida syntetisk livepilot kräver:
1. administrativ verifiering av `main`-skydd och historikbranchens regler;
2. godkänd separat permissionsmodell;
3. syntetiska tester och readback/restore;
4. användarens uttryckliga separata godkännande.


## 7. Uppföljning – `Protect main` verifierat (2026-11-19)

Efter administratörens konfiguration verifierades rulesetet direkt via GitHub Rulesets API:

- ID: `27619735`, namn: `Protect main`, enforcement `active`.
- Target: `~DEFAULT_BRANCH` (main).
- Bypass actors: tom lista; `current_user_can_bypass: never`.
- Regler: `pull_request` före merge, `deletion` och `non_fast_forward`.
- Pull request: 0 obligatoriska approvals; Code Owner review, senaste push approval och conversation resolution krävs inte.
- Merge-metoder: merge, squash, rebase.

Detta undanröjer den tidigare blockeraren för main-skydd. Skyddet kräver PR och blockerar radering/force push, men kräver inte mänsklig approval. Nästa blockerare är att utforma och verifiera separat skydd för historikbranchen samt en skrivmodell som inte kan kringgå `main`-regeln. Nuvarande inventeringsworkflow är fortsatt read-only. Ingen persistens eller `contents: write` har aktiverats.


## 8. Föreslagen skrividentitet och kvarvarande risk (2026-11-19)

Detaljerad modell finns i [PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md](PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md). GitHub App installerad endast på Skog, med Contents read/write och obligatorisk Metadata read, är bättre avgränsad än en användar-PAT eller bred token. Men dess behörighet är repository-scoped, inte branch-scoped. `Protect main` ger PR-grind och tom bypass-lista; Appen får inte Administration, Pull requests-write eller bypass. Historikbranchens ruleset kan blockera deletion och force-push men måste tillåta fast-forward-uppdatering. Det ger inte immutabilitet på filnivå: äldre run-kataloger måste skyddas av append-only-kod och negativa tester. Om repository-scope inte är tillräckligt ska separat repo eller annan branch-/container-scope-lagring väljas.

**Status:** designförslag endast. Ingen GitHub App, installation, privat nyckel, secret, historikbranch, persistence-workflow eller skrivbehörighet har skapats. Inventeringsworkflowet förblir read-only.

## 9. Nästa säkerhetsgrind – historikbranch (2026-11-20)

PR #445:s lokala Git-test är verifierat i CI, men det verifierar inte GitHub rulesets eller tokenens faktiska behörigheter. `Protect main` (ID 27619735) är aktivt och verifierat med PR-krav, deletion och non-fast-forward blockerat, tom bypass-lista. Read-only listning av repository rulesets visar fortfarande endast `Protect main`; inget ruleset för historikbranch finns ännu. Branch protection-endpointen för `main` kan inte läsas av integrationen (403), så användarens tidigare skärmbilder/administrativa konfiguration och ruleset-API:t är den tillgängliga evidensen.

Historikbranchens ruleset ska utformas enligt verifieringsmatrisen i `PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md`. Kritiska tester är: exakt target, aktiv enforcement, ingen bypass, tillåten vanlig fast-forward append, nekad force push, nekad deletion och nekad direktuppdatering av main med samma dedikerade identitet. En GitHub App med Contents-write i Skog är repository-scoped; ruleset ger skydd men inte en teknisk branch-scopad credential. Om branchscope är ett absolut krav måste separat repo eller annan lagring utredas.

Ingen historikbranch, App, private key, secret, write permission eller persistensworkflow skapas i detta steg. Persistens förblir spärrad.

## Beslut: separat privat historikrepository för v2b (2026-11-20)

Efter avvägning väljs ett separat privat Git-repository för projektledaragentens persistenta historik, i stället för en historikbranch i det publika Skog-repot.

Skäl:
- Skog-repot är publikt. En branch i samma repository ärver både repositoryns synlighet och dess befintliga Git-objekthistorik; att lägga till en ny branch ger inte en fristående/orphan-historik.
- En separat privat repository ger separat synlighet, separat ruleset och en GitHub App-installation vars Contents-write kan begränsas till just historikrepot. Det ger en starkare teknisk gräns än branchregler i Skog.
- Git behåller append-commits, SHA-1 objektidentitet och full historik; indefinite retention blir naturligt så länge repot och dess backup bevaras.

Nackdelar och hantering:
- Ytterligare repository att administrera, övervaka och säkerhetskopiera.
- Historik och inventeringskod blir två separata resurser; persistensjobbet måste verifiera artifact-proveniens och skriva endast till historikrepot.
- Git är inte i sig WORM/immutability: en administratör kan ändra rulesets eller radera repot. Kräv aktivt ruleset, ingen bypass för Appen, deletion/force-push-skydd, extern backup/restore-test och audit av administratörsåtgärder.
- Repositorynamn föreslås `skogskoll-project-manager-history`; skapa som Private. Indefinite retention är ett verksamhetsbeslut, inte en garanti mot kontoförlust eller administrativ radering.

Alternativet branch i Skog avvisas eftersom Skog är publikt och innehåller redan befintlig kod-/dataprojektshistorik. Separat privat repo ger bättre sekretess och credential-isolering. Azure Blob med container-scope-identitet är ett möjligt framtida alternativ om krav på objektlås/WORM eller kostnad/tillväxt gör Git olämpligt, men väljs inte i detta steg.

**Aktiveringsgräns:** Detta är ett arkitekturbeslut, inte tillstånd att skapa repo, App, nyckel, secret eller persistence-workflow. Nästa steg är att skapa det privata tomma historikrepot först efter uttryckligt godkännande av själva repo-skapandet; därefter ruleset och syntetiska tester med separat identitet. Ingen historik skrivs före verifiering och separat godkännande.


## 10. Aktuell verifiering – separat privat historikrepository (2026-11-20)

PR #458 är sammanslagen och ersätter branchalternativet i denna tidigare granskning.

| Kontroll | Resultat | Betydelse |
|---|---|---|
| Historikrepository | `dahlinrobert-lgtm/skogskoll-project-manager-history`, ID `1465873025` | Verifierat |
| Visibility | `private` | Verifierat via repository metadata |
| Default branch | `main` | Verifierat |
| Bootstrap | README samt `docs/HISTORY_FORMAT.md` och `docs/SECURITY_AND_OPERATIONS.md` | Verifierat |
| Repository rulesets | API returnerar `[]` | Inget ruleset konfigurerat |
| Klassisk branch protection för main | API svarar 403 för integrationen | Okänt; kräver administrativ kontroll |
| Produktionshistorik | Endast dokumentation | Ingen persistens |
| Writer identity/secret/workflow | Inte skapade | Ingen skrivväg aktiverad |

**Nästa blockerare:** administrativt konfigurera och verifiera ruleset för historikrepots `main` (active, block deletion, block non-fast-forward/force push, ingen bypass för framtida App-identitet). Därefter krävs extern backup/restore-verifiering och syntetiska negativa tester.

**Säkerhetsgräns:** ingen App, installation, privat nyckel, Actions-secret, Contents-write, schemaläggning eller persistensworkflow har skapats. Inventeringsworkflowet i Skog är fortsatt read-only. Persistens får inte aktiveras utan separat uttryckligt godkännande.
