# Skogskoll – snapshot- och change-feed-kontrakt

**Status:** Föreslaget domänkontrakt, implementerat som fristående valideringskärna. Inte ett produktions-API.  
**Senast uppdaterad:** 2026-11-22

## Syfte och avgränsning

Detta kontrakt definierar när två källsnapshots får jämföras och vilka händelser som får skapas till Skogskolls dag-för-dag-flöde. Det återanvänder befintlig identitet `source + source_id`, innehållshash, append-only observationshistorik och worker-/service-rollsgräns.

Det inför **inte** en ny databasmodell, kör inte ingestion, publicerar inga data och skickar inga aviseringar. Den befintliga Skogsstyrelsen-ingestionen är fortfarande källspecifik. Kontraktet är en säker, källneutral gräns för nästa lager ovanpå verifierade snapshotleveranser.

## 1. Snapshot-envelope

Varje jämförbar snapshot ska minst kunna beskrivas med:

| Fält | Betydelse |
|---|---|
| `snapshot_id` | Stabilt ID för den oföränderliga snapshotleveransen |
| `run_id` | ID för insamlingskörningen |
| `source` | Källidentitet |
| `product` | Exakt produkt/dataset från källan |
| `layer` | Exakt lager eller delmängd |
| `captured_at` | När Skog tog snapshoten |
| `status` | `complete`, `partial` eller `failed` |
| `coverage_key` | Kanonisk identitet för geografisk/temporal täckning och urval |
| `schema_version` | Version av normaliserat snapshot-schema |
| `identity_version` | Version av stabil källobjektidentitet |
| `customer_visibility` | Separat rättighetsgrind: endast `approved` kan ge kundhändelser |
| `rights_evidence_ref` | Spårbar referens till dokumenterat underlag för kundvisning |

Originalfil, manifest, körningsdiagnostik och kontrollsumma bevaras separat och oförändrade. `snapshot_id` får inte återanvändas för nytt innehåll.

## 2. Jämförbarhetsgrind

Två snapshots får jämföras endast när samtliga villkor är uppfyllda:

1. Båda har status `complete`. `partial`, `failed`, `running`, saknad eller okänd status stoppar jämförelsen.
2. `source`, `product` och `layer` är identiska.
3. `coverage_key` är identisk. En geografiskt eller temporalt ändrad täckning är en ny jämförelsebas.
4. `schema_version` och `identity_version` är identiska.
5. Snapshot-ID och körnings-ID finns och är olika mellan körningarna.
6. `captured_at` är giltig och den nya snapshoten är senare än den föregående.

En likadan posträkning bevisar inte att en extern källa varit transaktionellt oförändrad. Källspecifika krav på paginering, ID-integritet, transfer limits och manifestkontroll måste därför vara uppfyllda innan en leverans får märkas `complete`.

## 3. Baslinje och händelseklassning

- Första kompletta snapshoten etablerar baslinjen. Den skapar **inga** kundhändelser och inga retroaktiva larm.
- Efter etablerad baslinje ger ett nytt stabilt `source + source_id` en `first_seen`-händelse.
- Samma identitet med ändrad `content_hash` ger `changed`.
- Samma identitet och hash ger ingen händelse (oförändrad observation/touch).
- Geometriförändring ingår i innehållshashen och klassas som `changed`; den får inte döljas genom en separat geometriidentitet.
- Frånvaro i en senare snapshot ger **aldrig** `removed`, `deleted`, `cancelled` eller genomförd avverkning. Den kan endast bli en intern granskningssignal efter källspecifik verifiering. En framtida frånvaromodell kräver separat evidens för explicit tombstone/återkallelse från källan och ett eget beslut.
- En ändring i attribut eller geometri är inte automatiskt en ny avverkningsanmälan.

## 4. Tidssemantik och proveniens

Varje händelse skiljer på:

- `detected_at`: när Skogskoll först kunde härleda händelsen från en godkänd jämförelse,
- `source_event_at`: källans händelsedatum, om dess semantik är verifierad,
- `source_published_at`: källans publiceringsdatum, om det finns och är verifierat,
- `snapshot_captured_at`: när snapshoten hämtades.

Saknade eller oklara källdatum lämnas null; de får inte ersättas med insamlingsdatum. Händelsen ska kunna spåras till source, product, layer, source_id, snapshot_id, run_id, content_hash och rights_evidence_ref.

## 5. Kundvisningsgrind

En tekniskt åtkomlig observation är inte automatiskt kunddata. Kundhändelser får skapas endast när den exakta produkten/lagret har `customer_visibility = approved` och en icke-tom `rights_evidence_ref`. Alla andra statusar innebär fail-closed: ingen kundhändelse.

Rättighetsgrinden är separat från teknisk jämförbarhet. En jämförbar snapshot kan därför vara användbar för intern kvalitetssäkring men inte för kundvisning.

## 6. Föreslaget event-envelope

```json
{
  "event_id": "deterministic-or-persisted-id",
  "event_type": "first_seen | changed",
  "detected_at": "2026-11-22T12:00:00Z",
  "source_event_at": null,
  "source_published_at": null,
  "snapshot_captured_at": "2026-11-22T12:00:00Z",
  "source": "source.key",
  "product": "product.key",
  "layer": "layer.key",
  "source_id": "stable-source-id",
  "snapshot_id": "snapshot-id",
  "run_id": "run-id",
  "content_hash": "sha256",
  "rights_evidence_ref": "docs/source-rights-reviews/evidence.md"
}
```

Detta är ett domänkontrakt, inte ett löfte om att alla fält redan finns i befintliga tabeller. Persistens-/API-mappning ska göras separat efter inventering av faktiska manifest och migrations.

## 7. API-yta – föreslagen, ej implementerad

Kundens läs-API bör senare exponera en autentiserad, paginerad vy, exempelvis:

- `GET /v1/feed?watch_area_id=…&day=YYYY-MM-DD&cursor=…`
- `GET /v1/feed/events/{event_id}`

Svaret ska innehålla event-envelope, matchat bevakningsområde och kartgeometri eller referens till godkänd geometri. API:t ska filtrera på användarens behörighet och källans kundvisningsstatus på serversidan. Webbläsaren får aldrig anropa källornas worker eller använda service-role-nyckel.

Dagval ska baseras på `detected_at` (Skogskolls upptäcktsdag). Källans händelsedatum och publiceringsdatum visas som separata metadata, inte som ersättning för upptäcktsdag.

## 8. Acceptanskriterier före riktig feed

- Samtliga jämförbarhetsvillkor testas positivt och negativt.
- Första baslinjen ger noll kundhändelser.
- Partial/failed/unknown status ger noll kundhändelser och ingen frånvarosignal.
- Byte av källa, produkt, lager, täckning, schema eller identitetsversion stoppar jämförelsen.
- Oförändrad hash ger ingen händelse; ändrad hash ger `changed`.
- Frånvaro kan inte skapa borttagningshändelse.
- Saknad/ej godkänd rättighet eller evidens stoppar kundhändelser.
- Händelser har full proveniens och separata tidsfält.
- Persistens, API, auth/RLS och PostGIS verifieras i separat testprojekt innan aktivering.
