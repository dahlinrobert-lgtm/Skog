# Skogskoll – inventering av snapshots och observationshistorik

**Inventeringsdatum:** 2026-11-22  
**Bas:** GitHub `main` efter merge av PR #484 och #486  
**Status:** Kod- och filinventering. Ingen databasanslutning eller produktionsdata har ändrats.

## 1. Sammanfattning

Skog-repot har redan flera användbara historikmekanismer, men de är käll-/flödesspecifika. Det finns ännu ingen gemensam persistensmodell som direkt motsvarar hela snapshot-envelope i `SKOGSKOLL_CHANGE_FEED_CONTRACT.md`.

Den viktigaste befintliga byggstenen för Skogskoll är den workerstyrda observationsmodellen i `skogskoll/db`. Den har stabil identitet, SHA-256-innehållshash, append-only-historik, körningsposter och en atomisk sidcommit. Den är dock idag implementerad för en enda Skogsstyrelsen-källa och saknar flera uttryckliga snapshotfält.

## 2. Inventerade byggstenar

### 2.1 Skogskolls relationsmodell

Källor: `skogskoll/db/schema.sql`, migrations 002–004, `src/observation-core.mjs`, `src/scan-worker-core.mjs`, `src/supabase-adapters.mjs`.

| Befintlig tabell | Nuvarande roll | Relevans för change-feed |
|---|---|---|
| `source_observations` | Aktuellt tillstånd, unik nyckel `source + source_id`, hash, geometri, attribut, first/last seen och last_run_id | Bra current-state-lager; inte en daterad snapshot i sig |
| `source_observation_history` | Append-only rader med observed_at, event_type, hash, attribut/geometri och poll_run_id | Närmast befintlig händelsehistorik |
| `poll_runs` | Körnings-ID, källa, start/slut, status, antal och diagnostics | Kan bära run-proveniens; saknar uttryckliga produkt-/lager-/täckningsfält |
| `scan_sessions` | Återupptagbar paginerad scan med total, offset, antal, status och diagnostics | Bevisar scanens pagineringsförlopp, inte fullständigt snapshot-envelope |
| `scan_seen_ids` | Unika käll-ID:n per scan och offset | Integritetskontroll för dubbla ID:n och fullständig ID-täckning |

Migrationskedjan har en tydlig säkerhetsgräns: worker-tabellerna saknar publika RLS-policyer. Migration 003 skriver observationer, historik, sedda ID:n och checkpoint atomiskt per sida. `skogskoll_finish_scan` kräver att offset, hämtat antal och antal unika sedda ID:n motsvarar källans rapporterade total. Ofullständiga/failed scans markeras separat och funktionen gör ingen inaktivering av poster som inte setts.

### 2.2 Nuvarande identitet och händelser

`skogskoll/src/observation-core.mjs` definierar idag:

- `SOURCE_ID = skogsstyrelsen:avverkningsanmalan`.
- Stabilt ID hämtas från GeoJSON id eller OBJECTID-varianter.
- `contentHash` SHA-256-hashar kanoniserade properties och geometry.
- `normalizeFeature` håller `observed_at` separat från källfältet `Inkomdatum`.
- Observationer klassas som insert/first_seen, update/changed eller touch/unchanged.

I SQL-lagret klassas första körningen med mode `baseline` som `baseline`, medan senare nya ID:n blir `inserted`. Endast ändringar och baslinje/insert-händelser skrivs till historiktabellen; unchanged uppdaterar current state/last_seen men skapar ingen historikrad.

Det finns därmed en viktig mappningsskillnad mot det nya kontraktet: kontraktets `first_seen` är en kundhändelse efter baslinjen, medan befintlig historik använder `baseline` och `inserted`. Dessa får inte slås ihop utan att bevara skillnaden mellan första baslinjefångst och senare upptäckt.

### 2.3 Filbaserade snapshotformat i repot

Inventering av spårade filer på `main`:

| Område | Antal filer | Format / mekanism |
|---|---:|---|
| `data/snapshots/YYYYMMDDTHHMMSSZ.json` | 380 | Planerade avverkningsanmälningar, fulla snapshots och `feature-delta-v1` |
| `data/snapshots/completed_*.geojson.gz` | 377 | Utförda avverkningar, GeoJSON gzip och `completed-feature-delta-v1` |
| `data/samrad_snapshots/*.json.gz` | 22 | Samrådssnapshots |
| `data/lansstyrelsen-diary/snapshots/**/*.jsonl` | 36 | Diarie-/ärendeuttag per körning/period |
| `data/trafikverket/snapshots/2026-11-09/manifest.json` | 1 manifest i den inventerade pilotkatalogen | Manifest med lager, identitetsfält, antal, filreferens, storlek och SHA-256 |

