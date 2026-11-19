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
