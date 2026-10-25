# Skogskoll — bevakning av egen skog

Fristående, mobilanpassad app för privata skogsägare. Första leveransen är **förstudie + datakällprobe**; den skickar inga larm.

## Målarkitektur
- **Webbapp:** statisk app under `skogskoll/`, kan publiceras separat på GitHub Pages.
- **Beständig databas:** Supabase/Postgres med användare, bevakningsområden, källobservationer, larmhändelser och pushprenumerationer.
- **Schemalagd worker:** GitHub Actions var sjätte timme, med idempotent upsert/deduplicering.
- **Larm:** e-post via Resend och web push via VAPID/web-push. Larm är avstängda tills datakällans beteende har verifierats.
- **Befintliga lager återanvänds:** samma Skogsstyrelsen ArcGIS-tjänst för avverkningsanmälningar som i `docs/karta.html`.

## Säkerhetsgrind före larm
1. Kör `node skogskoll/scripts/probe-source.mjs` lokalt eller workflow `Skogskoll source probe`.
2. Granska `skogskoll/reports/source-probe-latest.json` som workflow-artifact.
3. Bekräfta att tjänsten returnerar stabila unika identifierare, datumfält och geometrier, samt att paginering och upprepade körningar ger förväntat resultat.
4. Implementera och verifiera DB-upsert/deduplicering mot faktisk respons.
5. Först därefter kopplas mejl/push på. Inga notiser skickas i denna version.

## Konfiguration för framtida drift
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: worker-only, aldrig i frontend.
- `RESEND_API_KEY`, `ALERT_FROM_EMAIL`: e-post.
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`: push.
- `ALERTS_ENABLED=false` ska vara standard tills verifieringsgrinden passerats.
- Frontendens Supabase anon key kan exponeras endast med korrekt RLS-policy. Lägg inte in service-role-nyckeln i webappen.

## Viktiga semantiska begränsningar
En ny post i tjänsten betyder att den är ny för vår historik, inte säkert att den inkom samma dag. Om källan saknar publiceringstid kan appen bara ange när posten först observerades. Geometrisk överlappning mot ett bevakningsområde är en matchning, inte ett juridiskt besked om ägande eller rådighet.

## Nästa steg
- Kör källprobe flera gånger med minst sex timmars mellanrum.
- Dokumentera fältschema, stabilitet, pagination och ändringar/borttagningar.
- Lägg till autentisering, RLS, bevakningspolygoner och testad idempotent historik.
- Aktivera larm separat efter uttryckligt beslut.
