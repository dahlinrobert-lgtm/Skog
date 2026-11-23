# Skogskoll – granskning och målarkitektur för kundwebben

**Granskad mot:** `main`, 2026-11-22  
**Status:** Arkitekturgranskning och föreslagen migreringsordning  
**Omfattning:** Kundapplikationens webbstruktur. Ingen produktionskoppling, datakälla eller kundvisning aktiveras här.

## 1. Beslutad produktgräns

- **Skogskoll är kundprodukten** för privata skogsägare.
- **Skog är den interna dataplattformen** för källinventering, inhämtning, rådata, snapshots, validering, historik och analys.
- Skogs interna demonstrations-, pilot- och analysvyer ska inte vara del av Skogskolls kundnavigation.
- Skogskoll ska återanvända verifierade och godkända data-/API-kontrakt från plattformen. Kundwebben ska inte innehålla källspecifik inhämtning eller hemligheter.

Den här granskningen ändrar inte tidigare beslut om datakvalitet, historik, rättigheter, baseline eller aviseringar.

## 2. Verifierat nuläge i GitHub main

### 2.1 Publicerad webbstruktur

GitHub Pages publicerar webbplatsen från `docs/`:

- `docs/index.html` är en Gräsmyr-/Nordmaling-orienterad analys- och demonstrationssida, inte en Skogskoll-kundstartsida.
- `docs/bevakning.html`, `docs/karta.html`, `docs/utforda.html`, `docs/händelsekedjor.html` och `docs/historik.html` är separata Skog-verktyg/vyer.
- `docs/skog-theme.css` och `docs/skog-theme.js` innehåller delat tema för Skog-sidorna.
- Kundprototypen ligger separat i `skogskoll/index.html`, publicerad på `/Skog/skogskoll/`.

### 2.2 Skogskoll-prototypen

Den nuvarande `skogskoll/index.html` är en fristående HTML-sida med inline CSS, markup och ett inline ES-modulscript. Den innehåller:

- lokal testregistrering av bevakningsområden som cirkel eller GeoJSON Polygon/MultiPolygon,
- lokal lagring i webbläsaren,
- syntetisk matchningsförhandsvisning,
- lokala önskemål om e-post/push och händelsetyper,
- tydliga testlägesmeddelanden om att databas, riktig inläsning och larm inte är anslutna.

Sidan länkar i huvudnavigationen tillbaka till `../index.html`, `../bevakning.html`, `../karta.html`, `../utforda.html`, `../händelsekedjor.html` och `../historik.html`. Det blandar kundprototypen med interna Skog-vyer och är den tydligaste navigationsmässiga gränsöverträdelsen.

### 2.3 Befintlig applikationskod

Under `skogskoll/src/` finns separerade moduler för geometri-/områdesmatchning, observationer, pagination, scan-plan, worker-kärna, Supabase-adaptrar och lokal matchningsförhandsvisning. Det finns riktade tester under `skogskoll/tests/`.

`skogskoll/scripts/` innehåller källprobe, probejämförelse, scan-runner och återställning av inaktuella scans. Databasschema finns i `skogskoll/db/schema.sql`.

Detta är en användbar grund: domänlogik, worker och adaptrar ska fortsätta vara separerade från presentationslagret. De befintliga modulerna är inte i sig bevis för en produktionssatt backend.

### 2.4 Databas och driftstatus

Schemat definierar bland annat `watch_areas`, `source_observations`, `poll_runs`, `alert_events` och `push_subscriptions`. RLS är aktiverat. Källobservationer och poll-körningar är worker-hanterade och har avsiktligt inga publika användarpolicyer.

Dokumentationen anger att Supabase/Postgres och PostGIS är målarkitektur, men att liveinstallation, autentisering, RLS och ingestion måste verifieras i separat testprojekt innan produktionskoppling. E-post/push ska förbli avstängt tills baslinje, datakvalitet, rättigheter och leveransflöde är verifierade.

