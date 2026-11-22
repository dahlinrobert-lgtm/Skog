# Skogskoll AI-projektledare – v2 plan och acceptanskriterier

**Status:** v2a implementerad, CI- och liveverifierad 2026-11-19  
**Utgångspunkt:** Agent v1 är mergad och liveverifierad via Actions #44413951767.  
**Mandat:** Fortsatt read-only. Användaren godkänner alla projektåtgärder.

## Mål

Göra inventeringen mer fullständig och ge ett tillförlitligt underlag för förändringsanalys mellan körningar utan att tolka begränsade eller ofullständiga uttag som verkliga borttagningar.

## Omfattning v2

### 1. Pagination och täckningsredovisning
- Hämta issues och pull requests sida för sida tills GitHub API inte längre returnerar en nästa sida.
- Använd en tydlig hård säkerhetsgräns för antal sidor och poster per lista.
- Spara antal hämtade sidor, antal poster, sidstorlek, gräns och om uttaget kan vara trunkerat.
- Rapporten ska skilja mellan komplett uttag, uttag vid säkerhetsgräns och tekniskt misslyckad hämtning.
- Vid API-fel ska körningen misslyckas tydligt; ett partiellt resultat får inte presenteras som komplett.

### 2. Historisk jämförelse – separat delsteg
- Jämför två inventeringar med samma schema och repository-identitet.
- Jämför stabila nycklar: issue-/PR-nummer, workflow-ID, workflow-run-ID och dokumentväg/blob-SHA.
- Redovisa nya observationer, ändrade statusar och ändrade dokument-SHA.
- Markera objekt som inte återfinns i den nya inventeringen som **ej observerade i detta uttag**, aldrig automatiskt borttagna eller avslutade.
- Om någon av inventeringarna är trunkerad eller har fel ska frånvarobaserade slutsatser undertryckas.
- Behåll råa inventeringar oförändrade och koppla jämförelsen till båda inventeringarnas körnings-ID, tidpunkt och SHA-256.

### 3. Baslinjehantering och lagring
- Före implementation ska lagringsmodell väljas: tidsbegränsade Actions-artifacts, separat GitHub-branch med manifest eller annan uttryckligen godkänd plats.
- Ingen automatisk commit till main.
- Ingen historik får skrivas över; varje baslinje ska vara append-only och verifierbar.
- Lagringsplats, retention, åtkomst och eventuell exponering av metadata ska dokumenteras.
- Om ingen beständig baslinje finns tillgänglig ska rapporten tydligt säga att historisk jämförelse inte kunde göras.

### 4. Arkitekturpassning och återanvändning – ny obligatorisk grind
Före varje rekommendation om ny funktion, workflow, agent, integration eller lagring ska agenten/projektledaren kontrollera aktuell main för befintliga komponenter, workflows, scheman, register, rapporter och lagringsflöden.
- Klassificera lösningen som återanvänd, utökad, ersatt eller ny separat komponent.
- En ny parallell komponent kräver dokumenterad motivering, överlappskontroll, systemgräns, auktoritativ datakälla, integrationspunkt, säkerhets-/driftkonsekvens och eventuell avvecklingsplan.
- Ge evidenslänkar till de befintliga delarna som granskats; markera ej undersökt som okänt.
- Om underlaget inte räcker ska rekommendationen uttryckligen vara preliminär och ingen ny arkitektur byggas på antagandet att befintligt saknas.
- Föredra minsta ändring som utökar befintlig arkitektur utan att skapa dubbla sanningskällor eller parallell drift.

### 5. Rapport och beslutsunderlag
- Separera fakta, signaler, osäkerheter och rekommenderade åtgärder.
- Varje rekommendation ska ha evidenslänk, prioritet, beroenden och föreslaget nästa steg.
- Misslyckade eller avbrutna workflows är granskningssignaler, inte bevis på fel i en datakälla.
- Agenten får inte själv ändra backlogg, issues, PR, kod, källstatus eller produktionsflöden.

