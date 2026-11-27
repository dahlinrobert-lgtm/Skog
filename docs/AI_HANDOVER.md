# Skog / Skogskoll – överlämning för fortsatt arbete

**Senast uppdaterad:** 2026-11-25  
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

## 3C. Projektledarens dokumentationsgrind

Projektledarens styrande dokumentations- och Definition of Done-regel finns i det privata projektledarrepot: [Project manager rules – documentation and completion](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/blob/main/docs/PROJECT_MANAGER_RULES.md). Den gäller vid tydliga delmål, färdig uppgift, PR-granskning/merge, driftsättning eller manuell konfigurationsändring samt överlämning – även när arbetet inte avslutas genom en PR. Varje meningsfull uppgift ska få statusen `Documented`, `Assessed – no update required` eller `Documentation outstanding`. Dokumentation ska bygga på verifierad kod, konfiguration eller evidens; små ändringar utan bestående påverkan behöver inte skapa dokumentationsarbete. PR-livscykeln ska ange dokumentationsstatus och får inte markera en leverans helt färdig medan nödvändig dokumentation återstår.



## 3A. Styrande prioritering – dagligt snapshotinformationsflöde först (fastställt 2026-11-22)

**Primär leverans:** ett tillförlitligt dagligt informationsflöde som sammanställer senaste snapshotstatus och förändringar per källa/produkt/lager. Det ska visa senaste kompletta observation, senaste körningsförsök, running/success/partial/failed, aktualitet, täckning/antal, jämförbarhet, avvikelser och granskningsbehov med länkar till manifest, artifact, workflow-run och PR där sådana finns.

Det dagliga informationsflödet är en daglig sammanställning och kontrollpunkt; det betyder **inte** att varje datakälla ska hämtas dagligen. Insamlingsfrekvensen bestäms per källa utifrån uppdateringsmönster, tekniska gränser, kostnad och rättigheter. Visa när källan senast kontrollerades och när nästa kontroll förväntas.

**Sekundärt:** håll en lång, strukturerad backlogg över framtida datakällor, nationell täckning, analys, kundfunktioner, drift, kvalitet, säkerhet och teknisk skuld. Backloggen ska vara omfattande men inte skapa parallellt aktivt arbete. Vid konflikt prioriteras daglig driftinformation och befintliga insamlingars tillförlitlighet före nya funktioner och backloggexpansion.

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

## 3B. AI-projektledarens obligatoriska arkitekturpassning (2026-11-22)

Före varje ny funktion, workflow, integration, agent eller lagringslösning ska projektledaren först kontrollera om befintliga komponenter och processer i aktuell `main` redan löser hela eller delar av behovet. Föredra återanvändning eller utökning av befintlig arkitektur framför parallella arbetsflöden och dubbla sanningskällor. Varje lösningsförslag ska klassificeras som återanvänt, utökat, ersatt eller nytt separat. Ny separat komponent kräver evidensbaserad motivering, överlapps-/konsekvensanalys, systemgräns, auktoritativ datakälla, integrationspunkt och eventuell avvecklingsplan. Saknad analys anges som okänd och får inte behandlas som att befintligt saknas. Regeln är dokumenterad i [PROJECT_MANAGER_RULES.md](PROJECT_MANAGER_RULES.md) avsnitt 4A och ska användas som obligatorisk beslutsgrind. Den deterministiska agentrapporten påminner om kontrollen men gör inte självständig arkitekturgranskning.

## 4. Källregister och automatisk rapport

Maskinläsbart register: `data-platform/config/sources.yml`  
Validerare: `data-platform/scripts/validate_source_registry.py`  
Rapportgenerator: `data-platform/scripts/build_source_status_report.py`  
Rapport: `docs/SKOGSKOLL_SOURCE_STATUS.md`