### 2.5 Rättighetsgräns

Den senast hämtade källstatusrapporten anger noll källor som uttryckligen godkända för kundvisning. Flera källor har villkor eller väntar på lager-/produktbedömning. Därför får webbarkitekturens lagerkatalog stödja status och avstängning per produkt/lager; en tekniskt åtkomlig källa får inte automatiskt bli synlig för kunder.

## 3. Problem som ska lösas

1. **Fel startsida för kundprodukten:** Pages-roten visar intern Gräsmyr-analys, medan kundprototypen ligger en nivå ned.
2. **Blandad navigation:** Skogskoll länkar direkt till interna Skog-sidor och använder varumärket "Skog" i huvudnavigationen.
3. **Olika visuella system:** kundprototypen, Skog-översikten och den omarbetade bevakningssidan har separata inline-/sidunika stilar. Gemensamma tokens och komponenter saknas i kundappen.
4. **Monolitisk kundsida:** bevakning, områdeshantering, historik, aviseringar och verifieringsinformation ligger i samma HTML-dokument.
5. **Otydlig produkt-/miljöstatus:** testfunktioner finns i samma yta som framtida kundfunktioner. De behöver avgränsas så att syntetiska poster och lokala inställningar aldrig uppfattas som riktig kunddata.
6. **Ingen gemensam klientgräns mot backend:** framtida API-anrop behöver gå genom ett tydligt klient-/tjänstelager; service-role-nycklar och källhämtning får aldrig ligga i webbläsaren.

## 4. Målbild för Skogskolls webbapp

### Kundens huvudnavigation

Håll huvudnavigationen till fem tydliga destinationer:

1. **Översikt** – senaste relevanta händelser, bevakningsstatus och tydliga nästa steg.
2. **Karta** – geografisk kontext för valda händelser och bevakningsområden.
3. **Bevakningar** – fastigheter och egna områden, status och inställningar för vad som följs.
4. **Historik** – upptäckter, ändringar och källans/tjänstens tidsstämplar.
5. **Konto** – användare, aviseringar, integritet och abonnemang när dessa funktioner finns.

Händelseflödet är produktens kärna. Kartan ska stödja förståelse och urval, inte vara enda ingången.

### Föreslagen filstruktur

Behåll den nuvarande publiceringssökvägen och URL:en under första migreringssteget för att undvika onödiga brutna länkar. Renodla därefter Skogskoll inom `skogskoll/`:

```text
skogskoll/
  index.html                 # Översikt / appens start
  pages/
    map.html                 # Karta
    watch-areas.html         # Bevakningar
    history.html             # Historik
    account.html             # Konto och inställningar
  assets/
    css/
      tokens.css             # Färger, typografi, spacing, ytor
      app.css                # Gemensam layout och komponenter
    js/
      app-shell.js           # Navigation, aktiv sida, gemensamt skal
      api-client.js          # Publik klient mot godkända backend-endpoints
  src/                       # Befintliga domän-/worker-moduler; behåll separerade
  scripts/                   # Ingestion/probe/underhåll; server-/CI-sida
  db/                        # Schema och migrationer
  tests/                     # Domän-, klient- och integrationskontroller
```

Detta är en målstruktur, inte en instruktion att flytta workerfilerna in i frontend. `src/`, `scripts/`, `db/` och `tests/` ska fortsätta hållas åtskilda från publika assets. Om den befintliga GitHub Pages-konfigurationen kräver en annan relativ sökväg ska den verifieras före filflytt.

### Tekniska gränser

