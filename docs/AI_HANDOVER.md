# Skog / Skogskoll – överlämning för fortsatt arbete

**Senast uppdaterad:** 2026-11-16  
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

- Nationell karta över älgförvaltningsområden finns i Jakt-läget i `docs/bevakning.html`. Den använder Länsstyrelsernas publika JaktAdm WMS, lager 1 (`LST Älgförvaltningsområden`), som enligt tjänstemetadata är de senast beslutade ÄFO-polygonerna i EPSG:3006. Kartan har Standard/Flygfoto och nationell utbredning. Statistikunderlaget är fortfarande regionalt (30 jaktområden för 2026/2027) och är inte joinat till polygonerna; kartan ska därför inte färgsättas som avskjutningskarta ännu.
- Källan är registrerad som `lansstyrelsen.elk_management_areas`. Åtkomsten via WMS är verifierad, men datasetsspecifika villkor för extraktion, cache, bearbetning, kommersiell användning och kundvisning är inte verifierade. Behåll attribution till Länsstyrelserna och behandla visning, lagring och vidareanvändning separat.

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
