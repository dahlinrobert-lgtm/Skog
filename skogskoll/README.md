# Skogskoll — bevakning av egen skog

Fristående, mobilanpassad app för privata skogsägare. Första leveransen är **förstudie + datakällprobe**; den skickar inga larm.

## Målarkitektur
- **Webbapp:** statisk app under `skogskoll/`, kan publiceras separat på GitHub Pages.
- **Beständig databas:** Supabase/Postgres med användare, bevakningsområden, källobservationer, larmhändelser och pushprenumerationer.
- **Schemalagd worker:** GitHub Actions var sjätte timme, med idempotent upsert/deduplicering.
- **Larm:** e-post via Resend och web push via VAPID/web-push. Larm är avstängda tills datakällans beteende har verifierats.
- **Befintliga lager återanvänds:** samma Skogsstyrelsen ArcGIS-tjänst för avverkningsanmälningar som i `docs/karta.html`.

## Källprobe — verifieringsstatus
- Första körningen lyckades 2026-10-25.
- Senaste verifierade körningen: [run 40179914630](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40179914630), conclusion `success`.
- Källans count-query rapporterade 129 734 poster vid den körningen.
- Provet läste 300 poster: 300 unika tekniska ID:n, inga dubbletter och inga saknade ID:n.
- Proben begränsas avsiktligt till tre sidor à 100 poster; den gör inte en fullständig inläsning. 300 poster var cirka 0,077 % av källans rapporterade antal.
- Senaste 100 urvalet sorterat efter `Inkomdatum` hade datum mellan 2026-10-23 och 2026-10-24 UTC.
- Kontroller för sidstorlek, källantal, ID-integritet, syntax och pagination core körs automatiskt i workflow.
- En lyckad källprobe betyder inte att aviseringar kan aktiveras eller att hela registret är historiskt validerat.

## Säkerhetsgrind före larm
1. Kör `node skogskoll/scripts/probe-source.mjs` lokalt eller workflow `Skogskoll source probe`.
2. Granska `skogskoll/reports/source-probe-latest.json` som workflow-artifact.
3. Kör minst två prober med minst sex timmars mellanrum och jämför fingerprint, datummönster och ID-beteende.
4. Implementera en separat fullständig/inkrementell ingestion med kontrollerad paginering, räknare, retry, checkpoint och tydliga regler för ofullständiga körningar.
5. Använd `skogskoll/src/pagination-core.mjs` som ren kontrollfunktion för att bedöma en skanning. Den markerar inte poster inaktiva och utför ingen databasoperation.
6. Verifiera idempotent DB-upsert/deduplicering och historik innan e-post eller push kopplas på.

## Källidentitet och datum
- `OBJECTID` behandlas som källans tekniska rad-ID; dess stabilitet över tid ska verifieras.
- `Beteckn` är en kandidat till ärendeidentitet, men får inte antas vara unik eller oföränderlig utan test.
- `Inkomdatum` bevaras som källans inkomdatum. Det är inte samma sak som när Skogskoll först observerade posten eller när den publicerades.
- Första upptäckt av en äldre post skapar en historisk baselinepost, inte en ny-händelse-avisering.

## Konfiguration för framtida drift
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: worker-only, aldrig i frontend.
- `RESEND_API_KEY`, `ALERT_FROM_EMAIL`: e-post.
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`: push.
- `ALERTS_ENABLED=false` ska vara standard tills verifieringsgrinden passerats.
- Frontendens Supabase anon key kan exponeras endast med korrekt RLS-policy. Lägg inte in service-role-nyckeln i webappen.

## Viktiga semantiska begränsningar
En ny post i tjänsten betyder att den är ny för vår historik, inte säkert att den inkom samma dag. Geometrisk överlappning mot ett bevakningsområde är en matchning, inte ett juridiskt besked om ägande eller rådighet. Skogsstyrelsen uppger att publicerade avverkningsanmälningar kan finnas kvar i upp till sex år beroende på när åtgärden genomförts; frånvaro i lagret kan därför inte tolkas som bevis för att ingen anmälan funnits.

## Nästa steg
- Kör källproben igen efter minst sex timmar.
- Jämför rapporternas datummönster och fingerprint.
- Bygg en separat fullständig ingestion som aldrig markerar ej sedda poster inaktiva efter misslyckad eller ofullständig poll.
- Aktivera aviseringar separat efter uttryckligt beslut.