- **UI:** HTML/CSS/JavaScript som kan köras responsivt i mobilwebbläsare och senare återanvändas/packeteras för mobil.
- **Domänlogik:** rena, testbara moduler utan DOM- eller plattformskoppling där det är möjligt.
- **API-klient:** enda frontendvägen till kund-API; validerar svar och hanterar fel/tillstånd.
- **Backend/worker:** autentisering, källhämtning, PostGIS-matchning, historik och aviseringar server-side.
- **Datakatalog/rättigheter:** endast produkter/lager med dokumenterad kundvisningsstatus får publiceras; status kontrolleras på backend, inte bara genom att dölja ett lager i UI.
- **Mobilberedskap:** responsiva komponenter, tydliga URL:er, delat domänkontrakt och inga funktioner som förutsätter mus/hover. PWA/appskal utvärderas efter stabil webbversion.

## 5. Renodlingsordning

### Steg 1 – gräns och navigation
- Gör Skogskoll-navigationen helt intern till kundappen.
- Ta bort länkar från kundnavigationen till Gräsmyr-/Skog-interna sidor.
- Lägg till gemensam app-shell, aktiv navigation och konsekvent sidfot/statusyta.
- Behåll intern Skog-webbplats tillgänglig via dess nuvarande URL för utveckling; exponera den inte i kundappen.

### Steg 2 – designsystem
- Extrahera färg-, typografi-, spacing-, yta- och brytpunktsvariabler till `assets/css/tokens.css`.
- Skapa gemensamma knappar, formulär, kort, statusetiketter, tomlägen och laddnings-/felmeddelanden i `app.css`.
- Säkerställ tillgänglig fokusmarkering, semantiska landmärken, tangentbordsnavigation och mobil layout.
- Minska sidunika inline-stilar stegvis; undvik stor omskrivning på en gång.

### Steg 3 – separera kundvyer
- Översikt: status och händelseflöde, inga syntetiska poster i produktionsläge.
- Bevakningar: skapa/ändra/inaktivera områden; skilj lokal prototyp från inloggad serverlagring.
- Karta: endast godkända lager, tydlig käll-/kvalitetsinformation och samma valda område/händelse som i flödet.
- Historik: visa första upptäckt separat från källans datum och publiceringsdatum; ofullständiga körningar får inte skapa borttagningshändelser.
- Konto: hålls som tydligt "kommer senare" tills autentisering och kontoflöde är implementerade.

### Steg 4 – API- och produktionskoppling
- Verifiera auth, RLS, PostGIS och scan-sessioner i separat testprojekt.
- Definiera kund-API-kontrakt utan att exponera worker- eller service-role-behörigheter.
- Kontrollera rättigheter per exakt källa/lager innan kundvisning.
- Behåll tyst första baslinje och fail-closed vid partial/failed scans.
- Aktivera e-post/push först efter explicit användarval och verifierad outbox/leverans.

### Steg 5 – mobil
- Testa webbappen på små skärmar och som installerbar PWA.
- Mät vilka vyer och interaktioner som behöver native-funktioner.
- Välj därefter eventuell Capacitor-/native-wrapper. Ingen separat mobilimplementation behövs innan webbens informationsarkitektur och API-kontrakt stabiliserats.

## 6. Migreringsregler och skydd

- Ändra inte `docs/index.html` till kundstartsida förrän en kontrollerad övergångsplan finns; den sidan används i dag som intern Gräsmyr-översikt.
- Flytta inte eller ta bort befintliga Skog-sidor, datakällor eller arbetsflöden som del av kundappens renodling.
- Byt inte databasmodell eller source identity utan separat analys av befintliga tester och historik.
- Behåll testläge tydligt tills riktig auth/backend finns. Inga påhittade kundhändelser.
- Inga datakällor blir kundsynliga enbart genom att UI-komponenter byggs.
- Ingen produktionsdata, kunddata eller hemlighet läggs i GitHub Pages.

## 7. Acceptanskriterier för första kodsteget

