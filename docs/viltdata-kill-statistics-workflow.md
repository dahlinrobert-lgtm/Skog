# Viltdata – manuell nationell snapshot-workflow

**Status:** Mergad i `main` (PR #422) och live-verifierad i GitHub Actions 2026-11-18.  
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

Antalet arter, län och förväntade förfrågningar hämtas dynamiskt från källans modell. Den live-verifierade GitHub Actions-körningen 2026-11-18 ([run #44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179)) skapade snapshot `20261118T204420Z` med 49 arter, 21 län och 550/550 lyckade statistikförfrågningar. Dessa tal är utfall från körningen, inte hårdkodade antaganden i workflowen.

## Lagring och säkerhetsgränser

- Rådata skrivs till runnerns temporära katalog och tillhörande workflow-artifact.
- Workflowen har endast `contents: read`; den committar inte data till Git och skriver inte till `main`.
- Den verifierade körningen kontrollerade 552 filer mot manifestets byteantal och SHA-256. Artifact ID `14470426808`, storlek 423 726 byte, artifact-SHA-256 `e7c4076bc5b62a0e05b58df6803b416e57e38b255a34b273efdc3e2678a2f069`, retention till 2026-12-18.
- Artifacten är ett kortlivat gransknings-/felsökningsunderlag, inte ett historiskt arkiv eller en produktionsbackup.
- Om insamlaren returnerar fel eller manifestet inte är komplett misslyckas jobbet. En sådan körning får inte användas som baslinje eller diffunderlag.
- Ofullständiga artifacts kan ändå laddas upp för diagnostik; deras status i manifestet gäller och de ska inte behandlas som kompletta snapshots.
- Azure Blob Storage är inte inkopplat i denna workflow. Permanent lagring och återkommande körning kräver separat verifiering av identitet, container/prefix, skrivbehörighet, integritet och återläsning.

## Historik och förändringsdetektion

Snapshot- och diffskripten bevarar null separat från noll och vägrar jämföra snapshots med ofullständig status eller olika observationstäckning. Den första kompletta snapshoten ska etableras som baslinje utan historiska larm. Larm eller kundvisning ingår inte i denna workflow.

## Rättigheter

Teknisk hämtning från den publika API-tjänsten är inte ett beslut om kommersiell användning, historisk lagring, bearbetning, kundvisning eller vidare distribution. Dessa frågor ska bedömas separat för den exakta statistikprodukten och användningen innan permanent arkivering eller kundexponering.

## Verifierad körning 2026-11-18

- Snapshot-ID: `20261118T204420Z`.
- Manifest: `status=complete`, `complete=true`, 49 arter, 21 län, 550/550 statistikförfrågningar och `errors=[]`.
- Riktade tester: 10/10 godkända.
- Integritetskontroll: 552 filer verifierade mot manifestets byteantal och SHA-256.
- Artifact: [viltdata-kill-statistics-44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179/artifacts/14470426808), ID `14470426808`, retention till 2026-12-18. Artifacten har laddats ned och granskats separat.

## Nästa steg

1. Utred skriftliga produktvillkor och rättigheter för exakt avskjutningsstatistikprodukt: historisk lagring, kommersiell användning, bearbetning, kundvisning och vidare distribution.
2. Utred och verifiera Azure Blob Storage som permanent historikplats: identitet, container/prefix, skrivbehörighet, oföränderliga original, kontrollsummor, återläsning och backup/restore.
3. Först därefter bedöms återkommande schemaläggning. Ingen schemaläggning eller avisering är aktiverad.
