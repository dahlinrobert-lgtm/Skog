# Skog / Skogskoll – överlämning för fortsatt arbete

**Senast uppdaterad:** 2026-11-22  
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

- Nationell ÄFO-karta i Jakt-läget byggs i samma Leaflet-karta som skogshändelserna. Den hämtar polygongeometrier från Länsstyrelsernas JaktAdm ArcGIS REST Feature Layer 1 (`LST Älgförvaltningsområden`) med ID-inventering och chunkad geometrihämtning; WMS-försöket i PR #394 visade endast bakgrundskartan utan synliga gränser och ersätts därför.
- Vid byte till Jakt visas ÄFO-polygonerna samt två separata valbara lager för licensområden och älgskötselområden; skogliga avverknings-, satellit- och samrådsgeometrier rensas. Vid byte till Viltolyckor rensas också skogslagren; ÄFO-lagret visas endast i Jakt. Vid återgång till Skog visas skogslagren igen.
- I älgstatistikvyn visas inte längre det nationella ÄFO-polygonlagret automatiskt; kartan är fri från de stora bakgrundsgränserna tills användaren väljer en statistikrad. Tabellen visar inte kolumnerna Jaktområde och Län; raderna behåller områdesidentitet i tillgänglighetsnamn/titel och är fortfarande klickbara. De fyra återstående kolumnerna får plats inom tabellens bredd med radbrytande rubriker.
- Direkt hämtning av enskild JaktAdm-geometri i webbläsaren har visat `NetworkError` i publicerad GitHub Pages-vy. För att undvika CORS-begränsningen använder områdesvalet nu ArcGIS JSONP (`f=json&callback=...`) och konverterar Esri JSON-geometrier via `arcgisGeometryToGeoJSON`. I älgstatistikläget döljs den separata `casePreview`-panelen helt; kartan får hela layoutbredden och status/fel visas endast i kartans sammanfattningsrad. JSONP-vägen är implementerad men behöver verifieras live i webbläsare mot JaktAdm.
- Efter PR #419 rapporterade användaren fortfarande att klick på exempelvis raden med ÄFO `Norra Hälsingland` inte centrerade kartan. Ny fixgren `fix/elk-row-direct-selection-and-geometry-zoom`: ersätter delegerad radinteraktion med direkta click/keydown-lyssnare som binds efter varje tabellrendering; uppslag sker i den aktuella `matchingAreas`-samlingen. Kartans `fitBounds` körs efter `requestAnimationFrame` och fördröjd `invalidateSize`, med giltiga bounds som krav och `animate:false`. Detta angriper både eventuell händelsedelegering och timing/layout vid kartzoom. JavaScript-syntax och regressionskontroller behöver köras; livehämtning av geometri från JaktAdm och faktisk kartcentrering måste fortfarande verifieras i webbläsaren.
- Efter PR #418 rapporterade användaren att klick på statistikrad inte gav någon synlig kartreaktion och att en tom resultatbadge låg kvar bredvid kartbakgrundsknapparna. Ny fixgren `fix/elk-area-row-selection-and-map-header`: flyttar radinteraktion till delegerade click/keydown-händelser på `#feed` (i stället för att binda per renderad rad), byter primär SQL-matchning från `UPPER(omrnum)` till exakt `omrnum = ...`, visar laddnings-/resultatstatus i `#imageryDate` och döljer tom `#mapSummary`-badge i jaktläget. JavaScript-syntax kontrollerad lokalt; geometrihämtning i riktig webbläsare mot JaktAdm måste fortfarande bekräftas.
- Senaste felsökningen av områdesvalet: tidigare JSONP-flöde gjorde först ID-sökning och därefter en separat objekt-ID-hämtning. Det är ersatt med direkta JSONP-frågor med geometri och attribut i samma ArcGIS-query, primärt matchad med `UPPER(omrnum)` och reservmatchning på områdesnamn/ÄFO. JSONP-timeout sänkt till 12 sekunder. I älgstatistikläget tas den generella jaktlagerkontrollen bort; endast vald geometri ska visas. `mapSummary` döljs i detta läge så inget felmärke visas; tekniska fel loggas i konsolen. Liveverifiering mot JaktAdm återstår.
- I älgstatistiktabellen kan användaren klicka på en rad för att isolera just det jaktområdet på kartan. Matchning sker i första hand via statistikens områdesnummer mot JaktAdm-fältet `omrnum`, med namn/ÄFO som reservmatchning. Vid val döljs övriga jaktområdeslager och ÄFO-lagret; endast den valda områdesgeometrin visas och kartan zoomar till den. Valt område ligger kvar isolerat när tabellen renderas om. Den generiska urvalslogiken ska återanvändas när kronhjortsdata och dess verifierade geometrier tillkommer; kronhjortsstödet är inte implementerat ännu.
- Älgjaktsområden hämtas från JaktAdm MapServer Layer 0 (`LST Älgjaktområden`) som oförenklade originalgeometrier. Licensområden och älgskötselområden har separata valbara lager. Klienten avgränsar ID-sökningen till aktuell kartvy och hämtar geometrier i chunkar först vid zoomnivå 8 eller närmare; den förenklar, klipper eller reparerar inte koordinaterna.
- ÄFO-gränserna hämtas som GeoJSON i EPSG:4326 för Leaflet-visning, med klick/zoom per polygon. Standard/Flygfoto och kartans gemensamma layout återanvänds. Statistikunderlaget är fortfarande regionalt (30 jaktområden för 2026/2027) och är inte joinat till polygonerna; kartan ska därför inte färgsättas som avskjutningskarta ännu.
- Källan är registrerad som `lansstyrelsen.elk_management_areas`. Teknisk åtkomst via REST ska verifieras i webbläsare/CI; datasetsspecifika villkor för extraktion, cache, bearbetning, kommersiell användning och kundvisning är inte verifierade. Behåll attribution till Länsstyrelserna och behandla visning, lagring och vidareanvändning separat.

## 4. Källregister och automatisk rapport

Maskinläsbart register: `data-platform/config/sources.yml`  
Validerare: `data-platform/scripts/validate_source_registry.py`  
Rapportgenerator: `data-platform/scripts/build_source_status_report.py`  
Rapport: `docs/SKOGSKOLL_SOURCE_STATUS.md`

Registret har 49 källposter och 12 poster med ett operativt `operations`-block vid senaste dokumenterade kontrollen. Övriga källor saknar ännu operativ status; det betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.

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
- Regression-workflowen `.github/workflows/police-nvr-matching-tests.yml` har passerat 57 riktade tester och den breda `snapshot-store-tests.yml`-workflowen har passerat 272 tester (2026-11-15). Den senare behövde kompletteras med GeoPandas/Pyogrio eftersom den kör hela testsviten.
- Lokal read-only-analys av väg 97-sträckan Sunderbyn–Notviken har genomförts med användarens separata vägnummer-GPKG och ortnamns-GPKG (EPSG:3006). Två ortankare låg 14,3 m respektive 26,45 m från väg 97-objekt.
- Den manuellt konstruerade vägsträckan omfattade 22 vägobjekt och blev 9 260,48 m efter klippning mellan ankarpunkterna. Geometrin var MultiLineString. Det är ett lokalt diagnostiskt resultat, inte en verifiering av den befintliga NVDB-berikningspipelinen.
- NVR-händelse `2026-348394` (2026-07-20 00:30) låg 3,0 m från den härledda sträckan; temporal status var `temporal_candidate_review`, tidsband `within_15m` och koordinatstatus `consistent`. Detta är endast geografiskt stöd för manuell granskning, inte en bekräftad match.
- NVR-händelse `2026-348777` (2026-07-20 20:16) låg 11 478,39 m från sträckan och hade temporal status `same_date_time_conflict_review`; den ska inte användas som geografiskt stöd för sträckan.
- Viktig avgränsning: polisens text anger Södra Sunderbyn, men den använda ortnamnsankarpunkten för sträckberäkningen var Sunderbyn TRAKTTX. Södra Sunderbyn BEBTÄTTX låg cirka 984 m från väg 97 i den separata vägnummerfilen. Ankare och ortnamnsdetaljtyp måste därför granskas innan sträckan kan betraktas som korrekt tolkad.
- Den lokala vägnummerfilen har annat schema än skriptets förväntade NVDB-lager `NVDB_DK_O_111_Vagnummer` och `NVDB_DK_O_22_Korsning`. Analysen bevisar därför inte att pipeline-skriptet kan reproducera resultatet med sin avsedda NVDB-produkt.
- Nästa steg: inventera lokala Luleå-kandidat- och NVR-filer med fullständiga filnamn, storlekar och datum; välj sedan flera positiva, negativa och tvetydiga geografiska testfall. Kör därefter temporal regression före/efter separat geografisk berikning. Ingen nationell NVDB-utökning i detta steg.

### Lantmäteriet – Fastighetsindelning Direkt
- Beställnings-/ärende-ID: LM2026/171963 och LM2026/171968 (registrerade 2026-11-13).
- Hämta och granska det faktiska beslutet och villkoren i Geotorget. Verifiera behörighet och omfattning för kommersiell användning, lagring, historik, bearbetning och kundvisning.
- Teknisk probe är inte ett beviljat produktions- eller återanvändningstillstånd.

### Länsstyrelsernas diarier

