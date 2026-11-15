# Skog / Skogskoll – överlämning för fortsatt arbete

**Senast uppdaterad:** 2026-11-15  
**Syfte:** Detta dokument är en kompakt startpunkt för fortsatt utveckling, även när arbetet fortsätter i en ny ChatGPT-chatt.

> Läs detta dokument först i en ny chatt. Läs därefter den automatiska källstatusrapporten och den fullständiga datakälleöversikten. Kontrollera alltid aktuella filer och GitHub Actions innan du påstår att en körning eller status fortfarande gäller.

## 1. Projektets uppdelning

- **Skog** är den bredare dataplattformen: källinventering, insamling, snapshots, historik, analys, validering och dokumentation.
- **Skogskoll** är den tänkta kundprodukten: fastighets-/områdesbevakning för privata skogsägare, geografisk matchning, historik och relevanta aviseringar.
- Skog-repot innehåller flera pilot- och analysflöden som inte automatiskt är produktionsklara eller avsedda för kundvisning.

Repository: https://github.com/dahlinrobert-lgtm/Skog  
GitHub Pages: https://dahlinrobert-lgtm.github.io/Skog/

## 2. Läsordning i en ny chatt

1. [Automatisk status för datakällor](SKOGSKOLL_SOURCE_STATUS.md) – sammanfattning av maskinläsbara statusfält.
2. [Datakällor, åtkomst och användning](SKOGSKOLL_DATA_OVERVIEW.md) – den fullständiga källinventeringen, nuläget och färdplanen.
3. [Data platform architecture](data-platform-architecture.md) – teknisk målarkitektur.
4. [Open data and commercial use](open-data-and-commercial-use.md) – rättighetsprinciper och bedömningar.
5. [Data platform README](../data-platform/README.md) – register, scheman, scripts och flöden.
6. Vid behov: [Product inspiration and roadmap](product-inspiration-and-roadmap.md).

## 3. Viktiga arkitektur- och säkerhetsbeslut

- Bevara rådata och ursprungliga snapshots oförändrade; bearbetade produkter ska kunna spåras till källa och körning.
- Varje snapshot ska ha källa, produkt/lager, hämtningstid, körnings-ID, status, täckning, antal, format och kontrollsumma när det är relevant.
- Skilj källans händelsedatum, publiceringsdatum och Skogskolls första upptäckt.
- Första kompletta baslinjen ska inte skapa aviseringar för historiska poster.
- En misslyckad eller ofullständig körning får aldrig markera objekt som saknas/inaktiva.
- Frånvaro i ett senare uttag är inte bevis för borttagning, avbokning eller genomförd avverkning.
- Bevara historik när källobjekt försvinner ur tjänsten.
- Slå samman/unionera genomförda avverkningspolygoner innan arealer summeras, så att överlapp inte dubbelräknas.
- Tekniskt åtkomlig data är inte automatiskt godkänd för kommersiell användning, historisk lagring, bearbetning, kundvisning eller vidare distribution. Bedöm dessa separat per exakt produkt/lager.
- Inga kundaviseringar ska aktiveras innan ingestion, baslinje, fullständighet, databas och rättighetsläge är verifierade.
- Hemligheter, API-nycklar, lösenord och åtkomsttoken får aldrig läggas i Git eller källregistret.

## 4. Källregister och automatisk rapport

Maskinläsbart register: `data-platform/config/sources.yml`  
Validerare: `data-platform/scripts/validate_source_registry.py`  
Rapportgenerator: `data-platform/scripts/build_source_status_report.py`  
Rapport: `docs/SKOGSKOLL_SOURCE_STATUS.md`

Registret har 47 källposter och 11 poster med ett operativt `operations`-block vid senaste dokumenterade kontrollen. Övriga källor saknar ännu operativ status; det betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.

Rapporten visar åtkomst, snapshots, historik, kommersiell användning, kundvisning och nästa åtgärd. Den ska uppdateras automatiskt när källregistret ändras via workflowet för källregistervalidering. Om rapporten blir inaktuell kan den byggas lokalt:

```bash
python -m pip install PyYAML==6.0.2
python data-platform/scripts/build_source_status_report.py --write
python data-platform/scripts/build_source_status_report.py --check
```

Statusar är operativ projektinformation, inte juridiska beslut.

## 5. Viktiga källspår just nu

### Skogsstyrelsen
- Avverkningsanmälningar: högsta prioritet. Fullständig paginering och minst två kompletta jämförbara körningar behöver verifieras innan frånvaro eller nyhet används som larm.
- Samråd: punkt-, linje- och polygonlager samlas separat. Kontrollera täckning och fullständighet per lager.
- SIS: metadataövervakningen hade misslyckade körningar 13–14 november 2026. Felsök workflow och verifiera rasterhämtning och produktvillkor.
- Skogliga grunddata/volym: bevara produktversioner och metadata; jämför endast jämförbara raster.

### SLU Torvkarta
- SLU lämnade 2026-11-02 ett skriftligt besked om fri kommersiell användning av nuvarande Torvkarta med angiven källhänvisning.
- Beskedet innebär inte automatiskt rätt att distribuera underliggande Lantmäteriets originaldata.
- En ny produkt har aviserats till december 2026; kontrollera slutlig produkt, metadata och licens när den publiceras.

### Trafikverket – håll tre produkter separata
- `trafikverket.miljoweb_landskap`: miljö-/landskapslager, veckovis Gräsmyr-pilot med daterade GeoJSON-snapshots och manifest.
- `trafikverket.nvdb.wildlife_collision_frequency`: aggregerad olycksfrekvens per vägsegment, inte individuella olyckor.
- `trafikverket.nvdb.road_network_lastkajen`: lokalt vägnätsunderlag med dokumenterad baslinje; återkommande versionshistorik är ännu inte verifierad.
- `trafikverket.open_data` är endast en katalog-/paraplypost, inte ett bevis på en gemensam insamling eller licens.

