# Viltdata – manuell nationell snapshot-workflow

**Status:** Implementerad på arbetsbranch; ännu inte live-verifierad i GitHub Actions.  
**Workflow:** `.github/workflows/viltdata-kill-statistics-manual.yml`  
**Insamlare:** `scripts/viltdata_kill_statistics_snapshot.py`  
**Tester:** `tests/test_viltdata_kill_statistics_snapshot.py` och `tests/test_viltdata_kill_statistics_diff.py`

## Syfte och avgränsning

Workflowen ger en kontrollerad manuell körning av Viltdata.se:s publika avskjutningsstatistik (report type `kill`). Den är inte en NVR-insamling och statistiken får inte beskrivas som populationsinventering eller enskilda djurobservationer.

Workflowen kan endast startas manuellt med `workflow_dispatch`. Ingen cron/schedule är aktiverad.

## Körning

Workflowen:

1. Checkar ut repot och använder Python 3.12.
2. kompilerar snapshot- och diffskripten,
3. kör de riktade Viltdata-testerna,
4. kör snapshotinsamlaren utan `--max-counties` eller `--max-species`, alltså full omfattning enligt källans aktuella modell,
5. använder batchstorlek 2 arter och 1 sekunds väntan mellan statistikförfrågningar,
6. kräver `status=complete`, `complete=true` och att samtliga förväntade statistikförfrågningar lyckats,
7. kontrollerar att varje råfil i manifestet finns och matchar angivet byteantal och SHA-256,
8. laddar upp den aktuella körningens katalog som GitHub Actions-artifact med 30 dagars retention.

Antalet arter, län och förväntade förfrågningar hämtas dynamiskt från källans modell. Den manuellt verifierade lokala körningen 2026-11-13 omfattade 49 arter, 21 län och 550 statistikförfrågningar. Dessa tal är ett tidigare utfall, inte hårdkodade antaganden i workflowen.

## Lagring och säkerhetsgränser

- Rådata skrivs till runnerns temporära katalog och tillhörande workflow-artifact.
- Workflowen har endast `contents: read`; den committar inte data till Git och skriver inte till `main`.
- Artifacten är ett kortlivat gransknings-/felsökningsunderlag, inte ett historiskt arkiv eller en produktionsbackup.
- Om insamlaren returnerar fel eller manifestet inte är komplett misslyckas jobbet. En sådan körning får inte användas som baslinje eller diffunderlag.
- Ofullständiga artifacts kan ändå laddas upp för diagnostik; deras status i manifestet gäller och de ska inte behandlas som kompletta snapshots.
- Azure Blob Storage är inte inkopplat i denna workflow. Permanent lagring och återkommande körning kräver separat verifiering av identitet, container/prefix, skrivbehörighet, integritet och återläsning.

## Historik och förändringsdetektion

Snapshot- och diffskripten bevarar null separat från noll och vägrar jämföra snapshots med ofullständig status eller olika observationstäckning. Den första kompletta snapshoten ska etableras som baslinje utan historiska larm. Larm eller kundvisning ingår inte i denna workflow.

## Rättigheter

Teknisk hämtning från den publika API-tjänsten är inte ett beslut om kommersiell användning, historisk lagring, bearbetning, kundvisning eller vidare distribution. Dessa frågor ska bedömas separat för den exakta statistikprodukten och användningen innan permanent arkivering eller kundexponering.

## Nästa steg

1. Kör workflowen manuellt från GitHub Actions.
2. Granska körlogg, manifest, täckning, råfiler och SHA-256-kontroller.
3. Bekräfta att artifacten kan laddas ned och återläsas.
4. Utred och verifiera Azure Blob Storage som permanent historikplats.
5. Registrera Viltdata i källregistret med försiktiga statusar och konkret evidens.
6. Först därefter bedöms daglig schemaläggning. Ingen schemaläggning eller avisering ska aktiveras automatiskt genom denna implementation.
