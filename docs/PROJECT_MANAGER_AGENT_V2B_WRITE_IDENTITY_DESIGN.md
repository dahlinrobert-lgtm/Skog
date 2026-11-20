# AI-projektledare v2b – design för separat skrividentitet

**Status:** Förslag för granskning; ingen GitHub App skapad, ingen token eller secret skapad, ingen skrivbehörighet aktiverad.  
**Beslutad lagringsmålbild:** separat Git-branch `project-manager-history`, indefinite retention.  
**Säkerhetskrav:** inventeringsjobbet förblir read-only; persistens aktiveras först efter verifiering och separat uttryckligt godkännande.

## 1. Rekommenderad modell

Använd en separat GitHub App installerad endast på repository `dahlinrobert-lgtm/Skog`, inte en användar-PAT och inte den ordinarie workflow-tokenen. Appen ska ha endast:
- Repository permission: **Contents – Read and write**.
- Metadata: endast den obligatoriska read-åtkomsten.
- Inga permissions för Administration, Actions, Issues, Pull requests, Workflows eller andra resurser.
- Installation begränsad till enbart Skog-repot.

Privat nyckel lagras som GitHub Actions secret med separat namn och exponeras endast i ett dedikerat persistensjobb efter att säkerhetsgrindarna är uppfyllda. Nyckel/token får aldrig skickas till inventeringsjobbet, pull_request-jobb eller kod från forks.

Detta är repository-scope, inte branch-scope: GitHub App-tokenen har fortfarande Contents write i hela Skog-repot. Därför är ruleset på `main` en nödvändig skyddsbarriär, inte något som App-permissionen i sig åstadkommer.

## 2. Hur modellen skyddar main

Verifierat ruleset `Protect main`:
- target `~DEFAULT_BRANCH` (main), active;
- kräver PR före merge;
- blockerar deletion och non-fast-forward/force-push;
- bypass-lista tom, `current_user_can_bypass: never`;
- 0 obligatoriska approvals.

Appen ska inte läggas till i bypass-listan och får inte Administration- eller Pull requests-write. Därmed kan den inte ändra ruleset eller själv mergea PR. En direkt ref-update till main ska nekas av PR-regeln. Detta måste bekräftas med ett kontrollerat syntetiskt negativtest innan någon riktig persistens.

**Viktig begränsning:** PR-krav skyddar inte andra brancher. Contents-write kan skapa och uppdatera andra brancher i samma repo. Appen ska därför installeras endast på Skog och persistensjobbet ska ha fast branch-/path-validering, men kodkontroller är inte en fullständig säkerhetsgräns mot komprometterad workflow-kod.

## 3. Historikbranchens ruleset

Föreslaget ruleset `Protect project-manager-history`:
- target endast exakt branch `project-manager-history`;
- enforcement active;
- blockera deletion;
- blockera non-fast-forward/force-push;
- ingen bypass-aktör;
- tillåt vanliga fast-forward-uppdateringar eftersom append-commits kräver detta;
- kräv inte PR för varje arkiveringscommit.

Aktivera inte `Restrict updates`: det skulle blockera normala append-commits om inte Appen får bypass, och en bred bypass riskerar att även kringgå deletion/force-push-regler. Rulesetet ger skydd mot radering och omskrivning av Git-historiken men kan inte i sig hindra en vanlig commit från att ändra äldre filer. Innehållsmässig append-only måste därför upprätthållas av arkiveringslogiken och verifieras med tester.

## 4. Persistensjobbets säkerhetsgrindar

Om separat aktiveringsbeslut senare ges:
1. Inventeringsjobbet körs med oförändrade read-permissions och producerar artifact.
2. Persistensjobbet hämtar endast artifact från samma betrodda workflow-run.
3. Jobbet kontrollerar repository, workflow/run-ID, source branch, artifactnamn, exakt filuppsättning, coverage och SHA-256.
4. Jobbet hämtar aktuell historikbranch-head och bygger en commit vars parent är just denna head; ingen force push.
5. Målkatalog får inte redan finnas. Identiskt run får endast vara no-op efter byte-för-byte-verifiering; avvikelse ger hårt fel.
6. Committen får endast lägga till en ny `runs/YYYY/MM/DD/<run_id>/` katalog med `inventory.json`, `report.md` och `manifest.json`.
7. Efter push läses filer tillbaka och samtliga checksummor verifieras.
8. Jobbet får aldrig köras från `pull_request`, forks eller obetrodda events. Ingen secret får exponeras till bygg-/testjobb.

## 5. Obligatoriska negativa tester

