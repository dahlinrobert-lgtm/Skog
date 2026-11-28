# Nationellt avverkningsarkiv – lagringsdesign och alternativ

**Datum:** 2026-11-28  
**Status:** Designgranskning – ingen lagrings- eller insamlingsändring aktiverad  
**Branch:** `docs/national-harvest-delta-storage-design`

## 1. Beslutspunkt och nuläge

PR #733 publicerade den första verifierade nationella baslinjen efter den stabila insamlingen i Actions #10. PR #734 dokumenterade storleksrisken. Nuvarande `data/national/` omfattar cirka 387 MiB i aktuell trädyta. `latest.json.gz` och senaste fullständiga snapshot är vardera cirka 99,76 MiB, nära GitHubs hårda gräns på 100 MiB.

Koden i `scripts/monitor_national.py` har redan ett feature-baserat historikformat:

- `create_delta()` jämför stabila feature-ID:n och registrerar `added`, `updated` och `removed`.
- Om en ändrad feature har oförändrad geometri utelämnas geometrin från delta-payloaden.
- `apply_delta()` kan rekonstruera ett komplett tillstånd.
- `read_archive_rows()` spelar upp fullständiga snapshots och deltan.
- Fullständiga kontrollpunkter skapas när senaste fulla snapshot är minst 30 dagar gammal.
- `latest.json.gz` skrivs alltid som en komplett aktuell kopia.

Det finns också ett återanvändbart Azure-mönster i `scripts/viltdata_azure_archive.py` och `.github/workflows/viltdata-azure-archive.yml`: create-only upload, manifest med kontrollsummor, djup audit och restore. Det verktyget är dock källspecifikt och ska inte kopieras blint. Azure-identiteten som det använder har bred Storage Account-scope och delas med andra flöden.

**Arkitekturklassning:** återanvänd befintligt nationellt delta-/checkpoint-format och återanvänd principerna/testmönstren från Viltdata-arkivet. Utöka med ett källspecifikt Azure-arkiv. Skapa inte en parallell snapshotmotor.

## 2. Alternativ

### A. Full snapshot vid varje körning

Varje körning sparar en komplett gzip-komprimerad kopia.

**Fördelar**
- Enkel återställning och felsökning.
- Varje datum är fristående.
- Låg risk för trasiga delta-kedjor.

**Nackdelar**
- Hög lagrings- och överföringskostnad.
- Många nästan identiska kopior.
- Git-historik växer snabbt när stora filer uppdateras.

**Bedömning:** behåll endast som kontrollpunkt/baslinje, inte som enda format.

### B. Full baslinje + förändringsdelta + periodiska kontrollpunkter

En fullständig baslinje följs av förändringsfiler. Varje delta innehåller tillagda, ändrade och borttagna käll-ID:n samt nödvändiga attribut/geometrier. En full kontrollpunkt skapas periodiskt eller när delta blir oproportionerligt stort.

**Fördelar**
- Bygger vidare på befintlig implementation och tester.
- Historiken visar exakt vad som ändrades mellan två kompletta observationer.
- Betydligt mindre lagring när få poster ändras.
- Återställning kan göras från närmaste kontrollpunkt och framåt.

**Nackdelar**
- Återställning kräver korrekt kedjeordning och verifiering av varje länk.
- En saknad eller korrupt deltafil kan bryta rekonstruktionen.
- Borttagningar måste bara accepteras från en fullständig, stabil källinventering.

**Bedömning:** rekommenderat grundformat. Behåll 30 dagar som initial kontrollpunktsregel, men mät faktiska delta-storlekar och lägg till en storleks-/kedjelängdsgrind innan frekvensen ändras.

### C. Innehållsadresserade objekt / deduplicering

Spara varje feature-version som ett separat objekt identifierat av SHA-256. Snapshotmanifest pekar på hashade objekt. Oförändrade features delas mellan snapshots och lagras bara en gång.

