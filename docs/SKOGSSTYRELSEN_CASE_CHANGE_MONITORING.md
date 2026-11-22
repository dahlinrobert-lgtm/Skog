# Skogsstyrelsen – ärendebaserad förändringsbevakning och månadskontroll

**Beslutsdatum:** 2026-11-22  
**Status:** Första schemalagda kontrollflödet etableras via PR; omfattningen är pilotområdet Gräsmyr med 10 km radie, inte nationell täckning.

## Syfte

Skilj mellan tät upptäckt av nya/ändrade ärenden och en periodisk kontroll av att vår sparade historik fortfarande motsvarar källans aktuella innehåll. Månadskontrollen är en kvalitetskontroll och får inte ensam skapa kundhändelser eller negativa slutsatser.

## Källor och vad kontrollen faktiskt gör

| Källa | Löpande kontroll som finns | Månadskontroll i första versionen | Begränsning |
|---|---|---|---|
| Planerade avverkningsanmälningar | Skogskoll source probe körs var sjätte timme. Den läser metadata, totalantal och ett begränsat urval (högst tre sidor). | Samma read-only-probe körs och rapporten sparas som Actions-artifact i 90 dagar. | Inte en fullständig snapshot eller full ärendehistorik. Proben sorterar på Inkomdatum, vilket inte är bevis på senaste ändringstid. |
| Samråd – punkt, linje, polygon | Befintlig daglig pilotinsamling. Varje geolager hämtas separat med paginering. | Fullständig hämtning inom befintligt konfigurerat pilotområde, alla tre lager, med oförändrade original-snapshots. | Pilotgeografi; inte nationellt. Inkomdatum är inte verifierat som ändringstid. |
| Utförda avverkningar | Befintlig snapshot-/deltaarkivering för Gräsmyr-området. | Ny kontrollsnapshot av hela det befintliga frågeområdet. Arkivet bygger vidare på fulla checkpoints och deltaarkiv. | Pilotgeografi; frånvaro i ett uttag bevisar inte borttagning eller avverkning. |

## Månatligt workflow

`.github/workflows/skogsstyrelsen-monthly-source-audit.yml` körs den första dagen varje månad kl. 07:17 UTC och kan även startas manuellt.

1. Kör tester för Samrådsinsamlaren och arkivet för utförda avverkningar.
2. Hämtar punkt-, linje- och polygonlagren för Samråd med befintlig paginering och fullständighetskontroll.
3. Hämtar och arkiverar utförda avverkningar inom samma konfigurerade pilotområde.
4. Kör Skogskolls read-only-probe för planerade avverkningsanmälningar.
5. Bevarar snapshots i Git och probe-rapporten som Actions-artifact i 90 dagar.

Workflowet ska misslyckas om en insamling eller ett test misslyckas. Det får inte publicera en ofullständig Samrådssnapshot. Arkivskrivning för utförda avverkningar behåller befintliga scope-fingerprints och checkpoint/delta-regler.

## Tolkning av resultat

- `success` betyder att den tekniska körningen lyckades för angivet scope; det betyder inte nationell täckning eller juridiskt kundgodkännande.
- ID som inte återfinns i en senare körning märks som frånvarande i uttaget, inte som borttaget, avbrutet eller utfört.
- Ändrat innehåll/geometry hash är en observerad källförändring. Klassificera inte automatiskt dess juridiska eller operativa innebörd.
- Samrådets punkt-, linje- och polygonobjekt kan representera flera geometrier för samma ärende. Behåll lagerseparation och gruppera vid behov med källans UUID/Beteckn.
- För planerade avverkningsanmälningar är Inkomdatum ett inkomstdatum. Ingen verifierad editDate/senaste ändringstid har ännu fastställts.
- För utförda avverkningar ska polygoner unioneras innan arealer summeras; råa överlapp får inte dubbelräknas.
- Ingen av dessa kontroller aktiverar kundaviseringar.

## Öppna verifieringsfrågor

1. Kontrollera ArcGIS-lagermetadata för alla fem sublager/produkter och identifiera editFieldsInfo, editor tracking, datumfält, advancedQueryCapabilities och eventuell historik-/replica-funktion.
2. Jämför minst två fullständiga, jämförbara månadssnapshots per lager innan beteendet beskrivs som ärendevis append/update.
3. Undersök om källan kan returnera uppdaterade ärenden via editDate/lastEditDate utan fullständig nedladdning.
4. Utöka planerade avverkningsanmälningar från begränsad probe till fullständig, paginerad snapshot inom definierat scope först efter separat test av kapacitet och fullständighet.
5. Bedöm nationell skalning separat; nuvarande månadskontroll är uttryckligen en Gräsmyr-pilot.
6. Dokumentera varje månad resultat: körnings-ID, datum, scope-hash, status, antal, ID-differenser, innehållsdifferenser, fel och slutsats.

## Säkerhetsregler

- Bevara originalsnapshots och kontrollsummor.
- Jämför endast samma källa, lager, query scope och jämförbar version.
- Ofullständig/failed/partial körning får inte skriva en giltig kontrollpunkt eller skapa borttagningshändelser.
- Första baslinjen är tyst.
- Teknisk åtkomst är inte samma sak som kommersiella rättigheter eller kundvisning.

## Driftverifiering 2026-11-22 – första manuella körningen

