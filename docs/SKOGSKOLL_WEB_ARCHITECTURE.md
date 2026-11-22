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