**Fördelar**
- Kan minska lagringen ytterligare när samma objekt återkommer i många snapshots.
- Immutable objekt och tydlig integritetskontroll.
- Snapshotmanifest kan vara mycket små.

**Nackdelar**
- Betydligt mer komplex indexering och återställning.
- Kräver referenshantering, orphan-detektering och kontrollerad garbage collection.
- Feature-filer kan bli många små blobbar; transaktions-/listkostnader och driftkomplexitet kan överstiga besparingen.
- Geometri/attribut måste kanoniseras stabilt för att hashning ska bli deterministisk.

**Bedömning:** intressant optimering först när mätningar visar att B inte räcker. Bör inte införas som första migrering.

### D. Databas som enda historikarkiv

Lagra varje feature-version och tidsintervall i en relations-/geodatabas.

**Fördelar**
- Effektiva frågor efter ID, geografi och giltighetstid.
- Bra för kundnära API och analys.

**Nackdelar**
- Databasbackup är inte samma sak som oföränderligt råarkiv.
- Kräver schema-/migrationsförvaltning och drift.
- Kan blanda ihop källans originalobservationer med härledda produktdata.

**Bedömning:** databasen kan senare vara en läsoptimerad/curated vy. Den ska inte ersätta oföränderliga källsnapshots eller manifest.

## 3. Rekommenderad målmodell

**Azure Blob som arkiv för råa nationella observationer; GitHub för kod, tester, dokumentation och små manifest/pekare.**

Föreslagen struktur (namn är designförslag, inte skapade resurser):

```text
skogsstyrelsen-harvest/
  manifests/
    latest.json
    <snapshot-id>.json
  checkpoints/
    <snapshot-id>.json.gz
  deltas/
    <snapshot-id>.json.gz
```

Manifest för varje observation bör innehålla minst:

- `source_id`, produkt/lager och schema-/formatversion
- `snapshot_id`, `run_id`, `checked_at`, källa och exakt scope
- `status=complete` samt evidens för två identiska ID-inventeringar
- antal förväntade/hämtade objekt och diagnostik
- typ: `baseline`, `checkpoint` eller `delta`
- föregående snapshot-ID och bas-/parent-ID
- filnamn, komprimerat byteantal och SHA-256
- resultatets kanoniska tillståndshash efter rekonstruktion
- antal tillagda, ändrade och borttagna poster

`latest.json` är en liten pekare till senaste kompletta snapshot/manifest, inte en ny 100 MiB fullständig kopia. Den ska publiceras atomiskt efter att payload och manifest har skrivits och lästs tillbaka. Historiska payloads ska vara create-only/immutable. Om pekaren versionshanteras ska tidigare pekarversioner kunna granskas.

## 4. Regler för säker delta-historik

1. Ett delta får bara skapas från föregående **kompletta** tillstånd med samma källprodukt, schema och scope.
2. `removed` får endast beräknas efter komplett hämtning, noll saknade/duplicerade/oväntade ID:n och identiska före-/efterinventeringar.
3. `partial`, `failed`, ändrad inventering eller schema-/scopebyte publicerar inget nytt latest-manifest och skapar inget delta.
4. Varje delta anger exakt parent-/base-ID, parent-hash och förväntad resultat-hash.
5. Rekonstruktion validerar att varje parent finns, att ordningen är entydig och att antal/hash efter varje steg stämmer.
6. Saknad eller korrupt länk gör rekonstruktionen till `failed`; systemet får inte hoppa över filen eller tolka den som tom.
7. Kontrollpunkt skapas minst var 30:e dag som initial regel, och tidigare om kedjan når en beslutad maxlängd eller deltafilen blir större än en konfigurerad andel av full snapshot.
8. Första baslinjen är tyst: inga historiska larm genereras.
9. Originaldata och befintliga Git-snapshots/historik bevaras. Ingen Git-historikomskrivning eller radering ingår.

