# AI-projektledare v2b – beslutsunderlag för historiklagring

**Status:** Beslutsunderlag – inget lagringsval är godkänt eller implementerat  
**Datum:** 2026-11-19  
**Omfattning:** Endast projektledaragentens inventeringsmetadata (inte Skogs källdata eller kunddata)

## 1. Utgångspunkt – verifierat nuläge

- Agent v1 och v2a är mergade och liveverifierade.
- Manuell körning #10 den 2026-11-19 producerade `inventory.json` och `report.md`; båda issues- och PR-listorna var kompletta och opaginerade/trunkerade var inte aktuellt.
- Nuvarande workflow laddar upp `skogskoll-project-manager-report` som GitHub Actions-artifact med 14 dagars retention.
- Inventeringen är read-only: GitHub API-behörigheterna är `contents: read`, `issues: read`, `pull-requests: read` och `actions: read`. Ingen beständig historik eller historisk jämförelse finns.
- Inventeringen innehåller metadata som är användbar för projektledning: issue-/PR-nummer, titlar, status, etiketter, tidsstämplar, URL:er, workflowresultat, commitmetadata och dokumentens blob-SHA. Issue- och PR-beskrivningar exporteras inte.

Kortvariga Actions-artifacts är användbara för felsökning och manuell granskning, men de är inte en långsiktig historikmodell.

## 2. Krav som måste gälla oavsett lagringsval

1. **Append-only:** en redan sparad körning får inte ändras eller ersättas av en senare körning.
2. **Unik identitet:** varje inventering får ett unikt `run_id`, UTC-tid, repository, branch och commit-SHA.
3. **Integritet:** spara SHA-256 för exakt `inventory.json` och `report.md`, samt manifest som binder ihop filer och körning.
4. **Kompletthetsgrind:** historisk jämförelse får endast använda listor med `status=complete`. Trunkerade listor kan arkiveras som observationer men får inte skapa slutsatser om frånvaro.
5. **Fail closed:** API-fel, saknad fil, felaktig JSON eller checksummefel ska stoppa arkiveringen. Ett fel får aldrig skapa en tom baslinje.
6. **Separera insamling och skrivning:** den nuvarande read-only-inventeringen ska behålla sina läsbehörigheter. Eventuell skrivbehörighet ska ligga i ett separat, tydligt avgränsat steg.
7. **Ingen automatisk borttagning:** saknade objekt mellan körningar är endast en förändringssignal. De ska inte markeras som borttagna/inaktiva utan komplett jämförbar täckning och separat regel.
8. **Sekretess:** lagra inte issue-/PR-body, kommentarer, personuppgifter, hemligheter eller token. Begränsa åtkomst till projektets behöriga underhållare.
9. **Återställbarhet:** verifiera att en arkiverad körning kan hämtas, avkodas och checksummeverifieras.
10. **Spårbar retention:** retention ska vara uttrycklig och dokumenterad; ingen automatisk rensning får införas innan retention är beslutad.

## 3. Alternativ

### A. Separat, skyddad Git-branch i Skog-repot

**Upplägg**
- En separat branch, exempelvis `project-manager-history`, innehåller en katalog per UTC-körning, exempelvis `runs/2026/11/19/<run_id>/`.
- Varje katalog innehåller `inventory.json`, `report.md` och `manifest.json` med SHA-256, körningsmetadata och täckningsstatus.
- En separat persistence-workflow tar emot och verifierar artifact från read-only-körningen och gör en ny commit endast om körningskatalogen inte redan finns.
- Branch ruleset ska förhindra force-push och branch deletion. Persistence-jobbet får `contents: write`; inventeringsjobbet förblir read-only.

**Fördelar**
- Låg driftkomplexitet; ingen ny Azure-resurs eller extern datatjänst.
- Git-commit-historik ger tydlig proveniens och enkel diff mellan körningar.
- Samma privata repository och befintliga GitHub-behörighetsmodell.

**Nackdelar/risker**
- Kräver en separat skrivväg och noggrann separation av job permissions; en felaktig workflow kan annars få för bred skrivförmåga.
- Git är inte ett WORM-arkiv: administratörer kan ändra regler eller radera branch. Append-only är därför en skyddad processregel, inte absolut oföränderlighet.
- Inventeringsmetadata och titlar blir kvar i Git-historiken och kan inte enkelt gallras selektivt.
- Repo-storleken växer med varje inventering; JSON kan komprimeras, men Git-historik kräver fortsatt storlekskontroll.

