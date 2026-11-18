# Viltdata – Azure Blob Storage

**Status:** Syntetiskt Azure Blob write/readback-test live-verifierat 2026-11-18. Arkivfunktionerna upload/audit/restore är mergade i `main` via PR #427, men ingen riktig Viltdata-snapshot har ännu laddats upp. Två separata kompletta GitHub Actions-snapshots finns för tillfällig granskning. Rättighetsbedömning saknas fortfarande.

## Befintlig Azure-miljö

Skog använder redan GitHub Actions OIDC mot Azure Storage-kontot stskogkolldata. Befintliga workflows använder secrets AZURE_CLIENT_ID, AZURE_TENANT_ID och AZURE_SUBSCRIPTION_ID, azure/login@v2, DefaultAzureCredential och Python-paketen azure-identity samt azure-storage-blob.

Befintliga arkiv ligger i separata containrar. Viltdata ska få en egen container för att inte blanda avskjutningsstatistiken med Kungjort eller polisdata:

- Konto: stskogkolldata
- Azure-loginens CLI-utdata visade `westus2` (behöver stämmas av mot resursens faktiska `location` i Azure; lagringsregistrets Sweden Central-uppgift är ännu inte bekräftad).
- Avsedd container: viltdata-kill-statistics
- Prefix för syntetiska åtkomsttester: smoke-tests/github-actions/<run-id>/attempt-<attempt>/
- Avsett framtida prefix för data: snapshots/<snapshot-id>/

Container `viltdata-kill-statistics` skapades framgångsrikt av workflow #1. Den använda GitHub OIDC-identiteten hade i den körningen tillräcklig behörighet att skapa container samt skriva, läsa och hämta metadata för testblobbar. Exakt RBAC-roll och scope har inte inspekterats separat i Azure Portal.

## Syntetiskt smoke test

Workflow: .github/workflows/viltdata-azure-storage-smoke-test.yml
Skript: scripts/viltdata_azure_storage_smoke_test.py

Workflowen är endast manuell (workflow_dispatch) och använder GitHub OIDC. Den ska:

1. Använda samma befintliga Azure-identitet som de andra Skog-flödena.
2. Skapa containern om den saknas, annars återanvända den.
3. Skriva en liten syntetisk JSON-payload med overwrite=False.
4. Spara ett manifest med körningsidentitet och kontrollsummor, också med create-only-semantik.
5. Läsa tillbaka payload och manifest.
6. Verifiera exakta bytes, byteantal, SHA-256 och Blob-metadata.
7. Ladda upp en kortlivad GitHub Actions-rapport.

Testet skriver inga Viltdata-original eller andra källdata. De syntetiska testobjekten bevaras under sitt unika körningsprefix för spårbarhet; inget befintligt objekt skrivs över eller raderas.

### Live-verifiering 2026-11-18

- Workflow run #1: [44401688469](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44401688469), `completed/success`, event `workflow_dispatch`, head commit `0c6d93da4796257cfed7783c8015b8bb89739a4b`.
- Alla steg passerade: checkout, Python setup, Azure SDK installation, GitHub OIDC login, syntetiskt write/readback, artifact upload.
- `container_created=true`, `payload_created=true`, `manifest_created=true`.
- Container: `viltdata-kill-statistics` i konto `stskogkolldata`.
- Payload: `smoke-tests/github-actions/44401688469/attempt-1/synthetic-payload.json`, 235 bytes.
- Manifest: `smoke-tests/github-actions/44401688469/attempt-1/manifest.json`.
- Payload SHA-256 och readback SHA-256 matchade: `3e5aaf7b3ce1607252a07b3bf1b7959d0c556f805aff3847666aa29a4a325063`; readback omfattade exakt 235 bytes.
- Båda blobbarna lästes tillbaka; manifestet validerades mot payloadens hash, byteantal och blobnamn.
- GitHub Actions-report artifact ID `14474565285`, 467 bytes, SHA-256 `6a44de686d0a1812ff52a71fccb14411f90e902404c1993fe821b7c5338b7530`, retention till 2026-12-18. Artifacten har laddats ned och dess JSON-innehåll granskats.
- Azure Portal → Storage Account `stskogkolldata` → Overview visar `Location: swedencentral` (Sweden Central), verifierat via användarens skärmbild 2026-11-18. Azure CLI-loginens `Region: westus2` avsåg inte Storage Account-resursens location och ska inte användas som regionuppgift.

## Säkerhets- och befordringsgränser