## Acceptanskriterier

1. Tester täcker 0, 1 och flera sidor samt exakt sidstorlek vid säkerhetsgränsen.
2. Tester visar att pagination fortsätter tills API:t signalerar slut eller säkerhetsgränsen nås.
3. Rapporten redovisar täckning och trunkering per lista.
4. API-fel kan inte omvandlas till en tom eller skenbart komplett lista.
5. Historisk jämförelse testar nya, ändrade och ej återfunna objekt.
6. Ej återfunna objekt får aldrig klassas som borttagna/inaktiva.
7. Trunkerad eller ofullständig inventering undertrycker frånvarobaserade slutsatser.
8. Råinventeringar bevaras oförändrade med körnings-ID, tidpunkt och kontrollsumma.
9. CI passerar; manuell workflowkörning producerar verifierbar rapport och artifact.
10. Varje nytt lösningsförslag innehåller en verifierbar återanvändnings- och arkitekturpassning med evidens och motivering för eventuell ny komponent.\n11. Behörigheter förblir read-only. Ingen schedule, LLM/API eller skrivbehörighet införs.

## Föreslagen leveransordning

- **v2a – Pagination:** implementera och testa fullständig sidinsamling, säkerhetsgräns och täckningsmetadata.
- **v2b – Historikmodell:** besluta och dokumentera beständig append-only-baslinje innan kod för lagring byggs.
- **v2c – Jämförelse:** implementera jämförelse först när v2b har en godkänd lagringslösning.
- **v2d – Rapport:** strukturera beslutsunderlag och risk-/osäkerhetsklassning.

## Öppna beslut

- v2b lagringsplats och retention är beslutade 2026-11-19: separat skyddad Git-branch och indefinite retention. Se [v2b-beslutsunderlaget](PROJECT_MANAGER_AGENT_V2B_STORAGE_DECISION.md).
- Hur ska jämförelsen i v2c initieras: manuellt med vald baslinje eller automatiskt efter separat godkännande? Detta är fortfarande öppet.

## Genomförandestatus v2a (2026-11-19)

PR #436 är sammanslagen i `main` (merge commit `fffad6fd9ccb9af356c89e7c486bdbac7ee53ce5`). Riktade tester och bred Snapshot storage tests passerade efter merge. Manuell workflowkörning #10 passerade och producerade artifact med `inventory.json` och `report.md`. Issues-endpointen gav 436 poster på 5 sidor; efter filtrering av pull-requestposter återstod 11 issues. PR-endpointen gav 425 poster på 5 sidor. Båda uttagen markerades `complete`, utan trunkering. Artifact SHA-256 `de613fbcc54d2f1567f5c8f5bab75b65a09b1e4a797d9dfb0e4a30cfa85c6dbb`, retention till 2026-12-03 04:12:41 UTC. Övriga v2-delar är inte implementerade.


## v2b – beslutsunderlag

Lagringsalternativ, integritetskrav, retention, åtkomst och rekommenderad stegvis pilot beskrivs i [v2b-beslutsunderlaget](PROJECT_MANAGER_AGENT_V2B_STORAGE_DECISION.md). Inget alternativ är godkänt och ingen beständig lagring är implementerad. v2c får inte starta före uttryckligt lagringsbeslut och verifierad persistens.


## v2b – användarbeslut 2026-11-19

Valt: separat skyddad Git-branch med indefinite retention (ingen automatisk gallring). Beslutet godkänner inte aktivering av persistens. Implementationsplanen är: (1) specificera katalog- och manifestformat, (2) bygga syntetiska tester för append-only/idempotens/fel/coverage/checksumma/restore, (3) verifiera branch ruleset och att write-behörighet endast finns i separat persistence-jobb och inte kan skriva till `main`, (4) genomföra syntetisk readback/restore-pilot, (5) presentera evidens och diff för separat godkännande. Först därefter får riktiga inventeringar arkiveras. Trunkerade körningar får lagras märkta `incomplete`, aldrig jämföras.