- Källan är fortsatt pilot: åtkomst och historik är delvis verifierade, kommersiell användning är villkorad per handling/post och kundvisning inväntar dokumentgranskning. Två avgränsade Norrbottenkörningar är nu verifierade; detta är inte nationell täckning.
- PR #397 och #399 är sammanslagna i `main`. Den aktuella insamlaren skickar både `seen` och `seen_diary_numbers` till fyrargumentsfunktionen `extract_grid`.
- **Pilot #16:** [GitHub Actions #16](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43964781619), Norrbotten, oktober 2026, kategori B. Sex intervall passerade med `pager_complete=true`, `reconciled=true` och utan fel. Resultaten var vattenverksamhet 15, markavvattning 0, dikesrensning 0, trumma 2, våtmarksanläggning 0 och omgrävning 0. De två trumma-posterna överlappar vattenverksamhet; totalt 15 unika diarienummer. Sex snapshots och sex manifestposter publicerades i `main`; publiceringscommit `dcd75e090ff2c49ad013b2cc2246b1f0d145b97f`.
- **Pilot #17:** [GitHub Actions #17](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43971226392), Norrbotten, september 2026, kategori B. Samtliga fem testmoduler passerade och alla sex intervall var kompletta och avstämda. Resultaten var vattenverksamhet 21, markavvattning 0, dikesrensning 0, trumma 1, våtmarksanläggning 0 och omgrävning 0. Posten under trumma överlappar vattenverksamhet; totalt 21 unika diarienummer. Sex snapshots och sex manifestposter publicerades i `main`, inklusive explicita nollresultat.
- Båda piloternas snapshots ligger under `data/lansstyrelsen-diary/snapshots/2026/11/`; manifestet är `data/lansstyrelsen-diary/snapshot-runs.jsonl`. Tillsammans omfattar de tolv avstämda län/fras-intervallobservationer för två olika registreringsmånader, men bara ett län och kategori B.
- **Ny manuell nationell diagnostikworkflow (PR #406 mergad):** `.github/workflows/lansstyrelsen-national-diary-discovery.yml`. Den delar de 21 länen i sju grupper om tre län och kör en kategori (sex fraser) per workflowkörning. Varje körning omfattar högst 18 län/fras-intervall. Den laddar endast upp diagnostikartefakt i 30 dagar; den anropar inte persistensskriptet, ändrar inte snapshots/manifest och har endast `contents: read`. Den är ännu inte körd eller verifierad mot liveportalen.
- Använd den nya workflowen endast som kontrollerad, manuell discovery efter merge av PR #406. Workflowen är ännu inte live-testad; kontrollera länsnamn och CLI-beteende i första körningen. Kör en grupp i taget; börja inte med alla sju grupper utan att först utvärdera belastning, felmönster och portalens tekniska villkor.
- Den befintliga `.github/workflows/lansstyrelsen-monthly-snapshots.yml` publicerar fortfarande godkända snapshots direkt till `main`. Använd inte den för nationella gruppförsök. Ingen återkommande schemaläggning ska aktiveras.
- Källornas historik är ojämn; äldre ärenden kan försvinna ur webbdiariet. Bevara metadata, skilj dokument/bilagor från metadata och granska sekretess, personuppgifter, upphovsrätt och tredje mans rättigheter per handling.
- Länsstyrelsens tidigare besked om tekniska begränsningar kvarstår. Teknisk åtkomst är inte ett godkännande för obevakad insamling, kommersiell användning eller kundvisning. Frånvaro i ett senare sökresultat får aldrig tolkas som att ett ärende har tagits bort.

## Viltdata – nationell avskjutningsstatistik (uppdaterad 2026-11-18)

### Verifierade kompletta snapshots

- **Körning #1:** [GitHub Actions #44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179), snapshot `20261118T204420Z`, 49 arter, 21 län, 550/550 lyckade statistikförfrågningar, noll fel och 552 filer SHA-256-verifierade. Artifact ID `14470426808`, 423 726 byte, SHA-256 `e7c4076bc5b62a0e05b58df6803b416e57e38b255a34b273efdc3e2678a2f069`, retention till 2026-12-18.
- **Körning #2:** [GitHub Actions #44408345762](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44408345762), snapshot `20261118T220720Z`, 49 arter, 21 län, 550/550 lyckade statistikförfrågningar, noll fel och 552 rå-/metadatafiler SHA-256-verifierade. De 550 statistikfilerna tillsammans innehåller 73 255 datapunkter (datasetvärden). Artifact ID `14475804318`, 423 705 byte, ZIP-SHA-256 `31ef0b6ac7c16fa524adaa9f1e5ed9037f19bd3a9cb714bdea16e6ad8264e0b2`, manifest-SHA-256 `ed7937c8f83657b51af98f88566cce675555d0a4d017111f3fb7a24ecdc72088`, retention till 2026-12-18 22:24:19 UTC.
- Körning #2 kompilerade båda skripten och passerade 10/10 riktade snapshot-/diff-tester. Manifestet har `status=complete`, `complete=true`, `statistics_requests_ok=550`, `statistics_requests_expected=550` och `errors=[]`. Artifacten innehåller 553 ZIP-poster (552 manifeststyrda källfiler samt manifest). Den har laddats ned och manifest, filantal, körnings-ID och SHA-256 har granskats.
- Båda snapshots är separata tidsstämplade observationer. De är tillfälliga GitHub Actions-artifacts med 30 dagars retention, inte permanent backup eller Azure-arkiv. Värden från rapporteringsår som ännu inte är slutrapporterade kan ändras vid senare uttag.
- Fortsatt manuell insamling kan köras oberoende av Azure-arkivering. Workflowen `.github/workflows/viltdata-kill-statistics-manual.yml` har ingen schedule och skriver inte till Azure.

### Azure och arkivering

- PR #427 är mergad i `main` (merge commit `7f4077b53ccb2d9d8308daa278d7fcb6674e79ee`). `scripts/viltdata_azure_archive.py` och `.github/workflows/viltdata-azure-archive.yml` erbjuder manuell upload/audit/restore. Upload kräver komplett manifest, samtliga råfiler och SHA-256/bytekontroll; create-only-semantik används. `rights_approved` är default false. PR-CI #476 och main-CI #483 passerade båda 322 tester, inklusive 8 arkivtester.
- Azure syntetiskt write/readback-test passerade i [run #44401688469](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44401688469). Endast syntetiska testobjekt skrevs; inga Viltdata-original har laddats upp.
- Storage Account `stskogkolldata` har verifierad Azure Portal-location `swedencentral` (Sweden Central).
- IAM visar tjänstens huvudnamn `skogskoll-github-actions` med rollen `Storage Blob Data Contributor` på scope `This resource` (Storage Account-nivå). Identiteten delas av flera Skog-workflows, bland annat Kungjort och polisdata. Ändra inte dess roll/scope utan konsekvensanalys; separat containeravgränsad identitet kan övervägas senare.
- Användaren har skickat mejl till dataleverantören. Skriftligt besked om historisk lagring och avsedda användningar inväntas. Fortsatt manuell hämtning till tidsbegränsade artifacts fortsätter; permanent Azure-arkivering är separat och `rights_approved` ska inte kringgås.

### Historik och nästa steg

- Första kompletta snapshot ska vara tyst baslinje utan historiska larm. Ofullständiga uttag får inte användas som baslinje eller jämförelse.
- Nästa tekniska steg är att jämföra snapshot `20261118T220720Z` med `20261118T204420Z` med befintligt diff-script. Kontrollera först att båda manifest och observationstäckning godkänns av skriptet. Spara diffen separat och tolka 2026-förändringar som rapporteringsvärden, inte automatiskt som avslutade årsvärden.
- Därefter fortsätt manuella kompletta snapshots. När skriftligt rättighetsbesked finns, besluta om Azure-upload och eventuell separat least-privilege-identitet; live-verifiera sedan upload, audit och restore.
- Ingen schemaläggning eller kundvisning är aktiverad.
## 6. Prioriterad arbetsordning

1. Verifiera de senaste schemalagda körningarna och snapshotmanifesten för avverkningsanmälningar, Samråd, Trafikverkets pilotflöden, SIS och NVR.
2. Felsök SIS-metadataövervakningen från 13–14 november.
3. Följ upp NVR:s 30-dagars test, jämför exporter och kontrollera att ofullständiga uttag inte ger falska borttagningar.
4. Hämta och granska Lantmäteriets beslut/villkor för LM2026/171963 och LM2026/171968.
5. Fortsätt utöka `operations`-fält i källregistret endast när det finns konkret evidens.
6. Håll den automatiska statusrapporten och denna överlämningsfil uppdaterade när beslut eller arbetssätt ändras.



## 8. Bevakningsflöde – experimentell scrollprototyp

- En separat testvy finns i `docs/bevakning-test.html`; den ordinarie `docs/bevakning.html` är oförändrad.
- Prototypen har en vertikal händelsetidslinje, läsprogress, diskreta scrollövergångar och synkronisering mellan aktiv händelse och kart-/ärendepanel. På mobil staplas flöde och karta.
- Kartan/ärendepanelen förhandsvisar automatiskt den händelseruta som läsaren stannar vid i 250 ms. Hela händelserutan är klickbar och fungerar även med Enter/mellanslag; länken ”Öppna kartan” är separat. Kartan använder Esri World Imagery och hämtar bilddatum samt källuppgift för kartans mittpunkt från Esris metadata när kartutsnittet ändras.
- Prototypen använder befintlig datainläsning, filter och kartfunktioner. Animationer respekterar `prefers-reduced-motion`.
- PR #370, #373, #374 och #378 är sammanslagna. PR #374 gör hela händelserutan klickbar och behåller ”Öppna kartan” som separat länk. PR #378 bytte till Esri World Imagery och visar bilddatum/källa från metadata för kartans mittpunkt. En efterföljande textfix tar bort parentesen ”(kartans mittpunkt)” från den synliga etiketten; datumfrågan hämtas fortfarande för kartans mittpunkt. Bilddatumetiketten reserverar höjd för två textrader så att kartsektionen inte hoppar när datum-/källtexten radbryts.
- **Nästa steg:** granska testvyn manuellt avseende scrollkänsla, kartkoppling, mobil, tangentbordsnavigering och prestanda. Ersätt inte den officiella sidan innan användaren har godkänt resultatet.

## 9. Hur en ny chatt ska arbeta vidare

- Börja med att läsa denna fil, statusrapporten och datakälleöversikten.
- Kontrollera sedan relevanta filer, senaste commits och GitHub Actions i repot. Dokumenterade datum är inte bevis för aktuell driftstatus.
- Fortsätt praktiskt i befintliga filer och workflows i stället för att skapa parallella system.
- Gör små, validerbara ändringar och dokumentera varför.
- Kör relevanta tester/validerare. Säg tydligt om CI inte har kunnat verifieras; anta aldrig att en workflow-körning lyckats.
- Uppdatera källregistret och dokumentationen tillsammans när ett nytt faktum har verifierats.
- Fråga bara när ett nödvändigt beslut, en behörighet eller ett användningsval inte kan härledas från projektets dokumentation.

### Startprompt för en ny chatt

> Fortsätt arbetet med Skog/Skogskoll i GitHub-repot dahlinrobert-lgtm/Skog. Börja med att läsa docs/AI_HANDOVER.md, docs/SKOGSKOLL_SOURCE_STATUS.md och docs/SKOGSKOLL_DATA_OVERVIEW.md. Kontrollera aktuellt repo- och workflowläge innan du ändrar något. Följ befintliga arkitektur- och säkerhetsbeslut, arbeta konkret i GitHub och uppdatera överlämningsdokumentationen när nuläget ändras.


### Lantmäteriet Ortnamn – tillägg till Luleå Police–NVR-piloten (2026-11-15)
- Ortnamn Nedladdning, vektor är tekniskt åtkomlig via användarens Geotorget-behörighet.
- Verifierad STAC collection/item: `ortnamn` / `ortnamn_se`; nationell GeoPackage EPSG:3006. Autentiserad ZIP-nedladdning fungerade 2026-11-13 (58 553 634 byte; innehåller `ortnamn_se.gpkg`, 156 000 256 byte).
- Ortnamn ska komplettera NVDB vid tolkning av ort-/områdesnamn i polisens fritext, särskilt Sunderbyn/Södra Sunderbyn och Notviken. Ortnamnspunkter kan vara kartografisk textplacering och får inte användas som exakta olyckspositioner eller ortsgränser.
- Ny read-only inspektionskod: `scripts/inspect_ortnamn_geopackage.py`; tester: `tests/test_inspect_ortnamn_geopackage.py`.
- Lokal GeoPackage-inspektion kördes 2026-11-15: ett lager (`ortnamn`), 990 073 objekt, EPSG:3006 och 53 textträffar för Sunderbyn/Notviken. Fyra riktade tester passerade.
- Kommunfiltrering på `kommunkod=2580` gav 11 lokala träffar i det granskade utdraget: Norra Sunderbyn (1), Sunderbyn (1), Södra Sunderbyn (2), Notviken (6) och Notvikens badplats (1). De lokala Notviken-posterna har flera observerade `detaljtyp`-värden; behåll källkoderna utan att hårdkoda semantik innan produktens officiella kodlista har verifierats.
- `lopnummer` behålls endast som källattribut och får inte antas vara stabilt eller unikt. `source_row_index` är endast en positionsreferens i aktuell snapshot.
- PR #376 är sammanslagen i `main` (merge commit `de0f3f3181b8ae53eeb5d5f7a058afda9d2ab17a`). Read-only-exportskriptet `scripts/export_ortnamn_municipality_reference.py` och testerna `tests/test_export_ortnamn_municipality_reference.py` finns nu i `main`.
- Full kommunexport kördes lokalt 2026-11-15 med status `completed_read_only`: 6 239 objekt för kommunkod 2580 från 990 073 nationella objekt, EPSG:3006. Källfilens SHA-256: `3a3d26bc3ec95142f47208cc6afaff45a70e5ee04417f770d058777a5465a92d`.
- Fördelning per källans `detaljtyp`: TERRTX 2 314; TRAKTTX 866; BEBTX 806; SANKTX 680; VATTTX 568; VATTDELTX 435; VATTDRTX 371; ANLTX 68; NATTX 58; KULTURTX 48; BEBTÄTTX 19; KYRKATX 6. Koderna bevaras som råa källvärden; semantik ska verifieras mot Lantmäteriets aktuella kodlista.
- Kommunexportens CSV och JSON-rapport ligger i användarens OneDrive working-mapp och har inte committats. Käll-GeoPackage har inte ändrats.
- Lokala tester för exportskriptet: 4/4 passerade. Lokal körning mot GeoPackage: `completed_read_only`, 6 239 objekt exporterade för Luleå (2580), SHA-256 ovan. Detta verifierar exporten för den aktuella filen, inte framtida snapshots eller rättigheter.
- Nästa steg: analysera kommunexportens relevanta namn och detaljtyper mot NVDB:s väg 97-ankare. Behåll Ortnamn som namn-/områdesreferens; inga automatiska matchningar eller bekräftelser. Kommersiell användning, lagring, bearbetning och kundvisning är fortsatt ej bedömda. Kommersiell användning, lagring, bearbetning och kundvisning är fortsatt ej bedömda.
- Kommersiell användning, historisk lagring, bearbetning och kundvisning är inte bedömda genom den tekniska nedladdningen.


## NVR – rättighetsbesked 2026-11-15
- Polismyndigheten har i ett skriftligt mejlsvar (utdrag tillhandahållet 2026-11-15) bekräftat att NVR-materialet är offentlig information, att CSV-uttaget omfattar de djurposter myndigheten har tillgång till från 2015 och framåt och att återkommande hämtning/arkivering för egen geografisk analys och statistik är tillåten med källhänvisningen **Nationella viltolycksrådet**.
- Beskedet omfattar inte uttryckligen vidare distribution av rådata eller en fristående rådatatjänst. Se `docs/source-rights-reviews/2026-11-15-nvr-public-information-attribution.md`.
- Historik 2015–2026 finns arkiverad, men importen 2026-11-09 var `partial`; ofullständiga körningar får inte ge falska borttagningar.

## Bevakningsprototyp – nästa filterstruktur
- Separata filtergrupper ska finnas: skogliga aktiviteter (Alla/Planerade/Utförda/Samråd) samt vilt och jakt (Alla/Viltolyckor/Jakt).
- Samråd ska visas med Skogsstyrelsens tre geolager: punkt, linje och polygon, och visa källans datum.
- Älgstatistiken flyttas till Jakt. Viltolyckor ska visa individuella NVR-händelser med datum och geometri samt källtexten **Källa: Nationella viltolycksrådet (NVR)**.
- Älgvyn i testprototypen visar en förändringshistorik från varje jaktområdes `snapshots`: varje rad är en icke-noll differens mellan två tillgängliga snapshots. Både ökningar och minskningar visas med tecken och respektive snapshots totalvärde/datum. Baslinjer med `delta: null` och oförändrade snapshots visas inte. Saknade snapshots ger ingen interpolerad dagsförändring. En minskning presenteras som observerad ändring/rättelse, inte som bevis för att tidigare fällda djur tagits bort.
- Älgvyns informationsruta har särskild dark-mode-styling; negativa och positiva differenser har separata färger.
- Filtersektionen har två rubrikrutor: **Skog** med minimalistisk trädillustration ovanför Planerade/Utförda/Samråd och **Djur** med minimalistisk djurillustration ovanför Viltolyckor/Jakt. Rubrikrutorna matchar filtergruppernas bredd och har samma 37 px höjd som filterraden. Skog-gruppen döljs i Djur-lägena. Dark mode har särskild färgsättning.
- Den godkända scrollprototypens UI har flyttats till den skarpa sidan `docs/bevakning.html`; sidan har kvar sin ordinarie URL och är inte längre märkt som test. `docs/bevakning-test.html` behålls som separat prototyp-/referenssida.
- Kartan har växling mellan **Flygfoto** (Esri World Imagery) och **Standard** (OpenStreetMap). Kartgeometrier får bakgrundsanpassade färger: flygfoto använder orange för planerad avverkning, cyan för satellitindikation/utförd och gul för samråd; standard behåller de tidigare färgerna (orange planerad, grön övrig). Bilddatum hämtas bara i flygfotoläget och pågående metadataförfrågningar ogiltigförklaras vid byte till standard.
- I filtersektionen ska både **Skog**- och **Djur**-rubrikrutor alltid vara synliga. När viltolyckor eller jakt väljs markeras Djur-rubriken som aktiv, medan Skog-rubriken och dess filterrad ligger kvar synliga. I skogsläget markeras Skog-rubriken. Aktiv rubrik har tydligare bakgrund, kant och kontrast även i dark mode.
- Aktiv markering av kategorirubriker är separat från datalägets `animalMode`: `activeFilterCategory` sätts av den senast använda filtergruppen. Klick i Skog-gruppen aktiverar Skog och återgår till skogsläget; klick i Djur-gruppen aktiverar Djur. Därmed kan Djur-knappen **Alla** inte av misstag få Skog-rubriken att lysa. 
- NVR-arkivet finns i OneDrive. GitHub Pages saknar ännu en verifierad publik, skrivskyddad läsendpoint; publicera inte OneDrive-rådata eller autentiseringsuppgifter direkt. Etablera en kontrollerad endpoint med manifest och fullständighetsstatus först.
- Fortsätt endast i `docs/bevakning-test.html`; ändra inte `docs/bevakning.html` innan prototypen har godkänts.

## Police–NVR geografisk matchningsmodell – designarbete (2026-11-15)
- Ny designfil i branch `feat/police-nvr-geographic-match-model`: `docs/police-nvr-geographic-match-model.md`.
- Målet är en förklarbar, review-only modell som kombinerar temporal evidens, art, vägkontext, avstånd från NVR-koordinat till oberoende konstruerad vägkorridor och platsnamn.
- Polisens informella vägtext ska kunna matchas mot ramp/anslutningsväg när verifierad NVDB-topologi visar kopplingen till angiven huvudväg. En ramp mellan två större vägar kan behålla båda vägidentiteterna; närhet ensam får inte skapa anslutning.
- En preliminär 0–100-poäng diskuteras endast som ordinal prioritering för manuell granskning, inte som sannolikhet. Kalibrering kräver manuellt märkta positiva, negativa och tvetydiga exempel.
- Ingen kod för matchningslogik, temporal logik, källdata eller produktionsflöde har ändrats i detta designsteg.
- Aktuell begränsning: `scripts/enrich_police_nvr_geography.py` läser vägnummerattributen `ELEMENT_ID`, `Europavag`, `Huvudnummer`, `Lankroll` och korsningsattribut, men etablerar inte verifierad topologisk koppling mellan ramper och huvudvägar.
- Nästa steg: verifiera NVDB:s faktiska nätverksfält och ramp-/anslutningsobjekt i den använda produkten. Först därefter implementera och testa separat vägkontext/avståndsmodell, med invarians att temporal kandidatlista, poäng och status är oförändrade.

## NVDB-topologi för Police–NVR – nästa verifieringssteg (2026-11-15)
- PR #385 är enligt användaren merged till main. Matchningsmodellens design finns i `docs/police-nvr-geographic-match-model.md`.
- Trafikverkets offentliga NVDB-dokumentation har nu kontrollerats: vägnätets topologi representeras av referenslänkar, noder och portar. Referenslänkar har start-/slutnoder och portkopplingar representerar anslutning mellan nätelement. Enskilda företeelselager/linjegeometrier är inte automatiskt ett komplett routningsnät.
- Officiella referenser: Trafikverkets dataproduktspecifikationer för vägdata, introduktion till NVDB:s vägnät och företeelser, NVDB:s aktuella datamängder (bl.a. Vägnummer och Vägtrafiknät) samt Trafikverkets dokument om ruttnning med NVDB. Se länkar i `docs/police-nvr-geographic-match-model.md`.
- Ny read-only-inspektör i branch `feat/inspect-nvdb-network-topology`: `scripts/inspect_nvdb_network_schema.py`. Den listar GPKG-lager, geometri, antal objekt, CRS och fält, samt markerar fältnamn som kan vara topologirelaterade. Den läser inte ut feature-rader, ändrar inte källfilen och drar inga slutsatser om faktisk anslutning.
- Nytt test: `tests/test_inspect_nvdb_network_schema.py`; Police–NVR-workflowen har uppdaterats så att testet körs.
- Inspektören har ännu inte körts mot användarens lokala NVDB-GPKG. Nästa steg är att köra den mot det exakta vägnäts-GPKG som innehåller referenslänkar/noder/portar (inte enbart vägnummer- eller korsningslager), och därefter jämföra faktiska fält och värden med rätt dataproduktspecifikation.
- Ingen matchningskod eller temporal logik har ändrats. Ingen geometri har kopplats ihop automatiskt. Nästa implementeringsbeslut väntar på schema- och topologiverifiering.


## Nationell NVDB-närmaste-väg-matchning – första prototyp (2026-11-16)

- Beslut: prioritera **A. Nationell automatisk vägmatchning**. Grundmetoden ska hitta närmaste NVDB-vägnummerobjekt till en händelsekoordinat och redovisa vägnummer, avstånd och alternativa kandidater. Full nätverksrekonstruktion används bara vid särskilt tvetydiga fall.
- Separat branch från aktuell main: `feat/national-nvdb-road-proximity`.
- Nytt skript: `scripts/match_points_to_nvdb_roads.py`. Det accepterar flera länsvisa GeoPackage-filer, läser vägobjekt via lokalt bbox-filter runt varje WGS84-koordinat och skriver en ny review-CSV. Indata ändras inte.
- Ny testfil: `tests/test_match_points_to_nvdb_roads.py`; Police–NVR-testworkflowen har uppdaterats för att köra dessa tester.
- Ny metodbeskrivning: `docs/national-nvdb-road-proximity.md`.
- Matchningen är review-only. Temporal kandidatgenerering, score, status och `geographic_match_used` ska förbli oförändrade. Ett misslyckat källuttag ger `partial_source_read`; inga träffar i sökfönstret är inte bevis för att väg saknas eller att positionen inte hör till en väg.
- Nationell drift är inte verifierad. Lastkajens faktiska GPKG-filer, lager, CRS, fullständig täckning, länsgränsöverlapp, prestanda och användningsvillkor måste kontrolleras.
- Nästa steg: kör riktade tester och en liten Luleå-pilot med den faktiska NVDB-GPKG-filen. Därefter testa flera länsfiler och representativa positiva, negativa och tvetydiga fall. Kör separat temporal regression före/efter; ändra inte temporal matchningslogik.


## NVDB – nationell länsarkivsinventering (2026-11-16)
- OneDrive-mappen `Skogskoll/Lastkajen/Länsfiler NVDB data` inventerades via Microsoft Graph: 21 länsvisa GeoPackage-ZIP-filer, 10 677 114 317 byte totalt. Samtliga 21 länsfiler fanns i molnmappen vid kontrollen.
- Detta verifierar endast arkivmetadata (namn, storlek och existens), inte innehållet, NVDB-lager, CRS, schema eller geografisk täckning.
- Ny read-only-inspektör i arbetsbranch `feat/national-nvdb-archive-inventory`: `scripts/inventory_nvdb_county_archives.py`. Den använder ZIP-medlemsmetadata och GDAL `/vsizip/` för att lista GeoPackage-lager och läsa lagerdefinitioner utan att extrahera eller ändra källarkiven.
- Målager: `NVDB_DK_O_111_Vagnummer`; obligatoriska fält: `ELEMENT_ID`, `Europavag`, `Huvudnummer`, `Lankroll`. Rapporten ska markera saknat lager/fält eller läsfel som avvikelse/partial, aldrig som bevis på att en väg saknas.
- Testfil: `tests/test_inventory_nvdb_county_archives.py`. Testerna är tillagda men har ännu inte körts i denna arbetsmiljö. Ingen nationell matchning har körts.
- OneDrive-originalen ska lämnas orörda. Rapporten ska sparas separat i OneDrive working-/inventory-yta. Nationell matchning startar först när kompatibilitetsinventeringen är genomförd och granskad.
- Nästa steg: användaren kör inspektören lokalt mot `C:\\Users\\dahli\\OneDrive\\Skogskoll\\Lastkajen\\Länsfiler NVDB data`; granska JSON-rapportens status per län och därefter besluta om ett gemensamt spatialt index eller direkt flerkällefråga.

## NVDB – direktinspektion av länsarkiv och nästa steg (2026-11-16)

- Den första arkivinventeringen fann 21 ZIP-arkiv (10 677 114 317 byte). `pyogrio.list_layers()` misslyckades i samtliga med `Geometry type is not supported: -2147483648`; detta är inte bevis för skadade arkiv eller saknade vägdata.
- Lokal miljö som användes: Python 3.12.10, Pyogrio 0.13.0, GDAL 3.12.4 via Pyogrio och SQLite 3.49.1. Python-paketet `osgeo` och kommandot `ogrinfo` saknas, men behövs inte för den fungerande metoden.
- Read-only-prober via `pyogrio.read_dataframe(..., sql_dialect="SQLITE")` kunde läsa `gpkg_contents` och `gpkg_geometry_columns` direkt ur Gotlands ZIP-medlem via `/vsizip/`.
- Direkt `pyogrio.read_info(path, layer="NVDB_DK_O_111_Vagnummer")` fungerade i två län:
  - Gotland: 6 203 objekt, EPSG:3006, obligatoriska fält finns.
  - Västerbotten: 26 902 objekt, EPSG:3006, obligatoriska fält finns.
  - Båda rapporterade geometrityp `Unknown`; faktisk geometri ska verifieras separat. Det är inte i sig bevis för att geometrin saknas.
- Branch `fix/nvdb-direct-layer-inventory` har skapats från main commit `acecd548b4da041766381b5ac07d306a1e7fa93b`. Den ersätter lagerlistning med en riktad fråga mot `gpkg_contents` och direktinspektion av vägnummerlagret. Den kontrollerar obligatoriska fält och EPSG:3006, behåller partiell status vid tekniska fel och bevarar originalarkiven.
- Tester har uppdaterats för direktinspektion, Unknown-geometri, saknat lager, saknade fält, fel CRS och tekniska läsfel. CI och faktisk körning mot samtliga 21 län återstår att verifiera.
- Nästa steg: granska PR och CI, låt användaren uppdatera sin lokala branch utan att skriva över ocommittade filer, kör inventeringen mot alla 21 ZIP och analysera rapporten. Nationell matchning är fortfarande inte körd; den ska förbli review-only. Temporal matchning, kandidatlista, score, status och `geographic_match_used` får inte ändras av geografi.


## NVDB – nationell metadata- och geometristickprovskontroll (2026-11-17)

- Användarens read-only-inventering av samtliga 21 länsvisa Lastkajen-arkiv är slutförd: 21/21 har status `compatible`, utan arkivfel. Arkivens sammanlagda storlek är 10 677 114 317 byte (cirka 9,94 GiB).
- Mållager: `NVDB_DK_O_111_Vagnummer`. Metadata visar totalt 456 444 features i de 21 länsarkiven. Obligatoriska attributfält `ELEMENT_ID`, `Europavag`, `Huvudnummer` och `Lankroll` finns enligt den genomförda kompatibilitetsinventeringen.
- Geometristickprov genomfördes read-only med 500 distribuerade features per län, totalt 10 500. Samtliga 21 län rapporterade EPSG:3006, exakt 500 av 500 förväntade stickprovsfeatures, endast `LineString`, 500 giltiga geometrier, 0 null, 0 tomma, 0 ogiltiga och 0 stickprovsfel.
- Geometristickprovsrapport: `OneDrive\\Skogskoll\\Lastkajen\\nvdb-geometry-national-sample-20261116.json`. Inspektionsskript: `OneDrive\\Skogskoll\\Lastkajen\\inspect_nvdb_geometry_national.py`. Körningen rapporterade `completed`, 21 arkiv, 0 fel, `read_only=true` och `source_archives_modified=false`.
- Detta är metadata-/schema-kompatibilitet och ett distribuerat geometristickprov, inte fullständig geometri-validering av samtliga 456 444 features, verifierad vägkilometer-/nätverkstäckning, sömlös länsgränsöverlappning eller bevis på att alla NVDB-produkter/versioner är jämförbara.
- Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution är fortsatt separata rättighetsfrågor och inte godkända genom denna tekniska kontroll.
- Nästa steg: genomför en avgränsad nationell vägmatchningspilot med representativa positiva, negativa och tvetydiga testfall, mät prestanda och kontrollera länsgränser/täckning. Behåll strikt review-only: geografi får inte ändra temporal matchning, kandidatlista, score, status eller `geographic_match_used`. Kör temporal regression före/efter.


### NVDB – ZIP-baserad vägmatchningspilot (2026-11-17)
- PR #409 och PR #410 är sammanslagna. Windows/GDAL `/vsizip/`-fixen är CI-verifierad (Snapshot storage tests #465 och Police–NVR matching tests #19 enligt användaren).
- Efter uppdatering av lokal `main` kördes `scripts/match_points_to_nvdb_roads.py` mot `nvdb-nearest-road-review-v1.csv` och Norrbottens + Västerbottens Lastkajen ZIP.
- Faktiskt underlag: **8 indata-/utdataposter**. Äldre dokumentation nämnde 9; korrigera den uppgiften, eftersom lokal `Import-Csv` och matcharens rapport båda visar 8 poster.
- Körstatus: `completed`; 2 källor; 0 källinitialiseringsfel; per post `geo_nvdb_sources_queried=2`, `geo_nvdb_sources_failed=0`; samtliga 8 har `completed_with_candidates`.
- Närmaste vägavstånd: 1,01–464,91 m. `geo_nvdb_candidate_count` varierade mellan 1 och 26 (totalt antal deduplicerade kandidater före begränsning till högst 5 returnerade kandidater).
- Temporal-/icke-geografisk regression: användaren jämförde samtliga 39 icke-`geo_*`-fält rad för rad mellan indata och utdata; **0 skillnader**. Detta verifierar att matcharskriptet bevarade indatans övriga fält i utdata, men ersätter inte separat regression av en eventuell senare temporal matchningspipeline.
- Resultatet är fortsatt endast review-only. Ingen nationell produktionskörning eller kundvisning är aktiverad.
- Nästa steg: manuellt granska vägkandidaterna mot karta/ort och kontrollera särskilt den längsta distansen. Därefter bygg ut testunderlaget med manuellt bedömda positiva, negativa och tvetydiga fall och fler län. Mät körtid och kontrollera länsgränser/täckning innan nationell pilot.
- Geografisk evidens får inte påverka temporal kandidatgenerering, kandidatlista, score, status eller `geographic_match_used`. Bevara originalarkiv och historik.



### NVDB – GeoJSON för manuell väggranskning (2026-11-17)
- Nästa steg efter den verifierade tvålänspiloten är manuell kartgranskning av 8 händelsepunkter och närmaste/alternativa vägkandidatlinjer.
- Branch `feat/nvdb-road-review-geojson` lägger till valfri `--geojson-output` i `scripts/match_points_to_nvdb_roads.py`. Den separata WGS84 GeoJSON-filen innehåller händelsepunkter och de valda kandidatvägarnas faktiska geometrier, med egenskaper för radnummer, kandidatordning, närmaste kandidat, vägnummer, roll, avstånd, element-ID och källfil.
- CSV-resultatets befintliga kandidatschema hålls oförändrat; geometri läggs endast i den separata GeoJSON-exporten. Indata ändras inte. Exporten är review-only och innehåller koordinater, så filen ska hanteras som lokal arbetsdata.
- PR #411 är sammanslagen i main (merge commit `29b2cf6b1838236fcbef57fb2ddd0d1ce2969422`). Det riktade testet för EPSG:3006 till WGS84 ingår i den sammanslagna ändringen.
- Lokal två läns körning har därefter verifierats: 8/8 händelser, två källor, noll initialiseringsfel och 43 GeoJSON-features. Händelse 6 har 464,91 m till närmaste kandidat och ska prioriteras i kvalitetsgranskningen. Ingen kandidat får bekräftas automatiskt.
- Ingen ändring i temporal matchning, score, status eller `geographic_match_used`. Ingen ny beständig lagringsplats i repot; därför ingen ändring av `STORAGE_INVENTORY.md`.



## NVDB – nationell valideringsrapport (2026-11-17)

En första fristående, standardbiblioteksbaserad rapportbyggare har lagts till i utvecklingsbranch `feat/nvdb-national-validation-report`:
- `scripts/build_nvdb_validation_report.py` läser matchningsskriptets CSV-utdata och skriver en JSON-kvalitetssammanfattning samt en separat CSV-kö för manuell granskning.
- Alla flaggade poster behålls. Icke-flaggade poster tas dessutom ut med ett deterministiskt stickprov per förekommande `source_file`.
- Rapporten innehåller sökstatusar, källäsningsfel, avståndsfördelning, kandidatantal och urvalsparametrar. Flaggor omfattar icke-standardstatus, långa avstånd och nära alternativa kandidater.
- Testfil: `tests/test_build_nvdb_validation_report.py`.
- Dokumentation: `docs/nvdb-national-validation-report.md`.

Viktiga begränsningar: källfilernas förekomst i kandidatlistor bevisar inte geografisk täckning; rapporten mäter inte precision/recall eller faktisk vägträffsäkerhet utan manuellt facit. Radnummer är endast körningslokal referens. En stabil händelse-ID-kolumn bör anges när sådan finns. Trösklarna är granskningsurval, inte automatiska kvalitetsbesked. Ingen temporal logik, kandidatlista, score/status eller `geographic_match_used` ändras.

**Verifiering återstår:** kör riktade tester och rapportbyggaren lokalt mot den befintliga åttahändelsepiloten. Därefter benchmarka med representativa urval från flera län och kalibrera urvalsreglerna mot manuellt bedömda fall. Nationell drift är inte godkänd eller aktiverad.


## NVDB – nationell valideringsrapport (2026-11-17)

PR #412 är sammanslagen i main: [Add scalable NVDB validation report and review queue](https://github.com/dahlinrobert-lgtm/Skog/pull/412), merge commit `c33ea60f92f94b6b6326851b42a492517a550f12`. GitHub Actions är verifierad: Police–NVR matching and geographic evidence tests #24 och Snapshot storage tests #470 slutfördes med `success`.

Implementation:
- `scripts/build_nvdb_validation_report.py` läser matchnings-CSV och skriver JSON-kvalitetssammanfattning samt separat CSV-kö för manuell granskning.
- Alla flaggade poster behålls; icke-flaggade poster tas med genom deterministiskt stickprov per förekommande källfil.
- Testfil: `tests/test_build_nvdb_validation_report.py` (fem riktade tester), kopplad till Police–NVR-workflowen.
- Dokumentation: `docs/nvdb-national-validation-report.md`.

**Nästa konkreta steg:** kör rapportbyggaren lokalt mot den befintliga åttahändelsepiloten och granska JSON/CSV-resultatet. Därefter skapa ett manuellt bedömt referensurval från flera län, benchmarka körtid/minne och kalibrera urvalsregler. Rapporten mäter inte precision/recall eller faktisk vägträffsäkerhet utan oberoende facit. Källfilernas förekomst bland kandidater bevisar inte geografisk täckning.

Ingen temporal matchningslogik, kandidatlista, score/status eller `geographic_match_used` ändras. Ingen nationell produktionskörning eller kundvisning är godkänd genom PR #412.


## NVDB – nationell egenskapsanalys (2026-11-17)

Användarens inriktning är att prioritera storskalig nationell analys framför manuell rad-för-rad-granskning av den första åttahändelsepiloten. En ny separat feature-extraktor har därför lagts till i branch `feat/nvdb-national-feature-analysis`:
- `scripts/build_nvdb_candidate_features.py` skapar en händelsenivåfil, en kandidatnivåfil och en JSON-sammanfattning från matcharens befintliga CSV.
- Funktioner omfattar närmaste/näst närmaste avstånd, avståndsgap och kvot, kandidatantal, vägnummer, vägroll, element-ID, källproveniens, sökstatus och källfel.
- `tests/test_build_nvdb_candidate_features.py` testar extraktion, trasig JSON och nollavstånd.
- `docs/nvdb-national-feature-analysis.md` beskriver metod och begränsningar.
- Police–NVR-workflowen utökas för att köra de nya testerna.

Detta är beskrivande feature-extraktion, inte en klassificerare eller kvalitetsmärkning. Utan oberoende facit kan klustring och statistik identifiera samvariation men inte bevisa korrekt väg. Kandidatlistans maxgräns begränsar vilka alternativ som går att analysera. Inga temporala fält eller matchningsbeslut ändras.

**Nästa steg:** invänta CI för PR, kör extraktorn mot åttahändelsepiloten för schema-/funktionskontroll och planera därefter benchmarkad nationell matchning mot de 21 länsarkiven. Mät körtid/minne och redovisa partiella källfel separat. Nationell matchning ska fortsatt vara analys/review-only.


## NVDB – nationell egenskapsanalys PR #413 sammanslagen (2026-11-17)

PR #413 [Add national NVDB candidate feature analysis](https://github.com/dahlinrobert-lgtm/Skog/pull/413) är sammanslagen i main. Merge commit: `408b098bbfa405d8cfe58f8e4c40f3e2295a18f8`.

Implementationen innehåller:
- `scripts/build_nvdb_candidate_features.py`: extraherar händelse- och kandidatnivåegenskaper ur matchnings-CSV och skriver två CSV-filer samt JSON-sammanfattning.
- `tests/test_build_nvdb_candidate_features.py`: tre tester för normal extraktion, felaktig kandidat-JSON och nollavstånd.
- `docs/nvdb-national-feature-analysis.md`: körinstruktioner, analysidé och begränsningar.
- Police–NVR-workflowen kör de nya testerna.

Användarens beslutade inriktning är nationell, datadriven analys av återkommande egenskaper – inte manuell rad-för-rad-granskning av åttahändelsepiloten. Extraktorn beskriver bland annat avståndsgap/kvot mellan de två närmaste kandidaterna, vägnummer, vägroll, kandidatantal, element-ID, källproveniens och sökstatus.

**Verifieringsstatus:** PR är bekräftat merged. Workflowresultat för merge commit behöver kontrolleras separat. Ingen nationell matchningskörning eller träffsäkerhetsmätning är ännu verifierad. Nästa steg är att köra extraktorn mot pilotfilen för att verifiera utdataformatet och därefter förbereda en benchmarkad nationell matchningskörning mot de 21 länsarkiven.

Begränsningar: egenskaper och kluster är inte facit; de kan visa samvariation men inte ensamma bevisa rätt olycksväg. Ingen temporal kandidatlista, score, status eller `geographic_match_used` ändras. Ingen automatisk bekräftelse eller kundvisning aktiveras.


## Rovbase – initialt dataintag (2026-11-18)

- Originaluttag mottaget och arkiverat oförändrat i OneDrive `Skogskoll/Rovbase/raw/rovbase_originaluttag_2026-11-18.zip` (65 735 567 byte; SHA-256 finns i datakvalitetsrapporten).
- 15 561 unika poster i fyra artfiler: björn 9 620, lodjur 4 652, varg 855, järv 434.
- Kvalitetsunderlag och skript finns i OneDrive `Skogskoll/Rovbase/quality/`; årsvis fullständighetsfil har 162 art-årsrader med antal och andelar.
- 35 RT90-poster avviker >10 m mot leverantörens SWEREF99-kolumner vid preliminär transformation (EPSG:3021). Avvikelsen är inte klassad som fel.
- 32 poster har dödsorsaken `Skyddsjakt enskilds initiativ`; kräver förtydligande från källägaren.
- Befintliga kommungränser ska återanvändas: Lantmäteriets `kommun-lan-rike_2025.gpkg` i OneDrive (290 kommunpolygoner, EPSG:3006; lager kommun/lan/rike). SCB:s `Kommun_2016.gml`–`Kommun_2026.gml` finns också för historisk jämförelse.
- Geografisk polygonvalidering är ännu inte genomförd eftersom GPKG-filen inte varit tillgänglig i denna körmiljö. Skriptet `validate_rovbase_geography.py` är uppladdat i OneDrive quality/ och har testats för ZIP-inläsning, 15 561 unika ID och koordinattransformationer.
- Rovbase är inte registrerad i `sources.yml`; rättigheter för kommersiell användning, historisk lagring, bearbetning och kundvisning är inte bedömda.

**Nästa konkreta steg:** kör skriptet lokalt mot OneDrive-originalarkivet och befintligt Lantmäteriet-GPKG. Granska kommun-/länsmissar och koordinatavvikelser innan någon normaliserad produkt eller automatiserad insamling byggs.


## Rovbase – första geografiska körningen och korrigerad namnmatchning (2026-11-18)

Den lokala körningen av `validate_rovbase_geography.py` mot det befintliga Lantmäteriet-`kommun-lan-rike_2025.gpkg` slutfördes med **15 561 poster**, 290 kommunpolygoner och 21 länspolygoner. Samtliga 15 561 transformerade källkoordinater och levererade SWEREF99-koordinater träffade exakt en kommunpolygon och exakt en länspolygon. Ingen punkt rapporterades utanför eller i flera kommun-/länspolygoner.

Den första körningen gav 9 396 granskningsrader. Av dessa flaggades 9 379 på kommunnamn och 35 på koordinatskillnad över 10 meter; tre länsnamnsavvikelser rapporterades. Analys av CSV-exempel visade ett systematiskt falskt positivt mönster: Rovbase anger exempelvis `Filipstad`, medan polygonlagret anger `Filipstads kommun`. Den dåvarande normaliseringen tog bort `kommun` men inte genitiv-s. Granskningskön ska därför inte tolkas som 9 396 geografiska fel.

Skriptet i OneDrive `Skogskoll/Rovbase/quality/validate_rovbase_geography.py` har uppdaterats för att godta exakt namnlikhet eller en begränsad genitiv-s-variant. Sex riktade tester passerade (bland annat Filipstad/Filipstads, Köping/Köpings, Västerås/Västerås och negativa kontroller för Krokom/Strömsund). Den korrigerade fullständiga körningen mot GPKG återstår; den första körningens utdata ska bevaras som diagnostik och inte skrivas över.

35 koordinatpar skiljer fortfarande mer än 10 meter mellan oberoende transformation och leverantörens SWEREF99-koordinat. RT90 antas vara EPSG:3021 och behöver bekräftas av Rovbase. Enstaka verkliga kommunavvikelser kan finnas; exempelvis finns en rad med deklarerad kommun Krokom där polygonträffen är Strömsund. Den och de tre länsavvikelserna ska granskas efter den korrigerade körningen.

**Nästa konkreta steg:** kör den uppdaterade skriptversionen till en ny separat outputmapp, exempelvis `geographic-validation-2026-11-18-v2`. Granska därefter kvarvarande kommun-/länsavvikelser och de 35 koordinatskillnaderna. Import/normalisering till `processed/` ska inte påbörjas innan dessa avvikelser och Rovbases koordinatsystem är utredda. Rovbase är fortfarande inte registrerad som operativ källa i `data-platform/config/sources.yml`; teknisk mottagning innebär inte kommersiellt användnings- eller kundvisningsgodkännande.


## Viltdata – förberedelse för Azure Blob smoke test (2026-11-18)

Azure-inventeringen i main visar att Skog redan använder kontot `stskogkolldata`, GitHub Actions OIDC via `azure/login@v2`, secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` och `AZURE_SUBSCRIPTION_ID`, samt `DefaultAzureCredential` och Azure Blob SDK. Befintliga containrar/prefix används separat för Kungjort och polisarkiv.

PR #424 är sammanslagen i main (merge commit `f979e4c675194316a1f91b56ad3c7071c1364397`). Den breda Snapshot storage tests-workflowen #474 passerade 313 tester, inklusive fem nya Viltdata Azure-smoketester. Följande finns nu i main:
- `.github/workflows/viltdata-azure-storage-smoke-test.yml`: manuell workflow, `contents: read`, `id-token: write`, befintlig OIDC-identitet, ingen schedule.
- `scripts/viltdata_azure_storage_smoke_test.py`: syntetisk payload och manifest i avsedd container `viltdata-kill-statistics`, create-only, readback, byteantal, SHA-256 och metadata.
- `tests/test_viltdata_azure_storage_smoke_test.py`: isolerade tester av payload och immutable upload-beteende.
- `docs/viltdata-azure-storage.md`: arkitektur, säkerhetsgränser och nästa steg.

Container `viltdata-kill-statistics` skapades i Azure av den manuella workflowen. Körning [#44401688469](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44401688469) avslutades `completed/success`. OIDC-login, container creation, payload-/manifestupload, readback och artifact upload passerade. Payloaden var syntetisk, 235 bytes; SHA-256 för källpayload och readback matchade: `3e5aaf7b3ce1607252a07b3bf1b7959d0c556f805aff3847666aa29a4a325063`. Artifact ID `14474565285`, 467 bytes, SHA-256 `6a44de686d0a1812ff52a71fccb14411f90e902404c1993fe821b7c5338b7530`, retention till 2026-12-18. Artifacten har laddats ned och rapporten granskats. Inga Viltdata-original skrevs till Azure.

Azure CLI skrev ut `Region: westus2` vid login. Detta är ännu inte verifiering av Storage Account-resursens `location`; stäm av den faktiska regionen i Azure Portal mot tidigare inventeringsuppgift Sweden Central. Praktiskt skriv-/lässtöd är verifierat för den aktuella identiteten, men exakt RBAC-roll och scope är inte inventerade. En lyckad teknisk kontroll ändrar inte källans rättighetsstatus. Ingen schemaläggning eller kundvisning aktiveras.

**Nästa steg:** verifiera Storage Account-resursens region och identitetens RBAC-roll/scope i Azure Portal. Därefter byggs separat snapshot-upload-, audit- och restore-flöde med fullständighetskrav, oförändrade rå-JSON-filer, manifest, create-only-skydd och SHA-256. Ingen schemaläggning eller uppladdning av riktiga Viltdata-snapshots innan rättighetsfrågorna för historisk lagring/kommersiell användning/visning är bedömda. Första kompletta snapshot ska vara en tyst baslinje utan historiska larm.


## AI-projektledare – grundimplementation (2026-11-18)

Användaren har beslutat att bygga en AI-projektledare för hela Skog/Skogskoll. Mandatet är **föreslå och planera; användaren godkänner åtgärder**. Arbetet pågår i branch `feature/ai-project-manager-foundation`; ändringarna ska granskas via PR och inte skrivas direkt till `main`.

Nya dokument:
- `docs/PROJECT_MANAGER_RULES.md` – uppdrag, mandat, evidensregler, prioriteringsmodell och säkerhetsgränser.
- `docs/PROJECT_STATUS.md` – första nulägesbaslinje baserad på GitHub main och dokumenterad evidens 2026-11-18.
- `docs/PROJECT_BACKLOG.md` – prioriterade arbetsområden och länkade befintliga issues.
- `docs/PROJECT_ROADMAP.md` – föreslagna utvecklingsfaser.
- `docs/PROJECT_DECISIONS.md` – uttryckliga beslut om omfattning och mandat.
- `docs/PROJECT_DEPENDENCIES.md` – externa och tekniska blockerare.

Första baslinjen är dokument-/issuebaserad, inte en fullständig kodrevision. Åtta öppna issues identifierades vid GitHub-sökningen; några beskriver redan genomförda delmoment och måste synkas mot aktuell kod/Actions innan de kan stängas. PR-sökningen gav poster vars öppna/stängda status inte kunde klassas säkert, så ingen PR-status har antagits.

**Viktig avgränsning:** Detta är projektledarens styr- och dokumentationsgrund, inte ännu en autonom AI-agent. Ingen modell/API-integration, schemalagd inventering eller automatisk issue-/PR-skrivning är implementerad. Nästa steg är read-only inventering av issues, PR, workflows och dokumentens aktualitet. Därefter kan en veckorapport genereras som utkast. Modellval, API-nyckel/secret, kostnadsram och körfrekvens kräver separat beslut.

Fortsättningsinstruktion:
1. Läs projektledardokumenten och kontrollera att de är förenliga med aktuell main.
2. Bygg read-only GitHub-inventering med tester och minsta behörighet.
3. Lägg inte till schedule eller AI-modell/API innan användaren godkänt kostnad, frekvens och secret-/behörighetsmodell.
4. Uppdatera denna överlämning när PR-status och nästa implementation är verifierade.


## AI-projektledare – agent v1 liveverifierad (2026-11-18)

PR #432 är mergad i `main` (merge commit `9c8be18276396f3c53ff30d0dbe91c57e69a293c`). Agentens kod, tester och manuella workflow finns i huvudgrenen.

- **Manuell livekörning #5:** [GitHub Actions #44413951767](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44413951767), körd på `main` vid commit `9c8be18276396f3c53ff30d0dbe91c57e69a293c`.
- Jobben `tests` och `inventory` avslutades båda med `success`. Steget för read-only inventering och artifact-uppladdningen passerade.
- Artifact `skogskoll-project-manager-report`, ID `14479221503`, innehåller `inventory.json` och `report.md`. Storlek 31 063 byte; SHA-256 från Actions-artifactmetadata: `e8376f26d807a961b801e177f756fb3a4b4018bc46ec7d62299a92514d4cce33`. Retention till 2026-12-02 22:42:32 UTC.
- Rapporten redovisar 6 issues i insamlingsfönstret (5 öppna), 300 PR-poster (5 öppna, 292 mergade), 100 workflows, 50 senaste workflowkörningar och 14 misslyckade/avbrutna körningar. Samtliga nio projektledardokument hittades.
- **Viktig begränsning:** issues och PR hämtas med högst tre sidor vardera och workflowhistoriken omfattar 50 körningar. Rapporten är därför en avgränsad nulägesinventering, inte en fullständig inventering av GitHub-historiken eller alla öppna objekt om fler sidor finns.
- Misslyckade/avbrutna körningar är granskningssignaler, inte automatiskt bevis på källfel. Den tidigare misslyckade agentkörningen #44411646613 finns kvar som historisk signal trots att körning #5 lyckades.
- Agent v1 är deterministisk och read-only. Ingen LLM/API, ingen schedule och inga GitHub-skrivoperationer. Agenten ändrar inte backlogg, issues, PR eller källstatus.

**Nästa steg:** granska inventeringens avgränsningar, förbättra pagination och lägg till jämförelse mot föregående inventering med tydlig historik/proveniens. Separat modell-/kostnads-/databehandlingsbeslut krävs innan LLM eller schedule övervägs.


## AI-projektledare – v2 planerad (2026-11-18)

- PR #434 är mergad i `main`; merge commit `57453875cff3f1e7d5e0597deed1ae2cc0bdb3a7` dokumenterar liveverifierad v1.
- PR #435 är sammanslagen i `main` (merge commit `eb32aebbac949390998a9b2ab5c6901cf905709a`); den fastställde v2-planen.
- v2a implementeras på separat branch `feature/project-manager-agent-v2a-pagination`: GitHub Link-pagination för issues/PR, hård gräns 10 sidor/1 000 poster per lista och täckningsmetadata.
- API-fel ska avbryta inventeringen; trunkerade listor redovisas och får inte användas för frånvarobaserade slutsatser.
- v2b (append-only-baslinjelagring) kräver fortfarande separat beslut. Ingen historisk jämförelse, schedule, LLM/API eller skrivbehörighet införs i v2a.


**Nästa konkreta steg:** v2b-beslutet är mergat i PR #438. Teknisk design för Git-historik finns i [PROJECT_MANAGER_AGENT_V2B_TECHNICAL_DESIGN.md](PROJECT_MANAGER_AGENT_V2B_TECHNICAL_DESIGN.md). Nästa steg är en ren Python-modul och syntetiska tester för manifest, SHA-256, append-only, idempotens och restore. Ingen workflow eller skrivbehörighet införs i detta steg.


## AI-projektledare v2b – beslut fattat, implementation spärrad (2026-11-19)

Användaren har valt separat skyddad Git-historikbranch och indefinite retention (bevara tills vidare utan automatisk gallring). Beslutet gäller målbild och planering, inte aktivering. Inventeringsjobbet ska fortsatt vara read-only. Eventuell `contents: write` ska endast finnas i separat persistence-jobb och begränsas till historikbranchen. Före aktivering krävs syntetiska tester, verifierat branchskydd, verifierad behörighetsisolering, checksumme-/readback-/restore-test samt ett separat uttryckligt godkännande efter granskning. Ingen persistens, skrivbehörighet eller schedule har ännu införts. Se [v2b-beslutsunderlaget](PROJECT_MANAGER_AGENT_V2B_STORAGE_DECISION.md).


## AI-projektledare v2b – säkerhetsgranskning (2026-11-19)

PR #441 är mergad och dess CI-checkar passerade. Därefter genomfördes read-only granskning av GitHub-lagringsskydd. Repository rulesets-endpointen returnerade `[]`. Klassisk branch protection för `main` kunde inte läsas: GitHub-integrationen returnerade HTTP 403 (`Resource not accessible by integration`). Historikbranchen `project-manager-history` finns inte (404), vilket är avsiktligt före aktivering. Nuvarande project-manager-workflow har fortsatt endast `contents: read`, `issues: read`, `pull-requests: read`, `actions: read`; inget persistensjobb eller `contents: write` finns.

**Slutsats:** skyddet av `main` och branchspecifik skrivisolering är inte verifierade. Persistens får inte aktiveras. Administrativ kontroll i GitHub Settings krävs. Se [säkerhetsgranskningen](PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md). En mindre CI-korrigering läggs också till så att ändringar i `project_manager_history.py` och dess tester triggar testworkflow vid push till main.


## Verifierat skydd för main (2026-11-19)

Repository ruleset `Protect main` är nu verifierat via GitHub Rulesets API, ID `27619735`, `enforcement: active`, target `~DEFAULT_BRANCH` (main), tom bypass-lista och `current_user_can_bypass: never`. Aktiva regler: `pull_request` före merge (0 obligatoriska approvals; inga krav på Code Owners, senaste push eller trådlösning), `deletion` blockerad och `non_fast_forward` blockerad. Tillåtna merge-metoder: merge, squash och rebase. Regeln kräver alltså PR men inte mänskligt godkännande; det är avsiktligt i nuläget. Inventeringsworkflowet har fortsatt endast read-permissions och ingen persistens. Nästa blockerare är separat skydd och verifierad skrivmodell för historikbranchen; inget `contents: write` har lagts till.


## v2b – skrividentitetens säkerhetsdesign (2026-11-19)

Ny design finns i [PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md](PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md). Rekommendationen är en separat GitHub App installerad endast på Skog, med endast Contents read/write och obligatorisk Metadata read. Detta är fortfarande repository-scope, inte branch-scope. `Protect main` med PR-krav, tom bypass-lista och blockering av deletion/force-push är verifierat; Appen ska inte ha bypass, Administration eller Pull requests-write. Historikbranchens ruleset ska rikta sig endast mot exakt branch, blockera deletion/force-push och tillåta fast-forward append. Innehållsmässig append-only måste säkras i kod och tester. Ingen App, secret, branch, persistence-workflow eller `contents: write` har skapats/aktiverats. Nästa steg: granska designen och implementera syntetiska tester utan livepersistens.

## v2b – syntetiskt Git-append under CI-verifiering (2026-11-19)

Ny separat branch feature/project-manager-v2b-synthetic-git-append lägger till ett syntetiskt test i tests/test_project_manager_history.py. Testet använder en temporär lokal Git-repository utan remote eller credentials: skapar main, skapar historikbranch, committar en enda syntetisk run-katalog och verifierar att main förblir oförändrad, att committen endast innehåller run-filerna, att identisk dubblett blir no-op och att avvikande byte ger konflikt utan ny commit. Befintligt project-manager-workflow triggas av testfilens ändring och behåller endast read-permissions.

Detta verifierar Git-commitmodellen lokalt, inte GitHub rulesets, App-tokenens faktiska scope eller livepersistens. Ingen historikbranch i GitHub, GitHub App, secret, contents: write, persistence-jobb eller schedule har skapats. Nästa steg är att låta PR-CI köra testen, granska resultatet och därefter vid behov utöka negativa tester. Persistens förblir spärrad tills separata GitHub-säkerhetskontroller och uttryckligt aktiveringsgodkännande är klara.

## v2b – PR #445 syntetiskt Git-test verifierat (2026-11-20)

PR #445 mergades till main med merge-commit e3a3ff72c3867043a4a91e2a24dfd96c534fe9b4. CI-run 44615910647 (Skogskoll AI project manager) avslutades success: tests-jobbet passerade; inventory-jobbet skipped enligt PR-flödet. CI-run 44615910611 (Snapshot storage tests) avslutades success och körde `python -m unittest discover -s tests -v`. Därmed är testsviten grön i PR-CI. Testet använder temporär lokal Git-repository utan remote/credentials. Det verifierar lokal branch-/commitlayout, oförändrad main, idempotens och konflikt vid avvikande innehåll. Det verifierar INTE GitHub rulesets eller App-tokenens faktiska behörighetsgräns. Ingen App, secret, GitHub-historikbranch, contents: write eller persistensworkflow har aktiverats. Nästa steg är att utforma/testa negativt skydd och separat ruleset utan att skapa produktionspersistens.

## v2b – nästa steg: historikbranchens ruleset (2026-11-20)

PR #456 är mergad (merge-commit `4b03cfe6dbde67cd3bbd861d156d0f154d3a4e2d`). GitHub-repositoryinventeringen visar flera separata projekt i samma ägarkonto; Skog är huvudrepot för Skogskoll. README har även verifierats för `alg-grasmyr` (Länsstyrelsens älgdata), `mark` (kommunal mark-/planinformation), `mark_gr-smyr` (separat Gräsmyr-projekt) och `bear-data` (björn-/Rovbase/GBIF-pipeline). Dessa repos ska inte antas dela behörigheter, dataflöden eller releasecykler. Denna v2b-uppgift och dess regler gäller endast `dahlinrobert-lgtm/Skog`.

Read-only ruleset-listning på Skog visar endast aktivt `Protect main` (ID 27619735); inget historikbranch-ruleset finns ännu. Branch protection-detaljendpoint gav 403 för integrationen. Nästa steg är att förbereda och granska ett separat ruleset för exakt `project-manager-history` enligt verifieringsmatrisen i `PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md`. Ingen branch, App, secret eller write permission har skapats. Livepersistens är fortsatt spärrad.

## Beslut: separat privat historikrepository för v2b (2026-11-20)

Efter avvägning väljs ett separat privat Git-repository för projektledaragentens persistenta historik, i stället för en historikbranch i det publika Skog-repot.

Skäl:
- Skog-repot är publikt. En branch i samma repository ärver både repositoryns synlighet och dess befintliga Git-objekthistorik; att lägga till en ny branch ger inte en fristående/orphan-historik.
- En separat privat repository ger separat synlighet, separat ruleset och en GitHub App-installation vars Contents-write kan begränsas till just historikrepot. Det ger en starkare teknisk gräns än branchregler i Skog.
- Git behåller append-commits, SHA-1 objektidentitet och full historik; indefinite retention blir naturligt så länge repot och dess backup bevaras.

Nackdelar och hantering:
- Ytterligare repository att administrera, övervaka och säkerhetskopiera.
- Historik och inventeringskod blir två separata resurser; persistensjobbet måste verifiera artifact-proveniens och skriva endast till historikrepot.
- Git är inte i sig WORM/immutability: en administratör kan ändra rulesets eller radera repot. Kräv aktivt ruleset, ingen bypass för Appen, deletion/force-push-skydd, extern backup/restore-test och audit av administratörsåtgärder.
- Repositorynamn föreslås `skogskoll-project-manager-history`; skapa som Private. Indefinite retention är ett verksamhetsbeslut, inte en garanti mot kontoförlust eller administrativ radering.

Alternativet branch i Skog avvisas eftersom Skog är publikt och innehåller redan befintlig kod-/dataprojektshistorik. Separat privat repo ger bättre sekretess och credential-isolering. Azure Blob med container-scope-identitet är ett möjligt framtida alternativ om krav på objektlås/WORM eller kostnad/tillväxt gör Git olämpligt, men väljs inte i detta steg.

**Aktiveringsgräns:** Detta är ett arkitekturbeslut, inte tillstånd att skapa repo, App, nyckel, secret eller persistence-workflow. Nästa steg är att skapa det privata tomma historikrepot först efter uttryckligt godkännande av själva repo-skapandet; därefter ruleset och syntetiska tester med separat identitet. Ingen historik skrivs före verifiering och separat godkännande.

## Nästa steg

Förbered separat privat repository `skogskoll-project-manager-history`. Ingen branch i Skog ska skapas. Invända på separat godkännande innan repo skapas; inventeringsworkflow förblir read-only.


## AI-projektledare v2b – privat historikrepo skapat (2026-11-20)

PR #458 är sammanslagen. Arkitekturbeslutet är separat privat Git-repository, inte historikbranch i det publika Skog-repot. Användaren har skapat `dahlinrobert-lgtm/skogskoll-project-manager-history`.

**Verifierat via GitHub API 2026-11-20:**
- Repository-ID `1465873025`, visibility `private`, default branch `main`.
- `README.md`, `docs/HISTORY_FORMAT.md` och `docs/SECURITY_AND_OPERATIONS.md` finns i repot. De två sistnämnda beskriver schema/append-only-regler respektive säkerhets- och driftkrav.
- Repository rulesets-endpointen för det privata repot returnerar `[]`: inget ruleset är konfigurerat.
- Klassisk branch protection för `main` kunde inte läsas av integrationen (HTTP 403 `Resource not accessible by integration`). Detta är okänt, inte bevis på att skydd saknas eller finns.
- Repot innehåller endast bootstrap-dokumentation. Ingen produktionshistorik har skrivits.

**Säkerhetsgräns:** Ingen GitHub App, installation, privat nyckel, Actions-secret, skrivbehörighet eller persistensworkflow har skapats/aktiverats. Inventeringsworkflowet i Skog förblir read-only.

**Nästa konkreta steg:** konfigurera ett aktivt repository ruleset på historikrepots `main` som blockerar deletion och non-fast-forward/force push, utan bypass för framtida automationsidentitet. Verifiera exakt target och effektiv policy via API/UI. Därefter planera backup/restore-test och negativa tester. Först efter dessa kontroller kan separat skrividentitet diskuteras; livepersistens kräver ytterligare uttryckligt godkännande.

De tidigare daterade avsnitten nedan om historikbranch i Skog beskriver historiska designsteg och ska inte användas som aktuell målarkitektur. Det separata privata repot enligt PR #458 ersätter dem.


## AI-projektledare v2b – historikrepots main-ruleset verifierat (2026-11-20)

Användaren har konfigurerat rulesetet `Protect history main` i det privata historikrepot. GitHub Rulesets API verifierar:
- Ruleset ID: `27761134`
- Enforcement: `active`
- Target: exakt `refs/heads/main`
- Regler: `deletion` och `non_fast_forward`
- Bypass actors: tom lista; `current_user_can_bypass: never`

Detta är verifierad ruleset-konfiguration, inte ett utfört negativt push-/delete-test. Klassisk branch-protection endpoint ger fortfarande 403 för integrationen, men repository ruleset-detaljerna är läsbara och bekräftar ovanstående policy.

**Nästa steg:** planera extern backup och ett återställningstest till tom katalog. Därefter syntetiska tester av acceptanslogik och Git-operationer. Ingen App, credential, Actions-secret, skrivbehörighet, persistensworkflow eller produktionshistorik är skapad/aktiverad. Persistens kräver separat uttryckligt godkännande.


## Nationell älgavskjutningskarta per ÄFO – återuppbyggnad 2026-11-21

- Original PR #393 var 448 commits bakom aktuell `main` och byggs därför om separat; den gamla grenen ska inte mergas.
- Korrigerad nationell ÄFO-batch från alg-grasmyr run #43952789564 verifierades med 129/129 AFO, 129 snapshots och 3 237 råa ÄJO-rader. Oberoende kontroll gav noll avvikelser mellan dashboard och råsummor för `ShotTotal`/`AssignedTotal`, samt noll avvikelser mot parentesvärdena i HTML-Summa.
- Alg-grasmyr PR #79 återinför insamlare och dagligt snapshotflöde på aktuell main. En ny full körning från main krävs innan kartan publiceras.
- Skog-kartan använder nationella dashboarden och JaktAdm layer 1, matchar exakt på sammansatt `afo_id`, visar separat nationell ÄFO-statistik och regional ÄJO-pilot, och skiljer noll från saknade värden.
- Rättighetsbedömningen för JaktAdm-lagret är fortfarande villkorad tills exakt metadata kan granskas. Kartan ska ha attribution och ingen rågeometri-nedladdning.


## Projektledardashboard – privat Azure Blob-läsning (2026-11-22)

Projektledargränssnittet utvecklas i det separata privata repot `dahlinrobert-lgtm/skogskoll-project-manager-history`. MSAL-baserad autentisering och läsning av en fast run-scoped snapshot är implementerad och mergad där i PR #37; dess CI passerade. Den publika Pages-skalfilen finns nu i detta repo under `docs/project-manager/`, mergad via PR #472 den 2026-11-21. GitHub Pages build och deploy för merge-commit `dd461eeff66bb77aa1eda7722f624f067ae7954a` slutfördes med success i run `44961792629`. Skalet innehåller endast klient-ID/tenant/offentlig konfiguration; ingen snapshot eller hemlighet publiceras.

Användaren har uppgett att Blob service CORS har konfigurerats för GitHub Pages-origin. Exakta portalvärden och faktisk browser-preflight är ännu inte oberoende verifierade. Publicera inte eller betrakta läsvägen som verifierad förrän PR-granskning/CI passerat och live-test visar: ingen data före inloggning, lyckad Entra-token och Blob-läsning för behörig användare samt nekad anonym/obehörig åtkomst. Den nuvarande klienten läser endast `snapshots/44958916377/dashboard-data.json`; den har ingen latest-snapshot-upptäckt. Schemalagd publicering, kundvisning och historik är fortsatt avstängda.


## Projektledardashboard – korrigerad MSAL CDN-referens (2026-11-22)

- Live-testet i användarens webbläsare visade att MSAL-biblioteket inte laddades; gränssnittet visade därför att inloggningsbiblioteket eller appkonfigurationen saknades.
- Den tidigare HTML-filen pekade på alcdn.msauth.net/browser/2.39.0. Den ersätts med Microsoft Learn-dokumentationens CDN-exempel för MSAL Browser v2.35.0 på Europe North-domänen alcdn.msftauth.net.
- Script-taggen versionslåses och använder Microsofts publicerade SRI-hash för den minifierade 2.35.0-builden samt crossorigin=anonymous.
- Ändringen påverkar inte MSAL v2-API, Entra-konfiguration, Blob-scope, Blob-URL eller RBAC.
- En testkontroll verifierar version, URL, SRI och CORS-attribut. CI och live-webbläsartest återstår efter PR-merge.
- Lokal hosting av MSAL är fortsatt ett alternativ men behövs inte för denna korrigering. Ingen token eller hemlighet läggs i Git.

Nästa steg: verifiera CI, invänta Pages-deploy och testa i webbläsaren att MSAL laddas, Microsoft-inloggningen fungerar och behörig användare kan läsa den privata Blob-snapshoten. Bekräfta separat att anonym/obehörig läsning nekas.


## Projektledardashboard – MSAL CDN-fix sammanslagen och CI verifierad (2026-11-22)

- PR #474 är sammanslagen i Skog main. Merge commit: 46eaeb19a88579ee3450bc09b68b76805c1af9ec.
- PR #39 är sammanslagen i det privata history-repot. Merge commit: 5fb467d852189bca85515303506c5437f4500ecd.
- Skog JavaScript-kontroll passerade i Actions run 44962834896; hela Snapshot storage tests passerade i run 44962834889.
- History-repots Project manager tests passerade i run 44962844181; Synthetic append-only tests passerade i run 44962844143.
- Verifierat i båda repornas main att dashboardens HTML använder MSAL Browser v2.35.0 på alcdn.msftauth.net med SRI och crossorigin=anonymous.
- CI verifierar kod/tester och metadata. Den bevisar inte att GitHub Pages-deployen är klar eller att MSAL kan ladda i den aktuella webbläsaren.

**Nästa konkreta steg:** verifiera Pages-deploy för Skog main och testa därefter den publicerade projektledarsidan i privat webbläsarsession: MSAL ska laddas, Entra-inloggningen ska lyckas och den behöriga användaren ska kunna läsa den privata Blob-snapshoten. Testa separat att anonym/obehörig läsning nekas. Ändra inte Azure RBAC eller slå på schemalagd publicering som del av detta test.


## Projektledardashboard – separat lista för workflow-avvikelser (2026-11-22)

History-repots PR #40 är sammanslagen (merge commit `d65618c107b5dbfe61f8e7f8598418e6e74ebe42`). Dashboarden har nu en egen sektion `Workflow-körningar att följa upp` som listar körningar med `status=completed` och `conclusion` annat än `success`, med direktlänk till respektive GitHub Actions-körning. Sammanräkningen benämns `Avvikande senaste körningar` eftersom listan även kan innehålla avbrutna eller andra icke-success-avslut, inte bara tekniska fel.

**Begränsning:** Insamlaren hämtar fortfarande endast de 20 senaste workflow-körningarna per aktivt repository. Ett äldre fel kan därför falla ur översikten när fler körningar tillkommer. Dashboarden visar en ögonblicksbild från Azure Blob; den uppdateras inte automatiskt och är inte en fullständig eller realtidsbaserad körhistorik. GitHub-mejlen är fortsatt en separat och snabb notifieringskanal.

Skog Pages-kopian under `docs/project-manager/` ska hållas synkroniserad med det privata history-repots `dashboard/`-filer. Den här uppdateringen kopierar den granskade UI-ändringen; autentisering, Blob-URL, RBAC och publiceringsflöde ändras inte.

**Nästa steg:** verifiera GitHub Pages build/deploy och öppna dashboarden igen. Kontrollera att den nya sektionen visar avvikande körningar och att länkarna leder till rätt Actions-run. Därefter kan insamlaren utökas med en separat, tidsavgränsad fellista så att fel inte försvinner bara för att fler än 20 senare körningar tillkommer.


## Projektledardashboard – prioritering av schemalagda körningar (2026-11-22)

History-repots PR #41 är sammanslagen (commit `043f42bd168f9756fda3f4b6e79226a5a8194189`). Insamlaren bevarar nu workflow-ID, workflow-sökväg, trigger-event och faktisk starttid. Dashboarden har separata sektioner för pågående schemalagda körningar och schemalagda fel utan senare lyckad körning, samt återhämtade fel där en senare lyckad körning av samma workflow finns i det insamlade urvalet. Återhämtade fel visas separat och räknas inte som olösta avvikelser.

Jämförelsen är begränsad till de 20 senaste körningarna per repository. Ett fel kan därför felklassificeras som olöst om den senare lyckade körningen fallit utanför urvalet. GitHub-mejlen är fortsatt snabb separat notifiering.

**Geografisk testnivå:** GitHub Actions run-metadata ger inte i sig en tillförlitlig standardiserad uppgift om körningens geografiska omfattning. Dashboarden visar körningens display title/workflow-sökväg som ledtråd, men ska inte gissa liten geografi eller nationell omfattning. Nästa utvecklingssteg är en verifierad metadata-/workflowkatalog som kopplar utvalda workflows till testnivå (lokal/regional/nationell), avsedd uppskalningsnivå och om körningen är ett pilot-/förtest eller produktionsflöde.

Skog Pages-kopian under `docs/project-manager/` synkroniseras med history-repots granskade dashboardfiler. Ingen workflow-schedule, Azure-behörighet, insamlingsfrekvens eller publiceringsfrekvens har ändrats.