- Ingen schemaläggning är aktiverad.
- Ingen Viltdata-snapshot laddas upp av smoke-testet.
- Inga källregisterstatusar höjs av att autentisering eller en syntetisk skrivning fungerar.
- En lyckad körning visar teknisk åtkomst för just den testade identiteten, containern och operationerna; den bevisar inte juridisk rätt till historisk lagring, kommersiell användning, bearbetning, kundvisning eller vidare distribution.
- Azure Portal → Storage Account → Access control (IAM) → Role assignments visar tjänstens huvudnamn `skogskoll-github-actions` med rollen `Storage Blob Data Contributor` på scope `This resource` (Storage Account-nivå), verifierat via användarens skärmbild 2026-11-18. Rollen ger därmed blobdataåtkomst på kontonivå, inte endast till Viltdata-containern. Samma OIDC-identitet används av flera befintliga Skog-workflows och arkiv (bland annat Kungjort och polisdata); begränsa eller byt inte dess scope utan separat konsekvensanalys. För framtida least-privilege bör en separat identitet eller containeravgränsad roll övervägas.
- Om container creation nekas ska vi inte återanvända en annan källas container. Då behöver container skapas separat eller Azure RBAC justeras av administratören.
- Efter godkänt test ska ett separat, uttryckligen avgränsat snapshot-upload/restore-flöde byggas och verifieras. Första kompletta snapshot ska fortfarande etableras som tyst baslinje utan historiska larm.

## Snapshotarkiv – implementation i main (PR #427)

`main` innehåller nu ett samlat verktyg `scripts/viltdata_azure_archive.py` med tre kommandon:

- `upload`: kräver `status=complete`, `complete=true`, fullständigt request-antal, modell-/länsinventering, samtliga råfiler, exakt filinventering och matchande byteantal/SHA-256. Råfiler och ursprungligt `manifest.json` laddas upp byte för byte under `snapshots/<snapshot-id>/...` med create-only-semantik. En befintlig blob accepteras endast om metadata och bytes överensstämmer.
- `audit`: inventerar samtliga snapshotprefix, läser manifest och varje råblob, kontrollerar manifestreferenser, storlek, SHA-256, Blob-metadata samt orphan-/saknade objekt.
- `restore`: hämtar ett angivet snapshot och skriver originalfilernas relativa sökvägar samt manifest till en ny katalog. Befintlig målkatalog skrivs aldrig över.

Workflow `.github/workflows/viltdata-azure-archive.yml` är mergad i `main`, manuell (`workflow_dispatch`) och har operationerna `upload`, `audit` och `restore`. Upload skapar ett nytt komplett snapshot och har en separat `rights_approved`-spärr (default false) som endast får bekräftas efter skriftlig rättighetsbedömning. Ingen schemaläggning finns. PR-CI [#476](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44404345303) och main-CI [#483](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44405429416) passerade båda med 322 tester, inklusive 8 arkivtester. CI verifierar lokal logik, inte Azure upload/audit/restore live.

## Senaste kompletta GitHub Actions-snapshot (2026-11-18)

- Run [#44408345762](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44408345762), snapshot `20261118T220720Z`, 49 arter, 21 län, 550/550 lyckade statistikförfrågningar, `status=complete`, `complete=true`, `errors=[]`.
- 552 manifeststyrda rå-/metadatafiler verifierades mot byteantal och SHA-256; hela artifact-ZIP innehåller 553 poster inklusive manifest.
- 73 255 datapunkter summerade över de 550 statistikfilerna.
- Artifact `14475804318`, 423 705 byte, ZIP-SHA-256 `${snapshot.zipSha}`, manifest-SHA-256 `${snapshot.manifestSha}`, expires 2026-12-18 22:24:19 UTC.
- De 10 riktade snapshot/diff-testerna passerade. Artifacten har hämtats ned och manifestet granskats separat. Detta är fortfarande temporär GitHub-lagring; inga Viltdata-original har laddats upp till Azure.

## Nästa steg

1. Inhämta skriftligt besked från Svenska Jägareförbundet/Viltdata om historisk lagring/arkivering av exakt `kill`-statistikprodukt samt avsedda användningar. `rights_approved` ska inte aktiveras före dokumenterat besked.
2. Kontrollera Storage Account-resursens faktiska `location` och den använda identitetens RBAC-roll/scope i Azure Portal.
3. När rättighetsbeskedet finns: kör manuell `upload` med `rights_approved=true`, därefter `audit` och `restore` till en ny katalog. Jämför återställd snapshot byte för byte/SHA-256 med ursprungsartefakten.
4. Dokumentera första arkiverade kompletta snapshot som tyst baslinje; skapa inga historiska aviseringar. Ingen schemaläggning innan upload, audit, restore, region/RBAC och rättigheter är verifierade.
