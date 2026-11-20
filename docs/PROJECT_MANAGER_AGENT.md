# Skogskoll AI-projektledare – agent v1 och v2-plan

## Arkitektur
Fristående Python-komponent i Skog-repot:
- Entrypoint: `scripts/project_manager_agent.py`
- Tester: `tests/test_project_manager_agent.py`
- GitHub Actions: `.github/workflows/project-manager.yml`
- Resultat: `inventory.json` och `report.md` som tidsbegränsad Actions-artifact.

## Vad v1 gör
Read-only inventering med repository-scopad `GITHUB_TOKEN` av issues (separerade från PR), pull requests inklusive merge-status, workflows och 50 senaste workflow-körningarna, senaste commits samt förekomst/blob-SHA för projektets styr- och överlämningsdokument. Rapporten visar öppna uppgifter, öppna PR, misslyckade körningar och saknade styrdokument. Insamlingsfönster och begränsningar redovisas.

## Säkerhetsgränser
- Token har endast `contents: read`, `issues: read`, `pull-requests: read` och `actions: read`.
- Inga POST/PATCH/DELETE-anrop görs.
- Ingen fil, issue, PR, branch, secret eller produktionsresurs ändras av agenten.
- Ingen schemaläggning; inventering körs endast vid manuell `workflow_dispatch`.
- Artifact behålls i 14 dagar.
- Issue-body, secrets och tokens skrivs inte till rapporten.
- Misslyckade körningar är granskningssignaler, inte bevis på källfel.

## Begränsningar i v1
Detta är en deterministisk inventerings- och rapportmotor, ännu inte en språkmodellbaserad AI-analys. Modell/API, secret, kostnadsgräns och återkommande körning kräver separat beslut.

## Körning
GitHub: Actions → Skogskoll AI project manager → Run workflow på `main`. Hämta artifact `skogskoll-project-manager-report`.

Lokal körning kräver en read-only GitHub-token i miljövariabeln `GITHUB_TOKEN`:
```powershell
$env:GITHUB_TOKEN = "github_pat_..."
$env:GITHUB_REPOSITORY = "dahlinrobert-lgtm/Skog"
python scripts/project_manager_agent.py --output-dir project-manager-output
```
Skriv aldrig token i skript, filer, kommandologgar eller issues.

## Nästa steg
Se [v2-plan och acceptanskriterier](PROJECT_MANAGER_AGENT_V2.md). Arbetet delas upp i pagination (v2a), separat beslut om append-only-baslinjelagring (v2b), historisk jämförelse (v2c) och rapportförbättring (v2d). LLM/API och schedule kräver separata beslut. Alla förslag förblir utkast; inga automatiska issue-/PR- eller kodändringar.


## v2a – pagination och täckning

Implementerad och sammanslagen via PR #436 (merge commit `fffad6fd9ccb9af356c89e7c486bdbac7ee53ce5`). Issues och pull requests följer GitHubs `Link`-header tills ingen `rel=next` återstår, med hård gräns 10 sidor à 100 poster per lista. Inventeringen redovisar status, hämtade sidor/poster, sidstorlek, maxgräns och trunkering separat för respektive lista. Om fler sidor finns vid säkerhetsgränsen markeras uttaget `truncated`; API-fel avbryter körningen. Workflow runs och commits är fortsatt separat begränsade. Manuell livekörning #10 passerade 2026-11-19; artifact innehåller `inventory.json` och `report.md`. Se [körningen](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44456582601). Ingen historiklagring eller jämförelse ingår.


## v2b – Git-historik beslutad, persistens ej aktiverad

Användaren har valt separat skyddad Git-branch och indefinite retention (ingen automatisk gallring). Nuvarande Actions-artifact med 14 dagars retention behålls som transport-/granskningsartifact. Inventeringsjobbet förblir read-only; endast separat persistence-jobb kan efter separat godkännande få begränsad `contents: write` till historikbranchen. Före aktivering krävs verifierade syntetiska tester, branchskydd, permissions-isolering, SHA-256, readback och restore. Se [v2b-beslutsunderlaget](PROJECT_MANAGER_AGENT_V2B_STORAGE_DECISION.md). Ingen historikjämförelse eller schedule ingår ännu.


## v2b – teknisk design

Beslutet om Git-historikbranch och indefinite retention är mergat via PR #438. Teknisk design/testmatris finns i [PROJECT_MANAGER_AGENT_V2B_TECHNICAL_DESIGN.md](PROJECT_MANAGER_AGENT_V2B_TECHNICAL_DESIGN.md). Första implementationen ska vara ren Python-logik med syntetiska tester och utan GitHub-skrivning. Persistensworkflow och skrivbehörighet hålls utanför tills verifiering och separat godkännande.


## v2b – offline manifestmodul under verifiering

PR-branch för första kodsteget innehåller `scripts/project_manager_history.py` (validering, deterministiskt manifest, SHA-256 och read-only append-only-kontroll) samt `tests/test_project_manager_history.py`. Befintligt workflow utökat för att köra testerna, med oförändrade read-only-behörigheter. Ingen persistens, GitHub-skrivning, ny branch eller workflow för arkivering ingår.


## v2b – lokal restore-verifiering

Efter verifierad merge av offline manifestmodulen i PR #440 byggs nästa isolerade steg: lokal återställning från manifest och två bytepayloads med kontroll av schema, filuppsättning, filnamn, storlek och SHA-256 före och efter readback. Målkatalog får inte finnas sedan tidigare. Ingen Git/GitHub-åtkomst eller produktionspersistens införs.

## v2b – syntetiskt Git-branch-/commit-test

En ny testgren lägger till ett lokalt Git-test i temporär repository. Det verifierar separat historikbranch, append-commit med endast körningsfiler, oförändrad main, idempotent dubblett och konflikt vid avvikande innehåll. Testet använder ingen remote eller GitHub-skrivning. PR-CI ska verifiera testet; detta är inte ett godkännande eller aktivering av livepersistens.

## v2b – syntetiskt Git-test verifierat

PR #445 är mergad och PR-CI passerade: project-manager tests-job success och Snapshot storage tests-job success (full unittest discovery). Testet validerar en lokal temporär Git-repository, inte GitHub rulesets eller credential-scope. Ingen GitHub-skrivning eller livepersistens ingår.