Första manuella körningen efter merge, [run #4](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45031069869), genomförde samtliga insamlingssteg framgångsrikt:
- Tester för Samrådsinsamlaren och completed snapshot-arkivet passerade.
- Samrådsinsamlaren avslutades framgångsrikt för samtliga tre geometrier.
- Snapshot av utförda avverkningar avslutades framgångsrikt.
- Read-only-proben för planerade avverkningsanmälningar avslutades framgångsrikt.
- Probe-rapporten laddades upp som artifact (artifact ID 14758060886; SHA-256 `c3af9908a5c5a72dbc83c00d29bbd0be77a330873a0367b2326b9e0d7efca208`).

Publiceringssteget misslyckades efter att snapshots hade skapats lokalt i runnern. Loggen visar att fyra filer ändrades, inklusive nya komprimerade snapshots:
- `data/samrad_snapshots/samrad_20261122T140801Z.json.gz`
- `data/snapshots/completed_20261122T140801Z.geojson.gz`

Push till `main` avvisades fem gånger av repository rules (GH013: “Changes must be made through a pull request”). Därmed publicerades inga snapshotfiler till main från denna körning. Detta var ett publicerings-/behörighetsflödesfel, inte ett insamlingsfel.

### Korrigering

Workflowet ändras till att använda `peter-evans/create-pull-request@v7` med separat automation-branch och `contents: write` + `pull-requests: write`. Varje månadskörning ska skapa eller uppdatera en PR med snapshots. Inga automatiska merges görs. Snapshotdata blir beständig i main först efter granskning och merge av data-PR:n.

**Verifieringsstatus:** Insamling och artifact-uppladdning verifierade för run #4. Git-publicering via PR är ännu inte verifierad; nästa steg är att köra workflowet efter att korrigeringen mergats och kontrollera att en snapshot-PR skapas.


## Uppföljning efter merge av publiceringskorrigering (2026-11-22)

PR #489 är mergad till `main` (merge commit `4c62e11b58c213e715bd9c4d939d514626cc2359`).

PR-checken [run #5](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45031856059) passerade. Den var en `pull_request`-körning: testerna kördes och passerade, medan alla tre källinsamlingar, snapshot-PR-steget och artifact-uppladdningen hoppades över med avsikt. Den är därför inte en driftverifiering av den nya publiceringsvägen.

**Återstående verifiering:** starta workflowet med `workflow_dispatch` på `main`. Godkänt utfall kräver att insamlingarna genomförs, en automation-PR med snapshots skapas/uppdateras och att dess manifest/scope/antal/kontrollsummor granskas innan data-PR:n mergas. Ingen auto-merge.


## Skogsstyrelsen monthly audit – första lyckade publiceringskörningen (2026-11-22)

- Manuell `workflow_dispatch` run #6 lyckades: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45033322810
- Alla jobb/steg passerade, inklusive tester, Samrådinsamling, completed-harvest snapshot, planned-harvest probe, skapande av snapshot-PR och artifact-uppladdning.
- Automatiska data-PR:n är [PR #491](https://github.com/dahlinrobert-lgtm/Skog/pull/491), öppen och mergebar men ännu inte mergad. Den innehåller `data/samrad_latest.json`, `data/completed_latest.json` samt två nya komprimerade snapshotfiler. Granska PR:n manuellt innan merge.
- Samråd, Gräsmyr-pilotens 10 km cirkulära scope: points 0; lines 20 hämtade i envelope, 11 kvar efter exakt cirkelfilter; areas 14 hämtade i envelope, 12 kvar efter exakt cirkelfilter. Status success för samtliga lager. Snapshot: `data/samrad_snapshots/samrad_20261122T143240Z.json.gz` (401 155 byte); scope hash `9c597758897297d34eb6ae733e56c5998587de4ff478fd8e82ae1a510dcfa76a`.
- Utförda avverkningar: 1 631 objekt i aktuell fullständig kontroll inom 10 km-scope. Ingen baseline; 0 nya, 0 saknade och 0 geometriändrade ID:n. Arkivfilen `completed_20261122T143240Z.geojson.gz` är en delta på 479 byte med 0 tillagda/uppdaterade/borttagna objekt; detta betyder oförändrat läge, inte att lagret är tomt. Full komprimerad motsvarighet uppskattades till 6 217 406 byte.
- Planerade avverkningsanmälningar: read-only-probe lyckades men är uttryckligen inte fullständig. Källan rapporterade 132 594 poster; proben läste 300 poster (3 sidor), capped=true, complete_scan=false, ca 0,0754 % av lagret. Den får inte användas som fullständig historik eller larmunderlag.
- Probe-artifact: `skogsstyrelsen-monthly-source-audit-45033322810`, artifact ID 14758965735, SHA-256 `c7a63d038d180ace683e90f086b790857b63f9adfe293cf93506805516c987de`.
- **Verifieringsstatus:** den nya PR-baserade publiceringsvägen är nu verifierad eftersom körningen skapade PR #491. Snapshotinnehållet är ännu inte beständigt i `main`; det sker först efter manuell granskning och merge av PR #491. Planerade avverkningsanmälningar är fortfarande endast en begränsad probe.
- Rättighetsgrinden för kundvisning påverkas inte. Ingen kundfeed eller larmfunktion aktiveras av denna körning.