1. Kundnavigationen innehåller bara Skogskolls kundvyer och inga länkar till interna Skog-sidor.
2. Alla kundsidors relativa länkar fungerar från aktuell publiceringssökväg `/Skog/skogskoll/`.
3. Testläge och lokal lagring är fortsatt tydligt märkta; inga larm eller serveranrop aktiveras av misstag.
4. Skog-webbplatsens interna sidor och befintliga länkar påverkas inte.
5. Befintliga Skogskoll-domäntester passerar och nya tester täcker navigationens länkar/sökvägar.
6. Ingen källa eller datatyp visas som kundgodkänd utan uppdaterat och verifierat rättighetsunderlag.

## 8. Nästa konkreta arbetssteg

Gör ett avgränsat första UI-PR: lägg till kundappens gemensamma navigation och designsystemgrund i `skogskoll/`, uppdatera befintlig prototyps navigation så den inte pekar på interna Skog-vyer och lägg till automatiska kontroller för kundnavigation och relativa länkar. Låt sidornas befintliga funktioner och datalogik vara orörda i detta PR.

## 9. Produktens särskiljande kärna – snapshotbaserat dag-för-dag-flöde

Skogskolls primära kundupplevelse är ett **kronologiskt förändringsflöde byggt av daterade snapshots**. Det är produktens huvudsakliga differentiering och ska vara startsidans tydligaste innehåll. Karta, bevakningsområden och historik ska vara sammanlänkade med flödet, inte konkurrerande fristående ingångar.

### Kundupplevelse

- **Flöde:** visa förändringar dag för dag och låt användaren välja en dag eller jämförelseperiod.
- **Snapshot:** visa vad som faktiskt observerades vid en bestämd avstämningstidpunkt, med källa, produkt/lager, hämtningstid, körnings-ID, status, täckning och kontrollsumma där det finns.
- **Förändringspost:** skilj mellan första upptäckt av Skogskoll, källans händelsedatum och publiceringsdatum. Visa tillkommet, ändrat och endast när evidensen räcker – försvunnet/inaktivt.
- **Karta:** samma valda dag och händelse ska styra den geografiska vyn. Kartan ska kunna leda tillbaka till händelsens tidslinje.
- **Historik:** användaren ska kunna följa ett objekts observationer över flera snapshots och förstå vilka jämförelser som ligger bakom slutsatsen.

### Datakvalitet och tidssemantik

1. Jämför endast snapshots som är kompletta och jämförbara för samma källa/produkt/lager och relevant geografisk täckning.
2. `partial`, `failed`, okänd täckning eller schema-/produktversionsskifte får inte skapa negativa slutsatser eller borttagningshändelser.
3. Bevara originalsnapshots oförändrade. Förändringsposter ska vara härledbara från källobservationer och körningsmanifest.
4. En första komplett baslinje fyller historiken men genererar inte retroaktiva kundlarm.
5. Frånvaro i en enskild senare snapshot är inte bevis för borttagning eller genomförd avverkning.
6. Varje förändring ska kunna granskas tillbaka till källa, snapshot och körning.

### UI-steg

Första UI-steget etablerar flödet som startsidans primära yta, datumval och tydliga snapshot-/fullständighetsstatusar. Det får inte visa syntetiska eller obekräftade poster som riktiga händelser. Den riktiga dag-för-dag-tidslinjen kopplas in först när godkända och verifierade snapshotkontrakt finns tillgängliga. Källstatusrapporten som granskades 2026-11-18 anger noll källor uttryckligen godkända för kundvisning; detta måste kontrolleras på nytt innan någon datakälla exponeras.


## 9. Snapshot- och change-feed-kontrakt (2026-11-22)

PR #483 har etablerat kundskalet med dag-för-dag-flöde. Nästa lager har nu fått ett separat domänkontrakt i [SKOGSKOLL_CHANGE_FEED_CONTRACT.md](SKOGSKOLL_CHANGE_FEED_CONTRACT.md) och en ren valideringsfunktion i `skogskoll/src/change-feed-contract.mjs`.