Källregistret har 53 källposter. Den aktuella genererade källstatusrapporten redovisar 16 poster med ett operativt `operations`-block och 37 utan. Rapportens `registry_checked_on` är fortfarande 2026-11-18; enskilda källrader har verifierats/uppdaterats senare, bland annat Älgdata 2026-11-25. Datumet ska därför inte tolkas som senaste verifieringsdatum för varje rad. Saknat operations-block betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.

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
- **Laserskanningsmetadata – baslinje och stabil publicering verifierade (2026-11-26):**
  - [Actions #23](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45846159692) visade HTTP 404 för ArcGIS GET med 500 `objectIds` i URL:en. PR [#670](https://github.com/dahlinrobert-lgtm/Skog/pull/670) flyttade feature-batcherna till POST, lade till `pipefail` och skyddade tomma commits.
  - [Actions #24](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45856597506) hämtade komplett 146 637 objekt och skapade `initial_baseline`, men direktpush till skyddad `main` blockerades av GH013. Ingen beständig snapshot publicerades från den körningen.
  - PR [#671](https://github.com/dahlinrobert-lgtm/Skog/pull/671) mergades 2026-11-26 16:22:22 UTC (merge commit `95297a2ef334902572dfafcdbc1ea691ad3e836f`). Workflowet använder nu `peter-evans/create-pull-request@v7`, separat automation-branch och manuell granskning/merge av data-PR. Ingen automatisk merge.
  - [Actions #25](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45858538660) kördes från main efter PR [#672](https://github.com/dahlinrobert-lgtm/Skog/pull/672) (mergad 16:24:38 UTC; merge commit `542d8ad9034837b4296231efd153a101d84418ec`). Insamlingen hämtade 146 637 objekt, status `initial_baseline`, content SHA-256 `53946c72a00f21ed7e638203e07898c41622478a00dc55e43eea4481146f95b9`. Den skapade data-PR [#673](https://github.com/dahlinrobert-lgtm/Skog/pull/673) med `latest.json` och `snapshots/20261126T162720Z_53946c72a00f.json.gz`.
  - PR [#673](https://github.com/dahlinrobert-lgtm/Skog/pull/673) mergades 2026-11-26 16:30:06 UTC, merge commit `3f90e181d08ddf4da178f8552bca6809c9d3e6e9`. Båda arkivfilerna verifierades därefter på `main`. `latest.json` anger 146 637 objekt, samma SHA-256 och `change_type: initial_baseline`; första baslinjen är tyst och ska inte generera historiska larm.
  - [Actions #26](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45859405953) kördes efter data-PR:ns merge och avslutades `success`. Resultatet var uttryckligen `unchanged`, 146 637 objekt och samma content SHA-256, med senaste snapshot `snapshots/20261126T162720Z_53946c72a00f.json.gz`. Ingen ny snapshot eller data-PR skapades.
  - **Verifierad omfattning:** teknisk hämtning, skapande av första baslinjen, PR-baserad arkivering till `main` och en efterföljande oförändrad kontroll. Långsiktig bevakning av verkliga källförändringar återstår att observera över tid. Arkivering eller generell källtillgång innebär inte i sig kommersiell rätt, kundvisningsrätt eller distributionsrätt; bedöm exakt produkt/lager och villkor separat.
  - **Nästa konkreta steg:** låt den schemalagda pollern fortsätta. Vid nästa observerade ändring ska körningen granskas för fullständighet, förändringstyp, feature count och hash; granska den automatiskt skapade data-PR:n innan merge. Bevara baslinjen och tidigare snapshots oförändrade.


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
- **PR #610 – paginering i webbdiariet (mergad 2026-11-25):** [PR #610](https://github.com/dahlinrobert-lgtm/Skog/pull/610) korrigerar framåtriktad glidande sidfönster-ellipsis (`Page$1`); logiskt sidindex behålls vid fönsterförflyttning, bakåtriktade ellipser avvisas och `Page$Last` används inte. PR-kontroller: [diary history audit #64](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45646210303) och [snapshot storage tests #544](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45646210196), båda godkända.
- **Livekontroll #1:** [körning #45647225093](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45647225093), group_06, kategori B, oktober 2026. 18/18 intervall avstämda; Kalmar 23/23, Gotland 6/6, Blekinge 19/19 (48/48). Diagnostics-only; inga snapshots/manifest ändrades.
- **Livekontroll #2:** [körning #45649334402](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45649334402), group_07, kategori B, oktober 2026. 18/18 intervall avstämda; Skåne 15/15, Halland 12/12, Västra Götaland 56/56 (83/83). Diagnostics-only; inga snapshots/manifest ändrades.
- **Samlad status efter fyra livekontroller:** de tre ursprungliga fraskörningarna omfattade 54/54 avstämda intervall (group_06/B, group_07/B och group_07/A). Därefter kördes [datumtest #7](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45662180296), date-only för 2026-10-15 i group_01: Norrbotten 60/60 över två sidor, Västerbotten 44/44 på en sida och Jämtland 27/27 på en sida. Alla tre datumintervall hade `pager_complete=true`, `reconciled=true` och inga ärendedubbletter. Norrbottens siddiagnostik innehåller 50 unika ärenderader på sida 1 och 10 på sida 2; `pages_read=2`. Detta verifierar live flersideshämtning och avstämning, men inte i sig att den specifika glidande sidfönster-ellipsisövergången (`Page$1`) inträffade. PR för explicit pager-diagnostik är under arbete: insamlaren ska spara sidnummer före övergång, vald etikett, postback-target/argument, om POST-respons sågs och om resultatsidan ändrades. Detta gör det möjligt att bevisa en faktisk `Page$1`-övergång i en senare livekörning. Koden och testerna är ännu inte verifierade i CI eller live; datumtestet var diagnostics-only och publicerade inga snapshots eller manifest.

- PR #397 och #399 är sammanslagna i `main`. Den aktuella insamlaren skickar både `seen` och `seen_diary_numbers` till fyrargumentsfunktionen `extract_grid`.
- **Pilot #16:** [GitHub Actions #16](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43964781619), Norrbotten, oktober 2026, kategori B. Sex intervall passerade med `pager_complete=true`, `reconciled=true` och utan fel. Resultaten var vattenverksamhet 15, markavvattning 0, dikesrensning 0, trumma 2, våtmarksanläggning 0 och omgrävning 0. De två trumma-posterna överlappar vattenverksamhet; totalt 15 unika diarienummer. Sex snapshots och sex manifestposter publicerades i `main`; publiceringscommit `dcd75e090ff2c49ad013b2cc2246b1f0d145b97f`.
- **Pilot #17:** [GitHub Actions #17](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43971226392), Norrbotten, september 2026, kategori B. Samtliga fem testmoduler passerade och alla sex intervall var kompletta och avstämda. Resultaten var vattenverksamhet 21, markavvattning 0, dikesrensning 0, trumma 1, våtmarksanläggning 0 och omgrävning 0. Posten under trumma överlappar vattenverksamhet; totalt 21 unika diarienummer. Sex snapshots och sex manifestposter publicerades i `main`, inklusive explicita nollresultat.
- Båda piloternas snapshots ligger under `data/lansstyrelsen-diary/snapshots/2026/11/`; manifestet är `data/lansstyrelsen-diary/snapshot-runs.jsonl`. Tillsammans omfattar de tolv avstämda län/fras-intervallobservationer för två olika registreringsmånader, men bara ett län och kategori B.
- **Manuell nationell diagnostikworkflow (PR #406 mergad):** `.github/workflows/lansstyrelsen-national-diary-discovery.yml`. Den delar de 21 länen i sju grupper om tre län och kör en kategori (sex fraser) per workflowkörning. Varje körning omfattar högst 18 län/fras-intervall. Livekörningar #1–#3 är verifierade: group_06/B, group_07/B och group_07/A för oktober 2026, sammanlagt 54/54 avstämda intervall. Körningarna har endast läst data och laddat upp diagnostikartefakter i 30 dagar; workflowen anropar inte persistensskriptet, ändrar inte snapshots/manifest och har endast `contents: read`.
- Fortsätt använda workflowen som kontrollerad, manuell discovery, en länsgrupp per körning. Workflowen har ett valfritt fält `search_term` som, när det fylls i, ersätter kategori A/B:s sex fraser med en enda validerad fras och kör tre länsintervall.
- **PR #647 – pager-DOM-diagnostik (mergad 2026-11-25):** [PR #647](https://github.com/dahlinrobert-lgtm/Skog/pull/647), merge commit `3b44a507f01c79fe6114905a61afd8f38e0e06ef`. Den befintliga read-only-insamlaren sparar nu `pager_states` före varje pagerbeslut: logiskt sidindex, synlig pager-rad, alla parsade postback-kandidater samt pager-radens `outerHTML` (max 12 000 tecken med trunkeringsflagga och ursprunglig längd). Befintliga `pager_actions` behålls. Två fokuserade enhetstester täcker insamling av tillstånd och HTML-gränsen. Merge verifierad i `main`; PR-kontrollerna efter merge var fortfarande pågående vid kontrollen. Liveverifiering av faktisk `Page$1`-övergång återstår. Diagnostikworkflowen är fortsatt manuell och read-only; inga snapshots eller manifest publiceras.
- **Livekontroll #11 – postbackfix och fokuserade tester verifierade:** [GitHub Actions #45674022616](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45674022616), group_01 (Norrbotten, Västerbotten, Jämtland), oktober 2026, sökordet `skog`. Alla 34 fokuserade tester passerade. Norrbotten 16/16, Västerbotten 39/39 och Jämtland 14/14; totalt 69/69 unika diarienummer, tre av tre intervall avstämda, `pager_complete=true`, inga dubbletter eller insamlingsfel. Detta verifierar live att länsvalet/postbacken fungerar efter PR #638 och att testmockfixen i PR #641 fungerar. Alla tre län hade en resultatsida; körningen bevisar därför inte en verklig `Page$1`-övergång. Körningen var diagnostics-only och publicerade inga snapshots eller manifest.
- **PR #638 – vänta på Länsstyrelsens länspostback:** [PR #638](https://github.com/dahlinrobert-lgtm/Skog/pull/638), mergad. Väljer län och väntar på navigation/asynkron postback samt verifierar att valt län behållits. Liveverifierad i körning #11.
- **PR #641 – korrigera Playwright-navigationmockar:** [PR #641](https://github.com/dahlinrobert-lgtm/Skog/pull/641), mergad. Testerna mockar navigationens context manager korrekt. 34 fokuserade tester passerade i körning #11.
- **Livekontroll #17 – upprepad resultatsida med diagnostikförlust:** [GitHub Actions #45705354336](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705354336), Blekinge isolerat, oktober 2026, custom phrase `av`. De 34 befintliga fokuserade testerna passerade. Insamlingen avbröts vid sidvisning 7 med `Repeated page signature at 7`; ingen intervall-JSON hann skrivas och artifacten innehöll endast den lilla sammanfattningen. Detta är en skyddad avbrytning, inte ett godkänt komplett uttag. Ingen snapshot/manifest ändrades.
- **PR #661 – bevara diagnostik vid upprepad sida (mergad 2026-11-25):** [PR #661](https://github.com/dahlinrobert-lgtm/Skog/pull/661), merge commit `a4e5b5df95e2e7c56a91da755e6b11b5d75fa02b`. Pager-state och DOM samlas nu in före signaturkontrollen. En upprepad sida returnerar ett uttryckligt ofullständigt intervall med tidigare poster, `pager_states`/`pager_actions` samt upprepad sidas diarienummer, radrader, pager-HTML (12 000 tecken med trunkeringsmetadata) och body-utdrag. Upprepade sidor räknas inte som nya sidor; `pager_complete=false` och `reconciled=false`. Ett fokuserat test täcker diagnostikobjektet och HTML-trunkeringen. PR är mergad; ingen separat workflow-run hittades på merge-commitens SHA vid kontrollen, så CI-status för ändringen är inte verifierad här.
- **Livekontroll #18 – Blekinge pagerfönster återgår bakåt:** [GitHub Actions #45706692645](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45706692645), oktober 2026, custom phrase `av`. 34 fokuserade tester passerade. Artifacten visar 254/254 unika diarienummer mot källtotalen 254, men intervallet är korrekt ofullständigt (`pager_complete=false`, `reconciled=false`) efter upprepad sida vid logisk sida 7. Pager-DOM på sida 6 var `<< ... 2 3 4 5 6`; ellipsen hade `Page$1` men var bakåtriktad. Den tidigare selectorregeln accepterade den ändå och återförde sidfönstret till `1 2 3 4 5 ... >>`. Artifact ID `15065143691`, SHA-256 `1d419ba46ea62cb0c64a8ae7cf1d0ffa64d4d6690441402a7a8136b391cf93a1`. Inga snapshots/manifest ändrades.
- **Livekontroll #15 – Blekinge isolerat, en sida:** [GitHub Actions #45703349664](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45703349664), 2026-10, `single_county=blekinge`, custom phrase `tomt` (kategori B vald men överskriven av sökfrasen). Jobbet, fokuserade valideringstester och artifact-uppladdning passerade. Artifact `lansstyrelsen-national-group_06-B-2026-10` (ID `15064327567`) redovisar `expected_intervals=1`, `observed_files=1`, `reconciled_intervals=1`, Blekinge 3/3 unika diarienummer (`5249-2026`, `5327-2026`, `5330-2026`), `pager_complete=true`, inga dubbletter och inga fel. En sida lästes; `pager_states` innehåller en state utan kandidater och `pager_actions=[]`. Detta verifierar att `single_county=blekinge` isolerar rätt län och att en liten custom-phrase-sökning kan stämmas av. Det verifierar **inte** flersidespaginering eller `Page$1`-övergången. Körningen var `diagnostics_only_no_persistence`; inga snapshots/manifest publicerades.
- **PR #656 – isolerad Blekinge-discovery (mergad 2026-11-25 21:14:25 UTC):** [PR #656](https://github.com/dahlinrobert-lgtm/Skog/pull/656), merge commit `00217176bbf98ed168b297a7aca0828d2841507d`. Den befintliga diagnostics-workflowen har valet `single_county=blekinge`, vilket åsidosätter `county_group` och kör endast Blekinge; standardvärdet `all` behåller befintliga grupper om tre län. Förväntat intervallantal beräknas från faktiskt antal län × fraser. Samma collector, fokuserade tester och diagnostics-only-artifact återanvänds. Workflowen publicerar fortfarande inga snapshots/manifest och har ingen schemaläggning. Arkitekturdokumentationen beskriver valet. Liveverifierat i körning #15 nedan.
- **Pager-riktningsfixen finns i `main`:** `scripts/lansstyrelsen_pager.py` skiljer framåt-/bakåt-ellipsis med hjälp av pager-DOM och regressionstesterna i `tests/test_lansstyrelsen_pager.py` täcker både bakåtriktad `<< ... 2 3 4 5 6` och framåtriktad `1 2 3 4 5 ... >>`. Discovery-workflowen kör detta test. Livekörning #19 verifierade en vanlig sexsidig sökning (253/253), men nådde endast en bakåtriktad ellipsis vid terminalsidans pager och bevisade inte framåtriktad `Page$1`. Livekörning #20 av den tidigare problemfrasen `vattenverksamhet` gav numera 18/18 på en enda sida; den verifierar inte regressionen 143 råa rader/135 unika poster eller glidande sidfönster. Nästa steg är en kontrollerad livekörning med ett känt flersidesresultat som faktiskt exponerar framåtriktad `Page$1`.

- Den befintliga `.github/workflows/lansstyrelsen-monthly-snapshots.yml` publicerar fortfarande godkända snapshots direkt till `main`. Använd inte den för nationella gruppförsök. Ingen återkommande schemaläggning ska aktiveras.
- Källornas historik är ojämn; äldre ärenden kan försvinna ur webbdiariet. Bevara metadata, skilj dokument/bilagor från metadata och granska sekretess, personuppgifter, upphovsrätt och tredje mans rättigheter per handling.
- Länsstyrelsens tidigare besked om tekniska begränsningar kvarstår. Teknisk åtkomst är inte ett godkännande för obevakad insamling, kommersiell användning eller kundvisning. Frånvaro i ett senare sökresultat får aldrig tolkas som att ett ärende har tagits bort.

### 2026-11-27 – Länsstyrelsen: live flersidespaginering verifierad i run #21

[Discovery run #21](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46068669201) kördes från `main` commit `1e350af783f0195fe89ddacafd2c434924a0a5dc`, med Blekinge, sökfrasen `an` och registreringsperiod oktober 2026. Fokuserade valideringstester, insamling, avstämning och artifactuppladdning passerade.

Artifact [15231658044](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46068669201/artifacts/15231658044) verifierades: källtotal 392, 392 unika diarienummer, åtta sidor, `pager_complete=true`, `reconciled=true` och noll processfel. Råa resultatrader per sida var 50, 50, 50, 50, 50, 50, 50 och 42 (summa 392); inga dubbletter av diarienummer eller case-ID rapporterades. Två icke-diarienummerrader per sida var pager-/navigationsrader och ingick inte i resultaträknaren.

**Pagerbeteende:** på sida 1–5 valdes nästa numeriska sida fram till att framåtriktad ellips med argument `Page$6` blev nästa kontroll. Den valdes från logisk sida 5; diagnostiken visar `response_seen=true` och `page_changed=true`. Portalen visade därefter det senare fönstret med `<< ... 4 5 6 7 8`; dess `Page$3`-ellipsis låg efter bakåtknappen `Page$First` och valdes inte. Sidorna 6, 7 och 8 hämtades via numeriska länkar och uttaget stämdes av komplett.

Detta är ett verkligt livebevis för vanlig flersidespaginering, framåtriktad fönsterförflyttning med portalens `Page$6`-kommando samt avvisning av bakåtriktad ellips. Det bevisar **inte** en liveövergång med särskilt `Page$1`-argument: den syntetiska regressionstesten finns, men just den kommandovarianten observerades inte i denna körning. Run #21 innehöll inte heller dubblettöverlapp och återtestade därför inte ursprungliga 143 råa rader/135 unika poster. De separata avstämningsreglerna har dock nu passerat live för 392 råa rader = 392 unika poster.

Körningen var `diagnostics_only_no_persistence`; inga snapshots eller manifest publicerades och ingen historik ändrades. Den ändrar inte källans kommersiella villkor, historiska lagringsrätt, kundvisningsrätt eller distributionsrätt.

### 2026-11-27 – PM-027 inventory #42: Länsstyrelsens diarier

[Project manager read-only inventory #42](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46064154483) avslutades `success` 2026-11-27 20:31 UTC: 3/3 repositories, 0 fel. Collector-tester, JavaScript-syntaxkontroll, repository-insamling och artifactuppladdning passerade. Artifact [15230022338](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46064154483/artifacts/15230022338) granskades. Inventeringen använde Skog `main`-commit `66a1eb32b9b908cebc79c8dd6090e7d6c2fd31bc` och var read-only; inga feature collections hämtades och inga källrepositorier skrevs.

För `lansstyrelsen.public_diary` hittade metadata-only-adaptern 36 manifestrader och 36 daterade snapshotfiler. Samtliga 36 intervall klarade adaptervillkoren: en query per manifestrad, komplett körning, publicerad snapshot som finns i Git-trädet, uttömd paginering, avstämt intervall utan fel samt `source_total = extracted_unique_ids = snapshot_unique_record_count`. Detta är 36 kompletta läns-/fras-/registreringsperiodintervall i arkivet; det är inte nationell täckning, inte en uttömmande diarieförteckning och inte 36 jämförbara återkommande driftkörningar.

Den tidigare problemkörningen [Skog run #46011210069](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46011210069) rapporterade 143 träffar men extraherade 135 när pagineringen avbröts; ingen snapshot publicerades. Efter korrigeringarna har två read-only livekontroller genomförts: [run #19](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46067066036) för Blekinge/`av`/oktober 2026 läste sex sidor och stämde av 253/253 unika diarienummer, med `pager_complete=true` och inga processfel. Pagerdiagnostiken visade dock endast en bakåtriktad `Page$1`-ellipsis på terminaltillståndet; den framåtriktade fönsterövergången användes inte. [Run #20](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46067888304) körde åter `vattenverksamhet`, men källan rapporterade då endast 18 träffar; 18/18 extraherades på en sida, utan dubbletter eller pager-actions. Den tidigare 143/135-regressionen är därför ännu inte live-reproducerad efter fixen. Båda körningarna var `diagnostics_only_no_persistence` och publicerade inga snapshots.

Senaste kompletta arkiverade observation förblir 2026-11-16: Norrbotten, frasen `omgrävning av vattendrag`, registreringsperiod 2026-09-01–2026-09-30, 0/0 poster. Det är ett komplett nollresultat för just det avgränsade intervallet, inte belägg för frånvaro i andra fraser, perioder eller län.

Den registrerade källprofilen saknar fortfarande `operations_profile`; drift-/riskbedömning och pilot readiness är därför `unknown/not_assessed`. Inventory #42 ändrar inte källans kommersiella villkor, rättighet till historisk lagring, kundvisning eller distributionsrätt. Dessa ska fortsätta bedömas separat.

Pager-riktningsfixen och regressionstesterna finns redan i aktuell `main`; den gamla arbetsbranchen ska inte användas som leverans. Nästa steg är en kontrollerad livekörning med ett flersidesresultat där framåtriktad `Page$1` faktiskt väljs, svaret tas emot och sidfönstret ändras. Försök åter fånga 143/135 om källan erbjuder ett jämförbart resultat, men om källtotalen har förändrats ska vi inte jämföra olika uttag som om de vore samma population. Behåll den senaste kompletta observationen och alla tidigare snapshots.

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


### Projektledardashboard – geografisk testnivå (2026-11-22)

PR #477 innehåller dashboardsektioner för pågående/olösta schemalagda körningar och återhämtade fel. Dubblering av schemalagda fel i den generella fellistan har tagits bort och felaktiga bokstavliga \\n-sekvenser i HTML har korrigerats. History-repots PR #42 lägger till en explicit katalog som mappar exakta workflow-sökvägar till granskad geografisk nivå och utvecklingsfas; oregistrerade workflows får värdet unknown. Katalogen innehåller verifierade poster för Gräsmyr, Norrbotten och nationell insamling. PR #42 är ännu inte verifierad/mergad; efter merge ska collector-data och dashboard synkroniseras och testas tillsammans.

Ingen schedule, insamlingsfrekvens, geografi, Azure-behörighet eller kundpublicering har ändrats.


### Projektledaragent – inventory #3 publicerad till Azure (2026-11-22)

- Read-only inventory [#3](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45002255351) kördes manuellt från `main` på commit `fc1c91d3204e0add22b5ef1bdcc446c83802a7fe`; status success, 3/3 aktiva projekt, 0 fel. Python-tester och dashboard-JavaScript-syntaxkontroll passerade i samma körning.
- Artifact `project-manager-inventory-45002255351` (6 548 byte) hämtades från GitHub Actions och inspekterades. Inventeringen innehåller exakt tre aktiva projekt: Skog, alg-grasmyr och project-manager-history. Workflow-run-data annoteras från `data/workflow_metadata.json`; oregistrerade workflow-sökvägar får `unknown`.
- Azure-publicering [#2](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45002466042) verifierades i jobbloggen: provenienskontroll, validering, Azure OIDC-inloggning och upload/read-back för både `snapshots/45002255351/dashboard-data.json` och `snapshots/45002255351/manifest.json` lyckades. Båda filerna jämfördes byte-för-byte efter Azure read-back. Publiceringen är run-scoped och append-only; äldre snapshot `44958916377` är orörd.
- En separat branch `feat/project-manager-snapshot-45002255351` uppdaterar den fasta Blob-referensen i `docs/project-manager/auth-config.js` till snapshot `45002255351`. Detta ska inte mergas/deployas innan Blob CORS för exakt GitHub Pages-origin är verifierad och riktig MSAL-inloggning samt Blob-läsning har testats.
- Kvarvarande aktiveringsgrindar: verifiera/configurera Blob-service CORS för `https://dahlinrobert-lgtm.github.io` med minsta nödvändiga metoder/headers; granska PR för snapshotreferensen; efter CORS-godkännande deploya statiskt skal och testa autentiserad läsning, anonym nekad åtkomst, saknad blob, gammal/partiell snapshot och nätverksfel. Ingen schemaläggning, publikering till kund eller automatisk latest-pekare aktiveras.


### Projektledardashboard – verifierad Azure-läsning och återstående säkerhetskontroll (2026-11-22)

- Efter merge av PR #478 och GitHub Pages deployment [#45002654191](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45002654191) har användaren bekräftat i webbläsaren att Microsoft-inloggning fungerar och att dashboarden hämtar den privata Azure Blob-snapshoten `45002255351`. Skärmen visar 3/3 projekt, 15 öppna poster, 0 olösta avvikelser och 56 lyckade körningar i urvalet. Detta verifierar den autentiserade läsvägen i den aktuella sessionen.
- Negativ åtkomstkontroll är ännu inte genomförd: utloggad/anonym åtkomst till dashboard och direkt Blob utan token ska nekas. Detta ska testas separat; fungerande inloggning bevisar inte i sig att alla obehöriga vägar är stängda.
- Azure CORS-regeln har enligt användarens bekräftelse uppdaterats med GitHub Pages-origin och begränsade metoder/headers. Den faktiska webbläsarläsningen fungerar nu. Spara inga token eller hemligheter i dokumentationen.
- Dashboardens roadmap uppdateras i en separat PR: privat hosting flyttas från planerat till verifierad; kvarstående anonym/obehörig nekad åtkomst visas som återstående; schemalagd insamling förblir planerad; run-scoped append-only-snapshot, manifest, SHA-256 och read-back är verifierade medan retention/restore-test återstår.
- Den synliga bokstavliga `\\n` mellan HTML-sektioner tas bort. Ingen auth-konfiguration, Azure RBAC, CORS, insamlingsfrekvens eller publiceringsfrekvens ändras i denna PR.


### Slutlig verifiering av projektledarens privata Azure-läsning (2026-11-22)

Denna notering ersätter tidigare punkter ovan som anger att anonym åtkomstkontroll, CORS eller snapshotkopplingen återstår.

- **Autentiserad läsning:** användaren har verifierat i webbläsaren att Microsoft-inloggning lyckas och att dashboarden läser privat Azure Blob-snapshot `45002255351`. Dashboarden visade 3/3 projekt och innehåll från det privata historikrepot.
- **Utloggad vy:** efter Microsoft-utloggning visade GitHub Pages `Inte inloggad`, enbart knappen `Logga in` och texten att ingen projektdata hämtas före autentisering. Ingen privat projektdata visades.
- **Direkt anonym Blob-åtkomst:** användaren öppnade den exakta URL:en för `snapshots/45002255351/dashboard-data.json` utan token. Azure svarade med `PublicAccessNotPermitted` och meddelandet `Public access is not permitted on this storage account.` Därmed är anonym direktläsning av snapshoten nekad på lagringskontonivå.
- **CORS:** användaren konfigurerade Blob service-regeln för GitHub Pages-origin med endast `GET`, `HEAD`, `OPTIONS` och nödvändiga headers. Den efterföljande autentiserade webbläsarläsningen fungerade.
- **Bedömning:** autentiserad webbläsarläsning, utloggad UI och anonym direkt Blob-åtkomst är manuellt verifierade. Detta verifierar den avsedda läsvägen och att publik Blob-åtkomst är avstängd. Det ersätter inte en fullständig penetrationstestning eller separat kontroll av alla möjliga identitets-/RBAC-scenarier.
- **Driftstatus:** dashboarden är publicerad och fungerar med den fasta run-scoped snapshoten. Automatisk schemalagd inventory/publicering, retention och återställning är fortfarande separata planerade arbetssteg. Ingen kundpublicering eller kundåtkomst är aktiverad.


### Skogskoll – kundwebbens arkitekturgranskning (2026-11-22)

- Användaren har valt att Skogskoll ska vara den enda kundprodukten; Skog är den bakomliggande interna dataplattformen. Skogs interna Gräsmyr-, analys- och pilotvyer ska inte ingå i kundnavigationen.
- Granskningen finns i [SKOGSKOLL_WEB_ARCHITECTURE.md](SKOGSKOLL_WEB_ARCHITECTURE.md). Den bygger på aktuell `main` och inventerar publiceringsstruktur, kundprototyp, befintliga domänmoduler, schema/RLS och källstatus.
- Verifierat problem: GitHub Pages-roten `docs/index.html` är en Gräsmyr-/Nordmaling-orienterad intern analysvy; kundprototypen ligger i `skogskoll/index.html` och dess huvudnavigation länkar tillbaka till interna Skog-sidor. Skogskoll-sidan är en monolitisk prototyp med lokal lagring och syntetisk matchning, inte en produktionsansluten kundapp.
- Befintliga worker-/domänmoduler, tester och Supabase/PostGIS-schema ska bevaras och hållas separerade från publika frontend-assets. Ingestion, service-role-nycklar och källspecifik hämtning får inte flyttas till webbläsaren.
- Källstatusrapporten anger noll källor uttryckligen godkända för kundvisning vid senaste rapporterade registerkontroll. Kundwebben ska därför stödja rättighetsstyrd publicering per exakt produkt/lager; teknisk åtkomst räcker inte.
- En separat dokumentationsbranch `docs/skogskoll-web-architecture-review` har skapats för granskningen. Nästa kodsteg enligt dokumentet: isolera kundnavigationen, lägga grund för gemensamt designsystem och testa relativa länkar utan att ändra befintlig datalogik eller interna Skog-sidor.
- Inga produktionskopplingar, datakällor, aviseringar eller kundvisningar har aktiverats i detta arbete.

## Skogskoll – dag-för-dag-flödet som produktens USP (2026-11-22)

Användaren har bekräftat att snapshot- och dag-för-dag-visningen i ett sammanhängande flöde är Skogskolls främsta särskiljande värde. Kundupplevelsen ska därför utgå från ett kronologiskt förändringsflöde byggt av daterade snapshots; karta, bevakningar och historik ska vara kopplade till samma tidsmässiga sammanhang.

- Startsidan ska vara **Flöde**, inte en generell statistiköversikt.
- Flödet ska skilja mellan tillkommet, ändrat och eventuellt försvunnet, men försvunnet får endast visas när två kompletta och jämförbara snapshots ger tillräcklig evidens.
- Varje händelse ska visa källans händelsedatum, publiceringsdatum och Skogskolls första upptäckt separat.
- Dagval och jämförelse ska kunna spåras till snapshot, källa, körnings-ID, status, täckning och kontrollsumma när relevant.
- Kartan ska synkroniseras med vald dag/händelse. Historiken ska visa samma objekts utveckling över flera snapshots.
- Syntetiska testposter får aldrig visas som verkliga kundhändelser. Ingen riktig feed är ansluten i första UI-steget.
- Källstatusrapporten som granskades 2026-11-18 anger noll källor uttryckligen godkända för kundvisning; status måste uppdateras och bedömas per exakt lager innan publicering.

Första UI-implementationen ligger i branch `feat/skogskoll-daily-change-feed-shell`: kundnavigation, primär flödesyta, dagväljare med tydlig frånvaro av anslutna snapshots, kartplaceholder utan länk till intern Skog-karta samt riktade UI-regressionstester. Backend, riktiga snapshots, källvisning och aviseringar aktiveras inte i detta steg.


## Skogskoll change-feed – kontrakt implementerat i utvecklingsbranch (2026-11-22)

- PR #483 är mergad till `main`: kundskalet har snapshotbaserat dag-för-dag-flöde och ren kundnavigation. Det betyder inte att verkliga snapshots eller kundhändelser är anslutna.
- Ny branch `feat/skogskoll-change-feed-contract` innehåller ett första fristående kontrakt och ren domänfunktion: `docs/SKOGSKOLL_CHANGE_FEED_CONTRACT.md`, `skogskoll/src/change-feed-contract.mjs` och `skogskoll/tests/change-feed-contract.test.mjs`.
- Jämförelse kräver kompletta snapshots med samma source, product, layer, coverage_key, schema_version och identity_version samt distinkta snapshot-/run-ID och strikt senare captured_at.
- Första kompletta baslinjen är tyst. Efter baslinje skapas endast first_seen/changed när kundvisningsstatus är approved och rights_evidence_ref finns. Oförändrad hash skapar ingen händelse.
- Frånvaro i aktuell snapshot skapar aldrig borttagningshändelse. Okänd/partiell/failed status och saknad rättighet stänger grinden.
- Funktionen är ren och skriver inte till databas, anropar inte API, aktiverar inte ingestion eller aviseringar. Den befintliga ingestionen är fortsatt Skogsstyrelsen-specifik.
- Testerna är tillagda i den befintliga Node-testkatalogen; de behöver verifieras av GitHub Actions innan kontraktet betraktas som CI-verifierat.
- Källstatusrapporten var senast genererad 2026-11-18 och angav inga källor uttryckligen godkända för kundvisning i den sammanfattande bedömningen. Rättighetsgrinden är därför avsiktligt stängd tills en exakt källa/produkt/lagerpost och evidens godkänts.

**Nästa steg:** verifiera PR-CI och granska kontraktet mot befintliga snapshotmanifest och databasens historikfält. Därefter kan ett separat API-/persistensförslag tas fram; ändra inte databasschema eller koppla verklig kundfeed innan den granskningen och rättighetsbedömningen är klar.


## Skogskoll change-feed-kontrakt – merge verifierad (2026-11-22 14:44 CET)

**Korrigering av föregående statusnotering:** PR #484 är nu verifierat mergad. GitHub REST visar `state=closed`, `merged=true`, `merged_at=2026-11-22T13:44:18Z` och merge commit `8f44a442e3e0eafb8055b03769e3d2877b05f725`. Användarens skärmbild bekräftar också GitHubs Merged-status.

- Kontraktet finns nu på `main`: `docs/SKOGSKOLL_CHANGE_FEED_CONTRACT.md`.
- Domänkärna och tester finns på `main`: `skogskoll/src/change-feed-contract.mjs`, `skogskoll/tests/change-feed-contract.test.mjs`.
- CI för kund-UI och hela Node-testsviten passerade i [run #45028806338](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45028806338).
- Befintlig source probe och relaterade ingestion-/SQL-kontroller passerade i [run #45028806343](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45028806343).
- Testworkflowens path-filter omfattar nu `skogskoll/src/**`, `skogskoll/tests/**` och kontraktsdokumentationen vid pull requests samt push till main.
- Ingen databas, kund-API, riktig kundfeed, ingestion eller avisering aktiverades.

**Nästa steg:** inventera befintliga snapshotmanifest och historikfält mot kontraktet. Identifiera vad som redan finns och vad som saknas innan någon databas-/API-mappning föreslås. Källstatusrapporten från 2026-11-18 anger fortfarande noll uttryckligen godkända kundvisningskällor; rättighetsgrinden förblir stängd.


## Skogskoll snapshot- och historikinventering (2026-11-22)

PR #486 är mergad (merge commit `31300a91b29f323a4f2ea677942de79594259a21`). En kod- och filbaserad inventering har genomförts och dokumenterats i [SKOGSKOLL_SNAPSHOT_INVENTORY.md](SKOGSKOLL_SNAPSHOT_INVENTORY.md).

Huvudfynd:
- Befintlig Skogskoll-DB har `source_observations` (current state), append-only `source_observation_history`, `poll_runs`, `scan_sessions` och `scan_seen_ids`. Atomisk sidcommit och strikt fullständighetskontroll finns i migrations 002–003. Finish av scan inaktiverar inte poster som saknas.
- Observationens identitet/hash och första baseline/efterföljande inserted/changed är redan modellerade, men worker/adaptern är källspecifik för Skogsstyrelsens avverkningsanmälningar.
- DB saknar uttryckliga snapshot-/produkt-/lager-/coverage-/schema-/identity-/rights-envelope-fält och history rows refererar poll_run_id, inte snapshot_id.
- Repot innehåller flera filbaserade format: 380 spårade planerade-avverknings-snapshots, 377 utförda-avverkningsarkiv, 22 samrådssnapshots, 36 diariefiler och Trafikverkets lager-manifest i pilotkatalogen. Dessa är separata format och scope; filantal avser GitHub-trädet, inte privata molnarkiv.
- Deltafältet `removed` används i arkivrekonstruktion och får inte mappas direkt till kundhändelse.
- Källstatusrapporten från 2026-11-18 anger noll källor uttryckligen godkända för kundvisning.

**Nästa steg:** bygg och testa en ren adapter-mappning för Skogsstyrelsens nuvarande `poll_runs` + `scan_sessions` + observationshistorik till snapshot-envelope. Kräv verifierad komplett scan, stabilt coverage key och rättighetsevidens. Ingen migration, livefeed eller kundvisning innan adapterkontraktet är granskat och testat.

## Skogsstyrelsen – månatlig källkontroll (2026-11-22)
- Ny PR-branch `feat/skogsstyrelsen-monthly-source-audit` etablerar `.github/workflows/skogsstyrelsen-monthly-source-audit.yml` och `docs/SKOGSSTYRELSEN_CASE_CHANGE_MONITORING.md`.
- Månatligt workflow: första dagen i månaden kl. 07:17 UTC. Det kör tester, hämtar fullständiga Samråd point/line/polygon inom befintligt Gräsmyr-pilotscope, tar snapshot av utförda avverkningar inom samma scope och kör read-only-proben för planerade avverkningsanmälningar.
- Viktig avgränsning: planerade avverkningsanmälningar har i denna första version endast en begränsad probe (högst tre sidor), inte en fullständig månadssnapshot. Befintlig probe är schemalagd var sjätte timme. Nationell täckning är inte etablerad.
- Samråd har redan ett separat dagligt pilotflöde. Månadskontrollen är en extra avstämning, inte ersättning för daglig insamling.
- Månatlig kontroll får inte tolka saknade ID som borttagning/avbokning/utförd åtgärd. Jämför endast samma källa/lager/scope och bevara originaldata.
- Nästa steg efter PR: verifiera workflow manuellt och kontrollera samtliga steg/artifact/commits; därefter granska metadata för edit tracking och bygg full paginerad snapshot för planerade anmälningar om kapacitet och fält stöder det. Skala inte nationellt innan pilotens fullständighet är verifierad.

## Skogsstyrelsen monthly audit – publiceringsfel och korrigering (2026-11-22)

- Första manuella run #4: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45031069869
- Alla tester och tre insamlingssteg lyckades: Samråd point/line/polygon, completed-harvest snapshot och planned-harvest read-only probe. Probe-rapporten laddades upp som artifact.
- Publiceringssteget skapade lokalt fyra ändrade filer (bl.a. Samråd snapshot `samrad_20261122T140801Z.json.gz` och utförd-avverkning snapshot `completed_20261122T140801Z.geojson.gz`) men push till main blockerades fem gånger av GH013 eftersom main kräver PR. Dessa snapshotfiler publicerades alltså inte till main.
- Korrigerings-PR skapas på branch `fix/skogsstyrelsen-snapshot-pull-request`: ersätt direktpush med `peter-evans/create-pull-request@v7`, automation branch `automation/skogsstyrelsen-monthly-source-audit`, och rättigheten `pull-requests: write`. Snapshot-PR ska granskas och mergas manuellt; ingen auto-merge.
- **Nästa steg:** merge korrigerings-PR, kör månadsaudit manuellt igen, verifiera att snapshot-PR skapas och granska innehåll/manifest innan den mergas.


## Skogsstyrelsen monthly audit – PR-publicering mergead (2026-11-22)

- Korrigerings-PR #489 är mergad till main: https://github.com/dahlinrobert-lgtm/Skog/pull/489
- Merge commit: `4c62e11b58c213e715bd9c4d939d514626cc2359`.
- PR-kontroll run #5 (45031856059) passerade testerna. Eftersom det var en `pull_request`-körning hoppades samtliga källinsamlingar och snapshot-PR-steget av enligt workflowvillkoren. Den verifierar alltså workflowets testgrind, inte publicering eller källinsamling.
- Nästa steg: kör workflow_dispatch manuellt från main och verifiera att Samråd, utförda avverkningar och planned-harvest probe körs samt att en separat snapshot-PR skapas. Granska snapshot-PR:n före merge.


## Skogsstyrelsen monthly audit – första lyckade publiceringskörningen (2026-11-22)

- Manuell `workflow_dispatch` run #6 lyckades: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45033322810
- Alla jobb/steg passerade, inklusive tester, Samrådinsamling, completed-harvest snapshot, planned-harvest probe, skapande av snapshot-PR och artifact-uppladdning.
- Automatiska data-PR:n [#491](https://github.com/dahlinrobert-lgtm/Skog/pull/491) mergades 2026-11-22 kl. 14:38:33 UTC (merge commit `e83b9d3059f91099497ad65d66dd35015d0c4cec`). Snapshotfilerna och latest-manifesten finns nu beständigt i `main`.
- Samråd, Gräsmyr-pilotens 10 km cirkulära scope: points 0; lines 20 hämtade i envelope, 11 kvar efter exakt cirkelfilter; areas 14 hämtade i envelope, 12 kvar efter exakt cirkelfilter. Status success för samtliga lager. Snapshot: `data/samrad_snapshots/samrad_20261122T143240Z.json.gz` (401 155 byte); scope hash `9c597758897297d34eb6ae733e56c5998587de4ff478fd8e82ae1a510dcfa76a`.
- Utförda avverkningar: 1 631 objekt i aktuell fullständig kontroll inom 10 km-scope. Ingen baseline; 0 nya, 0 saknade och 0 geometriändrade ID:n. Arkivfilen `completed_20261122T143240Z.geojson.gz` är en delta på 479 byte med 0 tillagda/uppdaterade/borttagna objekt; detta betyder oförändrat läge, inte att lagret är tomt. Full komprimerad motsvarighet uppskattades till 6 217 406 byte.
- Planerade avverkningsanmälningar: read-only-probe lyckades men är uttryckligen inte fullständig. Källan rapporterade 132 594 poster; proben läste 300 poster (3 sidor), capped=true, complete_scan=false, ca 0,0754 % av lagret. Den får inte användas som fullständig historik eller larmunderlag.
- Probe-artifact: `skogsstyrelsen-monthly-source-audit-45033322810`, artifact ID 14758965735, SHA-256 `c7a63d038d180ace683e90f086b790857b63f9adfe293cf93506805516c987de`.
- **Verifieringsstatus:** den PR-baserade publiceringsvägen är verifierad och snapshotinnehållet från run #6 är beständigt i `main` efter merge av PR #491. Planerade avverkningsanmälningar är fortfarande endast en begränsad probe.
- Rättighetsgrinden för kundvisning påverkas inte. Ingen kundfeed eller larmfunktion aktiveras av denna körning.


**Nästa konkreta steg:** bygg och verifiera en fullständig, paginerad och auditerbar snapshotlösning för planerade avverkningsanmälningar. Nuvarande 300-radersprobe är inte komplett.


## Statuskorrigering efter merge av PR #491 och #492 (2026-11-22)

- PR #491 är mergad till `main` med merge commit `e83b9d3059f91099497ad65d66dd35015d0c4cec`; snapshots/latest-filerna från run #6 är beständiga.
- Dokumentations-PR #492 är mergad till `main` med merge commit `950df85b3f6ded7b586b346815a80547e76cd348`.
- Run #6 verifierar insamling, snapshotgenerering, PR-publicering och artifact-uppladdning för Samråd och utförda avverkningar i Gräsmyr 10 km-piloten.
- Planerade avverkningsanmälningar är fortsatt endast en bounded probe: 300 av cirka 132 594 poster. Fullständig paginering, historik och ändringsspårning återstår.
- Nästa konkreta tekniska steg är att undersöka ArcGIS metadata/edit tracking och implementera/testa fullständig paginering för planerade avverkningsanmälningar. Ingen kundvisning eller kundavisering aktiveras.


## Status efter merge av Samråd- och Life2Taiga-publiceringsfixar (2026-11-22)

- PR #494 (Samråd) mergades till `main` med merge commit `740a481436004537c277b5bdc91e004ab4f6627f`.
- PR #495 (Life2Taiga) mergades till `main` med merge commit `88bd4bad06496340d3aec1f3f6ebab83d37049a1`.
- Efter merge körde Samråd-workflowet på push till main och lyckades: [run 45037391885](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45037391885). Tester, insamling av point/line/polygon, event-bundle och PR-publicering passerade.
- Efter merge körde Life2Taiga-workflowet på push till main och lyckades: [run 45037447855](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45037447855). Collector-test, hämtning, GeoJSON-validering och PR-publicering passerade.
- Dessa körningar skapade granskningsbara data-PR:er: [Samråd #496](https://github.com/dahlinrobert-lgtm/Skog/pull/496) och [Life2Taiga #497](https://github.com/dahlinrobert-lgtm/Skog/pull/497). Båda är öppna och ska granskas manuellt; ingen automatisk merge används.
- Viktig avgränsning: körningarna efter merge utlöstes av push till `main`, inte av cron. Schemalagd drift är därför ännu inte bekräftad efter korrigeringen. Nästa kontroll ska verifiera en faktisk schemalagd körning och att den skapar/uppdaterar respektive data-PR.
- Ingen kundvisning eller kommersiell rättighet följer av att data hämtas och publiceras i granskningsbara PR:er.

**Nästa konkreta steg:** granska PR #496 och #497:s filinnehåll, manifest, täckning och datadiff innan merge. Därefter invänta/utvärdera nästa cron-körning för båda flödena. Separat kvarstår fullständig paginering och historik för planerade avverkningsanmälningar.


## Statuskorrigering efter merge av data-PR #496 och #497 (2026-11-22)

- Samråd snapshot-PR #496 är mergad till `main` kl. 15:20:45 UTC, merge commit `f442d6a24832a347319bd7c70fa08e331b2a0674`.
- Life2Taiga data-PR #497 är mergad till `main` kl. 15:21:08 UTC, merge commit `467322df3f1c591717e58b0f650717471d2b80cc`.
- Därmed är båda datauppsättningarnas aktuella PR-baserade publicering genomförd till `main`, efter manuell granskning/merge.
- Efterföljande körningar #45037391885 (Samråd) och #45037447855 (Life2Taiga) var push-utlösta av workflow-fixarnas merge och skapade PR #496/#497. De är inte bevis på senare cron-körning.
- PR #498 dokumenterar publiceringsfixarna och är fortfarande öppen; dess kund-UI-test passerade.
- **Nästa steg:** verifiera nästa verkliga schemalagda körning för Samråd och Life2Taiga. Granska därefter resultat, manifest, täckning och PR-diff. Fullständig planerad-avverkning-paginering är fortsatt separat kvarstående arbete.


## Statuskorrigering efter merge av PR #498 (2026-11-22)

- Dokumentations-PR [#498](https://github.com/dahlinrobert-lgtm/Skog/pull/498) är mergad till `main` kl. 15:26:24 UTC med merge commit `21cfa30af358588eb6889d27f78b4e8bffc1fa9a`.
- Kundgränssnittstesterna passerade efter merge: [run 45038321932](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45038321932).
- Samråd-data-PR #496 och Life2Taiga-data-PR #497 är båda mergade. Deras snapshot-/datasetinnehåll finns beständigt i `main`.
- Samråd- och Life2Taiga-workflowfixarna (#494/#495) har verifierats med push-utlösta körningar som skapade data-PR:erna #496/#497. Det finns ännu ingen senare cron-utlöst lyckad körning efter dessa ändringar i den kontrollerade Actions-historiken.
- Nästa steg är att granska kommande schemalagda körningar och kontrollera att de skapar eller uppdaterar PR #496/#497-flödena utan direktpush. Därefter fortsätter arbetet med fullständig paginering av planerade avverkningsanmälningar.


## Gräsmyr – snapshot reconcilerad och publicerad via PR #502 (2026-11-22)

- Ersättnings-PR [#502](https://github.com/dahlinrobert-lgtm/Skog/pull/502) mergades 2026-11-22 kl. 15:50:22 UTC. Merge commit: `62a4d0d471409ae4af544128bc1dcef6bf30ae94`.
- Ursprunglig data-PR #485 stängdes utan merge efter att den visat sig ligga efter aktuell `main`. PR #502 byggdes från då aktuell `main` och förde över Gräsmyr-pilotens snapshot utan att skriva över senare Samråd-data eller senare data för genomförda avverkningar.
- Planerade avverkningsanmälningar: lyckad körning 2026-11-22 13:20:19 UTC, status `ok`, 165 objekt och 165 unika ID:n inom Gräsmyr 10 km-scope. Snapshot `data/snapshots/20261122T132019Z.json`; `initial_run=false`, befintlig baseline `20261121T155530Z.json`, 165 objekt före och efter, inga tillagda/uppdaterade/borttagna objekt i denna jämförelse.
- Change analysis skapad 2026-11-22 13:44:18 UTC: 381 planerade snapshots lästa, 0 oläsbara; 1 631 genomförda geometrier laddade. Analysens kategorier är evidens-/uppföljningsklassningar, inte bevis för att en viss planerad avverkning har genomförts.
- Sammanfogat `data/harvest_event_bundle.json` och `docs/data/harvest_event_bundle.json`: 188 observationer, 188 händelser, 188 evidensposter, 11 relationer och 165 kedjor. Gräsmyrs planerade avverkningskörning (165 poster) och aktuell Samrådskörning från main (23 poster) finns kvar som separata källkörningar. Båda bundle-filerna har samma innehåll.
- Ny daterad arkivfil för genomförda avverkningar `data/snapshots/completed_20261122T132033Z.geojson.gz` lades till. Befintlig `data/completed_latest.json` och senare genomförda-avverkningsdata från main behölls oförändrade.
- PR #502 omfattade nio filer. Efter merge verifierades att main pekar på merge committen och att ovanstående snapshot-/manifestdata finns på main. JSON-parsning och unika ID:n kontrollerades före PR. Ingen separat CI-körning/check-run utlöstes för denna data-only PR; gzip-arkivets innehåll har inte verifierats separat.
- PR-baserad publicering och databevarande är verifierade för denna körning. Detta etablerar inte nationell täckning, fullständig paginering av planerade anmälningar eller kommersiell rätt/kundvisning.

**Nästa konkreta steg:** fortsätt enligt prioriteringen att undersöka ArcGIS metadata/edit tracking och bygg fullständig, paginerad och auditerbar insamling av planerade avverkningsanmälningar. Verifiera sidantal, totalantal, stabila ID:n, fullständighetsmanifest och minst två jämförbara kompletta körningar innan frånvaro används som förändringssignal. Bevaka samtidigt nästa faktiska cron-körningar och deras data-PR:er. Ingen kundfeed eller kundavisering aktiveras.


## Komplett pagineringsflöde för planerade avverkningsanmälningar – kod mergad (2026-11-22)

- PR [#504](https://github.com/dahlinrobert-lgtm/Skog/pull/504) mergades 2026-11-22 kl. 16:02:26 UTC, merge commit `f75f5ac0832c4823da18fe88de1f516b5d7774f5`.
- Nya filer: `scripts/snapshot_harvest_notifications_pilot.py`, `tests/test_snapshot_harvest_notifications_pilot.py` och `.github/workflows/skogsstyrelsen-complete-harvest-pilot.yml`.
- Flödet är separat från befintlig sex­timmarsprobe och körs manuellt via `workflow_dispatch`. Scope är Gräsmyr 10 km (center 19.66455, 63.74646). Det är inte nationell insamling.
- Insamlingsmetod: ArcGIS `returnIdsOnly` inventerar alla ID:n för scopet; varje ID hämtas därefter via object-ID-batcher. Antal och ID-inventering kontrolleras före och efter uttaget. Batchar med transfer-limit, saknade/duplicerade ID:n eller källförändring under körningen avbryter hela körningen. Fel skriver inte latest-manifest och rör inte tidigare snapshots.
- Godkända PR-checkar: riktat workflow [run 45040997464](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45040997464) och bred snapshot storage-testsvit [run 45040997430](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45040997430). Den riktade PR-checken hoppade avsiktligt över själva insamlingen och data-PR-publiceringen; endast skyddstesterna kördes. En första körning #45040980543 misslyckades eftersom workflowet checkade ut main i stället för PR-grenen; checkout korrigerades och omkörningen passerade.
- Efter merge startade push-utlösta körningar för Gräsmyr monitoring [45041585086](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45041585086) och snapshot storage tests [45041585043](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45041585043). De är inte den manuella kompletta insamlingen och inte cron-verifiering.
- **Operativ verifiering återstår:** starta `.github/workflows/skogsstyrelsen-complete-harvest-pilot.yml` manuellt på `main` med `workflow_dispatch`. Kontrollera fullständig ID-inventering, count_before/count_after, ID-inventory stability, feature_count, snapshot SHA-256 och att data-PR skapas. Inga frånvarosignaler eller larm förrän minst två kompletta, jämförbara körningar finns.
- Ingen kundfeed, kundavisering eller rättighetsstatus ändras. Teknisk fullständighet inom pilotscopet är inte nationell täckning eller kommersiellt godkännande.

**Nästa konkreta steg:** kör workflowet manuellt efter att push-utlösta main-kontroller är klara. Granska den skapade data-PR:n och manifestet. Kör sedan en andra komplett körning vid senare tidpunkt med samma scope och jämför antal, ID:n och SHA-256. Först därefter bedöms om frånvaro kan bli en säker förändringssignal.


## Första kompletta Gräsmyr-hämtningen arkiverad på main (2026-11-22)

- Efter korrigeringen i PR [#506](https://github.com/dahlinrobert-lgtm/Skog/pull/506) lyckades manuell workflow-körning [#5 / run 45042577564](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45042577564). Alla steg passerade: skyddstester, komplett ArcGIS-hämtning, artifact-uppladdning och data-PR-publicering.
- Data-PR [#507](https://github.com/dahlinrobert-lgtm/Skog/pull/507) mergades 2026-11-22 16:15:13 UTC. Merge commit: `565a1134ac973bcf963e5269681792bb726a4054`; main verifierades på samma SHA.
- Arkiverade filer: `data/skogsstyrelsen/harvest_notifications/grasmyr/latest.json` och `data/skogsstyrelsen/harvest_notifications/grasmyr/snapshots/grasmyr_10km_20261122T161347Z.geojson.gz`.
- Manifest: fångad 2026-11-22 16:13:47 UTC; scope Gräsmyr 10 km, center 19.66455, 63.74646; OBJECTID; returnIdsOnly + object-ID-batcher om 200; count före/efter 165/165; ID count 165; feature count 165; unika ID 165; stabil inventering true; complete_scan true. Okomprimerad storlek 303 866 byte. SHA-256 för okomprimerad GeoJSON: `21df361fbef8b0151e7a01e06d2377fe1f5cb42a1d5265217c1e7b7ea3d6bbee`.
- Workflow-run skapade ett artifact (92 642 byte, artifact digest `sha256:c7f8f75d1847fd7a18d8059ccf86d0fb56aee45c8fe212614e11e32c120994d7`).
- Den tidigare körningen #3 misslyckades efter lyckad hämtning p.g.a. felaktigt tokenuttryck. PR #506 korrigerade autentisering och flyttade artifact-uppladdningen före PR-publicering. Körning #5 bekräftar att den korrigerade kedjan fungerar.
- Detta är första kompletta arkiverade observationen för scopet. En andra komplett körning vid senare tidpunkt krävs för att mäta förändringar. Ingen frånvaro får ännu klassas som borttagning och inga larm/kunddatabas-skrivningar sker.
- Ingen nationell täckning har verifierats. Kommersiella rättigheter och kundvisning ändras inte av den tekniska arkiveringen.

**Nästa konkreta steg:** kör samma manuella workflow igen vid nästa lämpliga kontrolltillfälle. Jämför ID-inventering, antal, objektinnehåll och manifest. Om källan är komplett och jämförbar, dokumentera differenser utan att ännu skapa kundlarm. Behåll sex­timmarsproben som separat monitor.


## Gräsmyr analys prestanda – strömmad arkivhantering (2026-11-22)

- PR [#509](https://github.com/dahlinrobert-lgtm/Skog/pull/509) mergades till main i commit `adac73f7d960330aa4a00f9612e99823b4fa8979`.
- Bakgrunden var att Gräsmyr monitoring-run [45041585086](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45041585086) hade stått länge i steget `Analyze planned and completed changes`. Vid kontroll 16:30 UTC var den fortfarande markerad in_progress; loggar kunde inte hämtas via GitHub-loggendpointen.
- Inventering av arkivfiler på main visade 379 genomförda-avverkning-arkiv under `data/snapshots/completed_*.geojson.gz`, cirka 194,8 MB komprimerat. 38 var större kontrollpunkter och 341 små deltaarkiv.
- `completed_snapshot_store.py` har nu `iter_completed_archive_transitions`, som strömmar giltiga arkivtillstånd och lämnar vidare endast tillagda/ändrade objekt från deltaarkiv. Fulla kontrollpunkter jämförs med föregående jämförbara tillstånd. `read_latest_completed_archive` återskapar endast senaste giltiga tillstånd för aktuell analys.
- `analyze_changes.py` använder dessa funktioner i stället för att materialisera samtliga historiska fullständiga tillstånd två gånger. Första arkivet förblir baslinje. Saknad/ogiltig delta-bas och ändrat scope får inte bli borttagningar eller förändringshändelser. Arkivparens räknare och scope-diagnostik behålls.
- Tester passerade på PR-grenen: [completed evidence transitions #45044134864](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134864), [completed snapshot tests #45044134796](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134796), [full snapshot storage tests #45044134896](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134896), [geometric union #45044134822](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134822) och [monthly source audit checks #45044134806](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134806).
- Workflowet `.github/workflows/completed-snapshot-store-tests.yml` har avgränsats till relevanta tester och installerar projektets beroenden före testning.

**Operativ verifiering återstår:** main-push startade en ny Gräsmyr monitoring-run [45044260811](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044260811), som vid dokumentationstillfället stod i pending på grund av den tidigare körningen med samma concurrency-grupp. Följ den nya körningen och verifiera att analyssteget avslutas och att data-PR skapas. Jämför faktisk körtid med den tidigare körningen. Därefter körs den andra kompletta Gräsmyr 10 km-snapshoten separat. Ingen kundavisering eller frånvaroklassning aktiveras före jämförbara kompletta observationer.


## Projektstyrning mot slutmålet – uppdatering 2026-11-22

Slutmålet är en driftsäker och kommersiellt hållbar Skogskoll-tjänst för privata skogsägare: registrera fastighet/bevakningsområde, upptäcka och verifiera relevanta skogshändelser, matcha dem geografiskt, visa spårbar historik och – först efter godkända datakällor och verifierad baslinje – skicka valbara aviseringar.

Arbetet styrs nu i fyra parallella men begränsade huvudspår:
1. Tillförlitlig kärnbevakning av avverkningsanmälningar, samråd och utförda avverkningar.
2. Gemensamt snapshot-/historikflöde med fullständighetsgrindar, manifest, proveniens och återställning.
3. Produktionsverifiering av Skogskolls databas, autentisering, RLS, PostGIS och serverbaserad ingestion i separat testmiljö.
4. Källspecifika rättighetsbesked för lagring, bearbetning, kommersiell användning och kundvisning.

Projektets roadmap och backlogg är styrande planeringsunderlag; en merge eller lyckad teknisk körning innebär inte automatiskt produktions- eller kundberedskap. Se `PROJECT_ROADMAP.md`, `PROJECT_BACKLOG.md` och `PROJECT_STATUS.md`.

Senast verifierad Gräsmyr-status 2026-11-22: PR [#514](https://github.com/dahlinrobert-lgtm/Skog/pull/514) rättade arkivrekonstruktionen så att `base_snapshot` följs explicit i stället för att anta föregående filnamn. PR:n mergades i `2ee3159902e70b6dc8c92598d852178d620a6ee5`; riktade arkiv-/evidenstester, full testsvit och audit passerade. Main-monitor-run [#45048859162](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45048859162) avslutades `success` efter 30m22s och samtliga steg passerade, inklusive `Analyze planned and completed changes` och data-PR-publicering. Efter körningen lästes 383 planerade snapshots utan oläsbara filer; 165 aktuella planerade objekt och 1 631 genomförda objekt analyserades. Planerade ID:n jämfördes mellan observationerna 16:42 och 17:20 UTC: exakt samma 165 ID:n återfanns. Analysrapporten rekonstruerade 381 genomförda arkiv, varav 370 jämförbara övergångar, 10 övergångar hoppades över på grund av saknat/ändrat query scope och 702 unika `new_completed_detection_overlap`-händelser återfanns. PR [#515](https://github.com/dahlinrobert-lgtm/Skog/pull/515) granskades och mergades 2026-11-22 i `db4aca33642812ee69a6bff5cf7083b50f320de6`.

Detta verifierar att den korrigerade arkivkedjan når fram till den senaste kompletta observationen och återger historiska evidensövergångar som tidigare saknades. De 702 händelserna är satellitbaserade överlappskandidater för manuell granskning, inte bevis för utförd avverkning. Äldre övergångar med saknat/ändrat scope är fortsatt exkluderade (10 st); inga frånvaroslutsatser får dras från dem. Planerade ID:n matchar exakt, men separat ID-/manifestjämförelse av samtliga genomförda polygoner återstår innan hela 10 km-piloten godkänns. Ingen kundavisering eller frånvaroklassning aktiveras.


## Gräsmyr – jämförelse av genomförda polygoner efter PR #516 (2026-11-22)

Efter PR [#516](https://github.com/dahlinrobert-lgtm/Skog/pull/516) gjordes en separat read-only-jämförelse av `data/completed_latest.json` på föregående monitor-commit `2ee3159902e70b6dc8c92598d852178d620a6ee5` och aktuell `main` efter data-PR #515.

- Observationer: 2026-11-22 16:42:36.002386 UTC respektive 17:21:11.807095 UTC.
- Query-scope SHA-256 var identisk i båda: `35078c26165a03b506f0cd0c7c32ed8dca9beab6ddc10413447d01b47a17bbca` (Gräsmyr, 10 km).
- Båda filerna hade `count=1631` och exakt 1 631 poster i `features_by_id`.
- Jämförelse av samtliga ID:n: 0 tillagda och 0 saknade.
- Jämförelse av samtliga `geometry_sha256`: 0 ändrade geometrier.
- Jämförelse av samtliga objektproperties: 0 ändrade attribut.
- Båda observationerna hade `baseline=false`; detta är en jämförelse mellan två icke-baslinjeobservationer.

**Slutsats:** Den genomförda polygonmängden var exakt oförändrad mellan dessa två observationer, både avseende ID, geometrihash och attribut, inom identiskt query scope. Detta kompletterar den tidigare jämförelsen av planerade ID:n. Det är inte en oberoende SHA-256-kontroll av varje historisk gzip-fil och ska inte beskrivas som en fullständig kontroll av samtliga 381 arkivfiler.

**Kvarstående arkivundantag:** De 10 äldre övergångarna från 2026-10-24 har fortsatt saknat tillräcklig scope-proveniens. Analysrapporten anger att scope saknas i båda ändar för de första nio paren och saknas i den äldre änden för det tionde. De förblir exkluderade från evidensjämförelser. De får inte repareras genom antagande, och de får inte skapa borttagnings- eller förändringshändelser. Bevara originalarkiven och utred endast om oberoende historisk scope-evidens kan hittas.

**Drift:** Monitor-run [#45048859162](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45048859162) var push-utlöst (inte cron) och avslutades success. Workflowet `.github/workflows/monitor.yml` har cron `17 5 * * *` (05:17 UTC dagligen). Nästa schemalagda körning ska verifieras separat; en push-utlöst körning bevisar inte schemalagd drift.

Ingen kundavisering, frånvaroklassning eller ändring av källrättigheter följer av denna kontroll.


## Skogskoll Operations Center – daglig projektinventering (2026-11-22)

Den första automatiserade projektledarkontrollen är implementerad i det separata privata repot `dahlinrobert-lgtm/skogskoll-project-manager-history` genom PR [#43](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/43), mergad 2026-11-22 i commit `30052942d061c32fb41615328af60895b0384823`.

- Workflow: `.github/workflows/project-manager-inventory.yml` i det privata historikrepot.
- Måltid: varje dag 07:00 Europe/Stockholm.
- GitHub cron körs i UTC och triggar 05:00 samt 06:00 UTC; `scripts/check_local_schedule.py` tillåter endast den trigger som motsvarar 07 lokal tid. Enhetstester täcker UTC+1, UTC+2 och den trigger som ska hoppas över.
- Inventeringen fortsätter använda `PROJECTS_READ_TOKEN` som read-only mot registrerade källrepon.
- Ett centralt driftärende skapas/uppdateras i det privata historikrepot vid fel. Samma öppna ärende återanvänds; senare komplett lyckad inventering dokumenterar återhämtning och stänger ärendet.
- Körningsunderlag laddas upp som artifact med 14 dagars retention. Ingen partiell körning får behandlas som komplett.
- Workflowets `GITHUB_TOKEN` har `issues: write` i det privata historikrepot; inga skrivbehörigheter till Skog eller andra inventerade källrepon har lagts till.

**Verifiering:** PR-CI för [#43](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/43) passerade både `unit-tests` och `synthetic-append-only`. Merge är verifierad. Den första faktiska schemalagda körningen har ännu inte inträffat/verifierats; kontrollera den 2026-11-23 kl. 07:00 svensk tid innan funktionen klassas som operativt verifierad.

Uppföljande PR [#44](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/44) är också mergad. Den inkluderar misslyckad artifact-uppladdning i samma centrala driftlarm och korrigerar README/driftdokumentationens status efter merge.

Uppföljande PR [#45](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/45) är mergad. Projektregistret valideras nu fail-closed före API-anrop: icke-objekt, saknade fält, dubbletter och okända lifecycle-värden stoppar inventeringen i stället för att kunna ge en falskt komplett täckningsbild. Kandidatprojekt är fortsatt exkluderade. PR-CI:s Python-tester och synthetic-append-only-kontroller passerade.

Uppföljande PR [#46](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/46) är mergad. Artefaktsteget använder nu `if-no-files-found: error`, så en utebliven inventeringsfil registreras som fel och hamnar i samma centrala driftärende i stället för att tyst ignoreras. PR-CI:s `unit-tests` och `synthetic-append-only` passerade.

PR [#47](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/47) är mergad. Dashboardens KPI för olösta avvikelser räknar nu även olösta schemalagda fel. Återhämtade fel visas separat och räknas inte som olösta; pågående schemalagda körningar visas i egen prioriterad sektion. PR-CI passerade.

Nästa steg: verifiera första schemalagda inventering, artifact, tidsgrind och central issue-hantering. Ingen Azure-publicering, historikpersistens eller kundavisering aktiveras av denna implementation.

## Nationell insamling – övergripande projektmål (beslut 2026-11-22)

**Mål:** För varje relevant och registrerad datakälla ska Skog utreda, bygga och verifiera en insamling med nationell geografisk täckning där källan erbjuder sådan täckning och där tekniska villkor och rättigheter medger det. Gräsmyr är en pilotgeografi för kvalitetssäkring, inte slutlig geografisk målbild.

Nationell täckning ska redovisas separat per källa och produkt/lager. Katalogposter, nationella kartvyer, metadata-prober eller lyckade regionala piloter räknas inte som nationell insamling.

Gemensamma acceptanskriterier per källa/lager:
- dokumenterad källomfattning, geografi, objekt-/tidsomfång och eventuella exkluderingar,
- komplett paginering eller annan verifierad uttagsmetod, stabila ID:n och avstämning av antal/täckning,
- manifest med källa, produkt/lager, körnings-ID, tidpunkt, status, scope, antal och SHA-256 där relevant,
- fail-closed publicering: partial/failed körning får inte ersätta senaste kompletta observation eller skapa borttagningsslutsatser,
- återkommande körningar och minst två kompletta, jämförbara observationer innan förändringsklassning,
- separat bedömning av teknisk åtkomst, lagring, bearbetning, kommersiell användning och kundvisning.

**Senaste verifierade framsteg:** Skogsstyrelsens planerade avverkningsanmälningar har en komplett read-only Gräsmyr 10 km-snapshot från 2026-11-22. 165/165 ID:n och geometrier stämdes av, ID-inventeringen var stabil under körningen, complete_scan=true, och snapshoten arkiverades genom PR #524 (mergad). Detta är endast en verifierad pilotobservation – inte nationell täckning och ännu inte två observationer för förändringsanalys.

**Nästa steg:** genomföra en andra komplett jämförbar Gräsmyr-observation; därefter designa nationell insamling med hänsyn till källans maximala uttagsmängd, begränsningar, paginering, belastning och lagringsvolym. Samråd ska verifieras separat för punkt-, linje- och polygonlager. Ingen kundvisning eller avisering följer av teknisk insamling.

## 2026-11-23 – PM-022 adaptersteg och metadatarevision

PR [#531](https://github.com/dahlinrobert-lgtm/Skog/pull/531) är mergad; sex adaptertester samt PR-kontrollerna customer UI tests och source probe passerade. PR [#532](https://github.com/dahlinrobert-lgtm/Skog/pull/532) uppdaterade denna överlämning och är mergad.

Metadatarevision mot `data-platform/config/sources.yml`, `skogskoll/src/supabase-adapters.mjs`, `skogskoll/src/observation-core.mjs` och `skogskoll/src/scan-worker-core.mjs` visar: källregistret har source_id/provider/access_method/connector/cadence/geography och villkorad rights-status, men saknar explicita snapshotfält för product, layer, coverage_key, schema_version och identity_version. Worker-adaptern pekar på Skogsstyrelsens ArcGIS MapServer layer 0, frågar `where=1=1`, hämtar hela attribut/geometri i EPSG:4326 och använder OBJECTID (med GeoJSON id-varianter) som stabil source_id. `normalizeFeature` hash:ar kanoniserade properties + geometry; mottaget datum `Inkomdatum` är inte verifierat publicerings-/ändringsdatum. Detta är kodverifierade observationer, men de versionsstyrda metadataidentiteterna är ännu inte beslutade. `coverage_key` bör inte hårdkodas som "Sweden" enbart från källregistrets geography; den behöver representera den faktiska query/scope-semantiken. Nästa steg: definiera explicit, versionsstyrd metadata för denna exakta workerkonfiguration och tester för att ändringar i endpoint/lager/query/schema/identitet ger ny jämförelsebas.

## Produktutvecklingsprincip – iterativ kundupplevelse

Skogskolls webb/app ska kunna itereras ofta utan att dataplattformen behöver ändras. UI/navigation/designsystem hålls frikopplade från worker, DB och rättighetslogik via stabila kontrakt och klientgräns. Bygg små vertikala, reversibla steg; prototypa med syntetiska data; testa centrala uppgifter, responsivitet och tillgänglighet; använd manuell UX-feedback utöver CI. Webb först och eventuell PWA/native app efter verifierat behov. Detaljerade regler finns i `PROJECT_MANAGER_RULES.md` avsnitt 4B och PM-021 i `PROJECT_BACKLOG.md`.


PR [#531](https://github.com/dahlinrobert-lgtm/Skog/pull/531) är mergad till `main` (merge commit `3db38bd8198eefc8c57d572e39663fe4963c362a`). Den rena adaptern `skogskoll/src/snapshot-envelope-adapter.mjs` mappar befintliga `poll_runs` + `scan_sessions` till change-feed-kontraktets snapshot-envelope. PR #535 är mergad (merge commit `429c15a000bdbe22f80275b2e55c042c82b30400`) och dess customer UI-test passerade. Jämförbarhetsnyckeln omfattar source, product, endpoint, layer, query definition, coverage, schema och identity version. Metadata måste vara explicit; saknad metadata kan inte ge complete. `customer_visibility` defaultar till `not_assessed`. Ingen DB-migration, ingestion, kundfeed eller avisering har aktiverats.
PR [#534](https://github.com/dahlinrobert-lgtm/Skog/pull/534) är mergad (merge commit `65f3ba9deea95e7ae781926ee807a7a605455a8e`) och `Skogskoll customer UI tests` passerade. Designagentens mandat och granskningsprocess är dokumenterade i `docs/SKOGSKOLL_DESIGN_AGENT.md` och `PROJECT_MANAGER_RULES.md` avsnitt 4C. Agenten är fortfarande en dokumenterad arbetsroll, inte en autonom tekniskt driftsatt agent.

**PM-022 status efter PR #538:** metadata är nu kopplad till worker/store-flödet och migration 005 är mergad i `main`. `runScanBatch` hämtar och fail-closed-validerar metadata före scan-start; metadataidentiteten sparas med run-/scan-sessionen och jämförs vid återupptagning. Terminala körningar mappas till det oföränderliga `snapshot_envelopes`-registret. Fullständighetsräkning och `captured_at` kontrolleras även av registrerings-RPC:n. CI för PR #538 passerade: 85/85 UI-tester, read-only probe 300/300 unika ID:n i en begränsad sample och migration 005/SQL-smoketest i disponibel PostgreSQL/PostGIS. Live Supabase-migration och liveanrop av metadatafunktionen mot ArcGIS är inte verifierade.

## 2026-11-23 – Designagent för iterativ produktutveckling

PM-028 har lagts till som styrningsuppgift. En separat designagent föreslås som produktdesigner/UX-granskare för Skogskolls webb och mobil webb, med eventuell PWA/native app först efter verifierat behov. Uppdrag, arbetsmodell, granskningsformat och mandatgränser finns i `PROJECT_MANAGER_RULES.md` avsnitt 4C. Agenten är i detta skede en dokumenterad arbetsroll/instruktionsspecifikation, inte en tekniskt driftsatt autonom agent. Den ska föreslå och granska; mänskliga användartester och projektledarens godkännande kvarstår.

**Nästa steg:** använd designagentens granskningsmodell i PM-021:s första konkreta UI-iteration. Välj en avgränsad vy eller användaruppgift, dokumentera nuläge och testuppgift, ta fram designförslag och granska innan implementation. Håll UI-iterationer separata från PM-022:s snapshotmetadata-/jämförbarhetsarbete.


## 2026-11-23 – Designagent för iterativ produktutveckling

PM-028 har lagts till som styrningsuppgift. En separat designagent föreslås som produktdesigner/UX-granskare för Skogskolls webb och mobil webb, med eventuell PWA/native app först efter verifierat behov. Uppdrag, arbetsmodell, granskningsformat och mandatgränser finns i `PROJECT_MANAGER_RULES.md` avsnitt 4C. Agenten är i detta skede en dokumenterad arbetsroll/instruktionsspecifikation, inte en tekniskt driftsatt autonom agent. Den ska föreslå och granska; mänskliga användartester och projektledarens godkännande kvarstår.

**Nästa steg:** använd designagentens granskningsmodell i PM-021:s första konkreta UI-iteration. Välj en avgränsad vy eller användaruppgift, dokumentera nuläge och testuppgift, ta fram designförslag och granska innan implementation. Håll UI-iterationer separata från PM-022:s snapshotmetadata-/jämförbarhetsarbete.


## 2026-11-22 – Metadataidentitet från Skogskoll ArcGIS-worker

En separat implementation på branchen `feat/skogskoll-arcgis-snapshot-metadata` lägger till `source.getSnapshotMetadata()` i den befintliga ArcGIS-källadaptern.

- Produkt-ID är explicit konfigurerat som `harvest_notifications`; endpoint och MapServer/FeatureServer-lagernummer härleds från den faktiska adapterkonfigurationen.
- Query-definitionen beskriver samma ofiltrerade feature-query som `getPage`: `where=1=1`, alla attribut, geometri, EPSG:4326, GeoJSON och sortering på det metadatahämtade OID-fältet. Paginering (`resultOffset`/`resultRecordCount`) exkluderas eftersom den inte ändrar den logiska mängden.
- `coverage_key=unfiltered-layer-query-v1` betyder endast att queryn saknar attribut-/geografiskt filter. Det är **inte** ett påstående om nationell täckning eller fullständighet.
- `schema_version` är SHA-256 över kanoniserad ArcGIS-fältmetadata, geometri-typ/dimensioner och spatialreferensinformation.
- `identity_version` identifierar det metadatahämtade ArcGIS OID-fältet och konverteringen till strängbaserat GeoJSON feature-id. Den påstår inte att OID är permanent stabilt över tid.
- `customer_visibility` är fortsatt `not_assessed`; `rights_evidence_ref` är null. Metadatafunktionen skapar inga rättigheter.

Metadatafunktionen var först fristående i PR #537 och kopplades därefter in i worker/store-flödet genom PR #538. PR #538:s implementation och migration 005 är mergade. Liveanrop av `getSnapshotMetadata()` mot ArcGIS metadata är fortfarande inte verifierat; metadataidentiteterna testades med mockad metadata. Den begränsade read-only-proben är inte ett fullständighetsbevis.

## 2026-11-23 – PM-022 worker-/snapshotregisterintegration (PR #538 mergad)

PR #537 är mergad i main (merge commit 8ad923d9d4f5b2ef3b4e995c0b9aa15035e8256a). Nästa integrationssteg finns på branchen feat/skogskoll-worker-snapshot-envelope-integration:

- runScanBatch hämtar och validerar metadata från samma ArcGIS-source-adapter innan scan startar. Ofullständig metadata stoppar körningen före databasallokering.
- Metadata skrivs vid scan-start till både poll_runs.diagnostics.snapshot_metadata och scan_sessions.diagnostics.snapshot_metadata. Den följer den ursprungliga scan-sessionen, inte varje workflowförsök.
- Återupptagning jämför kanoniserad metadata mot den sparade identiteten. Ändrad endpoint/query/schema/identitet gör att den gamla sessionen failas och en ny startas; redan committade observationer och historikrader bevaras.
- Migration 005 skapar det worker-only, append-only snapshot_envelopes-registret och RPC:n skogskoll_register_snapshot. Endast terminala scan-/run-poster kan registreras. En komplett envelope kräver fortfarande full count/offset/seen-ID-avstämning.
- Efter lyckad eller fatal avslutad scan läser store tillbaka run/session, mappar via mapWorkerScanToSnapshotEnvelope och registrerar envelope idempotent. En separat pending-RPC hittar terminala sessioner där registrering saknas; nästa workerstart försöker registrera dem igen efter ett transient registreringsfel. Saknad metadata ger inget snapshot; felaktig envelope stoppar registreringen.
- Kundvisning är fortsatt not_assessed, rättighetsevidens null. Ingen alert, kundfeed, schemalagd ingestion eller live-databasändring aktiveras av PR:n.

**Slutlig verifiering på PR-head 72c02f9c9ca293426335ee819f7e4e7584cf4e54:** customer UI-tests passerade 85/85 (run 45079711302); source probe passerade (run 45079711280) med 300/300 unika ID:n, 0 dubbletter och 0 saknade ID:n av källans rapporterade 132 589 (complete_scan=false). Databastesterna passerade (run 45079711277): migration 005 applicerades i disponibel PostgreSQL/PostGIS och både PostGIS-matchning samt transaktionellt ingestion-/snapshot-smoketest passerade med rollback, inklusive kontroll av captured_at mot persistad sluttid. Source-proben anropar inte getSnapshotMetadata mot live metadata; metadatafunktionen testas med mockad ArcGIS-metadata. Ingen live Supabase-anslutning eller produktionsmigration har gjorts. Källstatusrapporten ändras inte eftersom rättighets-/kundvisningsstatus är oförändrad.

**Verifiering på PR-head 7a7531de245d6ec87d4cb7f0e1d0ff530322fc33:** customer UI-tests passerade 85/85 ([run 45079498457](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45079498457)); source probe passerade ([run 45079498474](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45079498474)) med 300/300 unika ID:n, 0 dubbletter och 0 saknade ID:n av källans rapporterade 132 589. Proben var avsiktligt begränsad (complete_scan=false). Databastesterna passerade ([run 45079498504](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45079498504)): migration 005 applicerades i disponibel PostgreSQL/PostGIS och både PostGIS-matchning samt transaktionellt ingestion-/snapshot-smoketest passerade med rollback. Source-proben anropar inte den nya getSnapshotMetadata-funktionen mot live metadata; den funktionen testas med mockad ArcGIS-metadata. Ingen live Supabase-anslutning eller produktionsmigration har gjorts. Källstatusrapporten ändras inte eftersom rättighets-/kundvisningsstatus är oförändrad.

**Historiskt nästa steg – ersatt:** verifieringen i disponibla Supabase-testmiljön har genomförts och utökats med migration 006 och privilegiekontroller enligt avsnittet nedan. Återstående steg är en kontrollerad worker smoke-test i `skogskoll-test`, efter att nödvändiga GitHub Actions-secrets och en manuell, strikt avgränsad körväg har etablerats. Livehämtning av ArcGIS-lagermetadata read-only ska ingå som första kontroll. Produktionsmigration, schemalagd ingestion, full nationell scan, kundfeed och avisering kräver separata beslut och godkännanden.


## 2026-11-23 – Supabase-test behörighetsrevision och migration 006

En separat Supabase-testinstans `skogskoll-test` har skapats av användaren i region West EU (Ireland), Free/Nano. Användaren rapporterar att `schema.sql` och migrationerna 002–005 har körts. Read-only objektinventering i Supabase visade de sju förväntade tabellerna och åtta RPC-funktionerna; RLS var aktiverat på samtliga sju inventerade tabeller. Två SQL-integrationstester kördes manuellt i testprojektet och användaren visade `Success. No rows returned`: PostGIS-matchning och atomisk ingestion/snapshot-smoketest. Dessa resultat är användarrapporterade skärmbildsverifieringar, inte en oberoende anslutning från GitHub Actions till Supabase.

Behörighetsrevisionen visade att `anon`, `authenticated` och `service_role` saknade direkta tabellprivilegier. Kodgranskning av `skogskoll/src/supabase-adapters.mjs` på main visade att workeradaptern gör direkta REST-SELECT på `scan_sessions` och `poll_runs`, medan skrivningar sker via befintliga SECURITY DEFINER-RPC:er. Grundschemat har redan ägarbaserade RLS-policyer för `watch_areas`, `alert_events` och `push_subscriptions`, men saknade explicita GRANTs.

**Föreslagen migration 006** finns på branchen `fix/skogskoll-explicit-api-grants-rls-20261123`:
- `skogskoll/db/migrations/006_explicit_api_grants.sql`: authenticated får CRUD på egna watch areas och push subscriptions via befintliga RLS-policyer, SELECT på egna alert events, och endast service_role får direkt SELECT på poll_runs/scan_sessions. Övriga interna tabeller och snapshot_envelopes förblir utan direkt API-åtkomst. Service_role får inte direkta tabellskrivningar.
- `skogskoll/db/tests/api-grants-rls.sql`: testar privilegier, ägarisolering, push-sekvensbehörighet och workerläsning i transaktion med ROLLBACK.
- `.github/workflows/skogskoll-db-test.yml`: applicerar migration 006 och kör det nya RLS-testet i den befintliga disponibla PostGIS-testdatabasen.

Historisk statusnotering från före PR #540/#541; aktuell status dokumenteras i avsnittet **Supabase-test migration 006 och RPC-behörigheter verifierade** nedan. Migration 006 är nu mergad och användaren har installerat den i `skogskoll-test`. Ingen worker är ännu ansluten och ingen ingestion, kundfeed eller avisering är aktiverad.


### CI-fel och korrigering i PR #540 (2026-11-23)

Första CI-körningen för migration 006 stoppade i steget som skapar den minimala Supabase-kompatibla auth-miljön. Felet låg i test-workflowens SQL-definition av `auth.uid()`: dollarquoting-blocket hade blivit felaktigt återgivet som en ensam `$`, så PostgreSQL kunde inte parsa funktionen. Det var ett fixture-/workflowfel före applicering av schema och migrationer; det gav alltså inget resultat om migration 006 eller RLS-testets funktion.

Workflowet har korrigerats på PR #540:s branch genom att använda en vanlig citerad SQL-funktionskropp i stället för dollarquoting. Ny CI körs på commit `a7a1634081ac9f7048b98f991c9fdb1a20ea5e65`. Vid dokumentationstillfället är databas-, UI- och source-probe-workflows startade men ännu inte färdiga. Föregående source probe och UI-test passerade; databasjobbet på föregående commit misslyckades i auth-fixture-steget.


## 2026-11-23 – Supabase-test migration 006 och RPC-behörigheter verifierade

Användaren har installerat `skogskoll/db/migrations/006_explicit_api_grants.sql` manuellt i den separata Supabase-instansen `skogskoll-test`. Supabase SQL Editor visade `Success. No rows returned`.

Efter installationen visade privilegiekontrollen 27 rader med förväntat resultat:
- `anon`: inga direkta privilegier på de nio kontrollerade tabellerna.
- `authenticated`: CRUD på `watch_areas` och `push_subscriptions`, endast SELECT på `alert_events`; inga direkta privilegier på interna worker-/snapshot-tabeller.
- `service_role`: endast SELECT på `poll_runs` och `scan_sessions`; inga direkta INSERT/UPDATE/DELETE där och ingen direkt åtkomst till observations-/historik-/snapshotregister.

Separat RPC-kontroll visade åtta `skogskoll_*`-funktioner: `anon` och `authenticated` saknar EXECUTE, `service_role` har EXECUTE. Samtliga åtta är `SECURITY DEFINER` med fast `search_path=public, extensions`. Detta omfattar även `skogskoll_match_observations`, som enligt migration 004 är en serversidig matchningsprimitiv och inte direkt kund-RPC.

Tidigare manuellt visade resultat i samma testinstans: objektinventering med sju tabeller/åtta RPC-funktioner och RLS på samtliga sju tabeller; PostGIS watch-area matching-test samt atomiskt ingestion/snapshot smoke-test returnerade `Success. No rows returned`. PR #540 och dess CI-databastest inklusive migration 006 är mergade/godkända enligt GitHub-status.

**Verifierad avgränsning:** detta är schema-, privilegie- och SQL-testverifiering. En riktig workeranslutning, REST-läsning med service_role, RPC-körning från workern, ArcGIS metadata-provider live-anrop och end-to-end test är ännu inte verifierade. Ingen nationell insamling, produktionsanslutning, kundfeed eller kundavisering har startats. Källstatus och kundvisningsrättigheter ändras inte.

**Nästa steg:** förbered en isolerad worker smoke-test mot `skogskoll-test` med en separat testidentitet/secret. Bekräfta först att befintligt workflow och adapter kan återanvändas, att Supabase URL och service_role secret finns som GitHub Actions secrets (hemligheten får aldrig visas eller läggas i Git), och kör därefter en liten, uttryckligen avgränsad testkälla. Kontrollera RPC start/commit/finish samt snapshotregistrering och att inga kundaviseringar skapas. Håll nationell insamling avstängd.


## 2026-11-23 – Skogskoll live metadata och Supabase-anslutningsgrind

PR [#543](https://github.com/dahlinrobert-lgtm/Skog/pull/543) är mergad. Det befintliga sex-timmarsworkflowet `.github/workflows/skogskoll-source-probe.yml` har utökats med `skogskoll/scripts/probe-worker-metadata.mjs`. Skriptet anropar den riktiga `createArcGisSource().getSnapshotMetadata()` mot Skogsstyrelsens ArcGIS layer 0, kontrollerar obligatoriska metadatafält och fail-closed-värden för rättighet/kundvisning och sparar en separat rapport i samma artifact. PR-körning #283 och main-körning #284 passerade. Main-run [#45223866754](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45223866754) verifierar både den befintliga read-only-källproben och live metadata-adaptern. Inga Supabase-hemligheter används, inga databasoperationer utförs och ingen ingestion eller avisering sker.

Körning [#282](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45222656938) passerade samtliga steg. Artifacten visade 132 777 rapporterade objekt och en begränsad sample på 300/300 unika ID:n, 0 dubbletter och 0 saknade ID:n; `complete_scan=false`. Artifacten innehöll samtidigt `max_source_date=2026-11-23T17:41:09Z` trots att `checked_at=2026-11-23T17:00:03Z`. Samma maxdatum återkom i PR-körning #283 och main-körning #284, vars kontroller gjordes omkring 17:05 respektive 17:06 UTC. Detta är en observerad avvikelse i fältet `Inkomdatum`; dess orsak och semantik är inte fastställda. Behandla inte värdet som publiceringsdatum eller verifierad händelsetid. Följ upp med en oberoende observation och källsemantisk kontroll.

**Nästa tekniska steg:** PR [#544](https://github.com/dahlinrobert-lgtm/Skog/pull/544) är mergad och har infört ett separat manuellt workflow `.github/workflows/skogskoll-supabase-connection-check.yml`. Det är avsiktligt separat från det schemalagda publika source-probe-workflowet eftersom det använder `SUPABASE_SERVICE_ROLE_KEY`. Kontrollskriptet gör endast HTTPS REST-SELECT med `select=id&limit=1` mot `scan_sessions` och `poll_runs`; det skriver aldrig ut hemligheter eller svarsdetaljer och gör inga RPC-/databasskrivningar. PR-CI passerade. Nästa steg är att användaren manuellt startar workflowet och verifiera att de användarskapade GitHub Actions-secrets fungerar. Detta verifierar endast autentisering och de två SELECT-behörigheterna – inte skrivande RPC:er eller worker-ingestion.

**Viktiga gränser:** ingen live Supabase-anslutning är ännu bekräftad från GitHub Actions. Ingen scan har startats, ingen observation har skrivits, ingen snapshot-envelope har registrerats och inga kundaviseringar har skickats. Kundvisning för avverkningsanmälningar är fortsatt `not_assessed`/inväntar lagerkontroll enligt källstatusrapporten. Produktionsanslutning och nationell ingestion är fortsatt avstängda.


## 2026-11-23 – Supabase read-only connection check: URL endpoint failure

Manuell workflow-körning [#45225415712](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45225415712) misslyckades i skriptet `skogskoll/scripts/probe-supabase-connection.mjs`. Jobbloggen visar att både `SUPABASE_URL` och `SUPABASE_SERVICE_ROLE_KEY` injicerades i steget (GitHub maskerar värdena), men första REST-anropet gav HTML från Supabase Studio (`<!DOCTYPE html>`) i stället för JSON. Node kastade `SyntaxError: Unexpected token '<'` när svaret parsades. Detta talar starkt för att `SUPABASE_URL` är dashboard-/fel URL eller på annat sätt inte pekar på projektets REST API. Det avslöjar inte vilket konkret värde som finns i secret. Det är inte verifierat att REST-autentisering eller tabellbehörighet fungerade.

PR [#546](https://github.com/dahlinrobert-lgtm/Skog/pull/546) är mergad (merge commit `86a4f222ee14ea67240697b7052f135ddb5e87c1`). Kontrollskriptet validerar nu att `SUPABASE_URL` är en HTTPS-origin med standardhost `*.supabase.co`, utan path/query/fragment, kontrollerar svarens Content-Type före JSON-parsning och visar säkra diagnostikfält utan att skriva ut nyckel, full URL eller response body. PR-CI passerade. En ny körning av Supabase-anslutningsworkflowet har ännu inte utförts efter korrigeringen.

**Användaråtgärd före nästa test:** öppna Supabase-projektet `skogskoll-test`, gå till Project Settings → API och kopiera projektets **Project URL** (API URL), normalt `https://<project-ref>.supabase.co`. Uppdatera GitHub repository secret `SUPABASE_URL` i Skog-repot med exakt den adressen, utan `/dashboard`, extra sökväg eller snedstreck utöver eventuell avslutande slash. Låt `SUPABASE_SERVICE_ROLE_KEY` vara oförändrad om den kommer från samma projekt; verifiera i så fall endast att den är testprojektets service_role-nyckel. Visa eller skicka inte nyckelvärdet i chatt eller logg.

Efter uppdateringen körs det manuella workflowet `.github/workflows/skogskoll-supabase-connection-check.yml` igen. En godkänd körning verifierar endast service-role REST-auth och read-only SELECT på `scan_sessions` och `poll_runs`; den verifierar inte skrivande RPC eller ingestion. Fortsatt inga scans, observation writes, snapshot registrations, produktionsanslutningar, kundfeed eller aviseringar före separat steg och godkännande.

## 2026-11-23 – Supabase read-only connection check: successful authentication

Manuell workflow-körning [#45228866495](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45228866495), run #3, avslutades `completed/success` på main-commit `86a4f222ee14ea67240697b7052f135ddb5e87c1`. Jobbloggen verifierar att `SUPABASE_SERVICE_ROLE_KEY` autentiserar mot projektets REST API och att båda read-only-anropen lyckades:
- `scan_sessions`: HTTP-success, JSON, 0 exempelrader returnerade.
- `poll_runs`: HTTP-success, JSON, 0 exempelrader returnerade.

Detta bekräftar fungerande GitHub Actions → Supabase REST-anslutning och de två SELECT-behörigheterna. Noll returnerade exempelrader är förenligt med att testdatabasen ännu saknar workerposter. Körningen utförde endast GET/SELECT; inga RPC-anrop, tabellskrivningar, scan-sessioner, observationer, snapshot envelopes eller kundaviseringar skapades.

Den tidigare misslyckade körningen #45225415712 och 401-körningen #45228136142 är historiska felsökningsresultat. Den senare returnerade HTTP 401 för `scan_sessions`; efter korrigering av `SUPABASE_SERVICE_ROLE_KEY` passerade körning #3. Hemlighetens värde har inte lästs ut eller loggats.

**Aktuell verifierad status:** Supabase testprojektets read-only REST-anslutning fungerar från GitHub Actions. Skrivande RPC från worker, atomiskt page commit, finish, snapshot-envelope-registrering och end-to-end workerflöde är fortfarande inte verifierade. Ingen riktig ArcGIS-skanning, nationell ingestion, produktionsanslutning, kundfeed eller kundavisering har startats.

**Nästa steg:** granska aktuell workeradapter och samtliga migrationer på main. Utforma därefter ett separat, syntetiskt worker-smoketest med tydligt isolerad testidentitet och verifierad återställnings-/städstrategi. Testet ska omfatta start, sidcommit, finish och snapshotregistrering utan att använda produktionskällans identitet eller skapa kundaviseringar. Kör inte `run-scan` mot den riktiga ArcGIS-källan som anslutningstest.

## 2026-11-23 – Synthetic Supabase worker smoke test prepared

The worker/store review confirmed that the existing `runScanBatch` orchestration and `createSupabaseStore` adapter can be reused for a synthetic integration test. A source-identity mismatch was found: `runScanBatch` loads/allocates a scan using `source.key`, while `normalizeFeature` previously stamped every normalized observation with the fixed production `SOURCE_ID`. The worker now explicitly binds normalized records to the injected source identity; the production ArcGIS source continues to use the existing `SOURCE_ID`.

A dedicated manual workflow and fixture script are prepared on branch `feat/synthetic-supabase-worker-smoke-20261123`. The workflow requires an explicit boolean confirmation before any job runs and uses the existing Supabase secrets. The fixture uses the reserved source key `skogskoll:synthetic:worker-smoke-test`, two fixed synthetic IDs, a `.invalid` metadata endpoint and one bounded page. It does not call ArcGIS, customer matching, alert or notification code.

**Important persistence boundary:** this is a real write test, not a rollback test. The SQL RPCs commit each operation independently through PostgREST. Synthetic poll runs, scan sessions, seen IDs, observations, initial history rows and immutable snapshot envelopes are retained in `skogskoll-test` for audit; the workflow deliberately does not delete them. Repeated runs reuse the same fixture source and IDs, so they do not create a new observation identity set each time. Do not point this workflow at production.

Local automated tests cover the source-identity binding. The live Supabase workflow has not been run. A successful run will verify the existing adapter's start, atomic page commit, finish and snapshot registration against the test project; it will not verify ArcGIS ingestion, production, customer visibility or notifications.

**Next step:** review and merge the PR after CI; then manually dispatch the synthetic workflow with confirmation only after verifying that `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` still point to `skogskoll-test`. Inspect the resulting synthetic records and envelope before any further worker expansion.

## 2026-11-23 – Synthetic worker smoke test merged; CI green

PR [#551](https://github.com/dahlinrobert-lgtm/Skog/pull/551) was merged to main in commit `15380835ff6488393738c0552ba8ef5ddc1d4d5f`. The `Skogskoll customer UI tests` run [#45254523110](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45254523110) and `Skogskoll source probe` run [#45254522745](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45254522745) both completed successfully on the PR head.

The merged implementation includes the source-identity binding fix, regression test, a manually dispatched synthetic worker workflow and a fixture script restricted to the verified test-project API host `jdfekakdxmltaccslrkp.supabase.co`. The workflow requires `confirm_synthetic_write=true`; the script independently requires `SKOGSKOLL_ENABLE_SYNTHETIC_SMOKE_TEST=YES` and the exact test API hostname.

**Live status:** the synthetic Supabase worker workflow has not yet been dispatched. Thus worker RPC start, atomic page commit, finish and snapshot-envelope registration through the real Supabase adapter remain unverified. No synthetic database writes have been made by this workflow. No production ArcGIS scan or customer notification has been run.

**Next step:** obtain explicit confirmation before dispatching the workflow because it creates durable test records (poll run, scan session, seen IDs, observations/history and snapshot envelope) in `skogskoll-test`. These records are intentionally retained, not rolled back or deleted. After a confirmed run, inspect the records and envelope before planning any broader integration test.

## 2026-11-23 – Syntetiskt worker-smoketest genomfört med framgång

GitHub Actions-körning [#45259733480](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45259733480) kördes manuellt (`workflow_dispatch`) på `main`, commit `a29bf69e6b2ede4997ab233abcea45ea1a2132b7`. Workflow och enda jobbet `synthetic-worker-smoke` avslutades `completed/success`; steget `Run isolated synthetic worker against Supabase test project` passerade.

Jobbloggen visar att `run-synthetic-worker-smoke-test.mjs` kördes med testprojektets GitHub Actions-secrets (värden maskerade) och gav `status=complete`, `fetchedCount=2`, `pagesFetched=1`, `pagesExpected=1`, källa `skogskoll:synthetic:worker-smoke-test`, fixture `skogskoll-worker-smoke-v1`, `alertsEnabled=false` och `productionSourceUsed=false`. Worker-resultatet innehåller scan ID `1a53c3b2-fad4-47d1-afb4-9340dc50f15c`.

**Verifierat:** den verkliga worker-orchestreringen och Supabase-adaptern genomförde en komplett syntetisk körning med två fixtureposter på en sida. Genom kodgranskning av den version som kördes framgår att adaptern använder RPC:erna `skogskoll_register_snapshot`, `skogskoll_start_scan`, `skogskoll_commit_page` och `skogskoll_finish_scan`; ett komplett resultat kräver att workerflödet når finish efter full täckning. Detta verifierar inte ArcGIS, produktionskälla, kundmatchning, kundvisning eller aviseringar.

**Databasinsynens begränsning:** workflowlogg/resultat bekräftar worker-resultatet men innehåller inte en separat efterföljande SQL-inventering av alla lagrade rader. Skrivflödet ska betraktas som genomfört via adaptern, medan oberoende kontroll av varje tabellrad och snapshot-envelope i Supabase Dashboard/SQL ännu återstår.

Testet behåller de syntetiska poll runs, scan session, seen IDs, observations, historikrader och snapshot envelope i `skogskoll-test`; inget städades bort. Ingen produktionskälla användes och inga kundaviseringar aktiverades.

**Nästa steg:** gör en read-only efterkontroll i `skogskoll-test` av scan ID ovan och fixture-ID:na `worker-smoke-feature-001`/`worker-smoke-feature-002`, inklusive snapshot-envelope-status och antal observationer/historikrader. Därefter bedöms eventuella idempotens-/omkörningsfrågor innan en avgränsad källspecifik worker-probe övervägs. Fortsätt hålla produktionsingestion och alerts avstängda.


## 2026-11-23 – Read-only SQL audit prepared for synthetic worker run

Review of migration 006 confirms the worker service role has direct REST SELECT grants only on `scan_sessions` and `poll_runs`. It intentionally has no direct SELECT on `source_observations`, `source_observation_history`, `scan_seen_ids` or `snapshot_envelopes`. Therefore the GitHub Actions log cannot independently enumerate those protected rows through the current adapter permissions.

Added `skogskoll/db/diagnostics/verify-synthetic-worker-smoke.sql`, a SELECT-only script for Supabase SQL Editor. It inspects the known scan ID `1a53c3b2-fad4-47d1-afb4-9340dc50f15c`, the two fixed fixture IDs, linked poll run, seen-ID ledger, observation history, snapshot envelope and count reconciliation. It performs no writes or deletes. Run it only in the dedicated `skogskoll-test` project.

**Next step:** execute the diagnostic in Supabase SQL Editor and review all six result sets. Do not broaden service-role table grants merely for diagnostics; retain the current least-privilege boundary. Use observed results to decide whether a narrowly scoped, service-role-only audit RPC is warranted.


## 2026-11-23 – Oberoende SQL-antal verifierade för syntetiskt worker-test

Användaren körde den aggregerade SELECT-kontrollen i Supabase SQL Editor mot det dedikerade `skogskoll-test`-projektet. Resultatet var:

- `seen_id_count=2`
- `observation_count=2`
- `history_row_count=2`
- `snapshot_envelope_count=1`

Antalen stämmer med den syntetiska körningens två fixture-ID:n och en förväntad snapshot-envelope. Detta är oberoende verifiering av radantal i databasen, utöver workerloggens `status=complete`.

**Begränsning:** användaren har endast delat det aggregerade resultatradsetet. Scan-/poll-status, observationsfält och aktiv-status, historikens `event_type` samt envelope-status och `customer_visibility` är därför ännu inte verifierade genom delade SQL-resultat. Antalen ensamma bevisar inte dessa fält.

**Nästa steg:** kör och dela resultatraderna från diagnostikens frågor 1, 2, 4 och 5 för scan/poll run, observationer, historik och snapshot-envelope. Gör ingen andra workeromkörning förrän den första körningens innehåll och envelope har granskats. Behåll testdata; ändra inte grants och håll produktion/aviseringar avstängda.


## 2026-11-23 – Detaljerad read-only SQL-granskning av första syntetiska worker-körningen

Användaren delade SQL-resultat från Supabase SQL Editor i det dedikerade `skogskoll-test`-projektet för scan `1a53c3b2-fad4-47d1-afb4-9340dc50f15c`.

Verifierade uppgifter:
- Scan-sessionen har `status=complete`, `source_count=2`, `next_offset=2` och `fetched_count=2`.
- Seen-ID-ledgern innehåller exakt `worker-smoke-feature-001` (offset 0) och `worker-smoke-feature-002` (offset 1).
- Observationstabellen innehåller exakt två visade fixture-observationer. Båda har `active=true`, samma första/senaste observationstid vid baslinjen, och fixture-attribut med sekvens 1 respektive 2.
- Historiktabellen innehåller två rader, en per fixture-ID, båda med `event_type=baseline`. De är kopplade till poll-run `b7ce384f-d9fb-4240-ab6e-2bdee386a287`.
- Snapshot-envelope har `status=complete`, `customer_visibility=not_assessed`, `rights_evidence_ref=null`, produkten `synthetic_worker_smoke` och scope `synthetic-fixture-only-v1`.
- Aggregerad avstämning: seen IDs 2, observationer 2, historikrader 2, snapshot envelopes 1.

**Kvarstående kontroll:** SQL-resultatbilden för fråga 1 visar scan-kolumnerna men inte den horisontellt dolda delen med poll-run-status, fetched_count och finish-tid. Poll-run-ID kan bekräftas från historikraderna, men poll-run-status ska inte markeras verifierad förrän den synliga resultatraden har delats.

**Bedömning:** första körningens scan, baslinjehistorik, observationer och envelope är verifierade. Baslinjen har inte genererat inserted/changed-händelser eller kundaviseringar. Kör inte om worker ännu; kontrollera först poll-run-statusen och därefter genomförs en avgränsad idempotensomkörning i testprojektet. Behåll befintliga testposter och ändra inte grants. Produktion och kundaviseringar förblir avstängda.


## 2026-11-23 – Poll-run-status verifierad för första syntetiska worker-körningen

Användaren delade den fullständigt horisontellt synliga SQL-resultatraden för scan `1a53c3b2-fad4-47d1-afb4-9340dc50f15c` och poll run `b7ce384f-d9fb-4240-ab6e-2bdee386a287`.

Verifierade poll-run-fält:
- `status=success`
- `fetched_count=2`
- `inserted_count=2`
- `updated_count=0`
- `finished_at=2026-11-23 20:28:53.695946+00`

Tillsammans med tidigare delade SQL-resultat är första körningens scan och poll run terminalt lyckade, båda fixture-objekten är aktiva, båda historikraderna är `baseline`, och snapshot-envelope är `complete` med `customer_visibility=not_assessed` och `rights_evidence_ref=null`.

**Nästa steg – idempotenskontroll:** kör samma isolerade manuella workflow en gång till, endast med den explicita `confirm_synthetic_write=true`-bekräftelsen och fortsatt låst till `skogskoll-test`. Workflowet använder samma två fasta fixture-ID:n och samma innehåll. Förväntat resultat är en ny komplett scan/poll-run och ett nytt immutable snapshot-envelope, medan befintliga observationer förblir två och historikraderna förblir två eftersom båda posterna ska klassas `unchanged`. Detta är ett förväntat testresultat, inte ännu verifierat. Efter körningen ska SQL-kontrollen utökas/köras mot det nya scan-ID:t och de totala observation-/historikantalen jämföras. Testposter behålls; inga grants ändras. Produktion, kundmatchning och aviseringar förblir avstängda.


## 2026-11-23 – Idempotency audit prepared for second synthetic worker run

Reviewed the existing main-branch workflow, fixture script, worker core and SQL persistence logic. The existing manually dispatched workflow is reusable without code or workflow changes: it uses the same two stable fixture IDs, the same synthetic source identity, the same content and the host guard for the dedicated skogskoll-test project. The worker's observation classifier maps equal content hashes to unchanged; migration 003 does not append history for unchanged records and increments poll-run inserted/updated counts only for inserted/changed records.

Added skogskoll/db/diagnostics/verify-synthetic-worker-idempotency.sql, a SELECT-only audit for the second run. It identifies the latest scan dynamically and checks the linked poll run, latest seen-ID count, current observation count, retained history rows, current observation fields and both snapshot envelopes. Expected results are documented in the SQL file; they are not yet observed.

**Execution status:** no workflow dispatch has been made in this step. The available GitHub integration exposes read operations but no workflow_dispatch action. The second run creates durable records and must be manually dispatched in GitHub Actions with confirm_synthetic_write=true, after confirming the workflow is on main and the repository secrets still target only skogskoll-test. Do not use production credentials. After a successful run, execute the new SELECT-only audit in the test project's Supabase SQL Editor and review all five result sets.

No workflow, worker code, database schema, grants, source registry or customer-facing behavior was changed. No production ingestion, customer matching or alerts were enabled.


## 2026-11-23 – Third synthetic worker run confirms idempotency

The user supplied Supabase SQL Editor result screenshots for the latest synthetic run. The latest scan is `879f0071-68e4-462a-a0ff-216c10a8c6cf`, source `skogskoll:synthetic:worker-smoke-test`, with `source_count=2`, `page_size=2`, `next_offset=2`, `fetched_count=2`, `status=complete`, and a populated `snapshot_registered_at`. Its poll run is `6613004d-8f05-4de1-8c39-964014148eed`, `status=success`, `fetched_count=2`, `inserted_count=0`, `updated_count=0`.

The independent aggregate query reports 2 seen IDs in the latest scan, 2 current observations, 2 total observation-history rows, and 3 snapshot envelopes across the three completed synthetic runs. Both current fixture observations remain active; their original `first_seen_at` values remain unchanged, while `last_seen_at` and `last_run_id` reflect the latest successful poll. The only two history rows remain `baseline` events linked to the first poll run; the repeated unchanged polls did not append history. All three snapshot envelopes are `complete`, with coverage key `synthetic-fixture-only-v1`, customer visibility `not_assessed`, and no rights evidence reference.

**Assessment:** idempotency is verified for repeated identical fixture content: no duplicate current observations and no extra history rows were created. The new scan, poll run and snapshot envelope were persisted successfully. This is a test-project synthetic verification only; it does not establish production-source readiness, commercial rights, customer visibility, alert delivery, or production operational readiness. Keep test records and existing grants; no cleanup or privilege changes.


## 2026-11-23 – Controlled synthetic worker change-event test verified

PR [#560](https://github.com/dahlinrobert-lgtm/Skog/pull/560) added the explicit `change_feature_001` fixture variant to the existing synthetic worker workflow. The workflow was manually dispatched as [run #4](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45270531634) on `main`, commit `30a96696ae97179d3e60e33a2a1479020c128bee`, and completed successfully. The log confirms fixture variant `change_feature_001`, scan ID `9fddb92c-8ea0-444c-b4aa-9b8cff79d019`, `status=complete`, `fetchedCount=2`, one page, expected changed ID `worker-smoke-feature-001`, `alertsEnabled=false`, and `productionSourceUsed=false`.

The user's read-only Supabase SQL results from the dedicated `skogskoll-test` project independently verify the database effects:

- Latest scan `9fddb92c-8ea0-444c-b4aa-9b8cff79d019`: complete, source_count=2, page_size=2, next_offset=2, fetched_count=2, and snapshot registered.
- Linked poll run `7f5345d3-8f2c-46a1-a935-db87f1f92cb5`: success, fetched_count=2, inserted_count=0, updated_count=1.
- Latest scan seen-ID count=2; current observations=2; total history rows=3; snapshot envelopes=4.
- Current observation `worker-smoke-feature-001` has `sequence=101`; `worker-smoke-feature-002` remains at `sequence=2`. Both remain active.
- History contains the two original `baseline` rows from the initial poll run and exactly one new `changed` row for feature 001, linked to the latest poll run. No baseline history was overwritten.
- All four snapshot envelopes are `complete`; `customer_visibility=not_assessed` and `rights_evidence_ref=null`.

**Assessment:** the controlled single-observation change path is verified end-to-end in the isolated test project: the worker updated one existing observation, appended exactly one `changed` history row, retained the other observation and both original baseline rows, and registered the fourth complete snapshot envelope. Test records are durable and retained; no cleanup was run.

This does not establish production ingestion readiness, source rights, customer visibility, customer matching or alert delivery. No production source or customer notification was used. Keep the test project and its evidence isolated; do not change grants or delete test history.

**Next concrete step:** continue with the existing worker/adapter architecture and plan the next narrowly scoped validation only after checking current source readiness and rights. Do not enable production ingestion or customer alerts based solely on this synthetic test.


## 2026-11-23 – National ÄFO snapshot pipeline correction in alg-grasmyr

The separate repository `dahlinrobert-lgtm/alg-grasmyr` already owns the national Länsstyrelsernas Älgdata collection. Do not create a parallel collector in Skog. The national collector correction was merged in [alg-grasmyr PR #81](https://github.com/dahlinrobert-lgtm/alg-grasmyr/pull/81): dated per-ÄFO snapshots remain immutable, while the derived national dashboard may advance only to a newer complete batch. Identical same-day retries are idempotent; changed same-day snapshots/dashboard content and attempts to move the dashboard backwards are rejected.

Verification on PR head `77f23545c38ea0a684f9086047c98d40621955f9`:
- National ÄFO test workflow passed, including four new dashboard regression tests.
- Full stored-snapshot validator passed.
- Post-merge validation workflow passed on alg-grasmyr main commit `6ee9d450e54677b801fa673a1a16ade7191565a2`.

The prior national scheduled run #12 (2026-11-23) failed because the old implementation refused to update the 2026-11-21 dashboard. Its uploaded artifact was retained; no snapshot batch was committed. The correction is merged, but a fresh complete 129/129 national run has not yet been performed after the fix.

**Next concrete step:** manually dispatch [Daily national ÄFO avskjutning snapshots](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/workflows/daily-national-afo-avskjutning.yml) on `main`. Verify 129/129 active AFOs, exact match against current JaktAdm boundary IDs, raw ÄJO row preservation and aggregate sums from `ShotTotal`/`AssignedTotal`, then verify that the dashboard date advances without changing any earlier dated snapshots. Only after that run succeeds should Skog's source status and integration planning be revisited. No Skog worker integration, customer display, or alerts have been enabled.


## 2026-11-23 – Nationell ÄFO-avskjutning: fullständig snapshot verifierad

GitHub Actions [körning #13](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45273303393) avslutades `completed/success` på `main`, commit `3cba0cd17e17ae839f11a66b185cbc6cc47a6ac3`. Körningen passerade parser-/arkivregressionstester, full nationell insamling, artifact-uppladdning och commit av snapshots. Workflowet skapade därefter commit `8d78cdfd7eed017040b7ab74ce96b1c724f84d73` på alg-grasmyr `main`.

Oberoende granskning av artifact `national-afo-snapshot-batch` (ID `14867345764`, SHA-256 `0d0f812962051acb1893c4c0410aee690acf2bce0d5c031ca1d9c43e16046c3d`) verifierade:

- Dashboarddatum `2026-11-23`, säsong `2026/2027`, `afo_count=129` och `areas_with_data=129`.
- 129 daterade snapshotfiler för 2026-11-23 och 129 unika `afo_id`; ID-mängden motsvarar dashboardens 129 områden.
- Samtliga 129 snapshots innehåller bevarade `raw_area_rows`; totalt 3 237 råa ÄJO-rader.
- Summering direkt från de råa raderna ger `ShotTotal=57 687` och `AssignedTotal=79 704`. Dessa värden matchar exakt dashboardens summerade `fallda_totalt` respektive `avskjutningsmal_totalt`.
- Git-trädet efter körningen innehåller 129 filer daterade 2026-11-21 och 129 daterade 2026-11-23. De tidigare daterade filerna finns kvar separat; dashboarden har avancerat till 2026-11-23.
- Insamlaren kontrollerar att JaktAdm:s aktuella boundary `afo_id`-mängd exakt matchar den nationella säsongskatalogen före arkivering. Den lyckade fullkörningen innebär att denna kontroll passerade. Råa ÄJO-rader och HTML `Summa`-rad bevaras i varje snapshot.

Detta verifierar en fullständig nationell observation och den korrigerade summerings-/dashboardvägen. Värdena är kumulativa rapporterade säsongsvärden, inte individuella älghändelser eller exakta fälldatum. Teknisk åtkomst och insamlingsfullständighet ger inte automatiskt rätt till kommersiell användning, historisk lagring, bearbetning, kundvisning eller vidare distribution. Ingen Skogskoll-worker, kundfeed eller avisering har aktiverats.

**Nästa steg:** slutför rad-för-rad-jämförelse av samtliga råa ÄJO-rader mellan 2026-11-21 och 2026-11-23 med stabila registreringsnummer och separera ändrade värden från statusändringar. Behåll alla daterade snapshots. Genomför separat rights assessment för teknisk åtkomst, historisk lagring, bearbetning, kommersiell användning och kundvisning innan integration i Skogskoll övervägs.




## 2026-11-23 – Första nationella differensgranskningen 21–23 november

Dashboarderna i alg-grasmyr har jämförts direkt från Git-historiken: 2026-11-21 (`c16495a638a12f3e55a8e41ba94e01a3d7f9c6f2`) mot 2026-11-23 (`8d78cdfd7eed017040b7ab74ce96b1c724f84d73`). Båda avser säsong 2026/2027 och 129 unika ÄFO-ID:n. På dashboardnivå verifierades:

- Rapporterat kumulativt `fallda_totalt`: 56 715 → 57 687, differens +972.
- `avskjutningsmal_totalt`: 79 704 → 79 704, differens 0.
- 109 av 129 ÄFO har högre rapporterat fälltal; 20 är oförändrade; inget ÄFO har lägre aggregat.
- Största observerade ÄFO-differenser: 25-003 +76, 25-006 +55, 25-004 +46, 25-005 +45 och 07-001 +23.
- Antalet råa ÄJO-rader per ÄFO är oförändrat i dashboardmetadata för samtliga 129 områden. `FinishedReporting`-antalet ändras däremot i 10 områden; i 14-005 minskar det från 5 till 4. Detta visar att rapporteringsstatus inte ska behandlas som monotont eller som en händelsehistorik.

Detta avsnitt dokumenterar dashboard-/ÄFO-aggregatjämförelsen. Den fullständiga råa ÄJO-rad-för-rad-jämförelsen slutfördes senare och verifierades i alg-grasmyr PR #83 och Actions run 45283539790; resultat och stabil identitet dokumenteras i avsnittet **2026-11-23 – National ÄJO row-level comparison verified** längre ned i denna överlämning. De kumulativa differenserna ska inte tolkas som exakta fälldatum eller dagliga händelser. Bevara snapshots och skapa ingen automatisk borttagningshändelse vid frånvaro.
## 2026-11-23 – Azure prenumeration, budget och dataskydd verifierade

Användarens Azure Portal-skärmbilder verifierar att prenumerationen `Azure subscription 1` (ID `e758647f-da18-4063-adfd-f1ce79d5d2af`) visas som aktiv efter uppgradering till Pay-As-You-Go. En månadsbudget `Skogskoll-budget` på 200 SEK har skapats med faktiska kostnadsaviseringar vid 50/75/90 procent (100/150/180 SEK). Budgeten är en notifiering, inte ett hårt kostnadstak.

Storage Account `stskogkolldata` är `StorageV2`, standardprestanda, Sweden Central (`swedencentral`) och LRS. Dataskyddsbilden visar blobversionering aktiverad med alla versioner behållna, soft delete för blobbar och behållare aktiverat i 14 dagar, permanent borttagning inaktiverad samt Azure Backup, point-in-time restore, Change Feed och immutability inaktiverade. TLS-miniminivå är 1.2. Offentlig blobåtkomst är inaktiverad på kontonivå; offentlig nätverksåtkomst är däremot aktiverad för alla nätverk. Den senare inställningen ska inte förväxlas med anonym blobåtkomst.

Azure Monitor visade cirka 754,7 MiB och 770 MiB Used capacity vid två ögonblicksbilder samt 310 summerade transaktioner för den valda senaste 24-timmarsperioden. Detta är inte en tillväxtserie eller fakturaverifiering. En specifik blob `project-manager/snapshots/45002255351/dashboard-data.json` hade inga tidigare versioner listade vid kontrollen; detta är förenligt med att versionering är aktiverad men att filen saknar tidigare versioner.

Detaljer, begränsningar och kvarstående kontroller finns i [Azure – konto- och kostnadsdrift](azure-storage-operations.md). Även [STORAGE_INVENTORY.md](STORAGE_INVENTORY.md) och [viltdata-azure-storage.md](viltdata-azure-storage.md) har uppdaterats med kontots aktuella konfiguration. Ingen kod, workflow, behörighet, källdata eller kundavisering ändrades i detta dokumentationsarbete.

**Nästa konkreta steg:** följ faktisk kostnad och budgetaviseringar efter normal drift, och planera ett separat restore-test. Behåll nuvarande dataskydd; inför ingen automatisk gallring av historiska snapshots utan konsekvensanalys.


## 2026-11-23 – Plan för publik lansering av Skogsspan.se dokumenterad

GitHub-issue [#566 – Planera och förbered lansering av Skogsspan.se](https://github.com/dahlinrobert-lgtm/Skog/issues/566) är den samlade uppgiften och auktoritativa checklistan för lanseringsförberedelserna. Den omfattar:

- inventering av befintlig webbplats, Skogskoll-prototyp, GitHub Pages och återanvändbara komponenter;
- separat publik marknadswebbplats och inloggad kundapplikation;
- branch/PR-baserad utveckling med förhandsvisning så design och UX kan itereras utan att påverka produktion;
- GitHub Pages, domänkoppling för `skogsspan.se`, DNS och HTTPS samt eventuell framtida `app.skogsspan.se`;
- säkerhets- och sekretessinventering av relevanta GitHub-repon före eventuella visibility-beslut;
- robots-/indexeringsstrategi, där `robots.txt` och `noindex` inte behandlas som åtkomstskydd;
- verifiering av att publikt innehåll och kundvisning endast omfattar funktioner och datakällor med tillräckligt underlag och rättigheter.

**Beslutade arbetsprinciper:** använd GitHub för kod och historik, PR-baserad granskning och separerad förhandsvisning/produktion. Gör inga repos privata, ändra inte DNS/domän/Pages och publicera inte robots- eller åtkomständringar utan separat konsekvensbedömning och uttryckligt godkännande. Bevara nuvarande fungerande publicering tills ersättande lösning är verifierad.

**Status vid dokumentation:** issue #566 är skapad. Ingen repo-visibility, domän, DNS, Pages-konfiguration, robots.txt eller kundapplikationsåtkomst har ändrats. Project Manager-dashboarden använder en separat Azure Blob-snapshot och en fast snapshotreferens i klientkonfigurationen. Snapshotuppdatering och dashboardens livevisning är därför separata steg; uppdatera inte den fasta klientreferensen/deploya inte en ny dashboardversion förrän den dokumenterade CORS-, Entra-inloggnings- och behörighetskontrollen är genomförd. Den privata snapshotpubliceringsmiljön kunde inte läsas via aktuell GitHub-integration vid denna kontroll; dess workflowstatus och publicering är därför inte verifierade.

**Nästa konkreta steg:** genomför säkerhets-/sekretessinventering av befintliga publika repos och granska beroenden för Pages innan beslut om målstruktur eller synlighet. Separat: återställ åtkomst till det privata project-manager-history-repot, verifiera dess snapshotworkflow och CORS-/autentiseringsgrindar och uppdatera därefter dashboardens snapshot på ett append-only sätt utan att skriva över äldre snapshots.


## 2026-11-23 – National ÄJO row-level comparison verified

The national collector and immutable snapshot archive remain owned by `dahlinrobert-lgtm/alg-grasmyr`; Skog does not create a parallel collector. [alg-grasmyr PR #83](https://github.com/dahlinrobert-lgtm/alg-grasmyr/pull/83) was merged on 2026-11-23 (merge commit `bec3edb2f2cee4c1122b6b38e105ae842c26bd0a`).

The read-only row-level audit compared all 129 ÄFO snapshot pairs for 2026-11-21 and 2026-11-23 using the portal `drillDownToAjoReport` ID scoped by `afo_id`. [GitHub Actions run 45283539790](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45283539790) passed and uploaded artifact 14870128151.

Verified: 3,237 raw ÄJO rows on each date; 2,841 unchanged; 396 rows with one or more changed attributes; zero added and zero missing portal IDs. `ShotTotal` changed on 378 rows. `FinishedReporting` changed on 42 rows (41 `Nej`→`Ja`, one `Ja`→`Nej`). Dashboard cumulative `ShotTotal` rose by 972 (56,715→57,687), while `AssignedTotal` remained 79,704. These are cumulative season-report differences, not individual kill events or exact dates. The report confirmed that source snapshots were not modified.

The audit implementation, tests and run instructions are documented in [alg-grasmyr NATIONAL_AJO_ROW_DIFF.md](https://github.com/dahlinrobert-lgtm/alg-grasmyr/blob/main/docs/NATIONAL_AJO_ROW_DIFF.md). Missing rows are classified as unconfirmed absences, never as deletions. No Skog worker, customer feed or alerts are enabled.

**Next concrete step:** continue scheduled/controlled national snapshots and compare later dates using the same immutable row-level audit. Separately review the existing rights evidence for exact commercial/customer-display scope before any product integration. Do not interpret cumulative differences as event-level harvests.


## 2026-11-24 – Project Manager: drift-, täcknings- och källriskvy under utveckling

En separat staging-implementation finns i det privata repot [skogskoll-project-manager-history PR #52](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/52). Den utökar Project Manager-källvyn med explicit driftklassificering, geografisk täckning och risk-/kontinuitetsprofil per source_id.

Viktiga skydd:
- Fullständigt verifierad drift kräver exakt koppling till workflow, explicit produktionsstatus och scope samt minst två lyckade, kompletta och jämförbara körningar.
- Saknade uppgifter visas som okända/ej bedömda; inga servergränser eller täckningsnivåer får antas.
- Riskprofilen ska omfatta anropsintervall, samtidighet, sidstorlek, timeout, retry/backoff, kända servergränser, felpolicy och återhämtning.
- Vid driftstörning bevaras senaste kompletta snapshot. Partial/failed får inte skapa falska borttagningar; återhämtning ska vara kontrollerad och idempotent.

PR #52 ligger i privat staging-repo. Profilregistret är initialt tomt eftersom källspecifika servergränser, anropsbudgetar och återhämtningsbeteenden ännu inte har verifierats. CI för Python-enhetstester, JavaScript-syntax och syntetiska append-only-tester passerade på kodcommit 2f7464dcf3149b3d9ec82ba99d8fd982ea185109; en senare ändring uppdaterade endast profilmodellens dokumentation. PR är öppen och inte mergad.

Ingen Azure-publicering, latest pointer, GitHub Pages-deploy, auth/CORS-ändring eller ändring av befintlig produktionsdashboard har gjorts. Befintlig snapshot och manuell publiceringsgrind är oförändrade.

**Nästa steg:** granska och mergea staging-PR efter kodgranskning. Därefter koppla faktiska källor till exakta workflows och dokumentera risk-/kontinuitetsprofiler från API-dokumentation, leverantörsvillkor, befintlig kod och kontrollerad driftsevidens. Först därefter kan en ny komplett inventering och separat manuellt godkänd Azure-publicering ge dashboarden nya uppgifter.
## 2026-11-24 – Mobilappspublicering registrerad i projektbackloggen

GitHub issue [#573](https://github.com/dahlinrobert-lgtm/Skog/issues/573) och backloggpost PM-024 registrerar kommande arbete för att förbereda Skogskoll för Google Play och Apple App Store. Detta är planering/kravinsamling, inte ett beslut att börja bygga eller publicera.

Omfattningen inkluderar beslut om juridisk utgivare och kontoägare, read-only inventering av befintlig frontend, jämförelse av PWA/Capacitor/React Native, butikarnas integritets-, behörighets-, kontoraderings- och granskningskrav, testning samt drift och releaseförvaltning. Tidigare angivna butikskontoavgifter (Google Play 25 USD engångsvis, Apple Developer Program 99 USD/år) är endast preliminära budgetvärden och måste verifieras mot officiella aktuella villkor före registrering eller betalning.

Nästa konkreta steg är att inventera aktuell Skogskoll-frontend, mobilanpassning, auth, kartor och notifieringsflöden. Ingen utvecklarkontoregistrering, ny produktionsaktivering eller kundavisering ska ske som del av detta planeringssteg. Se [PROJECT_BACKLOG.md, PM-024](PROJECT_BACKLOG.md).


## 2026-11-24 – PM-027 arkitekturpassning och read-model-inventering

PM-027 är P0. Inventering mot aktuell Skog `main` och privata `skogskoll-project-manager-history` verifierar att det redan finns en repo-/workfloworienterad projektinventering, ett källregister med operativa fält, en daglig schemalagd inventory-workflow i det privata repot samt en separat manuell Azure-publisher med run-scopade snapshots och manifest. Den första Azure-publiceringen (`44958916377`, publisher run `44959260856`) verifierades byte-för-byte i samma workflow enligt det privata repots driftdokumentation.

Den befintliga projektledarinventeringen visar de senaste 20 workflow-körningarna per repo och läser källregistrets kadens, geografi och operations-fält. Den visar däremot inte ett verifierat senaste komplett snapshot per `source_id`/produkt/lager. Ingen generell source-to-workflow/manifest/snapshot-koppling har ännu verifierats. Azure-publishern är dokumenterad som manuell och run-scopad; den första publiceringen bevisar inte en återkommande daglig publicering. Skogs Project Manager-klient använder en fast Blob-referens och har schema-/freshness-/partial-kontroller, men live Azure-innehåll och webbläsarens Entra/CORS-flöde kunde inte verifieras genom GitHub-integrationen.

**Arkitekturval:** utöka befintlig privat collector/read-model och befintlig Azure snapshot/publisher efter kontraktsdesign. Återanvänd `data-platform/config/sources.yml` som auktoritativ källa till source/product/layer-identitet och källägda manifest/snapshots som evidens. Ingen parallell collector eller historikmodell.

**Nästa konkreta steg:** inventera exakta manifest-/snapshotindexformat för prioriterade befintliga källflöden; definiera versionsstyrd source-to-workflow-mappning och minsta normaliserade rapportkontrakt. Därefter implementera en read-only adapter med syntetiska tester för success, partial, failed, stale och unknown. Ingen ändring av schema, publicering, behörighet eller kundflöde är godkänd i detta inventeringssteg.


## 2026-11-24 – PM-027 källmanifest- och snapshotformat inventerade

Fortsatt read-only-granskning av Skog `main` identifierade konkreta format för:
- Skogsstyrelsens avverkningsanmälningar: `latest.json` manifest med scope, före/efter-ID-inventering, count, complete_scan, SHA-256 och gzip-GeoJSON-referens; workflow manuell och Gräsmyr 10 km pilot.
- Samråd: gzipade tidsstämplade snapshots samt `samrad_latest.json`; payload har source_id, scope_hash, per-lager status/paging/counts. Daglig workflow. Inget separat snapshotfil-SHA-fält i det granskade payloadkontraktet.
- Torvkarta/SIS: veckovis `geodata_timeline` JSON-snapshot, NPZ-sampel, metadata-/pixelhash och append-only events. Per-tjänst status; samplebaserat change detection, inte nationell full rasterdump.
- Länsstyrelsens diarier: append-only JSONL manifest per försök och immutable JSONL snapshot per county/phrase/interval. Fullständighet kräver paging och källtotal/unik-ID-reconciliation; delkörning är inte nationell fullständighet.
- Trafikverket Miljöwebb: datumpartitionerat manifest med per-lager antal, geometri/ID-fält, filreferens, storlek och SHA-256.
- Event bundle schema är en separat semantisk händelse-/evidensmodell, inte ersättning för råsnapshotmanifest.

**Viktig slutsats:** PM-027 behöver en källspecifik adapter/mapping, inte ett nytt universellt snapshotarkiv. Normaliserad read model måste behålla lager-/tjänstgranularitet, scope, source-specific completeness basis, run-/manifest-/snapshotreferenser och null/unknown där underlag saknas. Latest attempt och latest complete snapshot hålls åtskilda.

**Nästa steg:** skapa versionsstyrd mapping mellan source_id, produkt/lager, workflow, manifest locator och scope. Implementera därefter read-only adapter för avverkningsanmälningar och Samråd först, med fixtures och tester för complete/partial/failed/stale/unknown. Ingen ny snapshotlagring eller ändring av källinsamling.


## 2026-11-24 – PM-027: formell kontraktsdesign uppskjuten

Efter att ha granskat aktuell `main` i Skog och den privata `skogskoll-project-manager-history` är arbetsordningen justerad. Ett minsta rapportfältförslag finns redan i `PROJECT_BACKLOG.md`, men formell versionsstyrd kontraktsdesign bedöms vara för tidig innan den befintliga read modellen har prövats mot riktiga källmanifest.

**Verifierat i projektledarrepot:** `scripts/collect_github.py` samlar repo-/issue-/PR-/workflowmetadata och läser `data-platform/config/sources.yml` som `source_registry`. `data/workflow_metadata.json` klassar workflow paths. `scripts/validate_inventory.py` validerar inventorypayloaden. `scripts/append_history.py` och `docs/HISTORY_FORMAT.md` avser projektinventeringens append-only-historik, inte ett universellt kontrakt för källsnapshots. Dashboarden visar källregisterstatus och senaste 20 workflow-körningarna per repo; en verifierad koppling från varje source/product/layer till senaste kompletta källsnapshot saknas fortfarande.

**Nästa konkreta steg:** en avgränsad read-only genomförbarhetsprototyp i befintlig collector/read model för Skogsstyrelsens avverkningsanmälningar och Samråd. Använd befintliga källmanifest/snapshotformat och explicit workflow-/scope-evidens. Ingen ny collector, snapshotlagring, historikmodell, schedule, Azure-publicering eller kundfunktion. Unknown ska förbli unknown; latest attempt och latest complete snapshot ska hållas isär.

**Beslutspunkt:** efter prototypen avgörs om en liten utökning av befintlig payload räcker eller om ett separat versionsstyrt kontrakt behövs. Kontraktsdesign ska alltså inte vara ett självständigt förarbete innan denna konkreta prövning.


## 2026-11-24 – Projektledarens dagliga inventory-schema säkrat

I det privata repot `dahlinrobert-lgtm/skogskoll-project-manager-history` är PR [#55](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/55) mergad (commit `ccda5189e83deec96df5f0262412208fe1fdb3a3`).

- Inventory-workflowet använder en enda GitHub Actions-trigger kl. 07:17 med tidszonen `Europe/Stockholm`. Den tidigare dubbla UTC-triggern och exakta lokala entimmesgrinden är borttagna, så försenad start leder inte längre till att insamlingen hoppas över på grund av klockslaget.
- Schemalagda körningar kan enligt GitHubs dokumentation fortfarande försenas eller tappas vid hög belastning. Schemat är flyttat från hel timme, men faktisk körning och artifact måste fortsatt verifieras.
- Collector-jobbet har endast `contents: read`. Issue-sidoeffekten ligger i separat jobb med `issues: write`; manuella körningar har den avstängd som standard och kräver explicit `manage_alert_issue=true`.
- PR-CI passerade: Project manager tests run `45440389309` och Synthetic append-only tests run `45440389414`.

**Kvarstående:** ingen live inventory-körning eller nytt artifact efter merge är verifierat. GitHub-integrationen i denna session kan läsa workflow-runs och artifacts men erbjuder inte dispatch av workflow. Starta därför en manuell körning från projektledarrepots `main` via GitHub Actions, lämna `manage_alert_issue` avmarkerad och granska artifact innan PM-027:s två källor och dashboard verifieras. Ingen Azure-publicering, källskrivning eller kundavisering ingår.


## 2026-11-24 – PM-027 collectorimport korrigerad och mergad

I det privata projektledarrepot [skogskoll-project-manager-history PR #58](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/58) är importfixen för PM-027-adaptern mergad till `main` i commit `02e2ee876bf2a8293d8c7ab2ad0600c35a750f44`.

Collector använder nu paketrelativ import när den körs som modul och syskonimport som reserv när workflowet kör `python scripts/collect_github.py`. Regressionstestet reproducerar direkt skriptkörningsmiljön genom att lägga `scripts/` på `sys.path`, importera collector-modulen utan paketkontext och verifiera att befintlig `collect()`-väg faktiskt kopplar in adapterevidensen.

Verifiering:
- Korrigerad PR-CI: Project manager tests [45442219024](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45442219024) och Synthetic append-only tests [45442219569](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45442219569) passerade.
- Post-merge main-test: [45442304488](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45442304488) passerade.
- Tidigare manuella inventory-försök [45441579231](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45441579231) och [45440849681](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45440849681) misslyckades före denna korrigering (först dubblett i workflow-metadata, därefter importfel). De är inte live-verifiering av PM-027-adaptern.

**Kvarstående:** kör den befintliga read-only inventory-workflowen manuellt från projektledarrepots `main`. Lämna `manage_alert_issue` avmarkerad. Granska collector-status, fullständighet för aktiva projekt, source registry, de två `source_snapshot_evidence`-posterna (avverkningsanmälningar och Samråd) samt artifact. Latest attempt och latest complete snapshot ska fortsatt hållas isär; okänd evidens ska förbli `unknown`. Denna kodfix ändrar inte källinsamling, källrättigheter, Azure-publicering eller kundbeteende.

Ingen ny källstatus eller rättighetsbedömning följer av merge eller CI. Kundvisning och kommersiell användning förblir enligt källregistret oförändrade.


## 2026-11-24 – PM-027 live inventory #11 verifierad

Projektledarrepots [inventory run #11](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45443506944) är `completed/success` efter merge av PR #60. Collector rapporterade 3/3 aktiva projekt, 0 fel. Artifact [project-manager-inventory-45443506944](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45443506944/artifacts/14944607060) har laddats ned och granskats.

Verifierade resultat:
- Källregistret: 51 källposter, 14 operations-block, 37 utan operativ status; registerkontrolldatum 2026-11-18.
- PM-027-adaptern returnerade `status=success`; Skog Git tree var inte trunkerat.
- `skogsstyrelsen.harvest_notifications`: manifeststatus `manifest_complete` för Gräsmyr 10 km-pilot, 165 poster. Detta innebär inte nationell täckning. SHA-256 i manifestet är inte omräknad av adaptern.
- `skogsstyrelsen.samrad`: 24 daterade metadataidentifierade snapshots. Fullständighet, scope och punkt-/linje-/polygonantal är fortsatt `unknown`.
- `latest_attempt` var `unknown` för båda källorna, eftersom matchande workflows inte fanns bland de senaste 20 workflow-körningarna för repot. Det är en begränsning i lookup-fönstret, inte bevis för att körning saknas.
- Artifact uppladdades och dess SHA-256 digest var `256c010207f7719da4aa53e55c910f3dab63774e1db08c1b87d67007cb486fb8`. Alert-jobbet var överhoppat; inga källfeatures laddades ner.

PM-027 är därmed live-verifierad för befintlig read-only collector/read model och dess uttryckliga evidensgränser. Ingen rättighetsstatus, kommersiell användning, kundvisning eller kundfeed har ändrats.

**Nästa konkreta steg:** förbättra hämtningen av senaste matchande workflow-försök utan att skrapa all workflow-historik, därefter undersöka en liten separat Samråd-manifestfil med per-lager antal, paging och fullständighet. Behåll `unknown` där evidens saknas. Autentiserad dashboardvisning är inte verifierad av artifactkontrollen och ska testas separat.


## 2026-11-24 – PM-027 riktad latest-attempt-uppslagning mergad

Projektledarrepot [skogskoll-project-manager-history PR #62](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/62) är mergad i commit `c3f94216c07d2496e1a64cd44b739288e0682908`. PM-027-adaptern använder nu riktade read-only GitHub Actions-uppslag: lista workflow-metadata, matcha exakta konfigurerade workflow-sökvägar, hämta `per_page=1` för varje workflow-ID och välj senaste körning per källa. Den generella dashboardens latest-20-lista är oförändrad.

Saknat workflow eller tom körningshistorik ger fortsatt `unknown`. API-fel och felaktiga svar failar adaptern stängt så inventory blir partiell. Inga källors feature-data hämtas, inga källrepon skrivs och inga rättighets- eller kundvisningsstatusar ändras.

Verifierade tester på PR-commit `7573a7c87c975e93534c52b8bc3d3ae795055ab2`: [Project manager tests #45449073568](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45449073568) och [Synthetic append-only tests #45449073704](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45449073704) passerade. Post-merge [main tests #45449310070](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45449310070) passerade.

**Nästa konkreta steg:** kör den befintliga manuella read-only projektinventeringen från projektledarrepots `main`, lämna `manage_alert_issue` avstängd och granska artifactet. Verifiera `latest_attempt` för både `skogsstyrelsen.harvest_notifications` och `skogsstyrelsen.samrad` mot exakta workflow-run-ID:n. Om inget matchande workflow/run finns ska `unknown` bevaras. Liveinventering efter ändringen är ännu inte genomförd/verifierad.


## 2026-11-24 – Länsstyrelsernas eldningsförbud: metadata-connector förberedd

Ny källpost `lansstyrelsen.fire_ban` har lagts till i `data-platform/config/sources.yml` på branch `feat/lansstyrelsen-fire-ban-connector`, tillsammans med en manuell read-only metadata-inspektör:
`data-platform/scripts/inspect_lansstyrelsen_fire_ban_service.py`.

Källan är Länsstyrelsernas externa WebbGIS **LST Eldningsförbud i skog och mark (EXT)**. Metadata-ID `53514d5d-b1ea-4162-bc56-58e496f0f4f7`. FeatureServer:
https://ext-geodata-nationella-visning.lansstyrelsen.se/arcgis/rest/services/LST/LST_eldningsforbud_EXT/FeatureServer

Användarens metadata-skärmbild visar revision 2026-08-26, underhåll årligen/kontinuerligt, fem statusvärden och att inga användnings-/åtkomstvillkor anges i metadata. Maskinläsbar metadata, exakt lagerstruktur, fält, geografisk täckning, stabil identitet, paginering och villkor är ännu inte verifierade. Status är därför fail-closed: åtkomst ej verifierad, snapshots ej startade, historik ingen, kommersiell användning okänd, kundvisning ej bedömd.

Connectorn hämtar endast service- och lager/tabellmetadata, sekventiellt med timeout och säkerhetstak. Den frågar inte efter feature-poster eller geometrier och skapar inga snapshots. Ingen schemaläggning/workflow har lagts till.

**Användarbeslut:** schemaläggning och operativa snapshots får tidigast börja om två månader, satt till 2027-01-24. Före det datumet kan endast manuell metadata-inspektion och teknisk förberedelse göras. Första operativa snapshot ska bli tyst baslinje utan historiska larm. Saknad information/”ej angivet” får aldrig tolkas som inget eldningsförbud.

**Nästa steg efter PR:** granska och merg:a connectorn, kör därefter den manuella metadata-only-proben när endpointen är åtkomlig. Uppdatera sedan dokumentationen med faktiska lager-/fält-/scope-/pagineringresultat. Vänta med featurehämtning, schemaläggning och snapshots till tidigast 2027-01-24 och separat godkännande.


## 2026-11-24 – Eldningsförbud metadata-connector mergad

Skog PR [#590](https://github.com/dahlinrobert-lgtm/Skog/pull/590) är mergad i main (merge commit `ea5e65a947c239d7100b15171e4f532975ab7413`). PR-headens tre GitHub Actions-kontroller passerade: `test`, `validate` och `customer-ui-tests` (commit `fd44ea344d70ca7e7d02a71449b054703b3b5f01`).

Main innehåller nu:
- källposten `lansstyrelsen.fire_ban` i `data-platform/config/sources.yml`,
- manuell metadata-only connector `data-platform/scripts/inspect_lansstyrelsen_fire_ban_service.py`,
- tester `tests/test_inspect_lansstyrelsen_fire_ban_service.py`,
- uppdaterad datakälle- och statusdokumentation.

**Runtime-status:** connectorn är inte körd mot FeatureServer ännu. Ett försök att öppna den direkta REST-metadataadressen via tillgänglig webbläsarhämtning gav inte åtkomst. Därför finns ännu inga verifierade liveuppgifter om lager-ID:n, fält, extent/täckning, objektidentitet, maxRecordCount eller paginering. CI verifierar kod/tester och register, inte extern endpoint.

**Nästa konkreta steg:** kör manuellt från en miljö med nätverksåtkomst:

    python data-platform/scripts/inspect_lansstyrelsen_fire_ban_service.py --out /tmp/lansstyrelsen-fire-ban-metadata.json
Granska resultatet och uppdatera `SKOGSKOLL_DATA_OVERVIEW.md` och källregistrets evidens först när de faktiska metadataresultaten finns. Behåll källstatus fail-closed tills dess.

Ingen feature-query, geometrihämtning, snapshot, schemaläggning eller kundvisning är aktiverad. Enligt användarens beslut får schemaläggning och operativa snapshots tidigast övervägas 2027-01-24, efter separat beslut. Första operativa snapshot ska vara en tyst baslinje utan historiska larm.


## 2026-11-24 – Älgdata: öppna data-villkor preciserade

Länsstyrelsen Västerbottens officiella öppna data-sida beskriver Älgdata som statistik över fällda älgar och inrapporterad avskjutning, anger att databasen får användas helt fritt, att villkor saknas och att formatet är Microsoft XLSX. Samma uppgift har kontrollerats på Länsstyrelsen Stockholm och Jämtland. Detta ger starkt stöd för fri återanvändning av den publicerade statistiken, inklusive historisk jämförelse, bearbetning, kommersiella analyser och kundvisning inom statistikens scope. Attribution anges inte som villkor; källhänvisning rekommenderas ändå.

**Viktig avgränsning:** detta villkorsbesked dokumenterar inte portalens interna API som ett stabilt automatiseringsgränssnitt, dess anropsfrekvens eller SLA. Innan högfrekvent/produktionskritisk maskinhämtning bör Länsstyrelsen bekräfta den tekniska hämtvägen. JaktAdm-geometrier är en separat produkt och omfattas inte automatiskt av Älgdata-statistikens villkor.

Se [rättighetsgranskningen](source-rights-reviews/2026-11-16-lansstyrelsen-elk-afo.md), avsnitt 5. Nästa konkreta steg: begär ett kort tekniskt besked från Länsstyrelsen om återkommande maskinell hämtning via den använda statistikportalen/API-vägen och eventuella frekvensbegränsningar. Ingen kod, worker eller kundfeed aktiveras i detta dokumentationssteg.



## PM-029 – Projektledarens uppdateringskadens (beslut 2026-11-24)

Användaren har godkänt följande målbild för den privata projektledarsidan:
- Europe/Stockholm, vardagar 16.00–01.00: read-only GitHub-inventering var femte minut.
- Helger 10.00–01.00: read-only GitHub-inventering var femte minut.
- Övrig tid: inventering en gång per timme.
- Webbläsaren kontrollerar efter ny publicerad snapshot varje minut under de aktiva tiderna och en gång per timme övrig tid.

Detta är ett beslutat schema, inte implementerad eller verifierad drift. Befintlig arkitektur ska återanvändas: read-only collector och validator i `skogskoll-project-manager-history`, separat OIDC-publisher med containerbegränsad Azure-behörighet, privata run-scopade snapshots och autentiserad Entra/MSAL-läsare. Ingen publik projektdata, containerlistning i browsern eller parallell collector.

Viktiga nulägesfynd:
- Inventeringsworkflowet kör för närvarande dagligen 07.17 Europe/Stockholm.
- Azure-publishern är manuell och skriver run-scopade snapshots/manifest; ingen latest-pointer eller schemalagd publicering är verifierad.
- Pages-konfigurationen i Skog pekar på snapshot `45002255351`, medan staging-konfigurationen i det privata projektledarrepot pekar på `44958916377`. Referenserna måste jämkas genom en säker latest-mekanism, inte genom att hårdkoda ytterligare run-ID.
- Den publicerade browserklienten saknar automatisk polling.
- GitHub Actions schematriggers kan försenas eller tappas; actual run/artifact freshness måste kontrolleras.

Nästa konkreta arbetssteg:
1. I det privata projektledarrepot: implementera/testa en DST-säker tidsgrind (Europe/Stockholm), femminuterskadens i aktiva fönster och timkadens övrig tid. Undvik att alert-jobbet får onödiga issue-sidoeffekter vid varje femminuterskörning.
2. Lägg till en atomiskt publicerad latest-manifest/pekare först efter komplett validering och byte-for-byte read-back; behåll alla run-scopade snapshots oförändrade.
3. Uppdatera den publicerade Pages-klienten att kontrollera pekaren enligt minut-/timkadensen och endast läsa ny snapshot vid ändrat run-ID. Behåll Entra-autentisering och fail-closed-visning.
4. Testa midnatt, veckodagsgräns, helg, sommar-/vintertid, parallella körningar, misslyckad/partial insamling, saknad pekare, stale data och återhämtning.
5. Genomför liveverifiering av Azure CORS/RBAC/browser read före aktivering. Uppdatera PM-029 och denna handover med faktisk evidens efter varje steg.

Dokumentationsbedömning: PM-029 är registrerad i `docs/PROJECT_BACKLOG.md`. Källstatus och datakälleöversikt behöver inte ändras eftersom inga källor, källrättigheter eller datainsamlingsflöden har ändrats.


## 2026-11-24 – Lokal miljöinventering och befintlig Windows-lagringsinventering

**Verifierat nuläge:**
- Lokal miljöinventering är genomförd i avgränsade steg. Windows 10 Home/build 26200, Windows PowerShell 5.1.26100.9818, Git 2.56.0.windows.4, Python 3.12.10 och 3.15.2 samt Node.js/npm identifierades.
- Python 3.12 är den fungerande Skog-miljön vid kontrollen: 42 installerade paket, alla åtta direkta krav i `requirements.txt` uppfyllda, `pip check` utan fel. Python 3.15 har 8 paket och saknar minst Shapely i no-index-kontrollen av projektkraven. Ingen virtuell miljö hittades i Skogs projektträd.
- Lokala Git-repon: Skog på `main` med 34 ospårade poster och bear-data på `audit/nvr-rt90-coordinate-recovery` med 15 ospårade poster. Inga spårade ändringar rapporterades. Ospårade data/skript ska bevaras tills de klassificerats.
- Avgränsad skanning fann 3 107 filer i `data` (cirka 702,86 MiB), 11 filer i `data-platform`, 3 analys-CSV i `road_network_endpoint_analysis`, 2 154 filer i `data/viltdata` och 1 fil i `data/police_events/external_import`. Detta är inte en fullständig diskinventering.
- Befintlig Windows Task Scheduler-aktivitet `Skogskoll - local storage inventory` kör dagligen kl. 21:00 med `powershell.exe` och `scripts/inventory-local-storage.ps1`. Senaste kontrollerade körning 2026-11-23 21:00:01 hade resultatkod 0 och 0 missade körningar. Nästa körning vid kontrollen var 2026-11-24 21:00.
- Schemalagda parametrar: standardrötter och standardoutput; `-IncludeRemovableDrives` aktiv; `-HashFiles` inaktiv. Inga anpassade rötter/outputkataloger. Ingen aktivitet eller fil ändrades.

**Kodgranskning – öppna risker:**
- `Get-ChildItem -Recurse -ErrorAction SilentlyContinue` kan dölja underkatalogfel.
- `missing` skapas utan krav på komplett inventering.
- Förra och nuvarande root-set jämförs inte; ändrat scope kan ge falska bortfall.
- JSON-rapporter innehåller dator-/användaridentitet och fullständiga lokala sökvägar.
- Resultatkod 0 är inte bevis på fullständig inventering eller filintegritet.

**Projektledare:** Issue [#597](https://github.com/dahlinrobert-lgtm/Skog/issues/597) skapad med mål, risker och acceptanskriterier. Skog är aktivt i projektledarens register och dess collector läser öppna issues. Den befintliga Project Manager-webbklienten visar `open_work_items`; issue #597 bör visas efter nästa kompletta inventory och publicerade dashboard-snapshot. Ingen webbklientkod eller publicering ändrades här.

**Nästa konkreta steg:**
1. Läs senaste lokala inventeringsrapporten från den faktiska outputkatalogen och kontrollera roots, errors, antal och tidigare snapshot.
2. Utforma fail-closed-status per rot och root-set-jämförelse i `inventory-local-storage.ps1`; `missing` får bara beräknas mellan kompletta jämförbara inventeringar.
3. Lägg till tester för nekad katalogåtkomst, partiell inventering, ändrat root-set, baseline och komplett jämförbar körning.
4. Behåll daglig Task Scheduler-konfiguration, read-only-egenskaper och tidigare rapporter. Ingen SHA-256-aktivering eller schemaläggningsändring utan separat beslut.

**Dokumentationsstatus:** Documented för inventeringsnuläge och riskbedömning; implementation är öppen via issue #597.


### PM-029 – implementation update 2026-11-24

Den första runtime-delen är nu mergad i det privata projektledarrepot `dahlinrobert-lgtm/skogskoll-project-manager-history`.

- PR #66: https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/66
- Merge commit: `1317798385eff9a9eafd3998b1d27b36a77fb75a`.
- `.github/workflows/project-manager-inventory.yml` triggar nu en lättviktig schedule-gate var femte minut i `Europe/Stockholm`.
- `scripts/schedule_gate.py` använder `zoneinfo` för att avgöra om read-only collector ska köras var femte minut under vardagarnas 16.00–01.00 och helgernas 10.00–01.00, eller endast vid hel timme övrig tid.
- Alert-jobbets `issues: write` är separat och schemalagt endast vid hel timme. Manuella dispatchar hanterar inte ärenden om inte `manage_alert_issue=true` uttryckligen väljs.
- Collector behåller `contents: read`, separat read-only-token och run-scoped artifact. Ingen Azure-publicering, latest-pointer eller browser-polling ingår ännu.

**Verifiering:** Merge-commitens main-run #117 (Actions run 45483671689) passerade. Python-enhetstester och dashboardens JavaScript-syntaxkontroll är gröna. En tidigare testkörning hittade ett felaktigt UTC-testvärde för helggränsen; testet korrigerades före merge. Detta verifierar kod och testsvit, inte långvarig faktisk schedule-drift. GitHub schedule events kan försenas eller tappas; kadensen är inte en SLA.

**Nästa konkreta steg:** bygg och testa den separata OIDC-baserade Azure-publiceringen i projektledarrepot. Publicera först immutable run-scoped snapshot och manifest efter komplett inventory-validering och read-back. Inför därefter en skyddad latest-pekare som endast flyttas efter verifierad publicering. Efter det uppdateras Pages-klienten med autentiserad polling och tydlig freshness/stale-status. Behåll senaste kompletta snapshot vid partial/failed och bevara historiska snapshots.


### PM-029 – Azure-publicering och latest-pekare mergad 2026-11-24

Den andra runtime-delen av PM-029 är nu mergad i det privata projektledarrepot `dahlinrobert-lgtm/skogskoll-project-manager-history`.

- PR #68: https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/68
- Merge commit: `44c2bfa73b14193c7d7fb364084b69c791819ca8`.
- Main CI run #45486205149 passerade Python unit tests och dashboardens JavaScript-syntaxkontroll.
- Publiceringsworkflowet triggas automatiskt efter avslutad inventory-workflow via `workflow_run`, och behåller manuell dispatch som operatörsväg.
- Källkörningen måste vara lyckad, färdig, komma från exakt inventory-workflow på `main` i rätt repo och ha ett enda namngivet/oexpirerat artifact. Gate-tick utan inventory-artifact hoppas över.
- Payload och deterministiskt manifest lagras run-scopat. Byte-för-byte read-back krävs innan `latest.json` uppdateras. Äldre run får inte flytta latest bakåt; samma run kräver matchande manifestreferens och payload-SHA-256.
- Befintlig OIDC-identitet och privat Azure Storage återanvänds. Ingen anonym blobåtkomst, containerlistning, källfeaturedata eller kunddata införs.

**Verifieringsgräns:** merge och CI är verifierade. Automatisk trigger efter en verklig schemalagd inventory-run, OIDC/RBAC, Azure-upload/read-back, latest-pekarens liveinnehåll samt Entra/CORS/browserläsning är ännu inte verifierade. Ingen browser-polling är implementerad eller aktiverad.

**Nästa konkreta steg:** invänta nästa lyckade inventory-run på `main`; verifiera att publishern triggas och att payload, manifest och `latest.json` läses tillbaka korrekt i privat Azure. Testa också att partial/failed-run inte kan flytta latest. Först därefter implementeras autentiserad Pages-polling mot latest-pekaren och dashboardens freshness/stale-visning.


## 2026-11-24 – Fail-closed lokal lagringsinventering mergad

PR [#600](https://github.com/dahlinrobert-lgtm/Skog/pull/600) är mergad i `main`, merge commit `670b8dd5cfad60f7a1eb0a26ef1c91e2921bb599`. Issue [#597](https://github.com/dahlinrobert-lgtm/Skog/issues/597) stängdes automatiskt vid merge.

**Implementation i main:**
- `scripts/inventory-local-storage.ps1` producerar schema 2.0 med `inventory_status`, `comparison_status`, `comparison_reason`, rotstatus och antal rötter/kataloger/filer/fel.
- Enumereringsfel fångas. Saknade rötter behålls i scope och kan inte tyst försvinna ur jämförelsen.
- Diff beräknas endast när aktuell inventering är komplett, föregående schema 2.0-rapport är komplett och rotuppsättningen är identisk. Annars undertrycks diffen.
- Schema 1-rapporter är avsiktligt icke-jämförbara och ger en tyst baseline.
- PowerShell 5.1-parsning och regressionstest passerade i [Actions run 45486453158](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45486453158). Testfallen täcker baseline, komplett jämförelse, ändrat rot-set och saknad rot.

**Viktiga kvarstående begränsningar:**
- ACL-test med nekad åtkomst till en underkatalog saknas; befintligt partielltest använder en saknad rot.
- JSON-rapporten har inte längre dator-/användaridentitetsfält, men innehåller fortfarande fullständiga lokala filsökvägar. Markdownrapporten innehåller datornamn. Rapporterna ska hållas lokalt och inte publiceras utan separat granskning.
- Den nya versionen är inte manuellt körd på användarens dator. Task Scheduler-aktiviteten, dess dagliga 21:00-schema, removable-drive-inställning och SHA-256-inställning har inte ändrats.

**Nästa konkreta arbetssteg:**
1. Bevara en kopia av lokalt `scripts/inventory-local-storage.ps1` och hela rapportmappen innan lokal uppdatering.
2. Uppdatera den lokala arbetskopian från `main` och kör skriptet manuellt en gång. Ändra inte Task Scheduler och aktivera inte `-HashFiles`.
3. Granska schema 2.0, samtliga rotstatusar, `error_count`, `comparison_status` och `comparison_reason`. En första schema 2.0-körning ska vara baseline; äldre schema 1 ska inte skapa historiska missing-händelser.
4. Lägg till ett isolerat ACL-regressionstest för nekad underkatalogåtkomst och utred minimering av filsökvägar/datornamn i lokala rapporter.
5. Efter godkänd manuell kontroll: låt befintlig schemalagda aktivitet vara oförändrad och verifiera en senare schemalagd körning.

**Dokumentation:** `docs/STORAGE_INVENTORY.md`, `docs/PROJECT_BACKLOG.md` och denna handover uppdateras i dokumentations-PR efter implementationens merge. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms inte behöva ändras: inga källor, källrättigheter eller datainsamlingsflöden ändrades.


## 2026-11-24 – PM-030: lokal lagringsinventering schema 2.1 mergad

**GitHub main:** PR [#604](https://github.com/dahlinrobert-lgtm/Skog/pull/604) är mergad i commit `a08163a8bee42848ed27d76c381103105fed9d7d`. Föregående delar: PR #600 (fail-closed schema 2.0) och PR #603 (ACL-test för nekad underkatalog) är också mergade. Main Actions [run 45491349781](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45491349781) har genomfört Windows PowerShell 5.1-parsning och regressionstester med success på jobbet; kontrollera workflowets slutliga conclusion om körningen fortfarande var in progress vid dokumentationstillfället.

**Schema 2.1:** JSON-/Markdownrapporter innehåller `root_id` och relativa sökvägar i stället för absoluta lokala sökvägar; datornamn har tagits bort. `root_id` är SHA-256-baserad och deterministisk för samma rot, alltså pseudonymisering snarare än anonymisering. Filnamn och relativa katalogvägar finns kvar. Schema 2.0 och äldre rapporter är icke-jämförbara; första schema 2.1-körningen blir tyst baseline. Jämförelse kräver kompletta rapporter och identiskt root-ID-set.

**Kvarstående lokal driftsättning – ej genomförd/verifierad:** användaren har inte lämnat bekräftelse på backup av det lokala skriptet och hela rapportkatalogen. Fastställ först den faktiska rapportkatalogen; kopiera den separat till en backupplats utanför katalogen. Bevara alla lokala ospårade filer. Uppdatera därefter lokal main-kopia, kör skriptet manuellt och granska schema 2.1, rotstatus, error_count och `comparison_status=baseline`. Ändra inte Task Scheduler (dagligen 21:00, `-IncludeRemovableDrives`) och aktivera inte `-HashFiles`. Efter godkänd manuell körning: verifiera en senare schemalagd körning. Råa lokala inventeringsrapporter ska inte laddas upp till GitHub.

**Nästa konkreta arbetssteg:** invänta användarens backupkörning/output; verifiera att både skriptbackup och hela faktiska rapportkatalogen finns innan några lokala uppdateringskommandon körs. Därefter ge en säker, stegvis lokal uppdaterings-/baselineprocedur.

**Dokumentationsbedömning:** `STORAGE_INVENTORY.md`, `PROJECT_BACKLOG.md` och denna handover uppdateras i dokumentations-PR. `SKOGSKOLL_SOURCE_STATUS.md` och `SKOGSKOLL_DATA_OVERVIEW.md` är kontrollerade på main och lämnas oförändrade eftersom inga källor, källrättigheter eller insamlingsflöden ändrats.


## 2026-11-24 – PM-027 inventory #13 och Samråd-manifest

Projektledarrepots manuella read-only inventory [run #13](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45495087348) avslutades `completed/success`. Artifacten `project-manager-inventory-45495087348` granskades. Collector rapporterade 3/3 aktiva projekt, 0 fel; tester och dashboardens JavaScript-syntaxkontroll passerade. Det separata write-enabled alert-jobbet var `skipped`. Ingen kundwrite eller källrepo-skrivning utfördes.

Riktad latest-attempt-lookup visar:
- `skogsstyrelsen.harvest_notifications`: senaste matchande workflow är `.github/workflows/national-monitor.yml`, run [43881404640](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/43881404640), `completed/failure`, 2026-11-16. Den andra konfigurerade workflow-sökvägen saknas. Senaste kompletta snapshot som adaptern kan verifiera är fortfarande Gräsmyr 10 km-pilotens manifest, 165 poster, 2026-11-22; inte nationell täckning. SHA-256 är källans manifestpåstående och räknas inte om av adaptern.
- `skogsstyrelsen.samrad`: senaste matchande workflow är `.github/workflows/collect-samrad.yml`, run [45454250815](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45454250815), `completed/success`, 2026-11-24. Jobbloggen redovisar 0 punkter, 11 linjer och 12 polygoner inom Gräsmyr-pilotens 10 km-scope. 20 linjeposter och 14 polygonposter hämtades i query-envelope; punkterna gav 0. Totalt 23 poster behölls inom scope. Alla 5 Samråd-tester och 6 händelsekedjetester passerade. Gzip-snapshoten var 401 176 byte och data-PR [#549](https://github.com/dahlinrobert-lgtm/Skog/pull/549) uppdaterades.
- Samråd-adaptern har fortsatt `latest_complete_snapshot=unknown`, eftersom nuvarande `samrad_latest.json` kombinerar manifestmetadata med featuredata och adaptern avsiktligt inte laddar ned den stora filen. Scope och lagerfullständighet är därför fortfarande okända i projektledarens read model. Körningsloggen är verifierad evidens för den enskilda körningen, inte en källtotalavstämning eller nationell täckning.

**Pågående ändring i denna gren:** `feat/samrad-small-snapshot-manifest` i Skog lägger till en separat liten `data/samrad_latest_manifest.json` med snapshotreferens, SHA-256 för den komprimerade snapshotfilen, scope-hash samt status och antal per punkt-/linje-/polygonlager. Geometrier som saknas eller inte kan behandlas räknas explicit och hindrar status `complete_for_configured_scope`. Manifestet anger `source_total_reconciled=false`; komplett betyder alltså endast paginerad och geometriskt klassificerad inom konfigurerat scope, inte verifierad mot en separat auktoritativ total. Tester och workflow-arkivering ingår. Detta är ännu inte mergat eller liveverifierat.

**Nästa konkreta steg:** granska och merge:a manifest-PR efter CI. Därefter uppdatera projektledarrepots befintliga PM-027-adapter att läsa endast den lilla manifestfilen, verifiera att refererad gzip-snapshot finns i Skog main-trädet och exponera per-lager evidens utan att ladda ned features. Kör därefter en ny read-only inventory och granska artifact. Behåll okända värden som unknown; manifestet ändrar inte källans kommersiella användning eller kundvisningsstatus.

**Dokumentationsstatus:** Documentation outstanding tills manifestimplementeringen är mergad och adapterintegrationen är liveverifierad.


## 2026-11-24 – Samråd small manifest och PM-027-adapter mergade

Båda beroendeimplementationerna är nu mergade:
- Skog PR [#606](https://github.com/dahlinrobert-lgtm/Skog/pull/606), merge commit `917fa445559413385a0c995d448c1203d0520c2a`: separat liten `data/samrad_latest_manifest.json`, per-lager pagination-/antal-/geometristatus, explicit räkning av saknad/felaktig geometri och SHA-256 av den skrivna gzip-snapshoten. `complete_for_configured_scope` kräver att alla tre lager är framgångsrikt paginerade och att samtliga hämtade geometrier kan klassificeras. `source_total_reconciled=false` bevaras.
- Projektledarrepo PR [#70](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/70), merge commit `9f27cc7b61761b09cba37bf84ccb7b24a6d45a5b`: PM-027-adaptern läser endast det lilla manifestet och Git-trädets metadata, kräver samtliga tre kompletta lager samt att refererad snapshot finns. Den laddar inte ned featuredata eller gzip-snapshot. SHA-256 exponeras som manifestets påstående (`checksum_verified_by_adapter=false`), inte som omräknad checksumma.
- Projektledarens post-merge CI [run 45497224654](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45497224654) passerade. PR-testet omfattade 75 Python-tester och JavaScript-syntaxkontroller.

**Liveverifiering återstår:** manifestfilen har ännu inte verifierats på Skog `main` efter en körning av produktionsworkflowet, och projektledarens nya adapter har ännu inte verifierats i en ny read-only inventory/artifact efter merge. Den senaste verifierade read-only inventory är fortfarande run #13 [45495087348](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45495087348), som föregick merge av dessa två PR:er. Ingen automatisk workflow-dispatch är tillgänglig i denna session.

**Nästa konkreta steg:** kör `.github/workflows/collect-samrad.yml` från Skog `main` för att skapa och verifiera `data/samrad_latest_manifest.json`. Kontrollera att manifestets status och per-lagerfält är rimliga och att snapshotreferensen finns. Kör därefter projektledarens read-only inventory från `main` med `manage_alert_issue` avstängd; granska artifacten och verifiera att Samråd exponeras som `manifest_complete_for_configured_scope` endast om manifestet klarar adapterns grindar. Om manifest saknas/är partiellt ska status förbli `unknown`.

**Dokumentationsstatus:** Documentation outstanding tills båda post-merge-körningarna och artifactgranskningen är klara. Rättighetsbedömning, nationell täckning och kundvisning har inte ändrats.


## 2026-11-25 – Viltdata första differensanalys verifierad

Två kompletta nationella Viltdata-snapshots från 2026-11-18 har jämförts: baslinje `20261118T204420Z` (Actions #44394070179) och senare observation `20261118T220720Z` (Actions #44408345762). Båda har 49 arter, 21 län, 550/550 statistikförfrågningar och 552 råfiler vars byteantal/SHA-256 har verifierats. Täckningen matchar exakt med 73 255 observationsnycklar per snapshot.

Resultat: 73 252 oförändrade och 3 ändrade observationer; inga tillkomna/saknade nycklar, inga nya värden, inga nya nollvärden och inga värden som blivit saknade. Alla tre ändringar avser Älg 2026: nationellt 18 158→18 163 (+5), län 7 1 025→1 026 (+1), län 17 2 014→2 018 (+4). De två länsdifferenserna summerar till den nationella differensen. Null (3 364) och explicita nollvärden (24 950) är bevarade separat.

Detaljer och reproducerbar körinstruktion: [docs/viltdata-kill-statistics-diff-20261118.md](viltdata-kill-statistics-diff-20261118.md). Första snapshoten är tyst baslinje; inga historiska larm har skapats. Original-artifacts och rådata har inte ändrats. GitHub Actions-artifacts är tidsbegränsade och inte permanent arkiv. Rättigheter för permanent lagring, bearbetning, kommersiell användning, kundvisning och distribution är fortsatt inte bedömda/godkända.

**Nästa konkreta steg:** invänta skriftligt rättighetsbesked för exakt Viltdata-statistikprodukt. Vid nästa manuella uttag krävs åter fullständigt manifest, 550/550 (dynamiskt enligt källmodell), råfilernas SHA-256/bytekontroll och jämförbar täckning innan diff. Ingen schedule, permanent arkivering eller kundvisning aktiveras.


## 2026-11-25 – Samråd-historik från daterade snapshots (PR #612 mergad)

- Separat branch `feat/samrad-snapshot-event-history` utökar den befintliga `scripts/build_harvest_event_bundle.py`; ingen parallell historikmodell eller nytt workflow införs.
- Byggaren läser de oföränderliga `data/samrad_snapshots/samrad_*.json.gz`-filerna. Varje komplett snapshot blir en `source_run` med daterad `snapshot_ref`; varje distinkt innehållsversion blir en `observation` som pekar på rätt gzip-snapshot.
- Kanoniska Samråd-händelser grupperas med befintliga Beteckn-/UUID-/källobjektsnycklar. `first_observed_at` och `last_observed_at` beskriver arkiverad observationstid. En post som saknas i ett senare uttag tas inte bort ur historiken och får ingen avslutsstatus.
- Historikbehörighet kräver `status=success`, tidsstämpel, scope-hash, alla tre lager, sidräknare och avstämda antal; saknad geometri och geometrifel måste vara noll. Partiella/okända snapshots hoppas över och används aldrig som frånvaroevidens. En oläsbar gzip-fil avbryter byggandet (fail-closed).
- Exakt identiskt snapshot dedupliceras. Oförändrade objektversioner dedupliceras enligt befintligt event-bundle-kontrakt; ändrat innehåll ger ny observation.
- Ändringen påverkar endast härledd event bundle. Rådata, daterade snapshots, insamlingskadens, kundvisning och aviseringar ändras inte.
- Status: PR #612 är mergad till `main`. Regressionstestets textassertion korrigerades i commit `1833f172` utan att ändra historiklogiken. Den mergade implementationen bevarar daterade snapshotreferenser och frånvarande poster utan att skapa avslutsstatus. Ändra inte källans rättighetsstatus på grund av denna tekniska historikförbättring.

## Samråd – historik och snapshotarkiv verifierade efter PR #613 (2026-11-25)

- PR [#613](https://github.com/dahlinrobert-lgtm/Skog/pull/613) är mergad till `main` 2026-11-25 16:20:51 UTC, merge commit `e224a7fd9102095059eb60e8293a4296ab79be3b`. Den uppdaterade snapshotgrenen innehöll daterat snapshot och härledd event bundle.
- Föregående push-körning [Collect Samråd pilot snapshots #47](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45650638344) hade lyckad insamling, tester och event-bundle-byggande men misslyckades i sista steget för create/update pull request. PR #613 och dess automation-branch hade ändå uppdaterats; PR:n mergades därefter manuellt.
- I den körningen rapporterade event-bundlen 26 arkiverade Samråd-snapshots, 21 Samråd-observationer och 21 Samråd-händelser. Regressionstesterna för tomt punktlager med 0 sidor passerade. Event bundle contract [#22](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45650638711) och snapshot storage tests [#552](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45650638347) passerade.
- Snapshotmanifestet var `success` och `complete_for_configured_scope`, med points 0 poster/0 sidor, lines 9 poster inom scope/1 sida och areas 12 poster inom scope/1 sida. `source_total_reconciled=false`; detta är inte nationell avstämning.
- PR-merge gör snapshots och bundle beständiga i `main`; den bekräftar inte att Samråd-workflowets sista PR-skapandesteg fungerar felfritt. Följ upp nästa schemalagda/manuella körning och kontrollera särskilt det steget.
- Rättighetsstatusen ändras inte: teknisk åtkomst och historik är inte i sig godkännande för kommersiell användning, kundvisning eller vidare distribution.

**Nästa konkreta steg:** kontrollera nästa Samråd-körning efter merge, inklusive insamling, manifest, event-bundle och PR-automationen. Håll nationell täckning och kundrättigheter som separata öppna frågor.


## Samråd – PR-automation verifierad och run #48 arkiverad (2026-11-25)

- Efter att PR [#617](https://github.com/dahlinrobert-lgtm/Skog/pull/617) dokumenterat det tidigare arkivet kördes [Collect Samråd pilot snapshots #48](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45656496498) manuellt från `main` (commit `3b1f6a0ee03d078932225ed1c3a9429c323f95da`). Alla jobbets steg passerade, inklusive `Create or update Samråd snapshot pull request`.
- Loggen bekräftar att workflowet skapade data-PR [#619](https://github.com/dahlinrobert-lgtm/Skog/pull/619). Därmed är felet i sista PR-steget från run #47 inte reproducerat i run #48; run #48 verifierar att steget fungerar för denna körning.
- Run #48-manifestet: `success`, `complete_for_configured_scope`, scope hash `9c597758897297d34eb6ae733e56c5998587de4ff478fd8e82ae1a510dcfa76a`, `source_total_reconciled=false`. Gräsmyr-pilotens 10 km-scope: points 0 poster/0 sidor; lines 18 hämtade i envelope, 9 inom scope och 9 utanför; areas 14 hämtade, 12 inom scope och 2 utanför. Inga saknade geometrier eller geometrifel.
- Snapshot `data/samrad_snapshots/samrad_20261125T164133Z.json.gz`, 400 407 byte, manifest-SHA-256 `fe502340f2fc3301e9cb9bc486a0292867c0c8de6f83bd26befa8701c7876c5f`. Event bundle byggdes med 27 arkiverade Samråd-snapshots, 21 Samråd-observationer och 21 Samråd-händelser; totalt 186 observationer och 186 händelser i bundle.
- PR #619 granskades före merge. Den lade till en daterad råsnapshot och uppdaterade latest-filer samt härledd event bundle; tidigare arkiverade snapshots behölls. PR:n mergades 2026-11-25 16:44:28 UTC med merge commit `e4aaf853f4b16e79c4b744784dabd3bb3295d8e5`. Snapshoten finns verifierat i `main`.
- Detta verifierar endast den aktuella manuella körningen och pilot-scope. Det bevisar inte nationell täckning, avstämning mot källans totaler eller kommersiell/kundvisningsrätt. Källstatus och rättighetsbedömning ändras inte av att snapshoten har arkiverats.
- Historikprincipen kvarstår: saknade objekt i senare uttag får inte tolkas som avbokning, borttagning eller genomförd åtgärd.

**Nästa konkreta steg:** verifiera nästa schemalagda Samråd-körning, inklusive att workflowet skapar eller uppdaterar PR utan fel och att snapshot, manifest och event bundle är konsistenta. Granska data-PR:n före varje merge.


---

## Gräsmyr – reconciliation av monitoring run #604 mergad (2026-11-25)

- Reconciliation-PR [#623](https://github.com/dahlinrobert-lgtm/Skog/pull/623) är mergad till `main` 2026-11-25 17:04:57 UTC. Merge commit: `af0877f69bc1efa2975fcc161435b7133f56d03c`. PR #530 användes inte; dess äldre bas ersattes av en ny reconciliation från aktuell `main`.
- Publiceringen omfattar Gräsmyrs planerade snapshot från monitoring run #604 (163 objekt), completed snapshot och tillhörande analys-/vyfiler. Daterad planned snapshot: `data/snapshots/20261125T161908Z.json`; completed snapshot: `data/snapshots/completed_20261125T161924Z.geojson.gz`.
- Event bundle publicerades i både `data/harvest_event_bundle.json` och `docs/data/harvest_event_bundle.json`. PR-granskningen verifierade 4 source runs, 184 observationer, 184 händelser, 184 evidence-poster, 8 relationer och 163 kedjor; 21 Samråd-händelser och 163 planned-harvest-händelser. ID-unikhet, observationernas run-referenser samt relationers och kedjors event-referenser kontrollerades utan avvikelser. De två bundle-filerna var identiska.
- Samtliga tre Samråd source runs och den daterade snapshotreferensen `data/samrad_snapshots/samrad_20261125T164133Z.json.gz` finns med i den reconcilerade bundle-versionen. Historiska snapshots bevarades. Observationernas ursprungliga provenance-referenser behölls; händelsernas senaste geometri pekar på den senaste arkiverade snapshoten.
- Merge bevarar databaslinjen för Gräsmyr 10 km-piloten. Den innebär inte nationell täckning, fullständig nationell avstämning eller rättighetsgodkännande för kommersiell användning/kundvisning. Frånvaro i jämförbara uttag får inte tolkas som avbokning, borttagning eller utförd avverkning.
- **Verifieringsgräns:** manuell integritetsgranskning genomfördes före merge. PR #623 hade inga registrerade CI-statuskontroller i den tillgängliga kontrollen; ingen ny fullständig testsvit ska därför påstås ha passerat för just denna data-only PR.
- **Dokumentationsbedömning:** `Assessed – no update required` för `SKOGSKOLL_SOURCE_STATUS.md` och `SKOGSKOLL_DATA_OVERVIEW.md`: ingen källåtkomst, källomfattning, rättighet eller arkitektur ändrades. Denna överlämningsnotering dokumenterar däremot den nya beständiga snapshot-/event-bundle-publiceringen.

**Nästa konkreta steg:** kontrollera nästa schemalagda Gräsmyr-monitoringkörning och verifiera att planned/completed snapshots, analysfiler och event bundle publiceras konsistent ovanpå aktuell `main`. Behåll Samråd-historiken och jämför endast kompletta, jämförbara uttag. Granska eventuell data-PR före merge.

## Projektledarsidan – latest-snapshot-koppling mergad (2026-11-25)

PR [#626](https://github.com/dahlinrobert-lgtm/Skog/pull/626) är mergad till `main` 2026-11-25 kl. 17:13:38 UTC. Merge commit: `787482dc22c20d0742834f5c52876a844d59f73a`.

**Verifierad implementation på main:**
- `docs/project-manager/auth-config.js` pekar nu på Azure-containern och `latest.json`, inte längre på den fasta snapshoten `45002255351`.
- `docs/project-manager/app.js` hämtar den senaste publiceringspekaren, validerar schema och run-scopade blobreferenser, kontrollerar payloadens byteantal och SHA-256 samt observationstid innan den renderar data. Vid fel visas ingen projektdata.
- Sidan visar inventeringskörning och publiceringstid.
- `docs/project-manager/index.html` har versionsparametrar för cache-busting.
- `.github/workflows/project-manager.yml` inkluderar dashboardfilerna i relevanta triggers och kör Node syntaxkontroll.
- `docs/PROJECT_STATUS.md` innehåller rotorsak, implementation och verifieringsgräns.

**CI före merge:** projektledartester och Website JavaScript syntax passerade för PR #626 (Actions runs [45662337875](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45662337875) och [45662337807](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45662337807)). Även de två tidigare körningarna för föregående PR-commit passerade.

**Post-merge ännu inte verifierat vid dokumentationstillfället:** workflowet för projektledartester och GitHub Pages deployment hade startat på merge commit `787482d` men var fortfarande pågående. Kontrollera att båda slutförs framgångsrikt. Därefter krävs livekontroll i webbläsare av Microsoft-inloggning, Azure CORS, hämtning av `latest.json` och visning av aktuell snapshot. Publisher-run #6 hade före merge bekräftat att snapshot `45644895332` och `latest.json` laddats upp och lästs tillbaka byte-för-byte.

**Dokumentationsbedömning:** `docs/PROJECT_STATUS.md` och denna handover uppdaterade (Documented). `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedömda Assessed – no update required: ändringen gäller projektledarens read-only driftvy, inte källåtkomst, datatäckning, rättigheter eller kundvisning.

**Nästa konkreta steg:**
1. Kontrollera post-merge Actions för projektledartester och Pages deployment.
2. Öppna [projektledarsidan](https://dahlinrobert-lgtm.github.io/Skog/project-manager/) i webbläsare, logga in och verifiera att senaste publicerade snapshot läses från `latest.json`.
3. Kontrollera att sidan visar aktuell inventeringskörning/publiceringstid och att SHA-256-verifieringen släpper igenom payloaden.
4. Om livekontrollen misslyckas, felsök Entra-inloggning, Azure Blob Data Reader och CORS utan att falla tillbaka till en hårdkodad äldre snapshot.

Ändringen ger inte skrivbehörighet, kundvisningsrätt eller kommersiellt godkännande för datakällor.

## Polisarkivet – UTF-8 BOM-historikbugg korrigerad och mergad (2026-11-25)

**Rotorsak verifierad:** data/police_events/events.csv skrivs med UTF-8 BOM (utf-8-sig), men scripts/ingest_police_events.py::read_events() läste den som vanlig UTF-8. Det dolda BOM-tecknet i första kolumnnamnet gjorde att befintliga event-ID:n inte hittades. I [Police events archive run #25](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45639053543) rapporterades därför archive_events=500 och changed_or_new_versions=500. Råsegmentet verifierades i Azure med 500 rader, 1 992 823 bytes och SHA-256 7b8701a7c51c8be478ab3d622acd305e24e23b56f2152f45a2905deb242ef879.

**Dataeffekt och avgränsning:** PR [#448](https://github.com/dahlinrobert-lgtm/Skog/pull/448) innehåller en annan 500-posters normaliserad vy än dåvarande main. 30 tidigare ID:n saknades i PR-versionen och 30 nya ID:n tillkom. PR #448 har inte mergats; main-historiken är därför inte ersatt. Azure-råsegmentet för run #25 är bevarat och hashverifierat.

**Korrigering mergad:** PR [#630](https://github.com/dahlinrobert-lgtm/Skog/pull/630) mergades 2026-11-25 med commit fc90d567fa993b60faccc1136afd9213c9f99b69. read_events() använder nu utf-8-sig. Ett regressionstest säkerställer att en befintlig BOM-skriven post behålls vid inkrementell hämtning och att endast nya poster läggs till i råsegmentet. Den befintliga Police event history tests-workflowen kör både historikbyggarens tester och ingestion-regressionen.

**Tester verifierade:** på PR-commit b526673 passerade Police event history builder tests [run 45665135758](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665135758), Snapshot storage tests [run 45665135920](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665135920) och Skogskoll customer UI tests [run 45665135841](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665135841). Efter merge passerade polisarkivets testworkflow [run 45665350499](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665350499), snapshot storage tests [run 45665350619](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665350619) och kundgränssnittstester [run 45665350556](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665350556). GitHub Pages deployment [run 45665349746](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45665349746) passerade.

**Dokumentationsbedömning:** docs/police-events-norrbotten.md och denna handover uppdateras (Documented). docs/SKOGSKOLL_SOURCE_STATUS.md och docs/SKOGSKOLL_DATA_OVERVIEW.md bedöms Assessed – no update required: ingen källåtkomst, rättighet eller dataarkitektur har ändrats.

**Nästa konkreta steg:** invänta nästa schemalagda Police events archive-körning och kontrollera att PR #448 uppdateras från main med tidigare event-ID:n bevarade och nya poster tillagda. Kontrollera även att kandidatutdrag och kvalitetsrapport räknas om från den bevarade normaliserade händelselistan. Merge:a inte PR #448 förrän denna historikjämförelse är verifierad. Bevara Azure-råsegment och kandidater; frånvaro i en API-sida får inte tolkas som borttagning.

## 2026-11-25 – Projektledarsidan visar prioriterad PM-backlogg

PR [#633](https://github.com/dahlinrobert-lgtm/Skog/pull/633) är mergad till `main` med squash-commit `65b62308950323e9e83fa262ea1fec22c30e8422`. Den kompletterar den privata projektledarens read-only inventory med en separat vy för strukturerade PM-uppgifter.

- Collector-förändringen är mergad i privata [skogskoll-project-manager-history PR #73](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/73), merge commit `b21a850e691f964f1a0ed50f7a46162877475ce3`.
- Den privata collectorn läser `docs/PROJECT_BACKLOG.md` från Skog `main`, extraherar PM-avsnitt med uttrycklig prioritet/status/nästa steg och lägger med backloggens blob-SHA i inventory-payloaden.
- Projektledarsidan visar nu PM-ID, titel, prioritet, status och nästa steg i sektionen **Prioriterade utvecklingsuppgifter**. Den visar också källa/commit och markerar dubbla ID:n i stället för att slå ihop uppgifter.
- Backloggen i Skog-repot är fortsatt enda sanningskälla. Ingen parallell task-lista, ny datalagring, ny credential eller direkt GitHub-anrop från webbläsaren har införts.
- Om backloggen inte kan hämtas eller tolkas markeras inventory som `partial`; en saknad uppgiftslista visas inte som en tom/komplett lista.

**Verifierade CI-kontroller före merge:**
- Private collector: [Project manager tests #132](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45666872858) – success.
- Private append-only regression: [Synthetic append-only tests #114](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45666872860) – success.
- Skog Pages: [Website JavaScript syntax #307](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45666813070) – success.
- Skog regression suite: [Snapshot storage tests #562](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45666812959) – success.
- Skog project manager tests: [run #26](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45666813045) – success.

**Inte ännu liveverifierat:** en ny schemalagd inventory-run efter merge, att Azure latest-publiceraren publicerar den nya payloaden, samt att den autentiserade webbläsaren visar den nya uppgiftssektionen. PR-merge och CI bevisar inte detta. Nästa steg är att kontrollera nästa lyckade inventory/publisher-kedja och därefter verifiera sidan efter Microsoft-inloggning.

**Dokumentationsbedömning:** `docs/PROJECT_MANAGER_AGENT.md`, `docs/PROJECT_STATUS.md` och denna handover uppdaterade (Documented). `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedömda Assessed – no update required: ingen datakälla, datatäckning, rättighet eller källinsamling ändrades.

## 2026-11-25 – Skogsstyrelsens generella geodatavillkor verifierade

Skogsstyrelsens officiella sida [Villkor för nyttjande av Skogsstyrelsens geodata](https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/villkor/) kontrollerades 2026-11-25. Den anger att villkoren gäller geodata producerade av Skogsstyrelsen och att dessa, om inget annat anges, är öppna data under CC0 1.0 Universal. Källan rekommenderar attribution till Skogsstyrelsen; attribution är inte ett krav enligt CC0.

Källregistret och rättighetsdokumentationen uppdateras för berörda geodataprodukter. Huvudregeln innebär fri kommersiell användning, bearbetning, lagring och vidare distribution för produkter/lager som faktiskt omfattas. Produktspecifika undantag, tredje parts material samt tekniska konto-/API-/tjänstevillkor ska fortsatt kontrolleras separat. Skogsstyrelsens statistikdatabas omfattas inte av denna geodataregel utan har en separat rättighetsbedömning.

**Nästa steg:** kör källregistervalidering och rapportgenerering i PR-CI. Behåll produkt-/lagerundantag och SIS-produktbeskrivningens särskilda licenssektion som kontrollpunkter; ändra inte kundvisningsstatus eller teknisk åtkomststatus enbart på grund av den generella licenstexten.


## 2026-11-25 – PM-027 live inventory #16 och Samråd-historikens uppföljning

Projektledarrepots manuella read-only inventory [run #16](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45644895332) avslutades `completed/success`. Artifacten granskades enligt projektledarrepots dokumentation.

- Collector rapporterade 3/3 aktiva repositories och 0 insamlingsfel. 75 Python-tester och `node --check dashboard/app.js` passerade i inventory-jobbet.
- Det separata write-enabled alert-jobbet var `skipped`. Inventoryn var read-only; inga källfeatures laddades ned och inga källrepon skrevs till.
- Samråds senaste försök i artifacten var [run 45643662888](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45643662888), `completed/success`, via `.github/workflows/collect-samrad.yml`.
- Samråds senaste kompletta snapshot i just denna inventory var `manifest_complete_for_configured_scope`, fångad 2026-11-25 15:19:17.791517 UTC. Den omfattade 21 poster inom konfigurerat 10 km-scope: 0 punkter, 9 linjer och 12 polygoner. Alla tre lager hade uttömd paginering och noll saknade/felaktiga geometrier. Vid inventoryn fanns 25 daterade snapshotfiler i Git-trädet.
- `source_total_reconciled=false`: manifestet styrker endast det konfigurerade pilotområdet, inte nationell täckning eller avstämning mot källans totala antal. Manifestets SHA-256 är ett källpåstående och omräknades inte av adaptern.

**Efter inventory #16:** Skog [Collect Samråd pilot snapshots #48](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45656496498) skapade [data-PR #619](https://github.com/dahlinrobert-lgtm/Skog/pull/619), som mergades 2026-11-25 16:44:28 UTC. Aktuellt manifest på Skog `main` anger nu snapshot `data/samrad_snapshots/samrad_20261125T164133Z.json.gz`, fångad 16:41:33.484740 UTC, och snapshotarkivet omfattar 27 daterade filer. Inventory #16 föregår denna merge; en ny projektledarinventory behöver därför verifiera att den uppdaterade manifestversionen har slagit igenom i read model/Azure-publiceringen.

**Samråd event bundle – separat uppföljning:** den nuvarande härledda bundle-versionen innehåller tre Samråd source runs och 21 Samråd-händelser, medan arkivet har 27 daterade snapshotfiler. Två tidigare observerade objekt (`lines:47112` och `lines:47734`) saknas i aktuell bundle. Detta är ännu inte bevisat vara ett implementeringsfel; äldre snapshots kan falla utanför den strikta fullständighetsgrinden. Read-only-utredningen är registrerad i [issue #639](https://github.com/dahlinrobert-lgtm/Skog/issues/639). Råsnapshotarna är fortsatt sanningskälla och får inte ändras eller ersättas.

**PM-027-status:** den befintliga projektledarens read-only adapter är live-verifierad för avverkningsanmälningarnas Gräsmyr 10 km-manifest och Samråds konfigurerade pilotmanifest. PM-027 som helhet är inte färdig: rapportering för alla registrerade källor och separata produkter/lager, kadensbaserad freshness och fullständiga evidenslänkar återstår. Ingen ny collector eller parallell historikmodell ska införas.

**Dokumentationsbedömning:** Documented – live inventory #16, efterföljande Samråd-run #48/PR #619 och den separata historikfrågan är registrerade. Källstatusrapporten behöver inte ändras: ingen teknisk åtkomst, kommersiell användning eller kundvisningsrätt ändras av denna read-only verifiering.


## 2026-11-25 – PM-031: Samråd-arkivet inventerat, äldre format kan inte styrkas kompletta

Read-only-inventeringen i [PR #643](https://github.com/dahlinrobert-lgtm/Skog/pull/643) kördes framgångsrikt i [inventory run #3](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45676077199). Test, Python-kompilering, inventering och artifact-uppladdning passerade. Artifactet klassificerar samtliga 27 daterade gzip-snapshots:

- 3 snapshots är godkända av den oförändrade produktionsfunktionen `samrad_snapshot_is_complete()`: 2026-11-25 15:19:17, 16:03:41 och 16:41:33 UTC.
- 24 äldre snapshots (2026-11-02–2026-11-22) saknar per lager räknarfälten `records_outside_scope`, `records_missing_geometry` och `records_geometry_error`; 0 filer är oläsbara.
- De tre godkända snapshotsens 21 stabila `layer:ObjectId`-identiteter och 21 case/event-identiteter matchar event bundle exakt. Inga extra eller saknade ID:n finns inom den nuvarande fullständighetsgrinden.

**Varför äldre snapshots inte kan godkännas retroaktivt:** collector-koden i commit [3dd2fd0](https://github.com/dahlinrobert-lgtm/Skog/commit/3dd2fd0389e920d85bc7cd28acf6abcfca14be9d), som föregår de äldre arkiven, hoppade tyst över features utan geometri och features där geometriprojektionen gav fel. Den sparade endast antal hämtade poster, antal poster inom scope och sidantal. Den registrerade inte hur många poster som hoppats över på grund av saknad geometri eller geometrifel. De äldre snapshotarnas `status=success` bevisar därför att hämtningen/pagineringen lyckades, inte att alla features i envelope kunde klassificeras. Att de features som faktiskt sparades har stabila ID:n och giltiga geometrier bevisar inte att inga andra features tappades före arkivering.

Arkivet innehåller tre äldre Samråd-ärenden som saknas i dagens bundle, men som **inte** får återföras som verifierade historiska händelser utan fullständighetsbevis:
- `S 9480-2021`: `lines:28009` och `lines:47112`, observerade i 24 äldre snapshots från 2026-11-02 till 2026-11-22.
- `S 9481-2021`: `lines:28726` och `lines:47734`, observerade i samma 24 snapshots.
- `S 8667-2021`: `lines:49488`, observerad i fyra snapshots den 2026-11-02.

**Beslut:** ändra inte `build_harvest_event_bundle.py`, lätta inte på fullständighetsgrinden och skapa ingen kompatibilitetsadapter som antar att saknade räknare är noll. Bevara de 24 originalarkiven oförändrade och håll dessa äldre observationer utanför frånvarobedömning och verifierad eventhistorik. PM-031:s inventering är genomförd; frågan om äldre snapshots kan styrkas via annan bevarad körningsevidens är fortfarande öppen. Om sådan evidens saknas ska de förbli exkluderade.

Detta ändrar inte källtäckning, rättighetsstatus, kommersiell användning, kundvisning eller aviseringar.


## 2026-11-25 – PM-027 read-only inventory #17 verifierade Samråd-manifestet

Projektledarens [read-only inventory #17](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45674653249) slutfördes `completed/success`. Artifactet verifierar att `skogsstyrelsen.samrad` nu har `latest_complete_snapshot.status=manifest_complete_for_configured_scope` och pekar på `data/samrad_snapshots/samrad_20261125T164133Z.json.gz` med manifest `data/samrad_latest_manifest.json`. Lager: points 0/0, lines 18 hämtade i envelope varav 9 inom scope och 9 utanför, areas 14 hämtade varav 12 inom scope och 2 utanför. Pagineringen är uttömd och manifestet anger noll saknade/felaktiga geometrier. Arkivinventeringen rapporterar 27 daterade snapshots, fortfarande endast metadata-inventering.

Detta verifierar PM-027:s konkreta manifest/read-model-uppföljning efter PR #619. Begränsningarna kvarstår: `source_total_reconciled=false`, ingen nationell täckning hävdas och manifestets SHA-256 har inte räknats om av projektledarens adapter. PM-027:s bredare mål – full käll-/produkt-/lagerkoppling, kadens/freshness och full evidenslänkning för alla registrerade källor – är fortsatt öppet.


## 2026-11-25 – PM-031: read-only loggranskning av historiska Samråd-körningar

Efter PR [#643](https://github.com/dahlinrobert-lgtm/Skog/pull/643) och inventory run [#3](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45676077199) granskades bevarade GitHub Actions-jobbloggar för Samråd samt aktuell körningshistorik.

- Inventory-jobbet passerade alla steg, inklusive test av diagnostiken, Python-kompilering, inventering mot oförändrad produktionsgrind och artifact-uppladdning. Artifact: `samrad-snapshot-inventory-45676077199`, SHA-256 `678e8b3a41e11e6e8a928b5b8e0acb0a66ed34f31933d934f5e79fabb55cbf20`, tidsbegränsad till 2026-12-25.
- Actions-loggen för Samråd run [45037391885](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45037391885), 2026-11-22, redovisar endast `records_fetched_in_envelope`, `records_in_scope` och `pages`. Samma begränsning gäller run [45454250815](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45454250815), 2026-11-24. Loggarna styrker lyckad hämtning/paginering i de konfigurerade lagren men redovisar inte poster som hoppats över på grund av saknad eller felaktig geometri.
- Från run [45648958631](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45648958631), 2026-11-25 15:49 UTC, finns explicita `records_outside_scope`, `records_missing_geometry` och `records_geometry_error` för alla tre lager. De tre snapshots som redan godkänts av PM-031-grinden (15:49, 16:03 och 16:41 UTC) förblir de enda verifierade historikobservationerna i inventeringen.
- Run [45664696922](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45664696922), 2026-11-25 17:26 UTC, passerade insamling, bundle-byggande och skapade data-PR [#629](https://github.com/dahlinrobert-lgtm/Skog/pull/629). Den loggade 28 arkiverade Samråd-snapshots, 21 Samråd-observationer samt kompletta per-lagerräknare. Run #48 skapade data-PR [#619](https://github.com/dahlinrobert-lgtm/Skog/pull/619) med snapshoten 16:41 UTC. PM-027 inventory [#17](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45674653249) verifierade manifestet från 16:41 UTC; inventoryn föregår run #49/PR #629 och verifierar alltså inte den senare publiceringen.
- Den åtkomliga run-listan exponerade fyra Samråd-körningar; separata artifacts för de äldre insamlingarna hittades inte. Detta är inte bevis för att inga andra historiska loggar/artifacts någonsin funnits, men ingen oberoende fullständighetsevidens har hittats som täcker geometriutvärderingen för de äldre arkiven.

**Slutsats/beslut:** PM-031:s konservativa beslut står fast. De 24 äldre arkivfilerna ska bevaras oförändrade och förbli exkluderade från verifierad eventhistorik och frånvarobedömning. Äldre `status=success`, sidantal och giltigheten hos sparade geometrier får inte användas som ersättning för de saknade räknarna. De tre äldre ärendegrupperna `S 9480-2021`, `S 9481-2021` och `S 8667-2021` får inte återföras utan oberoende fullständighetsbevis.

**Nästa konkreta steg efter merge:** kör/avvakta en ny PM-027 read-only inventory efter Skog PR #629 och verifiera att projektledarens read model pekar på manifestets snapshot `samrad_20261125T172634Z.json.gz`. Inventory #17 föregick denna publicering och räknas inte som verifiering av den. Håll PM-031:s beslut om de 24 äldre arkiven oförändrat om ingen ny oberoende fullständighetsevidens tillkommer.

**Dokumentationsstatus:** Documented i denna handover. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms Assessed – no update required: den här åtgärden är en evidens-/logggranskning; den ändrar inte källa, datatäckning, källrättighet, insamlingsflöde eller kundvisningsstatus.


## 2026-11-25 – Samråd snapshot från run #49 publicerad (PR #629)

Samråd data-PR [#629](https://github.com/dahlinrobert-lgtm/Skog/pull/629) är mergad till `main` 2026-11-25 20:22:32 UTC. Merge commit: `29f0d38a649584e308d0a04391a44d0f2f15176d`. GitHub compare bekräftar att denna merge commit är identisk med aktuell `main`.

Manifestet i `main` pekar nu på snapshoten `data/samrad_snapshots/samrad_20261125T172634Z.json.gz`, kontrollerad 2026-11-25 17:26:34.567268 UTC. Snapshotstorlek 400 407 byte; SHA-256 `c65398097cfa2fc9881457790a31432ea41984dbd67537adad627bf3103125ff`. Status `success`, `complete_for_configured_scope`; alla tre lager har uttömd paginering och noll saknade/felaktiga geometrier. Inom Gräsmyr-pilotens oförändrade 10 km-scope: points 0, lines 9 (18 hämtade i envelope, 9 utanför scope), areas 12 (14 hämtade i envelope, 2 utanför scope). `source_total_reconciled=false`; detta är inte nationell fullständighet eller avstämning mot källans total.

Run [45664696922](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45664696922) passerade insamling, bundle-byggande och skapande av PR #629. Workflowet rapporterade 28 arkiverade Samråd-snapshots och 21 Samråd-observationer/händelser i event bundle. Originalarkiv och den befintliga event-bundle-byggaren återanvänds; ingen parallell historikmodell införs.

**Kvar att verifiera:** PM-027 inventory #17 föregick PR #629 och verifierar därför inte den nya manifestversionen. Kör/avvakta nästa read-only inventory och kontrollera att den refererar till snapshoten 17:26:34 UTC. Ingen ändring av PM-031-beslutet om 24 äldre snapshots. Kommersiell användning, kundvisning och vidare distribution förblir separata och inte godkända genom denna tekniska publicering.


## 2026-11-25 – PM-027 read-only inventory #18 verifierade Samråd PR #629 i read model

Projektledarens manuellt startade [read-only inventory #18](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45697167605) avslutades `completed/success` 2026-11-25 20:40:43 UTC. Artifacten `project-manager-inventory-45697167605` granskades direkt. Collector-jobbet och dess teststeg passerade; 3/3 registrerade repositories insamlades utan fel. Det separata skrivaktiverade alert-jobbet var `skipped`, i enlighet med read-only-körningen.

För `skogsstyrelsen.samrad` pekar projektledarens read model nu på samma snapshot som publicerades genom Skog PR [#629](https://github.com/dahlinrobert-lgtm/Skog/pull/629):

- Snapshot: `data/samrad_snapshots/samrad_20261125T172634Z.json.gz`, fångad 2026-11-25 17:26:34.567268 UTC.
- Manifest: `data/samrad_latest_manifest.json`.
- Git blob för snapshot: `e9d70e578617c8b13e6946afb59890995213df6c`; manifestblob: `79e06dfe7b4133173a6b54ac393a78e52b10a28f`.
- Manifestets påstådda SHA-256: `c65398097cfa2fc9881457790a31432ea41984dbd67537adad627bf3103125ff`; adaptern räknade inte om kontrollsumman.
- 28 daterade snapshots inventerade (metadata-only).
- Lagerstatus: points 0 inom scope; lines 9 inom scope (18 hämtade i envelope, 9 utanför); areas 12 inom scope (14 hämtade, 2 utanför). Pagineringen är uttömd och alla lager rapporterar noll saknade/felaktiga geometrier.

Detta sluter den tidigare öppna verifieringspunkten efter PR #629: inventory #17 pekade ännu på snapshoten 16:41 UTC, medan inventory #18 nu verifierar 17:26-snapshoten i projektledarens read model. Samråds scope är fortfarande Gräsmyr-pilotens 10 km; `source_total_reconciled=false`, vilket inte styrker nationell täckning eller avstämning mot källtotal.

**Säkerhets-/rättighetsgräns:** artifacten anger `read_only=true`, `source_feature_data_downloaded=false` och `source_repository_writes=false`. Inventeringen ändrar inte kommersiell användning, kundvisning eller vidare distributionsrätt. PM-031:s beslut om att bevara och fortsatt exkludera 24 äldre snapshots utan fullständighetsevidens står oförändrat.

**Dokumentationsbedömning:** Documented – inventory #18:s liveverifiering registrerad här. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms Assessed – no update required i sak: ingen källåtkomst, rättighet, insamlingskadens eller datatäckning har ändrats. Nästa PM-027-arbete är fortsatt breddning av käll-/produkt-/lagerkoppling, freshness/kadens och evidenslänkning; PM-027 som helhet är inte färdig.


## 2026-11-25 – PM-027 första evidensbaserade driftprofilen för Samråd

Projektledarrepot har nu en första källspecifik driftprofil för `skogsstyrelsen.samrad`, införd i PM [PR #77](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/77), mergad 2026-11-25 20:55:23 UTC med merge commit `d8fc62ac708cc58dd52eafec021cd65c77e6fcfa`.

Profilen binder källan till exakt workflow `.github/workflows/collect-samrad.yml` och tre lyckade kompletta körningar: [45648958631](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45648958631), [45656496498](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45656496498) och [45664696922](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45664696922). Samtliga delar `scope_hash=9c597758897297d34eb6ae733e56c5998587de4ff478fd8e82ae1a510dcfa76a` och visar uttömd paginering samt noll saknade/felaktiga geometrier i de tre lagren. Profilens driftklass är `pilot_recurring`, inte produktion. Omfattningen är fortsatt endast Gräsmyr 10 km; `source_total_reconciled=false`.

Verifierad klientkonfiguration är sidstorlek 300, timeout 90 sekunder, sekventiell hämtning, ett jobb åt gången och säkerhetstak 1 000 sidor per lager. Ingen explicit retry/backoff finns i collectorn. Minsta anropsintervall och leverantörens rate limits/maxRecordCount är okända; därför är riskbedömningen partiell och `risk_assessed=false`. Dessa värden ska inte fyllas med antaganden.

PR #77:s första CI-körning föll på att ett befintligt enhetstest använde en syntetisk källregisterpayload samtidigt som den nya globala profilen lästes in. Testet isolerades genom att mocka profilladdaren i just den syntetiska parserkontrollen. Efter korrigeringen passerade [Project manager tests #143](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45699459266) med 79 tester och dashboardens JavaScript-syntaxkontroll samt [Synthetic append-only tests #121](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45699459216). PR #77 mergades därefter.

**Dokumentationsbedömning:** Documented i projektledarrepots profilregister och drift-/PM-dokumentation. Här är ändringen noterad i handover. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms Assessed – no update required: ingen källa, insamling, källtäckning, rättighet eller kundvisningsstatus har ändrats i Skog.

**Nästa konkreta PM-027-steg:** fortsätt inventera exakta workflowkopplingar och kompletta jämförbara körningar för övriga registrerade source_id och separata produkter/lager. Skapa profiler en källa i taget endast när underlaget räcker; bygg därefter kadensbaserad freshness. Autentiserad dashboard-rendering är fortfarande inte liveverifierad och PM-027 som helhet är inte färdig.


## 2026-11-25 – PM-027 kopplar nationell Älgdata och senaste snapshot

Projektledarrepot har efter Samråd-profilen lagt till en exakt workflowkoppling för `lansstyrelsen.elk_harvest_statistics` i PM [PR #78](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/78), mergad 2026-11-25 21:00:03 UTC (merge commit `f1ecda4ba73cb934bb92defd7f84d308a68c7ae8`). Den pekar på `dahlinrobert-lgtm/alg-grasmyr/.github/workflows/daily-national-afo-avskjutning.yml`.

Profilen har nationellt scope men klassificeras endast som `baseline`: ett komplett Actions-run-ID, [43952789564](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/43952789564), är separat verifierat. Aktuell alg-grasmyr main-dashboard visar däremot `snapshot_date=2026-11-25`, 129/129 aktuella ÄFO och 129/129 med data. Dashboardblobben är `58ec8e1d66170b9bb97400d8d9501490940332de`; bot-commit [62ece755](https://github.com/dahlinrobert-lgtm/alg-grasmyr/commit/62ece75597cb249f6ab618ad12a9a1aec3c46650) uppdaterade snapshoten. Dashboardraderna summerar till `ShotTotal=58 016` och `AssignedTotal=79 727`. Commit-evidens har inte omvandlats till ett påhittat Actions-run-ID.

Riskbedömningen är partiell: insamlingen sker sekventiellt, med upp till tre försök per AFO på en ny Playwright-sida och 90 minuters workflow-timeout. Leverantörens rate limits och minsta anropsintervall är inte verifierade. Profilen uppgraderas inte till återkommande/produktion förrän två kompletta jämförbara run-ID:n är länkade.

**Källregisteruppdatering:** PR:n uppdaterar Älgdata-postens senaste verifieringsdatum och senaste dashboardevidens. Rättighetsstatusen för publicerad statistik ändras inte. JaktAdm-gränsgeometrier är fortsatt en separat produkt med egna villkor.

**Nästa steg:** koppla de exakta Actions-run-ID:na för de senare kompletta Älgdata-snapshotsen och fortsätt PM-027:s käll-/produkt-/lagerkartläggning. PM-027 är inte färdigt.


## 2026-11-25 – korrigering av automatiserad source-status-PR-bas

Vid uppdateringen av Älgdata-källposten skapade workflowet `.github/workflows/validate-source-registry.yml` felbaserade automatiska rapport-PR:er eftersom `create-pull-request` saknade explicit `base: main`. PR [#637](https://github.com/dahlinrobert-lgtm/Skog/pull/637) och [#652](https://github.com/dahlinrobert-lgtm/Skog/pull/652) hade felaktiga basgrenar och stängdes som dubbletter; de mergades inte. Den korrekta rapport-PR:n [#571](https://github.com/dahlinrobert-lgtm/Skog/pull/571) hade `main` som bas och mergades 2026-11-25 21:03:27 UTC (merge commit `035cecb0e2b520a9a9b7dd558a3a47c7f6bb7965`). Den uppdaterade genererade rapporten är nu i `main`, med Älgdata senast verifierad 2026-11-25.

Fixgren `fix/source-status-report-pr-base-main` lägger till explicit `base: main` i actionens `with`-block. Syftet är att framtida push-utlösta rapportuppdateringar alltid skapar/uppdaterar PR mot auktoritativ `main`, inte mot den branch som råkade utlösa workflowet. PR #653 [fix: target source status report PRs at main](https://github.com/dahlinrobert-lgtm/Skog/pull/653) är nu mergad 2026-11-25 21:05:00 UTC med merge commit `b1c5515dad22b04c3ae3c67e13cbe8eb56a21613`. Den mergade main-workflowfilen har verifierat `base: main`. PR-kontrollerna passerade: [Validate source registry #111](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45700918422) (källregistervalidering och rapportbygge) samt [Skogskoll customer UI tests #296](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45700918400).

**Dokumentationsstatus:** Documented. Inga källdata, rättigheter eller kundvisningsinställningar ändrades.

## 2026-11-25 – PM-027 inventory #19 och Älgdata två-run-verifiering

Projektledarrepots read-only inventory [#19](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45702596272) kördes efter merge av PR [#78](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/78), från commit `f1ecda4ba73cb934bb92defd7f84d308a68c7ae8`, och avslutades `completed/success`. Artifact ID `15062948640` (SHA-256 `b18f0a53bf18b6de4d55f3d86e77ed583b5944fd0416faf0cb7c78650692d9b1`) granskades:

- 3/3 registrerade repositories lyckades, 0 insamlingsfel; 52 source_id, varav 15 med operations-block och 37 utan.
- Två kuraterade driftprofiler fanns i read model. Python-tester och dashboardens JavaScript-syntaxkontroll passerade; write-enabled alert-jobbet var `skipped`.
- Artifactens säkerhetsfält: `read_only=true`, `no_repository_writes=true`, `no_secrets_in_output=true`.

Inventory #19 verifierade att Älgdata-profilen från PR #78 var inläst, men den visades då som `baseline` eftersom endast ett komplett Actions-run-ID var länkat. En separat granskning av run-jobb och båda arkiverade artifacten styrker nu två jämförbara kompletta körningar:

- [Run 43952789564](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/43952789564): samtliga snapshotsteg passerade; artifact ID `14271201667`; 129 daterade ÄFO-filer för 2026-11-16, 129 unika ID:n, report 3, säsong 2026/2027, aktuella gränser och 3 237 råa ÄJO-rader.
- [Run 45273303393](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45273303393): samtliga snapshotsteg passerade; artifact ID `14867345764`; 129 unika ÄFO-filer för 2026-11-23 (artifacten innehåller också den separata tidigare batchen 2026-11-21), samma report/säsong/gränsläge och 3 237 råa ÄJO-rader.
- Jämförelse 2026-11-16 mot 2026-11-23: exakt samma 129 ÄFO-ID:n, 0 saknade och 0 tillkomna. Gemensam jämförbarhetsnyckel: `report=3|season=2026/2027|boundary=current|afo_count=129`.

PM-repo PR [#79](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/79) lägger till run `45273303393` i den befintliga profilen och ändrar `rollout_stage` från `baseline` till `pilot`. Efter merge ska read model klassificera Älgdata som `pilot_recurring` vid nästa inventory. PR:n är ännu inte mergad vid denna dokumentationsuppdatering. Ingen production-status hävdas: leverantörens rate limits och minsta anropsintervall är fortsatt okända och riskbedömningen är partiell.

Den 2026-11-25-dashboard som dokumenteras via bot-commit `62ece75597cb249f6ab618ad12a9a1aec3c46650` är separat commit-/snapshot-evidens; dess exakta Actions-run-ID är inte fastställt och ska inte härledas från committen.

**PM-027-status:** två profiler finns i projektledarrepots main (Samråd och Älgdata), men full daglig käll-/produkt-/lageröversikt, freshness per kadens och full evidenslänkning återstår. Källstatusrapporten visar 52 källor, 15 med operations-block och 37 utan; 13 av de 15 operativa källorna saknar ännu driftprofil.

**Nästa konkreta steg:** efter merge av PM-repo PR #79, kör en ny read-only inventory och verifiera att Älgdata visas som `pilot_recurring`. Därefter kartlägg Trafikverkets två separata produkter – Miljöwebb Landskap och NVDB Viltolyckor – mot befintligt workflow och manifest. Run #33 är en första komplett baseline inom Gräsmyrs ungefärliga 75 × 75 km-envelope, inte nationell täckning eller en historisk jämförelseserie. Skapa separata produktprofiler först när lager-/scope-evidensen är genomgången. Rättigheter för respektive produkt/lager förblir separata och villkorade.

**Dokumentationsstatus:** Documented för inventory #19 och de två verifierade Älgdata-körningarna. PM-027 som helhet är fortfarande öppen.

### Trafikverket – produktionskörning #33 och arkiverad snapshot verifierade (2026-11-25)

Efter merge av [PR #659](https://github.com/dahlinrobert-lgtm/Skog/pull/659) kördes [Trafikverket weekly geodata snapshots #33](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340) manuellt från `main` (commit `83934a18b28e118149a9d0788021cf8eaaa0d489`). Samtliga workflowsteg passerade: installation av pyproj, Python-syntaxkontroll, insamling, skärpt fullständighetskontroll, artifact-uppladdning och skapande av data-PR.

Manifestet `data/trafikverket/snapshots/2026-11-25/manifest.json` anger `status=complete`, 34 lager och 7 674 hämtade features inom pilot-envelope: 27 Miljöwebb-lager och 7 NVDB Viltolyckor-lager. NVDB-lager-ID:n 3, 5, 7, 9, 11, 13 och 15 finns med; varje lagers hämtade antal matchar antalet källobjekt-ID:n enligt workflowets kontroll. Miljöwebb 2 396 features + NVDB Viltolyckor 5 278 = 7 674 totalt. Täckningen gäller endast Gräsmyrs ungefärliga 75 × 75 km-envelope, inte nationellt.

Manifestets SHA-256 är `a80b7561de79c376ef1d6598d3f486d686f9d025cf943c34cbda5617fbe14b04`. Artifact `trafikverket-geodata-snapshot-45705661340` (ID `15063734584`) är 11 986 466 byte, SHA-256 `877e917b1bb18109a42966f1a2b37a239e1dbcb174acb47818211e3be9dad345`, med retention till 2027-02-23 21:35 UTC. Den daterade arkiveringen mergades via [data-PR #660](https://github.com/dahlinrobert-lgtm/Skog/pull/660) 2026-11-25 21:44:22 UTC, merge commit `5ed1a0b62373b1e78a2f994f384a5e4c24506ef0`. Snapshoten har verifierats direkt i aktuell `main`: manifestet och katalogerna `miljowebb/` och `viltolyckor/` finns under `data/trafikverket/snapshots/2026-11-25/`. PR:n publicerade manifest och 34 lagerfiler (35 filer totalt).

**Dokumentationsstatus:** run #33 verifierar en fullständig teknisk körning och fungerande data-PR-automation. PR #660 är mergad och snapshoten är verifierad i `main`. Detta är en första arkiverad baslinje, inte ännu en jämförbar historikserie. Nästa tekniska steg är att verifiera nästa kompletta veckokörning och jämföra manifest och stabila objekt-ID:n. Första baslinjen får inte skapa historiska frånvarolarm. Källornas kommersiella användning, kundvisning, historisk lagring och redistribution är oförändrat separat villkorade; teknisk körning/arkivering innebär inget nytt rättighetsbesked. Ingen kundavisering aktiveras.


## 2026-11-25 – PM-027 Trafikverket-profiler mergade

Projektledarrepots [PR #80](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/80) mergades 2026-11-25 22:13:35 UTC med merge commit `7450cd72f66a13544289d01e7afaf38f60aab4f5`. Den lägger till separata profiler för `trafikverket.miljoweb_landskap` och `trafikverket.nvdb.wildlife_collision_frequency`, båda kopplade till befintligt workflow `.github/workflows/trafikverket-weekly-snapshots.yml`. Workflowmetadata uppdaterar den befintliga workflow-posten i stället för att skapa en dubblett; main innehåller åtta workflowposter med åtta unika repository/workflow_path-kombinationer.

Båda Trafikverket-profilerna har en komplett baseline-observation från run [45705661340](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340): Miljöwebb 27 lager/2 396 features och NVDB Viltolyckor 7 lager/5 278 features i Gräsmyr-envelope. De är separata produkter trots gemensamt workflow. De är fortfarande baseline; en andra komplett körning med identiskt envelope och lager-ID:n krävs innan återkommande pilotdrift kan hävdas. Området är inte nationellt och source total är inte verifierad. NVDB Viltolyckor är aggregerad frekvens per väglänk, inte individuella olyckor.

Älgdata-profilen i PM-repot har två länkade kompletta run-ID:n (43952789564 och 45273303393) med samma 129 ÄFO-jämförbarhetsnyckel. Dokumentationen i PM-repot beskriver den som `pilot_recurring`, men en ny read-only inventory efter PR #79/#80 behövs fortfarande för att verifiera den faktiska publicerade read model-statusen. Denna inventory har inte verifierats i denna uppdatering; inga nya inventory-run-ID:n antas.

**Nästa konkreta steg:** granska nästa schemalagda read-only Project Manager inventory efter merge av PM PR #79/#80 och Skog PR #667. Workflowet triggas var femte minut och schedule-gaten samlar in var femte minut under vardagar 16:00–01:00 och helger 10:00–01:00 (Europe/Stockholm), samt varje hel timme utanför dessa fönster. Verifiera i artifacten att Älgdata klassas `pilot_recurring`, att båda Trafikverket-profilerna finns som baseline och att source-/workflow-kopplingarna visas korrekt. Därefter invänta nästa veckovisa kompletta Trafikverket-snapshot och jämför varje produkt separat mot sin baseline. PM-027 som helhet är fortfarande öppen.

**Dokumentationsstatus:** Documented. Ingen ny collector, snapshotmodell, rättighetsstatus eller kundvisningsrätt har införts.


## 2026-11-25 – PM-027 read-only inventory #20 verifierad

Projektledarens [inventory #20](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45712438496) kördes manuellt från PM-repots main-commit `7450cd72f66a13544289d01e7afaf38f60aab4f5` och avslutades `completed/success`. Artifact `project-manager-inventory-45712438496`, ID `15068286448`, SHA-256 `09f860249d451b64f581c4ce67983e66a425e2d4cb5b0f3b91a070173fa80212`, granskades. Payloadens observationstid är `2026-11-25T22:21:10.992689Z`: 3/3 aktiva repositories, 0 fel, status `success`. Collector-tester, JS-syntax, tokenkontroll, insamling och artifact-upload passerade; det skrivande central-alert-jobbet var `skipped`. Security assertions: read-only, inga repository writes och inga secrets i output.

Read model bekräftar:
- Samråd: `pilot_recurring`, 3 jämförbara kompletta körningar.
- Länsstyrelsernas Älgdata: `pilot_recurring`, 2 jämförbara kompletta nationella körningar med 129 ÄFO.
- Trafikverket Miljöwebb Landskap: `baseline`, 1 komplett körning, 27 lager/2 396 features.
- Trafikverket NVDB Viltolyckor: `baseline`, 1 komplett körning, 7 lager/5 278 features.

PM-backloggen lästes in (10 uppgifter) men innehåller fortfarande duplicerade PM-ID:n PM-023, PM-024 och PM-027. Inventeringen slår inte ihop dessa automatiskt.

**Adapterlucka:** artifactens `source_snapshot_evidence` för Skog innehåller fortfarande endast avverkningsanmälningar och Samråd. Älgdata samt de två Trafikverket-profilerna saknar därmed ännu adapterfält för senaste försök/snapshotinventering. Profilklassningarna ovan kommer från source registry och driftprofiler, inte från en full snapshotadapter för respektive produkt. Ingen ny collector eller historikmodell ska byggas; nästa tekniska steg är att utöka den befintliga read-only adaptern med exakta workflowkopplingar och manifest-/dashboardmetadata för dessa tre source_id, och testa fail-closed.

**Nästa konkreta steg:** utöka befintlig `scripts/source_snapshot_adapters.py` och dess tester i projektledarrepot. Älgdata ska behålla skillnaden mellan dashboard/blob-evidens och exakt Actions-run-ID. Trafikverkets två tjänster ska valideras separat mot samma manifest men respektive lager-ID och featuretotal. Metadata-only; inga GeoJSON-featurecollections ska hämtas. Därefter kör ny inventory och granska artifacten.

PM-027 är fortsatt P0 och inte färdig.


## 2026-11-26 – Kungjort API transport-retry fix mergad
Kungjort Azure-synkronisering [run #127](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45834845260) misslyckades efter att två ändringssidor hade arkiverats. Azure OIDC-inloggningen lyckades; felet var `http.client.RemoteDisconnected: Remote end closed connection without response` från Kungjort-API:t vid nästa anrop. Den befintliga klienten återförsökte HTTP 429/5xx men inte tillfälliga transportfel.

PR [#675](https://github.com/dahlinrobert-lgtm/Skog/pull/675) mergades 2026-11-26 16:45:57 UTC med merge commit `af012f63bc81993d8c9cdf4f578aa5ea79827610`. Ändringen i `scripts/sync_kungjort_azure.py` återförsöker nu `urllib.error.URLError`, timeout och anslutningsfel (inklusive RemoteDisconnected och connection reset), med högst sju försök och exponential backoff. Vanliga HTTP-klientfel återförsöks inte. Efter uttömda transportförsök avbryts körningen; ingen sida hoppas över.

Regressionstester lades till i `tests/test_kungjort_azure_sync.py` för RemoteDisconnected följt av framgång, connection reset, timeout och sju uttömda försök. PR-kontrollerna passerade:
- [Kungjort Azure Sync #128](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45861545510) – success.
- [Snapshot storage tests #593](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45861545514) – success.

Azure-arkivets schema, rådata, blobnamn och cursor-/checkpointordning ändrades inte. Varje sida arkiveras och integritetsverifieras fortfarande innan dess fortsättningscursor sparas. Om ett anrop misslyckas efter alla försök avbryts körningen utan att flytta cursor för den sidan.

**Verifieringsgräns:** PR-kontrollerna verifierar kod och tester, men ingen schemalagd/live Azure-synkronisering efter merge har ännu verifierats. Run #127 är fortfarande den senaste observerade schemalagda körningen i den kontrollerade workflowhistoriken. Nästa konkreta steg är att granska nästa schemalagda körning: kontrollera om den slutförs, antal arkiverade sidor, cursorförflyttning och att inga befintliga batcher skrivs över. Om den misslyckas ska felorsaken granskas innan någon manuell cursorändring eller återställning övervägs.

**Dokumentationsstatus:** Documented i denna handover och i [Kungjort Azure-sync runbook](data-sources/kungjort-azure-sync.md). `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms Assessed – no update required: ingen källtäckning, rättighetsbedömning, kommersiell användning eller kundvisningsstatus har ändrats. Teknisk åtkomst/arkivering innebär inte ett nytt rättighetsbesked.


## 2026-11-26 – PM-027 inventory #25: fem adapterposter verifierade

Projektledarens [read-only inventory #25](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45866881837) kördes manuellt 2026-11-26 17:20 UTC från PM-repots main-commit `23c685b9c79ab26c8919966e54af4965d8c494ca` (efter merge av PR #81 och #82) och avslutades `completed/success`. Artifact ID `15141206837`, 23 288 byte, GitHub-artifact digest `sha256:d055bee4f6e4a163e7536ca2b2a9e7434c78eacef365c02e6fe10849cfd1604b`; payloadens observationstid `2026-11-26T17:20:40.449164Z`. 3/3 repositories lyckades, 0 insamlingsfel. Collector-tester, dashboard-JavaScript, tokenkontroll, insamling och artifact-upload passerade. Skrivande central-alert-jobb var `skipped`. Säkerhetsfält: `read_only=true`, `source_feature_data_downloaded=false`, `source_repository_writes=false`, `no_secrets_in_output=true`.

Skogs `source_snapshot_evidence` har fem separata metadata-only-poster:
- Avverkningsanmälningar: senaste kompletta manifest/snapshot är fortsatt Gräsmyr 10 km-pilotens snapshot 2026-11-22 med 165 poster. Senaste attempt som adaptern hittar är run `43881404640` med conclusion `failure`; det ändrar inte statusen för den separat validerade kompletta snapshoten.
- Samråd: senaste attempt [run `45864838781`](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45864838781) är completed/success. Senaste kompletta snapshot är 2026-11-25 inom konfigurerat 10 km-scope; punkt 0, linje 9 och område 12. Inventeringen innehåller 28 daterade snapshots. Källtotal och nationell täckning är inte verifierade.
- Älgdata: senaste attempt [run `45837084941`](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45837084941) är completed/success. Dashboard 2026-11-26: report 3, säsong 2026/2027, `boundary_mode=current`, 129/129 ÄFO och 129 daterade filer för dashboarddatumet. Adaptern anger `source_run_id=null`; inget run-ID härleds från commit.
- Trafikverket Miljöwebb Landskap: separat post validerar manifestet 2026-11-25 för tjänstnyckel `miljowebb`, 27 lager och 2 396 features.
- Trafikverket NVDB Viltolyckor: separat post validerar samma manifest för tjänstnyckel `viltolyckor`, lager-ID 3, 5, 7, 9, 11, 13 och 15, sju lager och 5 278 features. Värdena avser aggregerad olycksfrekvens per vägsegment, inte enskilda olyckor.

**Kvarstående Trafikverket-avvikelse:** båda produktposternas `latest_complete_snapshot` är `manifest_complete_for_product_pilot_scope`, men `latest_attempt` är `unknown`. Adaptern anger att `.github/workflows/trafikverket-weekly-snapshots.yml` saknas i GitHub Actions workflow inventory trots att YAML-filen finns i Skogs `main`. PR #82 gör felorsaken explicit och testad. Inget Actions-run-ID har konstruerats från manifest- eller commit-evidens. Utred varför workflowet saknas i Actions-registret innan ett latest-attempt-run-ID rapporteras.

Trafikverkets två manifestposter gäller endast Gräsmyrs ungefärliga 75 × 75 km discovery-envelope. De verifierar inte nationell täckning eller global källtotal (`source_object_count=null`). Båda produkterna är fortsatt baseline; en andra komplett jämförbar körning med samma envelope och exakta lager-ID:n krävs före `pilot_recurring`. Kommersiella villkor, historisk lagring, bearbetning, kundvisning och vidare distribution ändras inte.

**PM-027-status:** adapterluckan från inventory #20 är stängd; inventory #25 verifierar alla fem evidensposter. PM-027 förblir P0/öppen eftersom backloggens mål är en full daglig rapport över alla relevanta källor/produkter/lager och endast fem utvalda källor har adapterposter. Artifacten läser 52 source_id och flaggar duplicerade PM-ID:n PM-023, PM-024 och PM-027 utan att slå ihop dem.

**Nästa konkreta steg:** (1) utred och återställ Trafikverkets workflowregistrering/Actions-synlighet utan att röra snapshotdatan; (2) kör ny inventory och verifiera faktiska latest-attempt-run-ID:n för båda Trafikverket-profilerna; (3) fortsätt PM-027:s käll-för-käll-mappning mot befintliga manifest/snapshotindex och prioritera full rapportering. Ingen ny collector eller historikmodell behövs för den nu stängda adapterluckan.

**Dokumentationsstatus:** inventory #25 och kvarstående workflowupptäcktsavvikelse dokumenteras här. Ingen källcollector, snapshotdata, rättighetsstatus eller kundvisningsrätt har ändrats.


## PM-027 – inventory #26 efter PR #83 (2026-11-26)

[Project manager read-only inventory #26](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45869038578) kördes 2026-11-26 17:35:34 UTC från projektledarrepots `main` efter merge av [PR #83](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/83), merge commit `915eed8bc554855b6a76308fc0928f254a6ba131`. Körningen avslutades success 17:35:53 UTC. Artifact ID `15141926416` (`project-manager-inventory-45869038578`, 23 299 byte) laddades ned och granskades.

Verifierat: 3/3 repos, 0 insamlingsfel; source registry 52 source_id (15 med operations-block, 37 utan); Skogs source_snapshot_evidence status success, `tree_truncated=false`, fem separata källposter. Read-only-skydd: inga käll-featuredata hämtades, inga källrepositorier skrevs, inga secrets i output. Central alert-job var skipped.

PR #83:s exact-path run-history fallback fungerar live för båda Trafikverket-profilerna. Både `trafikverket.miljoweb_landskap` och `trafikverket.nvdb.wildlife_collision_frequency` har `latest_attempt.status=completed`, `conclusion=success`, run-ID `45705661340`, path `.github/workflows/trafikverket-weekly-snapshots.yml` och `workflow_discovery=repository_run_history_exact_path_fallback`. Det är Skog Actions [run #33](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340), äldre exakt path-match är [run #32](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705067474). Orelaterade workflow-körningar väljs inte.

Snapshotbaslinjen är oförändrad: Miljöwebb 27 lager/2 396 features, NVDB Viltolyckor 7 lager/5 278 features, båda från manifest 2026-11-25 och endast inom Gräsmyrs ungefärliga 75 × 75 km discovery-envelope. Båda produkter är fortfarande baseline, eftersom endast en komplett jämförbar snapshot är verifierad per produkt. Nationell täckning och global källtotal saknas; NVDB-frekvenser är aggregerade per vägsegment, inte individuella olyckor.

PM-027 förblir P0/öppen: inventory #26 visar fem adapterposter, inte full rapportering över samtliga 52 registrerade källor och separata produkter/lager. Nästa konkreta steg är att jämföra nästa kompletta Trafikverket-snapshot separat per produkt mot 2026-11-25-baslinjen och fortsätta mappningen av övriga källor. Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution är oförändrade.

**Dokumentationsstatus:** Documented – inventory #26 och liveverifierad workflow fallback är dokumenterade; full PM-027-omfattning återstår.


## 2026-11-26 – Skogsdatalabbet geodata timeline: PR-publicering verifierad live

Workflow [Weekly Skogsdatalabbet data timeline, run #8](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45908028278) kördes från `main` efter merge av [PR #682](https://github.com/dahlinrobert-lgtm/Skog/pull/682) och avslutades `completed/success`. Samtliga steg passerade: installation av beroenden, `Test weekly delta logic`, `Capture weekly baseline or changes` och `Create or update geodata timeline snapshot pull request`. PR-actionen skapade automation-branchen `automation/geodata-timeline-snapshots` och [data-PR #683](https://github.com/dahlinrobert-lgtm/Skog/pull/683).

PR #683 mergades 2026-11-26 22:59:43 UTC, merge commit `7b6504f3f80fa8b6fcee39f9b5c078ac39d119f1`. Den publicerade fyra filer:
- `data/geodata_timeline/latest.json`
- `data/geodata_timeline/snapshots/20261126T225821Z.json`
- `data/geodata_timeline/samples/20261126T225821Z_torvkarta.npz`
- `data/geodata_timeline/samples/20261126T225821Z_sis.npz`

Efter merge verifierades `latest.json` direkt på `main`: JSON-parsning lyckas, filen slutar med en riktig newline och anger snapshot `20261126T225821Z`, observationstid `2026-11-26T22:58:21.035242+00:00`. Båda tjänsterna har `status=ok`, `change_status=unchanged` och föregående jämförda snapshot `20261116T125756Z`. Torvkarta jämfördes över två band med 250 000 giltiga pixlar per band; SIS över två band med 6 400 giltiga pixlar per band. Samtliga fyra band rapporterade 0 ändrade pixlar. Detta är endast det konfigurerade 1 km × 1 km Gräsmyr-provet och styrker inte nationell täckning eller fullständig källjämförelse.

**Arkitektur/verifiering:** PR #682:s etablerade PR-baserade publicering fungerar live. Ingen direktpush till skyddad `main` behövs. Snapshot, manifest och provfiler publiceras efter manuell PR-granskning/merge; historiska snapshots skrivs inte om. Den tidigare ogiltiga `latest.json` ersattes genom den nya data-PR:n och är nu giltig på `main`.

**Dokumentationsbedömning:** Documented här i handover. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms Assessed – no update required: verifieringen ändrar inte källans nationella täckning, källstatus, kommersiella användningsvillkor, historisk lagringsrätt, kundvisning eller vidare distributionsrätt. SIS-villkor måste fortsatt bedömas separat; teknisk åtkomst och snapshotarkivering är inte ett rättighetsbesked.

**Nästa konkreta steg:** kör en ny read-only PM-027-inventering i `skogskoll-project-manager-history` för att verifiera att adaptrarna läser den nu giltiga `latest.json` och snapshotmanifestet för `slu.peat_map.v1`/Torvkarta och `skogsstyrelsen.standortsindex_sis`/SIS. Granska inventory-resultat och eventuella fel innan PM-027-evidens dokumenteras eller källstatus ändras.


## 2026-11-26 – PM-027 inventory #36: Torvkarta och SIS-adaptrar verifierade

[Project manager read-only inventory #36](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45908520069) avslutades `completed/success` 2026-11-26 23:03 UTC. Körningen läste Skogs `main`; artifact `project-manager-inventory-45908520069`, ID `15158946831`, 24 150 byte, digest `sha256:8d8cbe460f7df9ab92b36e5e6a4386aef69548d2516d20d56f6389d84c72a0b6`. Artifactens observationstid är `2026-11-26T23:02:59.644079Z`. 3/3 repositories lyckades, 0 fel. Schemagaten och collector-jobbet passerade; collector-tester, dashboard-JavaScript, read-only-tokenkontroll, insamling och artifact-upload lyckades. Central inventory alert-jobbet var `skipped`.

Artifacten innehåller nu sex separata `source_snapshot_evidence`-poster. De nya posterna är:

- `slu.peat_map.v1` / Torvkarta: senaste attempt är Skog Actions [run #8](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45908028278), `completed/success`, exakt workflow path `.github/workflows/geodata-timeline.yml`. Senaste snapshot är `20261126T225821Z`, `sample_complete_for_service`, `change_status=unchanged`, föregående snapshot `20261116T125756Z`. Manifestet är `data/geodata_timeline/snapshots/20261126T225821Z.json`, blob SHA `a7628c626690480ab0a56868f2d6ae8320ea7e5e`. Provfilen är `data/geodata_timeline/samples/20261126T225821Z_torvkarta.npz`, array `500 × 500 × 2`, dtype `uint8`.
- `skogsstyrelsen.standortsindex_sis` / SIS: samma senaste attempt och exakta workflow path. Senaste snapshot är `20261126T225821Z`, `sample_complete_for_service`, `change_status=unchanged`, föregående snapshot `20261116T125756Z`. Samma manifest/blob SHA som ovan. Provfilen är `data/geodata_timeline/samples/20261126T225821Z_sis.npz`, array `80 × 80 × 2`, dtype `int16`.

Båda adaptrarna inventerar sex snapshotmanifest, rapporterar `pixel_comparison_status=compared` och `comparable_grid=true`. Deras scope är samma Gräsmyr-prov på 1 km × 1 km i EPSG:3006. Adaptern är metadata-only: den verifierar att NPZ-filerna finns i Git-trädet men laddar inte ned filerna eller räknar om pixelhasharna. Detta är inte fullständig rasterhämtning eller bevis på nationell täckning. SIS-produktens exakta produktbeskrivning och återanvändningsvillkor kräver fortsatt separat rättighetsgranskning.

Read-only-fält i artifacten är verifierade: `read_only=true`, `no_repository_writes=true`, `no_secrets_in_output=true`. Skogens adapterposter anger dessutom `source_feature_data_downloaded=false` och `source_repository_writes=false`. Artifactens source registry omfattar 52 source_id; source_snapshot_evidence har sex poster och är `status=success`, `tree_truncated=false`.

**PM-027-status:** den tidigare adapterluckan för Torvkarta och SIS är stängd och JSON-felet från inventory #33 är inte längre reproducerat. PM-027 förblir P0/öppen eftersom sex evidensposter inte är en fullständig käll-/produkt-/lagerinventering av hela registret. Kommersiella rättigheter, historisk lagring, kundvisning och vidare distribution ändras inte.

**Nästa konkreta steg:** fortsätt PM-027:s käll-för-käll-mappning och prioritera resterande relevanta produkter/lager. Följ nästa schemalagda geodata-timeline-körning och verifiera att ny snapshot/PR publiceras utan att skriva om historiken. Granska SIS-villkoren separat innan någon kommersiell användning eller kundvisning övervägs.

**Dokumentationsbedömning:** inventory #36 dokumenteras här. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` bedöms Assessed – no update required; ingen källtäckning, fullständighet, kommersiell rättighet eller kundvisningsstatus har ändrats.

## 2026-11-27 – parallell utvärdering av Polisens officiella händelse-API

Polismyndighetens IT-kansli svarade 2026-11-27 i diarienummer A698.287/2026 att de händelser som publiceras på polisen.se är vad som finns tillgängligt och att det inte finns mer data att tillhandahålla. Detta ska inte tolkas som att ett publikt API saknas: Polisen har en officiell dokumenterad endpoint `https://polisen.se/api/events`.

Polisens dokumentation anger att API:et innehåller 500 aktuella händelsenotiser som utgör ett urval av utryckningar. Uppgifter är preliminära och kan ändras. Publicering sker ofta inom några timmar men varierar. Koordinaterna är mittkoordinater för län/kommun, inte exakta händelsepositioner. API-reglerna kräver korrekt identifierande User-Agent, HTTPS, minst 10 sekunder mellan anrop, max 60 anrop/timme och 1 440/dygn; 404 är permanent och webbskrapning är inte tillåten där API finns.

En separat utvärderingsgren `feat/polisen-official-api-evaluation` har skapats. Den lägger till:
- `scripts/capture_polisen_official_events.py`: ett dagligt API-anrop, validerar JSON-array och unika ID:n, bevarar hela svaret och räknar Norrbottenposter separat.
- `scripts/upload_polisen_official_snapshot.py`: gzippar och lagrar snapshots immutable i befintlig Azure-container `police-events`, separat under `polisen-official/runs/{run_id}/attempt-{attempt}/`, med manifest och read-back SHA-256/byteverifiering.
- `.github/workflows/polisen-official-api-evaluation.yml`: daglig körning 04:55 UTC, 14 minuter efter befintlig Brottsplatskartan-körning 04:41 UTC. Endast read access till GitHub och OIDC till Azure.
- `tests/test_capture_polisen_official_events.py`: schema-, ID- och snapshot-envelope-tester.
- `docs/police-source-evaluation.md`: 30-dagars jämförelseprotokoll med minst 25 lyckade snapshots som mål.
- `data-platform/config/sources.yml`: separat source_id `polisen.events_official_api`, med kommersiell användning, historisk lagring och kundvisning kvar som separata bedömningsfrågor.

Befintlig Brottsplatskartan-insamling och dess Azure-historik är inte ändrad. Ingen automatisk sammanslagning, kundvisning eller kundavisering införs. Den officiella snapshoten bevarar hela aktuella listan (upp till 500 enligt dokumentationen); Norrbottenurvalet härleds ur `location.name`. Tomt/ogiltigt svar ska faila i stället för att skapa falsk borttagning eller baslinje.

**Verifieringsstatus vid dokumentation:** PR [#686](https://github.com/dahlinrobert-lgtm/Skog/pull/686) mergades 2026-11-27 i commit `338feab915c6332ba18c6af0d7d882b4fe209501`. Källregistervalidering och statusrapportgenerator passerade, samtliga 405 Python-tester passerade och kundgränssnittstester passerade. Första schemalagda officiella API-snapshot är ännu inte genomförd; workflowen är schemalagd dagligen 04:55 UTC och första förväntade körning efter merge är 2026-11-28. 30-dagarsperioden börjar först vid första lyckade verifierade snapshot. Källan är inte klassad som komplett register eller godkänd för kommersiell kundvisning.


## 2026-11-27 – Piloternas tipping point mergad i projektledaren

Projektledarrepots [PR #94](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/94) är mergad till main 2026-11-27 19:40:41 UTC. Merge commit: `eeb1306dc7459a0e586e489489eb9d970733e641`.

**Implementation på projektledarens main:**
- Den befintliga read-only källregisterbedömningen kompletteras med en deterministisk pilotbedömning.
- Tipping point för expansionsgranskning kräver minst två unika lyckade, kompletta körningar med samma icke-tomma jämförbarhetsnyckel och exakt workflowkoppling.
- Teknisk uppskalningskandidat kräver minst tre jämförbara kompletta körningar, bedömd request-/återhämtningsrisk och explicit geografiskt scope.
- Nya lyckade workflowförsök som ännu inte finns i den manuellt granskade complete_runs-evidensen flaggas för granskning. De räknas inte automatiskt som kompletta.
- Kommersiell användning och kundvisning förblir separata rättighetsgrindar. Ingen cadence, källscope, insamling eller kundpublicering ändras automatiskt.
- Dashboarden visar pilotrekommendation, tipping point, teknisk uppskalningsstatus, rättighetsgrind och eventuella väntande körningsgranskningar.

**Verifiering:**
- PR-körningarna för Python-tester och syntetiska append-only/Git-integrationstester passerade på slutlig PR-commit `2dabd8a02142d3f67ef918717038bbcba1112f3d`.
- Efter merge passerade projektledarens main-testworkflow [run 46058375432](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46058375432).
- Senaste verifierade read-only inventory är fortfarande [run 46020579522](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46020579522), före merge (2026-11-27 14:57 UTC). Ingen read-only inventory efter merge har ännu verifierats. Den nya dashboardbedömningen är därför mergad och testad, men ännu inte verifierad i en ny publicerad inventory/read model.
- Denna arbetsuppgift ändrar inte källregister, datakälleåtkomst, snapshots eller rättigheter. docs/SKOGSKOLL_SOURCE_STATUS.md och docs/SKOGSKOLL_DATA_OVERVIEW.md har kontrollerats på main och lämnas oförändrade.

**Nästa konkreta steg:** verifiera nästa schemalagda read-only inventory på projektledarens main. Kontrollera artifacten och dashboardens read model för Samråd/Älgdata tipping point, Trafikverkets två baslinjer och eventuella new_successful_attempt_pending_review-flaggor. Om ingen schemalagd körning dyker upp behöver PM-029:s schedule-trigger/gate felsökas innan liveverifiering kan slutföras.

**Dokumentationsstatus:** Documented – PR #94:s implementation, tester, merge och kvarstående liveverifiering är registrerade här. Ingen källdokumentation eller rättighetsstatus ändras.

## 2026-11-27 – Inventory #41 verifierad efter autentiseringsfix och pilotbedömning live

Projektledarrepots [PR #95](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/95) åtgärdade HTTP 403-felet i källregisterhämtningen genom att återanvända den befintliga read-only `PROJECTS_READ_TOKEN` i `collect_source_registry(token)`. PR #95 mergades 2026-11-27 i commit `f0b1f77a7724ba6dba65b1b891dc887e53b242cf`. En regressionstest verifierar nu att token skickas till källregisteranropet.

**Verifierad komplett inventory:** [Project manager read-only inventory #41](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46060358632), workflow_dispatch, completed/success 2026-11-27 19:58:14 UTC. Artifact `project-manager-inventory-46060358632`, ID `15227828739`, SHA-256 `e64252ac8e9a7d27d3fc85b7765d96c0c23a58b09a055270a9847af233a4e529`. Inventory JSON rapporterar status success, 3/3 aktiva repositories, 0 repositoryfel, källregisterstatus success med 53 källor (16 med operationsfält, 37 utan) och fyra driftprofiler. Projektbackloggen kunde också läsas. Inga fel på källregister eller backlogg.

**Pilotbedömning från artifacten (inte en ny källinsamling):**
- `skogsstyrelsen.samrad`: 3 manuellt granskade jämförbara kompletta körningar; tipping point nådd för expansionsgranskning. Rekommendation `review_expansion`; teknisk uppskalning inte godkänd eftersom riskprofilen fortfarande är partiell/ej bedömd. Ny lyckad körning [46036924262](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46036924262) flaggas `new_successful_attempt_pending_review` och räknas inte automatiskt in.
- `lansstyrelsen.elk_harvest_statistics`: 2 manuellt granskade jämförbara kompletta nationella körningar (129 ÄFO); tipping point nådd för expansionsgranskning. Rekommendation `review_expansion`; teknisk uppskalning inte godkänd eftersom rate limits/minimiintervall och fullständig riskprofil är okända. Ny lyckad körning [46013595922](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/46013595922) väntar på manuell granskning och räknas inte in automatiskt.
- `trafikverket.miljoweb_landskap`: en komplett Gräsmyr-baslinje, 27 lager/2 396 features; tipping point ej nådd.
- `trafikverket.nvdb.wildlife_collision_frequency`: en komplett Gräsmyr-baslinje, 7 lager/5 278 features; tipping point ej nådd. Detta är aggregerad olycksfrekvens per vägsegment, inte individuella olyckor.
- Torvkarta/SIS: lyckade metadata/sampleförsök [45908028278](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45908028278) flaggas för manuell evidensgranskning; de är inte automatiskt registrerade som kompletta körningar eller tipping point.
  
**Källspecifik latest-attempt signal:** Samråds senaste försök är success; Älgdata senaste försök är success. Länsstyrelsens diariekörning [46011210069](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46011210069) är failure, medan tidigare kompletta query-interval snapshots kvarstår. Trafikverkets latest-attempt lookup är fortfarande unknown eftersom workflowfilen inte finns i GitHubs workflow inventory/run history, även om kompletta baslinjemanifest finns. Harvest notifications senaste attempt är failure; senaste kompletta snapshot kvarstår. Dessa signaler ändrar inte complete-run-evidensen.

**Publicering:** Efter inventory #41 passerade Azure publisher [run #46060438135](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46060438135), completed/success, och validerade/publicerade en run-scoped snapshot. Detta verifierar publiceringskedjan för inventory #41; det innebär inte att en kunddashboard eller extern publicering aktiverats.

**Säkerhet och avgränsning:** Inventory #41 är read-only mot källrepositorierna. Artifacten bygger på metadata/små manifest och hämtar inte feature collections. Partiell körning #40 [46059822293](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46059822293) förblir en misslyckad historisk körning och behandlas inte som komplett. Inga source data, käll-cadence, geografiska scope eller rättighetsgrindar ändrades.

**Nästa konkreta steg:** granska manifests/fullständighet/jämförbarhetsnycklar för väntande Samråd #46036924262 och Älgdata #46013595922 samt Torvkarta/SIS #45908028278. Uppdatera manuellt kuraterade complete_runs endast där varje enskild snapshot verifieras mot exakt workflow, manifest och oförändrat jämförbarhetsscope. Felsök separat Trafikverkets workflow-discovery och Länsstyrelsens diariefel. Behåll risk- och rättighetsgrindarna oförändrade.

**Dokumentationsstatus:** Documented – aktuell liveverifiering och nya väntande granskningar registreras här. `SKOGSKOLL_SOURCE_STATUS.md` och `SKOGSKOLL_DATA_OVERVIEW.md` ändras inte: inga datakällor, ingestionbeteenden eller rättigheter har ändrats.



## 2026-11-27 – Manuell granskning av väntande pilotkörningar

Efter inventory #41 har de väntande källkörningarna granskats mot respektive workflow, manifest/dataartifact och jämförbarhetsscope.

**Älgdata – komplett tredje nationell observation verifierad**
- [Actions run #17](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/46013595922) completed/success. Artifact [15205477400](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/46013595922/artifacts/15205477400), SHA-256 `23680afbbc0840833e0c73bf998ec2b23e22d0b2bc7bb513b804a639534f6be7`.
- Artifacten innehåller 129 unika ÄFO-filer för 2026-11-27; samtliga har `area_rows_available`, report ID 3, säsong 2026/2027, aktuella gränser och obligatoriska totalvärden. Dashboard på `main` anger 129/129 områden. Dashboardcommit: [48b962a](https://github.com/dahlinrobert-lgtm/alg-grasmyr/commit/48b962a993bf6e27979024f669bcfa860ca9c805).
- Körningen är nu manuellt registrerad som tredje kompletta jämförbara run i projektledarrepots driftprofil via [PR #96](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/96), mergad 2026-11-27 (commit `05ee6714aa895a8e031648a605fe2cb600701c6a`). Profilen har fortsatt `rollout_stage=pilot`; tipping point för expansionsgranskning är nådd, men `risk_assessed=false` eftersom leverantörens rate limits/minimiintervall är okända. `scale_up_eligible=false`. Kommersiell användning, kundvisning och vidare distribution är separata och inte godkända av denna tekniska evidens.
- PR #96:s Python-enhetstester och syntetiska append-only/Git-integrationstester passerade.

**Samråd – komplett nytt snapshot men väntar på data-PR**
- [Actions run #65](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46036924262) completed/success. Samma scope-hash `9c597758897297d34eb6ae733e56c5998587de4ff478fd8e82ae1a510dcfa76a`, samtliga tre lager paginerade till uttömning, 21 giltiga observationer, 0 avvisade och 0 saknade/felaktiga geometrier.
- Snapshot och manifest ligger i [data-PR #677](https://github.com/dahlinrobert-lgtm/Skog/pull/677), som fortfarande är öppen. Den räknas därför inte som arkiverad på `main` eller tillagd i `complete_runs`. Befintliga tre manuellt registrerade körningar står kvar; ingen tipping-point-status ändras.

**Torvkarta/SIS – verifierad samplejämförelse, ej full källtäckning**
- Data-PR [#683](https://github.com/dahlinrobert-lgtm/Skog/pull/683) är mergad. Snapshot `20261126T225821Z` jämfördes med `20261116T125756Z` på samma 1 km × 1 km-ruta i Gräsmyr.
- Båda tjänsterna svarade HTTP 200, metadata och pixelhashar var oförändrade och båda banden i respektive prov hade 0 ändrade pixlar. Torvkarta-provet är 500 × 500 × 2 och SIS-provet 80 × 80 × 2. Detta verifierar endast dessa provfönster, inte full rasterhämtning eller nationell täckning. Ingen separat driftprofil eller uppskalningsstatus registreras här.

**Dokumentationsbedömning**
- `docs/AI_HANDOVER.md`: uppdateras med den manuellt verifierade evidensen och nästa steg.
- `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md`: `Assessed – no update required`; inga källidentiteter, insamlingsbeteenden, rättigheter eller kommersiella/kundvisningsbeslut ändrades.
- Nästa steg: granska och merge:a Samråds data-PR #677 först efter sedvanlig kontroll av datafiler och diff. Därefter kan körning #65 registreras manuellt i driftprofilen. Fortsätt bevaka riskgrindar och håll Torvkarta/SIS som lokala prover tills bredare täckning och riskprofil har verifierats.


## 2026-11-27 – Slutstatus efter arkivering och driftprofiluppdatering

Uppföljning till föregående manuella pilotgranskning:

- Samråds data-PR [#677](https://github.com/dahlinrobert-lgtm/Skog/pull/677) är mergad i commit [b90f38f](https://github.com/dahlinrobert-lgtm/Skog/commit/b90f38fc7bdd44b6b1583c46b9934525b14e2c9d). Snapshoten för 2026-11-27 ligger på `main`; filens byte length (400 407) och SHA-256 matchar manifestet exakt. Event bundle innehåller 6 source runs och 184 observationer; samtliga 21 Samrådsobservationer bevarar ursprungligt `first_observed_at`.
- Projektledarrepots [PR #97](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/97) är mergad i commit `6b28b85f28cf6db7ca1293324a74c630bfd4a5a4`. Samråd run #65 är nu manuellt registrerad som fjärde kompletta körning med samma 10 km scope-hash. Driftprofilen visar fortfarande `pilot_recurring`, `risk_assessed=false` och ingen teknisk uppskalningsbehörighet.
- Älgdata run #17 är manuellt registrerad via projektledarrepots [PR #96](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/96), mergad i commit `05ee6714aa895a8e031648a605fe2cb600701c6a`. Profilen har tre kompletta jämförbara nationella observationer (129 ÄFO, report 3, säsong 2026/2027, aktuella gränser); riskprofilen är fortsatt partiell och teknisk uppskalning inte godkänd.
- Torvkarta/SIS:s data-PR [#683](https://github.com/dahlinrobert-lgtm/Skog/pull/683) är mergad. 1 km-proven från 2026-11-26 är oförändrade jämfört med 2026-11-16. Detta är sampleevidens, inte full rasterhämtning eller nationell täckning.

**Samlad pilotbedömning:** Samråd och Älgdata har nått tipping point för expansionsgranskning. Det är inte ett beslut om uppskalning. Båda har `risk_assessed=false` eftersom leverantörsgränser/minimiintervall ännu är okända. Scope, cadence, kommersiell användning, kundvisning och vidare distribution har inte ändrats eller godkänts.

**Nästa konkreta steg:** gör en separat, evidensbaserad riskgenomgång av Samråds och Älgdatas anropspolicy (leverantörsdokumentation, minimiintervall, rate limits, retry/backoff och stoppvillkor). För Torvkarta/SIS: hitta exakt workflow-run-ID för den föregående 2026-11-16-snapshoten innan någon driftprofil eller tipping-point-status registreras. Fortsätt därefter med ordinarie inventory och manuell granskning av nya lyckade försök.

**Dokumentationsstatus:** Documented – Skogs AI_HANDOVER uppdateras. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` är fortsatt bedömda utan uppdateringsbehov eftersom källidentiteter, ingestion, rättigheter och kundvisning inte ändrats.


## 2026-11-27 – PM-027: paginerad Trafikverket workflow-discovery efter PR #100

Projektledarrepots [PR #100](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/100) är mergad 2026-11-27 i commit `b8ae75dc594aede6bf298823b5b64c37a142cab4`. Den read-only källsnapshotadapterns fallback för workflows som saknas i GitHubs workflow inventory söker nu repository-wide Actions-run history i upp till tio sidor (1 000 körningar), nyast först. Endast exakt `workflow.path` accepteras. Sökningen avslutas när alla saknade konfigurerade sökvägar hittats eller historiken är uttömd. Om 1 000-gränsen nås utan träff kvarstår fail-closed `unknown`, med explicit markering att sökningen trunkerats.

Regressionstestet placerar Trafikverkets exakta workflow-sökväg på sida två efter 100 orelaterade körningar och verifierar att run #33 hittas via den exakta sökvägen. PR-kontrollerna passerade: Python unit tests, dashboard JavaScript syntax och synthetic append-only tests. Ändringen är metadata-only och ändrar inte Skogs insamling, snapshots, källscope, rättigheter eller kundvisning.

**Direkt verifierad run-history-evidens (2026-11-27):** GitHubs repository-wide Actions-historik för Skog innehöll 100 körningar på sida 1 (äldsta i sidan 2026-11-26 22:49:45 UTC) och 100 på sida 2 (äldsta 2026-11-25 21:41:55 UTC). På sida 3 hittades de exakta workflow-path-träffarna:
- [Run #33](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340), completed/success, 2026-11-25 21:35:00 UTC.
- [Run #32](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705067474), completed/success, 2026-11-25 21:31:03 UTC.
- [Run #31](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45703502732), completed/failure, 2026-11-25 21:20:54 UTC.
Detta visar konkret varför en ensidig fallback missade #33: 200 nyare orelaterade körningar låg före den. #33 är senaste verifierade exakta path-match. Den nya paginerade adaptern ska hitta den på sida 3, men liveverifiering genom en ny read-only inventory efter merge återstår. Tills en ny komplett jämförbar snapshot finns kvarstår båda Trafikverket-produkterna på baseline 2026-11-25.

**Dokumentationsstatus:** Documented – projektledaradaptern och dess tester är uppdaterade i PM-repot; denna handover anger merge, verifierad CI och kvarstående livekontroll. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` är `Assessed – no update required`: ingen källstatus, ingestion, cadence, rättighet eller kundvisning ändrades.

## 2026-11-27 – PM-027 riskgenomgång: Samråd och Älgdata

Projektledarrepots [PR #102](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/102) är mergad i commit `baa68e6c121483c8c960f7f2d1a9d0b636944f7c`. Källprofilerna och `docs/PM027_ADAPTER_SPIKE.md` har uppdaterats med verifierad leverantörsmetadata och tydligare gräns mellan dokumenterade gränser och okända rate limits.

**Samråd**
- [Skogsstyrelsens ArcGIS REST-tjänst](https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaSamrad/MapServer) anger `MaxRecordCount=2000`; samtliga tre lager (punkt, linje, polygon) anger samma gräns och `Supports Pagination=true`.
- Collectorn använder `PAGE_SIZE=300`, under publicerad maxgräns. Fyra kompletta jämförbara körningar med samma scope-hash är verifierade; senaste [run 46036924262](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46036924262) passerade och publicerade snapshot/manifest 2026-11-27 16:50 UTC.
- Minsta anropsintervall och rate limits är inte publicerade/verifierade. Collectorn saknar explicit retry/backoff. Riskstatus kvarstår därför som partial; `risk_assessed=false`.

**Älgdata**
- Senaste [run 46013595922](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/46013595922) passerade 2026-11-27 och samlade 129/129 ÄFO för report 3, säsong 2026/2027, aktuella gränser.
- Collectorn använder statistikportalens webbgränssnitt och POST-rutten `/LoadData/GetData`, sekventiellt för 129 ÄFO med upp till tre försök per område. Ingen offentlig API-kontrakt, rate limit eller minsta anropsintervall identifierades i de granskade officiella sidorna.
- Länsstyrelsens öppna data-sida beskriver Älgdata-statistiken som fritt användbar utan särskilda villkor och listar XLSX som format. Detta ändrar inte separat bedömning av historisk lagring, härledd produkt, kundvisning och vidare distribution.
- Riskstatus kvarstår som partial; `risk_assessed=false` och `scale_up_eligible=false`.

**Beslut:** inga ändringar av insamlingsintervall, parallellitet, retry-policy eller kundvisning. Behåll nuvarande sekventiella insamling och fail-closed-beteende. Nästa steg är att inhämta skriftligt besked om minsta intervall/rate limits från respektive leverantör innan uppskalning. 

**Dokumentationsstatus:** Documented – PM-repots profiler och risknotering är uppdaterade. `docs/SKOGSKOLL_SOURCE_STATUS.md` är `Assessed – no update required` eftersom åtkomst-, licens-, kundvisnings- och rolloutstatus inte ändrats.

## 2026-11-27 – Project manager read-only inventory #43: adapterverifiering efter PR #98

[Inventory #43](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46065968120) avslutades completed/success 2026-11-27 20:47:47 UTC från projektledarrepots `main`, commit `4706bb76496538bc62fc73368841345c48f59880` (PR #99). Båda jobben för PM-029 schedule gate och collector passerade; central inventory alert/write-job var skipped. Artifact [15230274599](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46065968120/artifacts/15230274599), 26 933 byte, SHA-256 `d2e77234357a0085063c2084aef37e603500b442abaeeb034c7564e76d227207`, innehåller `dashboard-data.json`.

Read model: success, 3/3 repositories, 0 repositoryfel, source registry success, 53 källor (16 med operations-block, 37 utan) och fyra riskprofiler. Säkerhetsmetadata anger `read_only=true`, `no_repository_writes=true` och `no_secrets_in_output=true`.

**PR #98 – adapterresultatet verifierat efter merge**
- För både `skogsstyrelsen.torvkarta` och `skogsstyrelsen.standortsindex_sis` redovisas senaste sample nu som `sample_complete_for_service`, med `valid_sample=true` och `sample_scope_complete=true`.
- Snapshot-ID `20261126T225821Z`; jämförelsen mot `20261116T125756Z` är `unchanged` för båda tjänsterna. Torvkarta-provet är 500 × 500 × 2 (uint8), SIS-provet 80 × 80 × 2 (int16); båda avser samma 1 km × 1 km Gräsmyr-ruta.
- Adaptern verifierar att NPZ-samplefilen finns i Git-trädet men laddar inte ned filinnehållet och räknar inte om pixelhashen. Detta är giltig tjänsteprovsevidens för metadata-/pixelövervakning, inte full rasterhämtning, nationell täckning eller en fullständig återkommande driftprofil. Ingen tipping point eller uppskalning ska härledas för Torvkarta/SIS.

**Övriga pilotprofiler bekräftade**
- Samråd: fyra kompletta jämförbara körningar med samma 10 km scope-hash; `pilot_recurring`, tipping point nådd och `review_expansion`. `risk_assessed=false`, `scale_up_eligible=false`, kundanvändning inte godkänd och separat rättighetsgrind kvarstår.
- Älgdata: tre kompletta jämförbara nationella körningar, 129/129 ÄFO för report 3 och säsong 2026/2027 med aktuella gränser; `pilot_recurring`, tipping point nådd och `review_expansion`. Riskbedömning är fortsatt partiell, `scale_up_eligible=false` och kundanvändning inte godkänd. Att kommersiell användning i källprofilen anges som villkorad/godkänd tar inte bort den separata kundvisnings- och distributionsgrinden.
- Trafikverkets Miljöwebb Landskap och NVDB Viltolyckor har fortsatt varsin komplett baslinje från 2026-11-25. Senaste workflowförsök är fortsatt unknown eftersom den konfigurerade exakta workflow-sökvägen inte hittas i workflow inventory/recent run history. Ingen run-ID kopplas in på antagande.

**Nästa konkreta steg**
1. Fortsätt ordinarie read-only inventory och kontrollera att samplefält för Torvkarta/SIS kvarstår; ingen ytterligare adapterändring behövs utifrån #43.
2. Verifiera den mergade projektledar-PR #100:s paginerade exact-path fallback i nästa read-only inventory. Bekräfta senaste Trafikverket-försök med exakt workflow-sökväg; behåll manifestet från 2026-11-25 som baseline tills en ny komplett jämförbar snapshot finns.
3. Följ upp återstående okända leverantörsgränser för Samråd och Älgdata med respektive leverantör. PR #102 verifierar Samråds MaxRecordCount=2000 och paginering, men rate limits/minimiintervall är fortsatt okända; Älgdatas portal saknar identifierat publikt API-/rate-limitavtal. Båda riskprofilerna förblir partial och uppskalning spärrad tills detta klargjorts.

**Dokumentationsstatus:** Documented – inventory #43 bekräftar adapterändringen och uppdaterar nästa steg. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` är `Assessed – no update required`: inga source identities, källstatusar, insamlingsbeteenden, cadence, rättigheter eller kundvisningsbeslut ändrades.

## 2026-11-27 – Project manager read-only inventory #42 verifierad

[Inventory #42](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46064154483) avslutades completed/success 2026-11-27 20:31:51 UTC. Artifact [15230022338](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46064154483/artifacts/15230022338), SHA-256 `6d7abed530b231923d33374ffb68d4bbff7139c3dca6508f8ae0d07b4311ab31`, innehåller `dashboard-data.json`. Read model rapporterar success, 3/3 repositories, 0 repositoryfel, source registry success, 53 registrerade källor, 16 med operationsfält, 37 utan operationsfält och fyra driftprofiler. Alert-jobbet var skipped (ingen issue-skrivning).

**Live pilotbedömning i artifacten**
- Samråd: fyra kompletta jämförbara körningar, tipping point nådd, `review_expansion`; `risk_assessed=false`, `scale_up_eligible=false`, `rights_gate=separate_review_required`.
- Älgdata: tre kompletta jämförbara nationella körningar med 129 ÄFO, tipping point nådd, `review_expansion`; `risk_assessed=false`, `scale_up_eligible=false`, rättighetsgrinden är separat.
- Trafikverkets Miljöwebb Landskap och NVDB Viltolyckor: fortsatt en komplett baslinjekörning vardera; ingen tipping point.
- Torvkarta/SIS: read model behöll historisk pending-workflow-granskning i #42. Senaste samplemanifestet är dock arkiverat och har jämförbara 1 km-prov med 0 % pixeländring på båda banden. Ingen återkommande driftprofil eller nationell/full rasterkompletthet ska härledas från detta.

**Verifierad korrigering i projektledaradaptern**
[PR #98](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/98) är mergad i commit `ba402f84d29c4bf12049a87076e858dd326aad17`. Den gör geodata-adaptern tydligare med explicit samplekompletthet för enskild tjänst utan att ladda ned NPZ-innehåll eller skapa en fullständig raster-/nationell driftprofil. Regressionstester täcker giltigt sample, oberoende workflowupptäckt och risk-/rättighetsgrindar. Slutliga PR-kontroller: Python unit tests och synthetic append-only tests, båda success. PR:en ändrar inte insamling eller källscope.

**Nästa steg**
1. Kör en ny read-only inventory på main efter PR #98 och verifiera att Torvkarta/SIS sample status exponeras tydligt, utan att de räknas som återkommande komplett drift.
2. Följ upp eventuell ny veckokörning av Trafikverket. Den exakta workflowfilen `.github/workflows/trafikverket-weekly-snapshots.yml` återfinns fortfarande inte i main workflow-run-listan; inga nya körningar får kopplas dit utan exakt path/run-evidens.
3. Utred provider rate limits/minimiintervall för Samråd och Älgdata innan riskprofil kan bedömas som komplett.

**Dokumentation:** `docs/AI_HANDOVER.md` uppdateras. `docs/SKOGSKOLL_SOURCE_STATUS.md` och `docs/SKOGSKOLL_DATA_OVERVIEW.md` har lästs på main och bedömts `Assessed – no update required`: ingen källstatus, source registry, cadence, ingestion, rättighet eller kundvisning ändrades i detta arbete.


## 2026-11-27 – Länsstyrelsens diarier: PR #695 mergad och CI/audit verifierade

[PR #695](https://github.com/dahlinrobert-lgtm/Skog/pull/695) är mergad i `main` med merge commit `621aa168ef975a5030071b5b662434e7453437b7`. Ändringen skiljer portalens råa resultatrader från unika diarienummer efter deduplicering. Källans rapporterade total stäms av mot summan av giltiga diarienummerrader som faktiskt lästs över sidorna; unika län/diarienummer fortsätter vara identiteten för poster som lagras. Okänd total, olästa rader eller ej uttömd paginering får fortsatt inte godkännas. Persistensvalideringen har motsvarande separata kontroller för råa rader och unika poster.

**Verifierade kontroller**
- [Snapshot storage tests #607](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066108336): hela `python -m unittest discover -s tests -v` passerade.
- [Länsstyrelsen diary history audit #75](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066108277): regressionstester och historikaudit passerade.
- Audit-artifact [15231096142](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066108277/artifacts/15231096142): 3 910 state records, 41 565 eventrader, inga duplicerade event-ID:n, inga eventnycklar utan state record, inga okända eventtyper och inga poster som tolkas som borttagna. Audit rapporterar 18 observation_count-mismatchar som uttryckligen klassas som äldre historikluckor; inga retroaktiva händelser ska skapas för att dölja dessa. Auditens `ok=true`.

**Avgränsning och nästa steg**
Den ursprungliga Blekinge-körningen [#46011210069](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46011210069) visade 143 råa rader på tre sidor (50 + 50 + 43), men 135 unika diarienummer efter åtta överlapp. PR #695 korrigerar avstämningslogiken för detta mönster. Ingen ny livehämtning efter merge har ännu verifierat att portalen nu ger en komplett godkänd körning; detta är nästa konkreta steg. Den ofullständiga historiska körningen får inte omtolkas som komplett och får inte användas för frånvarobedömning.

Källstatusen är oförändrad: pilot, delvis verifierad åtkomst/historik, kommersiell användning villkorad per handling/post och kundvisning inväntar dokumentgranskning. Ingen rättighets- eller täckningsslutsats följer av PR #695.

**Dokumentationsstatus:** Documented – kodändringen, CI och historikaudit är dokumenterade här och i `SKOGSKOLL_DATA_OVERVIEW.md`. `SKOGSKOLL_SOURCE_STATUS.md` är `Assessed – no update required`: källans åtkomst-/rättighetsstatus och kundvisning har inte ändrats.