### B. Azure Blob Storage i befintligt Storage Account

**Upplägg**
- Separat container, exempelvis `project-manager-history`, i Storage Account `stskogkolldata` (region `swedencentral` enligt tidigare Portal-verifiering).
- Blobnamn partitioneras per datum och `run_id`; manifest och SHA-256 sparas tillsammans med inventering och rapport.
- GitHub Actions autentiserar via OIDC. Skrivning sker i separat job/workflow, medan insamlingsjobbet behåller read-only GitHub-behörighet.

**Fördelar**
- Passar projektets dokumenterade princip att Azure används för automatiserade historiska arkiv.
- Skalar bättre än Git för växande körningshistorik och kan ge separat retention, versionering och återställning.
- Dataarkivet separeras från kod och styrdokument.

**Nackdelar/risker**
- Kräver en ny, avgränsad identitet/federerad credential och RBAC på container-scope.
- Den befintliga OIDC-identiteten `skogskoll-github-actions` har enligt dokumentationen `Storage Blob Data Contributor` på hela Storage Account-scope och delas av flera flöden. Den ska **inte** återanvändas för detta ändamål utan separat konsekvensbedömning och least-privilege-lösning.
- Kräver verifiering av upload, readback, checksumma, retention och återställning.
- Immutable/WORM-policy kan vara svår eller omöjlig att återkalla när den väl låsts; får inte aktiveras utan separat uttryckligt beslut.

### C. Endast GitHub Actions-artifacts

**Upplägg:** fortsätta med dagens artifact, eventuellt ändra retention.

**Fördelar:** ingen ny skrivbehörighet eller lagringsarkitektur.

**Nackdelar:** retention är tidsbegränsad; ingen robust beständig historik efter utgångsdatum. Det räcker inte för v2c historisk jämförelse över längre tid.

**Bedömning:** behåll som transport-/granskningsartifact, inte som enda beständiga historik.

## 4. Rekommenderad väg – stegvis och utan att låsa ett oåterkalleligt val

**Rekommendation för beslut:** välj alternativ A för en första, avgränsad historikpilot om målet är att komma vidare med minsta möjliga nya infrastruktur. Det ger en lättgranskad lösning för små mängder projektmetadata. Alternativ B är lämpligare om historiken ska bli långlivad, växa eller få formella retention-/immutabilitykrav; då ska Azure väljas först efter att en separat container-scope-identitet har etablerats.

Rekommendationen är inte ett godkännande. Ingen branch, skrivbehörighet, persistence-workflow eller historikdata ska skapas innan användaren har valt alternativ och godkänt retention.

Föreslagen leveransordning efter beslut:
1. Besluta lagringsplats och åtkomstmodell.
2. Besluta retention och om körningar ska sparas även när en lista är trunkerad (rekommendation: ja, men uttryckligen märkta `incomplete` och spärrade från jämförelse).
3. Implementera separat persistensgräns; read-only-inventeringen ska inte få skrivbehörighet.
4. Testa append-only, idempotens, felhantering, checksumma, kompletthetsgrind och restore med syntetiska inventeringar.
5. Genomför en manuell livepilot och verifiera artifact/arkivobjekt.
6. Först därefter utforma v2c jämförelseregler.

## 5. Beslut som behövs

| Beslut | Rekommenderat utgångsläge | Kräver godkännande |
|---|---|---|
| Lagringsplats | A: separat skyddad Git-branch för första pilot | Ja |
| Retention | 5 år som diskussionsförslag; inte implementerat | Ja |
| Trunkerade inventeringar | Arkivera med `incomplete`-markering, aldrig jämförbara | Ja |
| Skrivbehörighet | Separat persistence-jobb; ingen write i read-only-jobbet | Ja |
| WORM/immutability | Avstå i pilot; utred senare vid behov | Ja |
| Körfrekvens | Fortsatt manuell workflow; ingen schedule | Ja, separat beslut |

## 6. Utanför omfattningen

- Ingen LLM/API, automatisk prioritering eller autonom projektåtgärd.
- Ingen schemaläggning.
- Ingen issue-/PR-/kodändring av agenten.
- Ingen automatisk slutsats om borttagning, inaktivitet eller avslut.
- Ingen koppling till Skogskolls kunddata eller kundaviseringar.
- Ingen Azure- eller GitHub-skrivning i detta beslutsunderlag.
