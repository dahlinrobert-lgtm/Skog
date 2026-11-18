# Viltdata – Azure Blob Storage

**Status:** Förberedd för isolerat syntetiskt test; Azure-skrivning och återläsning för Viltdata är ännu inte live-verifierade.

## Befintlig Azure-miljö

Skog använder redan GitHub Actions OIDC mot Azure Storage-kontot stskogkolldata. Befintliga workflows använder secrets AZURE_CLIENT_ID, AZURE_TENANT_ID och AZURE_SUBSCRIPTION_ID, azure/login@v2, DefaultAzureCredential och Python-paketen azure-identity samt azure-storage-blob.

Befintliga arkiv ligger i separata containrar. Viltdata ska få en egen container för att inte blanda avskjutningsstatistiken med Kungjort eller polisdata:

- Konto: stskogkolldata
- Region: Sweden Central (enligt befintligt lagringsregister)
- Avsedd container: viltdata-kill-statistics
- Prefix för syntetiska åtkomsttester: smoke-tests/github-actions/<run-id>/attempt-<attempt>/
- Avsett framtida prefix för data: snapshots/<snapshot-id>/

Container och prefix är målkonfiguration, inte bevis på att containern redan finns eller att behörighet är tilldelad.

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

## Säkerhets- och befordringsgränser

- Ingen schemaläggning är aktiverad.
- Ingen Viltdata-snapshot laddas upp av smoke-testet.
- Inga källregisterstatusar höjs av att autentisering eller en syntetisk skrivning fungerar.
- En lyckad körning visar teknisk åtkomst för just den testade identiteten, containern och operationerna; den bevisar inte juridisk rätt till historisk lagring, kommersiell användning, bearbetning, kundvisning eller vidare distribution.
- Om container creation nekas ska vi inte återanvända en annan källas container. Då behöver container skapas separat eller Azure RBAC justeras av administratören.
- Efter godkänt test ska ett separat, uttryckligen avgränsat snapshot-upload/restore-flöde byggas och verifieras. Första kompletta snapshot ska fortfarande etableras som tyst baslinje utan historiska larm.

## Nästa steg

1. Merg:a smoke-testförslaget efter kod- och CI-granskning.
2. Starta workflowen manuellt och granska Azure-login, container creation/existence, write/readback, metadata och SHA-256.
3. Kontrollera faktisk region, containerinställningar och RBAC-scope i Azure Portal.
4. Bygg därefter separat permanent snapshotarkivering med återläsning och backup/retention.
5. Bedöm rättighetsfrågorna separat innan historisk arkivering eller kundanvändning.