- App-token kan inte uppdatera `main` direkt.
- App-token kan inte radera `main` eller force-pusha.
- App-token kan inte ändra repository rulesets.
- App-token kan inte läsa/skriva andra repos i organisationen/kontot via installationen.
- Historikbranch tillåter normal fast-forward append.
- Historikbranch nekar force-push och deletion.
- Försök att ändra eller radera en äldre run-katalog avvisas av append-only-modulen.
- Dubblett-run med identiska byte ger no-op; avvikande byte ger fail.
- Artifact mismatch, coverage failure, checksumfel eller readbackfel ger ingen framgångsrapport.
- Restore till tom katalog fungerar och SHA-256 verifieras.

Testa först lokalt med syntetiska data och temporärt Git-repo. GitHub-negativtest ska göras med en separat testbranch och syntetiskt innehåll, aldrig genom att prova destruktiva operationer mot `main`.

## 6. Öppna beslut före skapande

- Bekräfta att repository owner kan skapa och installera en GitHub App med installation begränsad till Skog.
- Fastställ om App-tokenens Contents-write är acceptabel trots repository-scope, med `Protect main` som PR-grind.
- Bekräfta branch ruleset för historiken i UI/API efter skapande av branch.
- Fastställ secret-ägarskap, rotation och återkallelse.
- Genomför hotmodellgranskning av workflow-triggers, artifact-proveniens och untrusted code.

Om kravet är tekniskt garanterad branch-scopad credential snarare än repository-scope med branchskydd, uppfyller GitHub App inte det kravet. Då ska separat repository eller annan lagring med branch-/container-scope-identitet utredas.

## 7. Aktiveringsstatus

**Inte aktiverat.** Detta dokument ger inte tillstånd att skapa App, secret, historikbranch, persistence-workflow eller skriva data. Nästa steg är granskning av designen och därefter en separat, syntetisk implementation utan produktionspersistens.

## 8. Historikbranchens ruleset – verifieringsmatris (2026-11-20)

Föreslagen konfiguration för `project-manager-history` (inte skapad):
- Target endast exakt branch `project-manager-history`; verifiera att rulesetet omfattar exakt en branch och inte `main` eller feature-branches.
- Enforcement `active`.
- Blockera deletion och non-fast-forward (force push).
- Ingen bypass-aktör; `current_user_can_bypass` ska vara `never` där API:t redovisar detta.
- Kräv inte PR för historikbranchen om ett framtida, separat append-jobb ska göra direkt fast-forward-commit. Tillåt vanlig fast-forward push.
- Aktivera inte `Restrict updates`: det skulle stoppa avsedd append och kan skapa behov av bred bypass.

**Verifieringsmatris – först med syntetiska data och separat identitet:**
1. Read-only: lista rulesets och hämta rulesetdetaljer; bekräfta target, enforcement, regler och bypass.
2. Tillåten operation: skapa en ny syntetisk run-katalog på historikbranchen med vanlig fast-forward push; läs tillbaka commit och filer och verifiera SHA-256.
3. Negativ main-test: samma identitet försöker uppdatera `main` direkt; operationen måste nekas av PR-kravet. Ingen PR skapas eller mergeas i testet.
4. Negativ force-push-test: försök flytta historikbranchens ref bakåt/icke-fast-forward; måste nekas.
5. Negativ deletion-test: försök radera historikbranchen; måste nekas.
6. Filnivå: försök återanvända ett run-ID med identiska byte (idempotent no-op) respektive avvikande byte (hard fail utan overwrite).
7. Omfattning: försök skapa/uppdatera en annan branch; dokumentera utfallet. GitHub App Contents-write är repository-scoped och kan inte i sig begränsas till en enda branch.
8. Readback/restore: återläs manifest och payloads, verifiera exakt filuppsättning, storlek och SHA-256; genomför lokal restore till ny tom katalog.

**Säkerhetsgrind:** ingen App, private key, secret, `contents: write`, branch eller persistensworkflow skapas innan administrativt ruleset är granskat och användaren separat godkänt pilotkonfigurationen. Negativa liveoperationer får endast utföras med en dedikerad syntetisk identitet, syntetiskt innehåll och isolerad testgren; aldrig mot riktig data eller genom destruktiva operationer på `main`.

**Kvarvarande arkitekturrisk:** repository-scoped Contents-write ger inte branch-scope. Om kravet är att credential tekniskt bara ska kunna skriva till historikbranchen är separat repository eller lagring med container-/repo-scopad identitet säkrare än GitHub App i samma repo.
