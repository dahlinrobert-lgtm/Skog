# Skogskoll — bevakning av egen skog

Fristående, mobilanpassad app för privata skogsägare. Första leveransen är **förstudie + datakällprobe**; den skickar inga larm.

## Prototyp som går att prova redan nu

- Skapa, redigera och ta bort bevakningsområden lokalt i webbläsaren.
- Stöd för cirkel runt en punkt eller GeoJSON Polygon/MultiPolygon i WGS84.
- Inställningar för önskad e-post/push-kanal och händelsetyper sparas lokalt; inget skickas.
- Historikvyn visar uttryckligen att den saknar verifierade observationer i stället för att hitta på exempeldata.
- Lokal lagring är bara för prototypen: uppgifterna synkas inte och försvinner om webbplatsdata rensas.
- Ren geometrihjälpare i `src/geometry-match.mjs` kan testas utan databas och har syntetiska tester för radie, polygoner, korsande linjer och gränsfall. Den är en första approximativ matchare och ersätter inte PostGIS-validering.

## Målarkitektur
- **Webbapp:** statisk app under `skogskoll/`, kan publiceras separat på GitHub Pages.
- **Beständig databas:** Supabase/Postgres med användare, bevakningsområden, källobservationer, larmhändelser och pushprenumerationer.
- **Schemalagd worker:** GitHub Actions var sjätte timme, med idempotent upsert/deduplicering.
- **Larm:** e-post via Resend och web push via VAPID/web-push. Larm är avstängda tills datakällans beteende har verifierats.
- **Befintliga lager återanvänds:** samma Skogsstyrelsen ArcGIS-tjänst för avverkningsanmälningar som i `docs/karta.html`.

## Källprobe — verifieringsstatus
- Första körningen lyckades 2026-10-25.
- Senaste verifierade körningen som slutförts helt: [run #44](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40181356356), conclusion `success`. Senare körningar har lagt till worker-/adaptertester; deras CI-resultat kontrolleras separat.
- Källans count-query rapporterade 129 733 poster vid den körningen.
- Provet läste 300 poster: 300 unika tekniska ID:n, inga dubbletter och inga saknade ID:n.
- Proben begränsas avsiktligt till tre sidor à 100 poster; den gör inte en fullständig inläsning. 300 poster var cirka 0,077 % av källans rapporterade antal.
- Senaste 100 urvalet sorterat efter `Inkomdatum` hade datum mellan 2026-10-23 och 2026-10-24 UTC.
- Källans antal skiftade från 129 735 till 129 733 mellan två närliggande körningar. Det kan bero på källans uppdateringar, men vi ska fortsätta mäta detta och inte tolka ett enskilt count-delta som bevis för borttagna ärenden.
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

- Vänta in källprobe med minst sex timmars mellanrum och jämför rapporterna med `node skogskoll/scripts/compare-probes.mjs äldre.json nyare.json`.
- Kör SQL-smoketestet mot ett separat, disponibelt Supabase-projekt; statiska CI-kontroller är inte live-databasverifiering.
- Koppla inte den lokala prototypen till produktion eller skicka aviseringar innan auth, RLS, databastransaktioner och ingestion har verifierats.
- Efter live-test: koppla bevakningsgeometrier till PostGIS-matchning, bygg historikvyn på verkliga observationer och implementera aviserings-outbox med explicit opt-in.