Kontraktet kräver kompletta snapshots med identisk källa, produkt, lager, täckningsnyckel, schema- och identitetsversion. Snapshot-/run-ID måste skilja sig och aktuell snapshot måste vara senare. Första baslinjen är tyst. Efter baslinjen kan nya och ändrade poster bli händelser, men endast med explicit godkänd kundvisning och referens till rättighetsunderlag. Frånvaro ger aldrig automatiskt borttagningshändelse. Händelsens upptäcktsdatum hålls skilt från källans händelse- och publiceringsdatum.

Detta är ännu inte ett API, en persistensimplementation eller en produktionskoppling. Den befintliga worker-/databasmodellen för Skogsstyrelsen ändras inte. Nästa steg är CI-verifiering och jämförelse mot befintliga manifest och historiktabeller innan ett separat API-/persistensförslag.


## 10. Change-feed-kontrakt mergat (2026-11-22)

PR #484 är mergad till `main` (merge commit `8f44a442e3e0eafb8055b03769e3d2877b05f725`). Kontrakt, ren domänkärna och tester finns i repot. CI för hela Node-testsviten och source probe passerade. Testworkflowens path-filter är utökat så att framtida ändringar i `skogskoll/src/**` och `skogskoll/tests/**` kör testsviten även vid push till main.

Detta är fortsatt en domän-/valideringsimplementation, inte ett produktions-API eller en kundfeed. Nästa steg är en evidensbaserad inventering av befintliga snapshotmanifest och historikfält innan någon persistens- eller API-mappning utformas. Källornas kundvisningsgrind är fortsatt stängd enligt källstatusrapporten.


## 11. Inventering av befintliga snapshots och historik (2026-11-22)

Kod- och filinventeringen finns i [SKOGSKOLL_SNAPSHOT_INVENTORY.md](SKOGSKOLL_SNAPSHOT_INVENTORY.md). Den visar att Skogskolls relationsmodell redan har current state, append-only observation history, poll runs, resumable scans och atomiska sidcommits. Den är däremot ännu kopplad till Skogsstyrelsens enda befintliga worker-source och saknar ett gemensamt explicit snapshot-envelope för produkt, lager, coverage, schema-/identitetsversion och rättighetsevidens.

Filbaserade källarkiv använder separata format och scope. Delta-`removed` är en rekonstruktionsinstruktion, inte en kundhändelse. Rekommenderad fortsättning är en ren, testad adapter från befintlig worker-/run-/historymodell till snapshot-kontraktet innan någon ny databasmodell eller API-mappning införs.


## 2026-11-23 – Explicit API-privilegier och RLS (migration 006)

Supabase-testinstansen `skogskoll-test` har verifierats manuellt efter installation av grundschema och migrationerna 002–005. Objektinventering och befintliga PostGIS-/ingestiontester har visats lyckade av användaren. En separat privilegiekontroll visade att RLS var aktiverat men att API-rollerna saknade direkta tabellprivilegier.

Föreslagen migration 006 på branch `fix/skogskoll-explicit-api-grants-rls-20261123` kompletterar de redan befintliga ägarbaserade RLS-policyerna med minsta nödvändiga GRANTs:
- `authenticated`: CRUD på `watch_areas` och `push_subscriptions`, SELECT på `alert_events`; befintliga RLS-policyer begränsar rader till aktuell användare.
- `service_role`: endast direkt SELECT på `scan_sessions` och `poll_runs`, vilka den befintliga workeradaptern läser via REST. Workerwrites fortsätter via SECURITY DEFINER-RPC.
- `anon`: inga tabellbehörigheter.
- `source_observations`, `source_observation_history`, `scan_seen_ids` och `snapshot_envelopes`: inga direkta API-privilegier; snapshotregistret förblir append-only och RPC-skyddat.

Nytt SQL-test kontrollerar privilegier, ägarisolering och workerläsning med ROLLBACK. Migrationen är ännu inte applicerad i Supabase-testprojektet och får inte beskrivas som produktionssatt. Kundfeed, källvisning och e-post/push förblir avstängda.