### NVR – viltolyckor
- Historiskt material 2015–2026 har hämtats och delats upp per år.
- Äldre händelsearkiv och djurbaserat material hanteras separat.
- Importen 2026-11-09 hade status `partial`; fullständighet/jämförbarhet var inte intygad och saknade händelser undertrycktes.
- Backup med SHA-256-verifiering genomfördes 2026-11-10.
- Ett 30-dagars dagligt observationstest pågår. Kontrollera dagsarkiv, jämförbarhet och dokumenterat godkännande/ändamål innan status höjs.

### Luleå Police–NVR geografisk granskning (intern pilot)
- Separat arbetsbranch: `feat/nvr-police-geographic-review`. Kontrollera alltid branchens relation till aktuell `main` före fortsatt arbete.
- Polisurvalet omfattar både `wildlife_text_line_v1` och `wildlife_time_segment_v2`; `explicit_count_v1` hålls separat som antal, inte individuella olyckor.
- Temporal matchning och geografisk evidens är separata. Geografi får inte ändra temporal score/status eller `geographic_match_used`.
- Geografiberikningen jämför närmaste väg, angivet vägnummer, namngivna NVDB-objekt och – för vägsegment med två ortsankare – avstånd till sammanhängande väggeometri mellan ankarna. Resultatet är review-only.
- Senaste manuellt granskade urvalet omfattade 8 primära kandidatpar och 6 fördröjda kandidatpar. Ingen kandidat är bekräftad. Bland de starkaste geografiska observationerna finns riksväg 97/Notviken, länsväg 383/Smedsbyn och E4/Rutvik–Måttsund.
- `2026-358465` ligger geografiskt nära E4 och Måttsund-referensen; det ger starkare platsstöd för polisuppgift `509449:2` (Måttsund) än för `509449:1` (Norra Rutvik). Behåll båda kandidatkopplingarna i granskningsunderlaget tills manuell bedömning är gjord.
- Fördröjda kandidater ska ligga i separat fil och får inte tolkas som fynd-/eftersökstid; semantiken för NVR-fältet `Datum` är inte verifierad.
- Regression-workflowen `.github/workflows/police-nvr-matching-tests.yml` har passerat 57 riktade tester och den breda `snapshot-store-tests.yml`-workflowen har passerat 272 tester (2026-11-15). Den senare behövde kompletteras med GeoPandas/Pyogrio eftersom den kör hela testsviten. Nästa steg är att köra berikningen på de faktiska lokala Luleå-filerna, kontrollera segmentet Södra Sunderbyn–Notviken och granska de fyra starkaste primära kandidaterna. Ingen nationell NVDB-utökning i detta steg.

### Lantmäteriet – Fastighetsindelning Direkt
- Beställnings-/ärende-ID: LM2026/171963 och LM2026/171968 (registrerade 2026-11-13).
- Hämta och granska det faktiska beslutet och villkoren i Geotorget. Verifiera behörighet och omfattning för kommersiell användning, lagring, historik, bearbetning och kundvisning.
- Teknisk probe är inte ett beviljat produktions- eller återanvändningstillstånd.

### Länsstyrelsernas diarier
- Källornas historik är ojämn; äldre nyheter/ärenden kan försvinna ur webbplatser och API:er.
- Månatliga snapshots är därför viktiga.
- Skilj metadata från dokument och bilagor; granska sekretess, personuppgifter, upphovsrätt och tredje mans rättigheter per handling.

## 6. Prioriterad arbetsordning

1. Verifiera de senaste schemalagda körningarna och snapshotmanifesten för avverkningsanmälningar, Samråd, Trafikverkets pilotflöden, SIS och NVR.
2. Felsök SIS-metadataövervakningen från 13–14 november.
3. Följ upp NVR:s 30-dagars test, jämför exporter och kontrollera att ofullständiga uttag inte ger falska borttagningar.
4. Hämta och granska Lantmäteriets beslut/villkor för LM2026/171963 och LM2026/171968.
5. Fortsätt utöka `operations`-fält i källregistret endast när det finns konkret evidens.
6. Håll den automatiska statusrapporten och denna överlämningsfil uppdaterade när beslut eller arbetssätt ändras.

## 7. Hur en ny chatt ska arbeta vidare

- Börja med att läsa denna fil, statusrapporten och datakälleöversikten.
- Kontrollera sedan relevanta filer, senaste commits och GitHub Actions i repot. Dokumenterade datum är inte bevis för aktuell driftstatus.
- Fortsätt praktiskt i befintliga filer och workflows i stället för att skapa parallella system.
- Gör små, validerbara ändringar och dokumentera varför.
- Kör relevanta tester/validerare. Säg tydligt om CI inte har kunnat verifieras; anta aldrig att en workflow-körning lyckats.
- Uppdatera källregistret och dokumentationen tillsammans när ett nytt faktum har verifierats.
- Fråga bara när ett nödvändigt beslut, en behörighet eller ett användningsval inte kan härledas från projektets dokumentation.

### Startprompt för en ny chatt

> Fortsätt arbetet med Skog/Skogskoll i GitHub-repot dahlinrobert-lgtm/Skog. Börja med att läsa docs/AI_HANDOVER.md, docs/SKOGSKOLL_SOURCE_STATUS.md och docs/SKOGSKOLL_DATA_OVERVIEW.md. Kontrollera aktuellt repo- och workflowläge innan du ändrar något. Följ befintliga arkitektur- och säkerhetsbeslut, arbeta konkret i GitHub och uppdatera överlämningsdokumentationen när nuläget ändras.