Därtill finns separata historik-/arkivflöden för bland annat kungjort, polis, livsmiljöåtgärder, återvätning, brandytor, NVR och Viltdata. De använder egna manifest, JSONL-format, Azure-arkiv eller run-scoped artefakter. Den här inventeringen har inte hämtat eller validerat alla externa Azure-objekt eller alla historiska artefakter; filantal avser enbart spårade filer i GitHub-trädet.

#### Planerade avverkningsanmälningar

`scripts/snapshot_store.py` skriver fulla checkpoints eller `feature-delta-v1`. Deltaformatet har basfil, added/updated/removed-ID:n och payloads. Läsaren rekonstruerar en delta mot deklarerad bas och hoppar över delta vars bas saknas/inte kan läsas. Endast snapshots med lyckad källstatus och features-lista läses som lyckade.

#### Utförda avverkningar

`scripts/completed_snapshot_store.py` skriver gzip-komprimerade GeoJSON fulla checkpoints eller `completed-feature-delta-v1`. Den kräver `query_scope_sha256`; scope-byte tvingar full checkpoint. Läsaren hoppar över delta vars bas saknas eller vars scope-hash inte matchar.

**Viktig distinktion:** `removed` i dessa deltaformat är en intern instruktion för att rekonstruera den aktuella arkivbilden. Det är inte i sig ett verifierat källbesked om återkallelse eller ett kundevent. Det får inte direkt mappas till `removed` i Skogskolls flöde.

#### Trafikverkets manifest

Manifestet för 2026-11-09 visar en rikare struktur med snapshotdatum, skapandetid, geografiskt pilotområde, tjänst/lager, geometri-/identitetsfält, förväntat antal, hämtat antal, filväg, byte och SHA-256. Det är ett användbart exempel på leveransmanifest, men täckningen är en Gräsmyr-pilot/envelope och varje lager har egen täcknings-/antalssituation. Det kan inte utan vidare behandlas som nationell eller kundgodkänd täckning.

## 3. Gap mot change-feed-kontraktet

| Kontraktsfält / krav | Befintligt stöd | Bedömning |
|---|---|---|
| `snapshot_id` | Filnamn/run-ID förekommer i olika format; inget gemensamt ID i Skogskolls DB | Saknas som gemensam explicit identitet |
| `run_id` | `poll_runs.id`, workflow run IDs och källspecifika körningsnamn | Finns i olika domäner; behöver normaliserad referens |
| `source` | Ja | Finns |
| `product` / `layer` | Vissa manifest har lager; Skogskolls poll_runs har bara source | Saknas i relationsmodellen |
| `captured_at` | `observed_at`, `checked_at`, `created_at_utc` eller filnamnstid beroende på flöde | Semantiken varierar; måste mappas explicit |
| `status` / fullständighet | Scan status + antal/seen-ID; filformatens query-status; manifestantal | Finns källspecifikt, inte normaliserat |
| `coverage_key` | `snapshot_scope`, `query_scope_sha256`, geografiskt envelope eller urval | Finns i vissa flöden, inte gemensamt |
| `schema_version` | Formatversioner för deltas; vissa manifestversioner | Delvis |
| `identity_version` | Identitetsfält dokumenteras i vissa manifest; ingen gemensam version | Saknas |
| `content_hash` | Finns per observation och SHA-256 per arkivfil/lager | Finns, men på olika nivåer |
| `customer_visibility` + `rights_evidence_ref` | Källregistret har rättighetsstatus; ingen koppling i snapshot-/historiktabellerna | Saknas i persistensgränsen |
| Tidsfält för källhändelse/publicering/detektion | `source_received_at`, `observed_at`, källspecifika datum | Delvis; publiceringsdatum är inte generellt modellerat |
| Frånvaro-/bortfallsgrind | Scan completion och ingen inaktiv reconciliation i nuvarande worker | God grund, men måste fortsätta vara källspecifik och fail-closed |

## 4. Slutsatser och rekommenderad integrationsväg