## 5. Lagrings- och kostnadsoptimeringar i rätt ordning

1. **Ta bort den stora redundanta latest-kopian ur framtida Git-publicering** genom att ersätta den med en liten manifestpekare först när alla konsumenter och återställningsvägar verifierats. Befintliga Git-filer lämnas orörda.
2. **Använd befintligt deltaformat** och mät full-/delta-byte per körning. Nuvarande kods format är redan komprimerat gzip; byt inte komprimeringsformat utan benchmark.
3. **Mät ändringsgrad och delta/full-kvot** över flera kompletta körningar. Välj kontrollpunktsintervall från verkliga data, inte antaganden.
4. **Överväg innehållsadresserad feature-lagring** endast om mätning visar betydande återkommande duplicering efter deltaformatet.
5. **Håll råarkiv och sök-/kundvy separata.** GeoParquet eller databas kan användas för analyser och frågor, men inte som ersättning för originalarkivet.

## 6. Föreslagen genomförandeordning och grindar

### Fas 1 – read-only benchmark och rekonstruktionsgranskning

- Granska nuvarande arkivkedja från verkliga gzip-filer, inte bara enhetstester.
- Mät fullstorlek, delta-storlek, ändringsgrad, kompressionsgrad och rekonstruktionstid.
- Testa saknad, korrupt, duplicerad och felordnad delta; verifiera att inget latest-tillstånd publiceras vid fel.
- Kontrollera om `latest.json.gz` har externa konsumenter.
- Dokumentera byte-exakt eller kanonisk hash-jämförelse mellan återställt tillstånd och ursprungligt fullständigt uttag.

### Fas 2 – Azure-förberedelse utan källdata

- Bestäm separat container och separat least-privilege-identitet eller containeravgränsad RBAC. Återanvänd inte den gemensamma Storage Account-scope-identiteten utan ny konsekvensanalys.
- Kör endast syntetiskt write/readback/audit/restore-test.
- Verifiera region, nätverks-/åtkomstpolicy, versionering/soft delete, kostnadsnivå och behörighet.
- Inga riktiga källdata laddas upp innan rättighetsbedömningen för historisk lagring är dokumenterad.

### Fas 3 – parallell pilot

- Låt Git-publiceringen fortsätta oförändrad.
- Arkivera en eller flera kompletta observationer parallellt i Azure först efter rättighets- och behörighetsgrind.
- Kör djup audit och återställ minst en kontrollpunkt samt alla efterföljande deltan.
- Jämför återställt innehåll mot originalets SHA-256/kanoniska tillståndshash.

### Fas 4 – kontrollerad övergång

- Efter godkänd pilot: GitHub behåller liten pekare/manifest och koden; Azure blir auktoritativt råarkiv.
- Stäng inte av Git-publiceringen förrän återställning, audit, konsumenter och drift är verifierade.
- Behåll tidigare Git-snapshots och historik.

## 7. Öppna frågor / ej verifierat

- Storleken på verkliga deltafiler och andelen objekt som ändras per körning är inte mätt här.
- Det är inte verifierat att senaste arkivkedjan går att återställa byte-/hash-exakt från GitHub-binära filer.
- Gzip-binärernas interna innehåll har inte oberoende granskats efter PR #733.
- Azure-container, separat identitet/RBAC, källspecifik upload/readback/restore är inte etablerade.
- Rätt till permanent historisk lagring av exakt Skogsstyrelsen-produkt är inte dokumenterad i denna designgranskning.
- Externa konsumenter av `data/national/latest.json.gz` har ännu inte verifierats fullständigt.

**Nästa konkreta steg:** genomför Fas 1 som en read-only granskning/benchmark av befintliga filer och deltafunktioner. Ändra inte insamlingsschema, publicering, Azure-resurser eller källrättighetsstatus innan resultatet är dokumenterat och granskat.