1. **Återanvänd `poll_runs` som befintlig körningsidentitet för Skogskolls worker**, inte skapa en parallell generisk run-tabell utan tydligt behov. Lägg inte alla snapshotfält i `diagnostics` som enda sanningskälla.
2. **Inför ett separat, oföränderligt snapshot-/leveransregister först när mappningen är specificerad.** Det kan referera till `poll_runs.id` där en DB-scan finns, men måste även kunna representera filbaserade leveranser som inte har Supabase poll_run.
3. **Behåll `source_observations` som current state och `source_observation_history` som append-only observation history.** Lägg inte en andra parallell objekthistorik ovanpå dessa.
4. **Håll snapshot-envelope skilt från event-envelope.** En snapshot är en verifierad leverans/täckning; en händelse är en slutsats från två jämförbara leveranser och en godkänd rättighetsgrind.
5. **Mappa `baseline` separat från `first_seen`.** Baslinjen fyller historik tyst; nya poster efter baslinje kan ge first_seen först efter att jämförbarhet och rättigheter godkänts.
6. **Översätt aldrig delta-`removed` direkt till kundhändelse.** Det kan vara en skillnad mellan två arkivbilder eller en effekt av täckning/urval. Kräv separat källspecifik tombstone-/återkallelseevidens.
7. **Börja med en adapter för Skogsstyrelsens avverkningsanmälningar**, eftersom befintlig Skogskoll worker, stabila ID:n, hash, scan ledger och atomisk historik redan finns. Men kundvisningsgrinden för exakt lager är fortfarande inte godkänd enligt källstatusrapporten.
8. **Håll andra arkiv som separata adapters** tills deras täckning, manifest, identitetsstabilitet och rättigheter har verifierats. Trafikverkets Gräsmyr-manifest är ett bra manifestexempel, inte en automatisk kunddatakälla.

## 5. Föreslagna nästa arbetssteg

- [ ] Läs faktiska snapshot-/run-diagnostikexempel för Skogsstyrelsens avverkningsanmälningar och kontrollera om samma täckningsscope kan bevisas över minst två kompletta körningar.
- [ ] Definiera en adapter-mappning från befintlig `poll_runs` + `scan_sessions` + manifest till snapshot-envelope, inklusive statusöversättning och coverage key.
- [ ] Lägg till kontraktstester för adapter-mappningen, inklusive statusar success/warning/failed, ändrad total, ändrad täckning och saknad evidens.
- [ ] Först därefter ta fram en separat migrations-/API-PR. Ingen produktionsmigration eller livefeed i inventeringssteget.
- [ ] Uppdatera källstatusrapporten först när källregister och rättighetsunderlag faktiskt har ändrats; inventeringen i sig ger inget nytt kundgodkännande.

## 6. Säkerhets- och verifieringsgränser

- Den här rapporten bygger på kod, SQL och spårade filer i GitHub `main`; den har inte anslutit till Supabase eller hämtat alla privata molnarkiv.
- CI-status från PR #484 verifierades separat. Den här inventeringen har ännu inte ett eget teststeg eftersom den endast dokumenterar befintlig implementation.
- Ingen databas, snapshot, originalfil, källstatus, kundfeed eller avisering har ändrats eller aktiverats.
- Källstatusrapporten kontrollerad 2026-11-18 anger **0** uttryckligen godkända källor för kundvisning. Den grinden kvarstår.

## 7. Adaptersteg – worker till snapshot-envelope (2026-11-23)

En ren, fristående adapter har lagts till i `skogskoll/src/snapshot-envelope-adapter.mjs`. Den mappar befintliga `poll_runs`- och `scan_sessions`-rader till det neutrala snapshot-envelope-kontraktet utan att skapa en ny tabell, starta ingestion eller skriva data.

- `snapshot_id` byggs av befintligt poll-run-ID och scan-session-ID; båda behålls i proveniensen.
- `source`, produkt, lager, täckningsnyckel, schema- och identitetsversion mappas separat. Produkt/lager/scope/version måste lämnas som explicit metadata eftersom dessa fält saknas i nuvarande DB-tabeller; adaptern gissar inte.
- `complete` kräver både `scan_sessions.status=complete` och `poll_runs.status=success`, lika källidentitet, fullständigt source_count/fetched_count/next_offset, poll-run fetched_count samt båda sluttiderna.
- `running`/`warning`/räkningsavvikelse blir `partial`; failed/abandoned blir `failed`.
- Kundvisning defaultar till `not_assessed`; ingen rättighet eller evidens skapas av adaptern.
- Adaptern returnerar diagnostik och valideringsfel. Den persisterar, publicerar eller skapar inga kundhändelser.

Sex kontraktstester har lagts till för komplett scan, partiell scan, failed, räkningsavvikelse, saknad coverage metadata och källmismatch. CI-verifiering inväntas i PR. Ingen SQL-migration, live-databasanslutning, kundfeed eller avisering ingår.


## 8. ArcGIS-worker – metadataidentitet från faktisk källkonfiguration (under PR)

Den befintliga `createArcGisSource` får en read-only metod `getSnapshotMetadata()` som återanvänder samma endpoint och lagerdefinition som hämtningen.

| Envelope-fält | Härledning | Viktig avgränsning |
|---|---|---|
| `product` | Explicit worker-konfiguration: `harvest_notifications` | Produktklassning är konfiguration, inte ett fält från ArcGIS |
| `endpoint` | Normaliserad konfigurerad layer-URL | Ändrad endpoint ger ny jämförelsebas |
| `layer` | Layer-numret i `MapServer/{id}` eller `FeatureServer/{id}` | Saknat layer-ID stoppar metadataframtagning |
| `query_definition` | Samma where/outFields/geometry/SR/format/OID-sortering som feature-queryn | Offset och sidstorlek utelämnas; de ändrar inte queryns logiska scope |
| `coverage_key` | `unfiltered-layer-query-v1` | Betyder ofiltrerad lagerquery, inte nationell geografisk täckning |
| `schema_version` | SHA-256 av kanoniserade fältnamn, typer, längder, nullability, domäner, geometri-typ/dimensioner och spatialreferens | Nytt fält/schema ger ny version |
| `identity_version` | ArcGIS OID-fältnamn + strängnormalisering till GeoJSON feature ID | Bevisar inte långsiktig OID-stabilitet |

Metadataresultatet behåller `customer_visibility=not_assessed` och `rights_evidence_ref=null`. Detta är en metadatafunktion, inte ett fullständighetsbevis eller en snapshot. Den är ännu inte kopplad till worker-run-persistens/adaptern. PR #537:s customer UI-test passerade 78/78 tester (run 45078075239). Read-only source-probe passerade (run 45078075046) med 300/300 unika ID:n och noll dubbletter/saknade ID:n, men var avsiktligt begränsad och inte en komplett scan. Den nya metadatafunktionen har ännu inte verifierats mot live ArcGIS-metadata. Ingen migration eller live-ingestion ingår.

## 9. Persistens – ArcGIS worker till oföränderligt snapshotregister (PR under granskning)

Integrationsförslaget återanvänder poll_runs och scan_sessions som körningsidentiteter och lägger till ett separat register för färdiga snapshot-envelopes.

- Metadata från createArcGisSource.getSnapshotMetadata() sparas i båda körningsposternas diagnostics vid atomisk scan-start. Diagnostics är här proveniens för återupptagning; den auktoritativa färdiga snapshotposten är snapshot_envelopes.
- Återupptagning kräver samma kanoniserade metadata som vid scan-start. Om metadata har ändrats avslutas den tidigare sessionen som failed och en ny scan startar från offset 0. Befintlig observation-/historikdata raderas inte.
- Migration 005 skapar snapshot_envelopes, med unik snapshot_id och scan_session_id, run-/scan-referenser, centrala jämförbarhetsfält och hela envelope-JSON. Tabellen har RLS utan publika policies; registrering sker via service-role-only security-definer RPC.
- Registrerings-RPC kräver terminal scan/run, kontrollerar identiteter och att envelope-metadata/rights-status motsvarar metadata som sparades vid scan-start. Complete kräver scan complete + poll_run success; partial/failed kan inte uppgraderas till complete.
- Store läser tillbaka terminala poster, använder befintlig mapWorkerScanToSnapshotEnvelope och registrerar via RPC. Samma envelope kan återregistreras idempotent; en annan envelope för samma scan avvisas. snapshot_registered_at och pending-RPC gör misslyckad registrering återförsökbar vid nästa workerstart.
- In-progress scan får ingen snapshotpost förrän den avslutas. En fatal scan kan registreras som failed. En transient nätverksstörning behåller checkpointen och den ursprungliga metadataidentiteten.

Ingen live Supabase-anslutning eller produktionsmigration är utförd i denna PR. CI verifierade migration 005 i disponibel PostgreSQL/PostGIS och rollback-wrapped SQL-smoketest passerade i run 45079498504. Kundvisning är fortsatt not_assessed; detta register är intern proveniens, inte ett publicerings- eller rättighetsgodkännande.
