# Skogskoll – datakällor, åtkomst och användning

**Dokumentdatum:** 2026-11-14  
**Version:** 1.0  
**Omfattning:** Skogskoll kundprodukt och de datakällor i Skog-repot som kan användas av produkten.

> **Statusprincip:** Detta dokument skiljer mellan (1) teknisk åtkomst, (2) faktisk insamling/snapshot, (3) verifierad historik, (4) rätt att lagra och bearbeta, och (5) rätt att visa eller distribuera till kunder. En fungerande API-probe är inte bevis för fullständig historik eller kommersiella rättigheter.

## 1. Syfte och målbild

### Operativ huvudprioritet – dagligt snapshotinformationsflöde

Skog ska varje dag ge en samlad, read-only bild av senaste status för alla registrerade datakällor och separata produkter/lager. Informationen ska omfatta senaste kompletta snapshot, senaste körningsförsök, status/fullständighet, aktualitet, geografiskt scope/täckning, antal, jämförbarhet och avvikelser samt länkar till manifest, körning och arkiverat resultat.

Detta innebär inte att alla källor hämtas dagligen. Varje källa har en lämplig kadens utifrån uppdateringsmönster, tekniska begränsningar och rättigheter. Den dagliga rapporten visar källans kadens och ålder på senaste kompletta snapshot. En dagsrapport får aldrig dölja en misslyckad/partiell körning eller presentera en gammal snapshot som aktuell.

En lång och heltäckande backlogg ska parallellt fånga framtida utveckling, men är sekundär till det dagliga informationsflödet och till att befintliga insamlingar fungerar tillförlitligt.

Skogskoll ska vara en fristående, mobilanpassad bevakningstjänst för privata skogsägare. Användaren ska kunna registrera en eller flera fastigheter eller egna bevakningsområden och få relevanta händelser presenterade på karta och i en historik.

Målet är att kombinera myndighetsdata, geodata, raster, statistik och historiska observationer för att kunna svara på:

- Vad har tillkommit, ändrats eller försvunnit i närheten av min skog?
- När upptäckte Skogskoll förändringen?
- Vilken källa och vilken observation bygger informationen på?
- Berör händelsen ett bevakat område?
- Är det en faktisk händelse, ett planeringsunderlag eller en statistisk riskindikator?

Skogskoll ska i första hand sälja värdet av egen historik, bevakning, matchning, analys och programvara. Rådata ska bara distribueras vidare när rättigheterna uttryckligen medger det.

## 2. Två sammanhängande delar

### 2.1 Skog – dataplattform

Skog-repot innehåller bredare insamlings- och analysflöden. Plattformen ska:
- hämta data från identifierade källor,
- bevara originalfiler och snapshots,
- registrera källa, produkt, tidpunkt, version och kontrollsumma,
- upptäcka förändringar och bortfall,
- kvalitetssäkra och normalisera geometrier och attribut,
- dokumentera licenser, tekniska villkor och proveniens.

Alla datakällor i Skog är inte automatiskt en del av Skogskolls första produktversion.

### 2.2 Skogskoll – kundapplikation

Skogskoll ska:
- låta användaren skapa bevakningsområden,
- matcha relevanta observationer mot dessa områden,
- visa händelser och förändringar i en begriplig historik,
- låta användaren välja händelsetyper och aviseringskanaler,
- skicka e-post och push när en verifierad, relevant ny händelse upptäcks.

### Länsstyrelserna – älgjaktsområden (licensområden och älgskötselområden)

- Källa: JaktAdm MapServer Layer 0, **LST Älgjaktområden**, i samma tjänst som ÄFO-lagret. Exportinventeringen 2026-11-16 innehöll 2 927 objekt: 832 älgskötselområden och 2 095 licensområden.
- Bevakningssidan använder två separata, valbara lager i Jakt-läget. Geometrier hämtas direkt från ArcGIS REST med geografisk avgränsning till aktuell kartvy och uppdelade objektID-anrop. Klienten begär EPSG:4326 för Leaflet men förenklar, klipper eller reparerar inte geometrierna.
- För att undvika en nationell engångshämtning av den stora geodatamängden hämtas lagren först vid zoomnivå 8 eller närmare. Områdesnamn, typ, registreringsnummer och tillgängliga källattribut visas vid klick.
- När användaren väljer en rad i älgstatistiktabellen isoleras motsvarande jaktområde: statistikens områdesnummer matchas i första hand mot JaktAdm-fältet `omrnum`, med namn och ÄFO som reserv. Övriga jaktområdeslager och ÄFO-lagret döljs, endast vald geometri visas och kartan zoomar till den. Framtida kronhjortsstöd kan använda samma urvalsmönster när artens geometritjänst och nyckelfält har verifierats; det stödet finns inte ännu.
- Områdesgeometri begärs med ArcGIS JSONP (`f=json&callback`) för att hantera webbläsarens cross-origin-begränsning; Esri JSON-geometrin konverteras lokalt till GeoJSON utan förenkling eller reparation. I älgstatistikläget döljs den separata detaljpanelen och kartan använder hela tillgängliga bredden. Liveverifiering av JSONP-anropet mot JaktAdm återstår.
- För enskilt jaktområde hämtas nu geometri och attribut i samma ArcGIS JSONP-query, med områdesnummer som primär nyckel (`UPPER(omrnum)`) och namn/ÄFO som reserv. I statistikläget visas inte den generella kontrollen för nationella jaktområdeslager eller felstatusbrickan; endast valt område ska läggas på kartan. Teknisk liveverifiering mot JaktAdm är ännu inte genomförd.
- Statistikradens klick- och tangentbordsaktivering hanteras delegerat på flödescontainern för att tåla att tabellen renderas om. Primär matchning använder exakt `omrnum`-värde; namn och ÄFO är reservvägar. Laddningsstatus visas under kartans rubrik och den tomma resultatbadgen döljs i jaktläget. Liveverifiering av kartcentrering och geometri mot JaktAdm återstår.
- Efter uppföljande användartest flyttas klick- och tangentbordsaktivering till direkta lyssnare på varje tabellrad efter rendering, med uppslag i aktuell filtrerad områdeslista. Kartan invaliderar storleken efter nästa renderingscykel och anropar därefter `fitBounds` på den valda geometriens giltiga bounds. Liveverifiering mot JaktAdm återstår.
- Älgstatistikens kolumn **Föregående rapporteringsdag** härleds från föregående tillgängliga snapshot för samma jaktområde. Källans exporterare beräknar `delta` mot föregående CSV-snapshot i datumordning; kolumnen visar datumet för den jämförelsesnapshoten, inte ett fältdatum.
- I älgstatistikvyn visas inte det nationella ÄFO-polygonlagret som permanent bakgrund. Statistikens tabell har fyra kolumner (ÄFO, fällda totalt vid snapshot, förändring och rapporterad förändring observerad); jaktområdesnamn och län visas inte som separata kolumner. Rubrikerna radbryts så tabellen ryms inom tillgänglig bredd.
- Teknisk implementation finns i utvecklingsgrenen `feat/elk-hunting-area-boundaries`; detta är inte i sig ett juridiskt godkännande. Villkor för extraktion, cache, bearbetning, kommersiell användning och kundvisning är ännu inte verifierade på exakt lager-/produktnivå. Behåll attribution till Länsstyrelserna och behandla kundpublicering separat.

### Länsstyrelserna – nationella älgförvaltningsområden (ÄFO)

- Källa: Länsstyrelsernas publika JaktAdm MapServer/WMS, tjänst `Jaktadm/lst_jaktadm_visning`.
- Verifierad tjänstemetadata (2026-11-16): lager 1 heter **LST Älgförvaltningsområden**, är polygongeometri i SWEREF 99 TM (EPSG:3006) och beskrivs som de senast beslutade älgförvaltningsområdena. Tjänsten uppger att nya beslut blir synliga nästkommande dag.
- Tjänsten erbjuder både Map Service/ArcGIS REST och WMS. Bevakningssidan använder Feature Layer 1 via ArcGIS REST för att hämta polygongeometrier (ID-lista och uppdelade objektID-frågor) till samma Leaflet-karta som skogshändelserna. WMS-implementationen gav en bakgrundskarta utan synliga ÄFO-gränser och har ersatts.
- Källans metadata: [Geodatakatalogens metadata](https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/GetMetaDataById?id=93a41eff-e847-4db8-8c7e-154ddfdc34ad). MapServer: [tjänstmetadata](https://ext-geodata-applikationer.lansstyrelsen.se/arcgis/rest/services/Jaktadm/lst_jaktadm_visning/MapServer).
- Rättigheter för extraktion, lokal lagring, bearbetning, kommersiell användning och kundvisning är ännu inte verifierade på exakt datamängdsnivå. Publik tjänsteåtkomst ska inte tolkas som ett generellt återanvändningstillstånd.
- Statistikbegränsning: Älgdatas nuvarande 2026/2027-underlag i bevakningssidan omfattar 30 regionala jaktområden. Det har inte kopplats geografiskt till ÄFO-polygonerna. Kartan visar därför gränser, inte avskjutningsvärden eller färgklassning.

## 3. Teknisk nulägesbild

Skogskoll-prototypen har lokal hantering av bevakningsområden i webbläsaren, med cirklar och GeoJSON Polygon/MultiPolygon. Den lokala prototypen är inte en produktionsdatabas och uppgifterna synkas inte mellan användare eller enheter.

Planerad målarkitektur:
- webbapp: statisk, mobilanpassad app,
- beständig databas: Supabase/Postgres,
- geografisk matchning: PostGIS,
- schemalagd worker: GitHub Actions eller motsvarande serverbaserad körning,
- e-post: Resend,
- push: Web Push/VAPID.

Ingestion-kärna, databasstruktur, historikmodell, scan-sessioner, atomisk sidcommit och PostGIS-matchnings-RPC har utvecklats. Det finns tester med mock-adaptrar och PostGIS i CI. Detta ska inte förväxlas med en verifierad liveinstallation i ett produktionsprojekt.

Den fullständiga ingestionen är ännu inte aktiverad. Den manuella scan-entrypointen är avsiktligt skyddad av explicita miljövariabler och databasuppgifter. Inga användarlarm ska aktiveras innan fullständig baslinje, historik, databas och källbeteende är verifierade.

## Maskinläsbart källregister

Det operativa källregistret finns i `data-platform/config/sources.yml`. För utvalda källor finns ett valfritt `operations`-block med separata statusar för teknisk åtkomst, snapshots, historik, kommersiell användning och kundvisning. Registret innehåller inga autentiseringsuppgifter och statusarna är granskningsstöd, inte automatiska rättsliga godkännanden. NVR finns nu som en egen datakälla eftersom individuella olyckshändelser inte ska blandas ihop med Trafikverkets aggregerade NVDB-frekvenser.

## 4. Datakällor – status och avsedd användning

Statusorden nedan är avsiktligt försiktiga:
- **Verifierad åtkomst:** tjänsten eller filen har nåtts tekniskt.
- **Probe/inventering:** begränsat test av metadata, antal eller ett urval.
- **Snapshotflöde:** automatiserad eller dokumenterad insamling av daterade observationer.
- **Historik ej verifierad:** en komplett, jämförbar tidsserie har inte visats.
- **Rättighetskontroll kvarstår:** kommersiell lagring, kundvisning eller vidare distribution måste bedömas separat.

### 4.1 Skogsstyrelsen – avverkningsanmälningar

**Prioritet:** Mycket hög  
**Källa:** [ArcGIS Feature Layer](https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAvverkningsanmalan/MapServer/0)

**Nuvarande användning och tekniskt läge**
- Lagret används i Skogs kart- och övervakningsarbete.
- Skogskoll har en separat källprobe.
- Dokumenterad probe 2026-10-25 rapporterade 129 733 objekt; 300 poster lästes och kontrollerades med unika tekniska ID:n.
- Proben är begränsad och utgör inte en fullständig import.
- Källans antal har varierat mellan närliggande körningar; ett count-delta bevisar inte ensamt att objekt har tagits bort.

**Historik/tidsserie**
- Målet är kontroll var sjätte timme.
- Fullständig eller inkrementell ingestion ska ha paginering, checkpoint, retry, ID-kontroll och beständig historik.
- En ofullständig körning får aldrig markera ej sedda objekt som inaktiva.
- Första baslinjen får inte skapa nyhetlarm för gamla poster.

**Rättigheter**
Skogsstyrelsens officiella geodatavillkor verifierades 2026-11-25: myndighetens egenproducerade geodata är öppna data under CC0 1.0 Universal om inget annat anges. Det medger fri kommersiell användning, bearbetning, lagring och vidare distribution för produkter/lager som omfattas av huvudregeln. Ange gärna Skogsstyrelsen som källa (rekommenderat, inte ett CC0-krav). Kontrollera alltid exakt produkt/lager och eventuella undantag eller tredjepartsinslag. Tekniska kontokrav och tjänstevillkor är separata från licensen.

**Framtida användning**
En ny avverkningsanmälan som matchar ett bevakat område ska kunna visas som en ny upptäckt händelse. En anmälan är inte bevis för att avverkning har genomförts.

**Nästa steg**
Slutför källverifiering och fullständig ingestion, etablera baslinje och jämför minst två kompletta körningar innan larm.

### 4.2 Skogsstyrelsen – samråd

**Prioritet:** Mycket hög  
**Datatyper:** punkt-, linje- och polygonlager.

**Nuvarande läge**
Separata punkt-, linje- och polygonlager hämtas med paginering inom det konfigurerade pilotområdet. En tidigare dokumenterad körning av workflow [collect-samrad.yml](../.github/workflows/collect-samrad.yml) genomfördes 2026-11-24 i [run 45454250815](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45454250815), med status `completed/success`. Jobbloggen redovisade:
- punkter: 0 hämtade i envelope, 0 inom scope, 0 sidor,
- linjer: 20 hämtade i envelope, 11 inom scope, 1 sida,
- polygoner: 14 hämtade i envelope, 12 inom scope, 1 sida.

Detta är verifierade körningsvärden för den aktuella pilotkonfigurationen, inte nationell täckning eller en avstämning mot en separat auktoritativ källtotal. Den nuvarande `samrad_latest.json` innehåller både metadata och featuredata och är därför för stor för projektledarens metadata-only-adapter att läsa säkert. Det separata lilla manifestet gör nu att projektledaren kan verifiera senaste kompletta snapshot och konfigurerat scope utan att läsa featurepayloaden. Detta verifierades i projektledarens read-only inventory #17 den 2026-11-25.

**Senaste kompletta snapshot – 2026-11-27**
[Run 46036924262](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46036924262) avslutades completed/success. Manifestet `data/samrad_latest_manifest.json` pekar på `data/samrad_snapshots/samrad_20261127T165048Z.json.gz` (400 407 byte; SHA-256 `a1dbf827259537d4680af1f650ee483d5fea4331d8b82726fa9a444f8f505a2a`). Alla tre lager är paginerade till uttömning och har noll saknade/felaktiga geometrier: 0 punkter, 9 linjer och 12 polygoner inom scope; linjelagret hämtade 18 poster i envelope (9 utanför scope), polygonlagret 14 (2 utanför scope). `source_total_reconciled=false`; detta bevisar inte nationell täckning eller avstämning mot källtotal.

**Separat litet snapshotmanifest – implementation mergad och liveverifierad**
Skog PR [#606](https://github.com/dahlinrobert-lgtm/Skog/pull/606) mergades 2026-11-24 i commit `917fa445559413385a0c995d448c1203d0520c2a`. Insamlingsflödet skapar nu `data/samrad_latest_manifest.json` separat från feature-snapshoten. Manifestet innehåller snapshotreferens, gzip-SHA-256, scope-hash samt per-lager sid-/antal-/geometristatus. Saknad eller felaktig geometri räknas explicit och hindrar `complete_for_configured_scope`. Statusen avser endast paginerad och geometriskt klassificerad data inom konfigurerat scope; `source_total_reconciled=false` betyder att källans totala antal inte är avstämt.

PR #606:s CI körde Samråd-tester och händelsekedjetester med godkänt resultat före merge. Liveverifiering skedde genom projektledarens [read-only inventory #17](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45674653249): manifestet `data/samrad_latest_manifest.json` identifierade snapshoten från 2026-11-25 16:41:33.484740 UTC som `manifest_complete_for_configured_scope`. Resultatet omfattade 0 punkter, 9 linjer och 12 polygoner inom det konfigurerade 10 km-scope; pagineringen var uttömd och inga saknade/felaktiga geometrier rapporterades. `source_total_reconciled=false`; ingen nationell täckning eller kommersiell/kundvisningsrätt följer av detta.

**Historik/tidsserie**
Målet är dagliga snapshots där källans ID, geometri, attribut, hämtningstid och källans egna datum bevaras. Försvunna objekt ska först klassas efter en komplett och godkänd skanning. En lyckad körning eller komplett paginering inom pilotområdet bevisar inte nationell täckning.

**Rättigheter**
Skogsstyrelsens officiella villkor bekräftar CC0 1.0 för egenproducerade geodata om inget annat anges. Fri kommersiell användning, bearbetning, lagring och distribution följer för lager som omfattas. Kontrollera undantag i respektive produktmetadata och håll teknisk tjänsteåtkomst separat från licensrätten.

**Framtida användning**
Visa samråd som kan beröra en fastighet och skilj tydligt mellan ärende, planerad åtgärd och genomförd åtgärd.

**Tjänstegränser och anropsrisk (verifierat 2026-11-27)**
Skogsstyrelsens ArcGIS REST-metadata anger `MaxRecordCount=2000` på tjänsten och på vart och ett av de tre Samråd-lagren (punkt, linje och polygon). Alla tre lager stöder paginering. Collectorn använder `PAGE_SIZE=300` och hämtar lagren sekventiellt. Minsta anropsintervall och rate limits är inte publicerade/verifierade; collectorn har ingen explicit retry/backoff. Serverns postgräns är alltså känd, men säker maximal anropsfrekvens är det inte. Riskbedömningen förblir partial och uppskalning är inte godkänd.

### 4.3 Skogsstyrelsen – skogliga grunddata och volym omdrev 3

**Prioritet:** Hög  
**Datatyp:** raster och tillhörande produktmetadata.

**Nuvarande läge**
Rasterprodukter har laddats ned eller undersökts och används som skogligt analysunderlag. Originalarkiv och metadata ska hållas åtskilda från bearbetade produkter.

**Historik/tidsserie**
Spara varje tillgänglig produktversion med produktnamn, version, publicerings-/produktionsdatum, hämtningstid, CRS, upplösning, filstorlek och SHA-256. Jämförelser mellan versioner ska göras först när deras semantik och täckning är jämförbara.

**Rättigheter**
Skogsstyrelsens generella villkor anger CC0 1.0 om inget annat anges. Det omfattar fri kommersiell användning, bearbetning, lagring och vidare distribution av den produkt som omfattas. Kontrollera produktens metadata och eventuella undantag eller tredjepartsinslag.

**Framtida användning**
Skogligt grundunderlag, volymindikatorer och jämförelser över tid. Ingen komplett nationell tidsserie ska påstås finnas innan den är verifierad.

### 4.4 Skogsstyrelsen – Ståndortsindex SIS

**Prioritet:** Hög  
**Källa:** [SIS ImageServer](https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/SIS_1_0/ImageServer)  
**Produkter:** SIS Gran och SIS Tall. Produktbeskrivningen är daterad 2026-10-02.

**Nuvarande läge**
Produkten och tjänsten är identifierade. Metadataövervakning och återkommande geodataflöde har byggts/undersökts. I projektloggen finns misslyckade metadataövervakningskörningar 13–14 november som behöver felsökas; detta ska inte beskrivas som ett verifierat fungerande nationellt rasterarkiv.

**Historik/tidsserie**
Målet är återkommande metadata- och rasterversioner. Bevara produktversion och rasterfil, och jämför endast versioner med kompatibel täckning, upplösning och definition.

**Rättigheter**
De generella geodatavillkoren anger CC0 1.0 om inget annat anges. SIS-produktbeskrivningen har en särskild licens-/erkännandesektion; den ska fortfarande kontrolleras mot den generella huvudregeln innan produkten slutligt klassas för kommersiell distribution. Källhänvisning rekommenderas.

**Framtida användning**
Ståndortsunderlag för fastighetsspecifik skoglig analys. SIS ska inte blandas ihop med SIH, som baseras på mätningar i befintligt bestånd.

**Nästa steg**
Felsök workflow, kontrollera konto-/tjänstevillkor och dokumentera exakt vilka raster som går att hämta och arkivera.

### 4.5 SLU – Torvkarta 1.0

**Prioritet:** Hög  
**Källa:** [SLU Torvkarta](https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/torvkarta/)

**Nuvarande läge**
Torvkartan har identifierats som en SLU-produkt. Raster och produktbeskrivning har undersökts. Skogsdatalabbets tjänster och separat nedladdning har undersökts.

**Historik/tidsserie**
Veckovis kontroll av metadata och tillgängliga produktversioner är målet. En ny snapshot betyder inte att själva källprodukten uppdaterats den veckan.

**Rättigheter**
Skriftligt besked från SLU mottogs 2026-11-02: nuvarande Torvkarta får användas fritt även kommersiellt med följande källhänvisning:

> Källa: Torvkarta, Institutionen för Skogens Ekologi och Skötsel, SLU

Beskedet ska sparas som rättighetsunderlag. Det ger inte automatiskt rätt att distribuera underliggande Lantmäteriets originaldata.

SLU har uppgett att en ny Torvkarta planeras via Skogsstyrelsen i december 2026 under CC0. Detta är ett framtida besked; kontrollera slutlig produkt, metadata och licens när den publiceras.

**Framtida användning**
Torvmark, organiska jordlager, markförhållanden och klimat-/skogliga analyser.

### 4.6 Skogsstyrelsen – statistikdatabasen

**Prioritet:** Medelhög

**Nuvarande läge**
Källan är identifierad men en färdig återkommande Skogskoll-integration är inte verifierad.

**Historik/tidsserie**
Hämta relevanta tabeller återkommande med uttagsdatum, tabell-ID, variabeldefinitioner, enheter och eventuell revidering.

**Rättigheter**
CC0 för statistikdata enligt identifierade villkor. Rapporter, analyser, foton och illustrationer kan ha andra villkor.

**Framtida användning**
Regionala och nationella jämförelser samt kontext till fastighetens egna observationer.

### 4.7 Skogsstyrelsen – geodatatjänster och användarkonto

Ett konto för Skogsstyrelsens geodatatjänster har erhållits och används för att undersöka tillgängliga tjänster. Kontoåtkomst är inte samma sak som rätt till alla produkter eller alla typer av återanvändning.

Skogsstyrelsen har uppgett att vissa äldre produkter, bland annat äldre Markfuktighetskartan och Trädhöjd, är begränsade till myndigheter som deltar i Geodatasamverkan.

**Nästa steg:** inventera vilka produkter kontot faktiskt ger åtkomst till och dokumentera tekniska villkor, licens och exportmöjligheter per produkt. Förvara autentiseringsuppgifter i hemlighetshantering, aldrig i källkod.

### 4.8 Trafikverket – Miljöwebb Landskap

**Käll-ID:** `trafikverket.miljoweb_landskap`  
**Prioritet:** Medelhög  
**Källa:** [MWLEXGEO MapServer](https://vektor.trafikverket.se/gis/rest/services/MWLEXGEO/MiljowebbGeo/MapServer)

Innehåller bland annat viltpassager, artrika väg- och järnvägsmiljöer, invasiva arter, kulturmiljöer och vattenfaunapassager.

**Nuvarande läge**
Inventering och geometrisk snapshotinsamling för Gräsmyr-pilotområdet har utvecklats. Dokumenterat workflow körs varje måndag 05:50 UTC. Daterade gzip-komprimerade GeoJSON-filer och manifest sparas under `data/trafikverket/snapshots/YYYY-MM-DD/`, med kontrollsummor och validering av täckning.

**Historik**
Snapshots är veckovisa observationer av tjänsten; det innebär inte att Trafikverket uppdaterar varje lager varje vecka. Pilotområdet är en ungefärlig geografisk sökruta, inte en fastighetsgräns.

**Rättigheter**
Kontrollera exakt produkt och metadata före kundpublicering. Trafikverkets öppna data är normalt CC0 när produkten uttryckligen tillhandahålls som öppen data.

**Framtida användning**
Miljö- och infrastrukturinformation i närheten av bevakade fastigheter.

### 4.9 Trafikverket – NVDB Viltolyckor

**Käll-ID:** `trafikverket.nvdb.wildlife_collision_frequency`  
**Prioritet:** Hög  
**Källa:** [Viltolyckor NVDB MapServer](https://vektor.trafikverket.se/gis/rest/services/NVDB_p%C3%A5_karta/Viltolyckor_NVDBpakarta/MapServer)

Tjänsten innehåller sju lager med aggregerade olycksfrekvenser per vägsegment: klövvilt totalt, älg, vildsvin, rådjur, ren, kronhjort och dovhjort.

**Nuvarande läge**
Tjänsten är inventerad och ingår i Trafikverkets veckovisa snapshotflöde för Gräsmyr-piloten.

**Viktig begränsning**
Detta är aggregerad olycksfrekvens per vägsegment, inte enskilda olyckor med händelsedatum och exakt olycksposition.

**Rättigheter**
Kontrollera exakt produktvillkor och metadata. Teknisk åtkomst bevisar inte i sig rätt till kommersiell vidare distribution.

**Framtida användning**
Visa risk-/frekvensunderlag per vägsegment. Presentera det inte som en lista över faktiska nyligen inträffade olyckor.

### 4.10 Trafikverket – NVDB vägnät och Lastkajen

**Käll-ID:** `trafikverket.nvdb.road_network_lastkajen`  
**Prioritet:** Hög

**Nuvarande läge**
- Ett Lastkajen-material har bearbetats lokalt. Projektanteckningar anger ett attributindex med 455 812 poster, geometrier och attribut, EPSG:3006, SHA-256-kontroller och spatialt R-tree-index.
- OneDrive-mappen `Skogskoll/Lastkajen/Länsfiler NVDB data` inventerades via Microsoft Graph 2026-11-16: 21 länsvisa GeoPackage-ZIP-filer, totalt 10 677 114 317 byte (cirka 10,68 GB). Filinventeringen omfattar samtliga 21 länsfiler.
- Inventeringen bekräftar filernas existens och storlek, inte att GeoPackage-lagren, vägnummerlagrets schema, CRS eller feature-täckning är kompatibla. Detta ska verifieras lokalt med `scripts/inventory_nvdb_county_archives.py`, som läser lager-/metadata via GDAL `/vsizip/` utan att extrahera eller ändra originalarkiven.
- Nationell vägmatchning är ännu inte körd. Befintlig närmaste-vägmodell är fortsatt review-only.

**Historik**
Detta är en nationell filbaslinje i OneDrive, inte ett verifierat automatiskt uppdaterings- och förändringsflöde. Ingen nationell feature-täckning eller komplett vägdatabas är ännu bekräftad.

**Rättigheter**
Dokumentera exakt produktpaket, leveransvillkor och tillåten lagring/kundvisning.

**Framtida användning**
Vägidentifiering, avståndsberäkning, olycksmatchning och geografisk kontext. Håll NVDB-vägnät, aggregerade olycksfrekvenser och enskilda olyckshändelser som separata datamängder.

### 4.11 Nationella Viltolycksrådet (NVR)

**Prioritet:** Hög

**Nuvarande läge**
- Historiskt material från 2015–2026 har hämtats och delats upp per år.
- Äldre händelsearkiv och djurbaserat material hanteras separat.
- Backup med SHA-256-kontroll har genomförts.
- Ett 30-dagars dagligt observationstest har startats.
- Importkörningen 2026-11-09 rapporterades som `partial`; fullständighet/jämförbarhet var inte intygad och saknade händelser undertrycktes.

**Historik/tidsserie**
Dagliga observationer testas för att mäta hur snabbt nya olyckor blir tillgängliga. Kontrollera exportjämförelser, dagsarkiv och att ofullständiga uttag inte skapar falska borttagningar.

**Rättigheter och åtkomst**
Dokumentera uttryckligt godkännande, kontakt, datum, ändamål, historisk åtkomst och tillåtelse till återkommande hämtning. Bedöm separat lagring, bearbetning, kundvisning och vidare distribution.

**Framtida användning**
Faktiska olyckshändelser, djurslag, historiska mönster och geografisk matchning. NVR ska hållas åtskilt från Trafikverkets aggregerade vägsegmentdata.

### 4.12 Viltdata – avskjutningsstatistik

**Prioritet:** Medelhög

**Nuvarande tekniskt läge**
- Källan är Viltdata.se:s publika `StatisticsApi`, rapporttyp `kill`. Det gäller rapporterad avskjutningsstatistik, inte NVR-viltolyckor eller en populationsinventering.
- `scripts/viltdata_kill_statistics_snapshot.py` hämtar arter som källmodellen markerar för avskjutning, län och nationella/länsvisa årsserier. Original-JSON bevaras med manifest och SHA-256.
- Två kompletta nationella snapshots har nu live-verifierats 2026-11-18:
  - Snapshot `20261118T204420Z`, körning [#44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179): 49 arter, 21 län, 550/550 statistikförfrågningar, 552 filer SHA-256-verifierade, 73 255 datapunkter.
  - Snapshot `20261118T220720Z`, körning [#44408345762](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44408345762): 49 arter, 21 län, 550/550 statistikförfrågningar, noll fel, 552 filer SHA-256-verifierade, 73 255 datapunkter (3 364 null, 24 950 explicita nollvärden). Källans periodetiketter är nationellt 1939–2026 och länsvis 1960–2026. Artifact ID `14475804318`, 423 705 byte, ZIP-SHA-256 `31ef0b6ac7c16fa524adaa9f1e5ed9037f19bd3a9cb714bdea16e6ad8264e0b2`, manifest-SHA-256 `ed7937c8f83657b51af98f88566cce675555d0a4d017111f3fb7a24ecdc72088`, retention till 2026-12-18 22:24:19 UTC.
- Körning #44408345762 kompilerade båda skripten och passerade 10/10 riktade tester. Manifestets status var `complete` och `complete=true`; alla 550 förväntade statistikförfrågningar lyckades.
- `scripts/viltdata_kill_statistics_diff.py` jämför endast kompletta snapshots med samma observationstäckning. Den första jämförelsen mellan de två snapshotsen är nästa steg och ska sparas i en separat outputmapp. Null och noll förblir distinkta.
- `complete=true` innebär teknisk insamlingsfullständighet; det betyder inte att alla rapporteringsår är slutrapporterade. Värden för pågående rapporteringsår kan revideras vid senare uttag.

**Historik**
Bevara daterade snapshots, originalvärden, definitioner, artidentiteter och geografisk omfattning. Ofullständiga körningar får inte användas som baslinje eller diffunderlag. Första kompletta baslinjen ska inte skapa historiska larm.

**Lagring**
- Båda verifierade snapshots är tidsbegränsade GitHub Actions-artifacts med 30 dagars retention; de är inte permanent historik eller backup. Den andra artifacten är ID `14475804318` och löper ut 2026-12-18 22:24:19 UTC.
- Azure Blob Storage är verifierat för syntetiska testobjekt, men inga Viltdata-original har laddats upp. Storage Account `stskogkolldata` ligger i `swedencentral` (Sweden Central). OIDC-identiteten `skogskoll-github-actions` har `Storage Blob Data Contributor` på Storage Account-scope och delas med andra Skog-workflows.
- PR #427 är mergad i `main`. `scripts/viltdata_azure_archive.py` och `.github/workflows/viltdata-azure-archive.yml` tillhandahåller manuell upload, djup audit och restore. Upload kräver komplett manifest och SHA-256-verifierade originalfiler, använder create-only och är spärrad bakom `rights_approved` (default false). PR-CI #476 och main-CI #483 passerade 322 tester vardera. Azure upload/audit/restore är ännu inte live-verifierade.

**Rättigheter**
Teknisk åtkomst till den publika API-tjänsten är inte ett godkännande för permanent historisk lagring, kommersiell användning, bearbetning, kundvisning eller vidare distribution. Användaren har skickat mejl till dataleverantören; skriftligt besked om exakt statistikprodukt och avsedda användningar inväntas.

**Framtida användning**
Avskjutning, älgförvaltning och regionala jämförelser. Statistik ska inte framställas som enskilda observationer av djur.
### 4.13 Lantmäteriet – Fastighetsindelning Direkt (OAPIF)

**Prioritet:** Mycket hög för fastighetsfunktionen  
**Produkt:** [Fastighetsindelning Direkt API](https://geotorget.lantmateriet.se/geodataprodukter/fastighetsindelning-direkt-api)  
**API:** `https://api.lantmateriet.se/ogc-features/v1/fastighetsindelning`

**Nuvarande läge**
- Officiell OAPIF-produkt har valts som framtida lösning.
- Interna endpoints från Min karta ska inte användas i produktion.
- Manuell teknisk diagnostik har genomförts.
- Formella beställningar/ärenden har registrerats 2026-11-13: LM2026/171963 och LM2026/171968. Detaljerat beslut och omfattning måste verifieras i Geotorget innan status sätts till beviljad.

**Uppdatering**
Produktinformationen anger daglig uppdatering. Det betyder inte att Skogskoll redan har en daglig historik.

**Rättigheter**
Produkten beskrivs som avgiftsfri men kräver beställd API-behörighet och juridisk prövning/användningsvillkor. Kommersiell användning, lagring, historik, bearbetning, kundvisning och vidare distribution ska bedömas var för sig.

**Framtida användning**
Användaren söker kommun, trakt och fastighetsbeteckning; väljer rätt registerenhet; backend hämtar geometri; användaren granskar och bekräftar; geometri lagras som WGS84 Polygon/MultiPolygon. Flera delområden måste bevaras.

Geometrierna är vägledande översiktsunderlag och inte juridiskt gällande gränsbevis. API-nycklar ska hanteras server-side och aldrig exponeras i webbläsaren.

### 4.14 Lantmäteriet – Ortnamn Nedladdning, vektor

**Prioritet:** Hög för geografisk tolkning av polisens platsbeskrivningar i den interna Luleå Police–NVR-piloten.

**Teknisk åtkomst**
- Geotorget-behörighet finns på användarens konto.
- STAC API: `https://api.lantmateriet.se/stac-vektor/v1`
- Collection: `ortnamn`; item: `ortnamn_se`.
- Nationell GeoPackage i EPSG:3006.
- Autentiserad ZIP-nedladdning verifierades 2026-11-13 med HTTP Basic: 58 553 634 byte; innehåller `ortnamn_se.gpkg` (156 000 256 byte).

**Nuvarande läge**
- Teknisk nedladdning är verifierad. Den lokala read-only-inspektionen 2026-11-15 identifierade ett lager (`ortnamn`), 990 073 objekt, EPSG:3006 och 53 namnträffar för Sunderbyn/Notviken.
- Kommunurval med `kommunkod=2580` gav 11 poster i det granskade namnträffsutdraget: Norra Sunderbyn (1), Sunderbyn (1), Södra Sunderbyn (2), Notviken (6) och Notvikens badplats (1). Notviken-posterna har olika `detaljtyp`-värden. Koderna ska bevaras som källvärden; semantik ska följa verifierad produktkodlista.
- Inspektionsskript: `scripts/inspect_ortnamn_geopackage.py`. Ett separat read-only kommunexportskript har lagts till i utvecklingsbranch `feat/ortnamn-lulea-reference-export`: `scripts/export_ortnamn_municipality_reference.py`. Det exporterar alla objekt för vald kommunkod, attribut, geometriuppgifter och källfilens SHA-256.
- `lopnummer` är endast bevarat som källattribut; använd det inte som stabilt/unikt ID. `source_row_index` gäller endast aktuell källsnapshot. Exporten bevarar källattribut och ändrar inte GeoPackage-filen.
- Full kommunexport kördes lokalt 2026-11-15 med status `completed_read_only`: 6 239 objekt för kommunkod 2580 från 990 073 nationella objekt, EPSG:3006. Källfilens SHA-256: `3a3d26bc3ec95142f47208cc6afaff45a70e5ee04417f770d058777a5465a92d`.
- Fördelning per källans `detaljtyp`: TERRTX 2 314; TRAKTTX 866; BEBTX 806; SANKTX 680; VATTTX 568; VATTDELTX 435; VATTDRTX 371; ANLTX 68; NATTX 58; KULTURTX 48; BEBTÄTTX 19; KYRKATX 6. Koderna bevaras som råa källvärden; semantik ska verifieras mot Lantmäteriets aktuella kodlista.
- Kommunexportens CSV och JSON-rapport ligger i användarens OneDrive working-mapp och har inte committats. Käll-GeoPackage har inte ändrats.
- Exportverktygets fyra enhetstester passerade lokalt. De 11 posterna ovan avser endast det tidigare Sunderbyn/Notviken-namnträffsutdraget, inte hela kommunen.
- Nästa analyssteg är att använda den kommunala exporten för att välja relevanta ortnamnsreferenser till NVDB-granskningen. Inga automatiska Police–NVR-matchningar ska skapas.

**Avsedd användning**
Använd ortnamn som namn- och områdesreferens för att tolka polisens text, exempelvis Sunderbyn, Södra Sunderbyn och Notviken. Kombinera därefter med NVDB:s vägnummer, korsningsobjekt och sammanhängande vägnät. Ortnamn är en referenskälla, inte en olycksdatakälla.

**Viktig begränsning**
Ortnamnspunkter kan vara kartografisk textplacering och ska inte tolkas som exakta ortscentrum, ortsgränser eller olyckspositioner. Behåll geometri, objekttyp, avstånd och osäkerhet separat. Tekniskt åtkomstbesked är inte ett beslut om kommersiell användning, historisk lagring, bearbetning, kundvisning eller vidare distribution; dessa villkor ska granskas separat.

**Luleå Police–NVR: lokal väg 97-diagnostik (2026-11-15)**
En separat lokal analys byggde en cirka 9,26 km lång vägsektion mellan ortnamnsankare för Sunderbyn och Notviken genom 22 vägobjekt ur användarens vägnummer-GPKG. Ankarnas avstånd till väg 97-objekt var 14,3 m respektive 26,45 m. NVR-händelse `2026-348394` låg 3,0 m från den härledda sektionen; händelse `2026-348777` låg 11 478,39 m bort. Resultaten är endast diagnostiskt granskningsunderlag och ändrar inte temporal matchning eller kandidatstatus.

Tolkningen har en kvarstående osäkerhet: polistexten anger Södra Sunderbyn, men vägsektionens använda ortnamnsankare var Sunderbyn (TRAKTTX). En Södra Sunderbyn-referens av typen BEBTÄTTX låg cirka 984 m från väg 97 i den använda vägnummerfilen. Ortnamnens objekttyp och ankarval måste därför granskas innan vägsektionen kan anses motsvara polisens text.

Vägnummer-GPKG-filen har ett annat schema än NVDB-lagren som `scripts/enrich_police_nvr_geography.py` kräver. Den lokala analysen verifierar därför inte pipeline-skriptets reproducerbarhet. Nästa steg är att välja flera Luleå-testfall ur de lokala Police- och NVR-underlagen och genomföra separat regression av temporal matchning. Ingen automatisk matchning eller bekräftelse har gjorts.

### 4.14 Lantmäteriet – fastighetsprisregistret

**Prioritet:** Separat analysmöjlighet

Ett separat beställnings-/åtkomstspår har undersökts för historiska fastighetspriser. Det är inte samma produkt som Fastighetsindelning Direkt.

**Framtida användning**
Fastighetsmarknadsanalys, jämförelser och värderingsunderlag. Användningen måste följa det faktiska beslutet och villkoren för uttaget. Ingen kundpublicering ska antas tillåten innan rättigheterna är klarlagda.

### 4.15 Naturvårdsverket – skyddade områden och miljödata

**Prioritet:** Hög

**Nuvarande läge**
Datakataloger och geodatatjänster har undersökts. Exakta dataset och informationsansvariga måste identifieras per lager.

**Historik**
Bygg snapshots när källan och användningsbehovet motiverar det. Spara beslutstidpunkt, publiceringstidpunkt och insamlingstid separat.

**Rättigheter**
Villkorad grön per dataset. Kontrollera producent, metadata och eventuella tredjepartsrättigheter.

**Framtida användning**
Skyddade områden, naturreservat, biotopskydd och andra miljöförhållanden som kan påverka skogsbruk.

### 4.16 Länsstyrelserna – Vindbrukskollen

**Prioritet:** Medelhög

**Nuvarande läge**
Datainnehåll och geometrier har undersökts. Tidigare arbete omfattar en insamlingspilot och kontroll av objekt/geometrier.

**Historik**
Återkommande snapshots behövs för att bevara projekt, anläggningar och statusförändringar. Verifiera nationell täckning och varje körnings fullständighet.

**Rättigheter**
Undersökta datalager har metadata med CC0. Bakgrundskartor och kartografiskt material har separata upphovsrättsvillkor. Hämta data, inte skärmbilder eller bakgrundskartor.

**Framtida användning**
Befintliga och planerade vindkraftsprojekt i närheten av bevakade fastigheter.

### 4.17 Länsstyrelserna – diarier och ärenden

**Prioritet:** Medelhög

**Nuvarande läge**
Den publika webbdiarievyn har testats med länsvisa och frasavgränsade sökningar. Två manuella pilotkörningar för Norrbotten, kategori B, har verifierats för september och oktober 2026. Samtliga sex frasintervall var kompletta och avstämda i respektive körning. Det visar reproducerbarhet i den avgränsade piloten, inte nationell täckning eller fullständig diarietäckning.

En separat manuell discovery-workflow finns nu i `main` efter merge av PR #406: sju grupper om tre län, en kategori per körning och högst 18 län/frasintervall. Den delar länen i sju grupper om tre, kör en kategori per körning (högst 18 län/frasintervall) och sparar endast diagnostikartefakter i 30 dagar. Den skriver inte snapshots eller manifest till repot. Workflowen är ännu inte live-testad; länsnamn och CLI-beteende måste bekräftas i första kontrollerade körningen. Den befintliga månadsworkflowen publicerar däremot kompletta snapshots direkt till `main` och ska inte användas för nationell discovery.

**Paginering och avstämning – korrigeringar verifierade 2026-11-27**

Den tidigare pagineringskorrigeringen för glidande sidfönster finns i `main` via PR #610 och pager-DOM-diagnostiken via PR #647. Den specifika övergången med framåtriktad `Page$1` behöver fortfarande bevisas i en kontrollerad livekörning.

[PR #695](https://github.com/dahlinrobert-lgtm/Skog/pull/695) är nu också mergad. Den korrigerar en separat avstämningsbugg: portalens rapporterade total avser resultatrader, medan insamlarens resultatlista dedupliceras över sidor. I Blekinge-körning [#46011210069](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46011210069) var sidornas råa rader 50 + 50 + 43 = 143, men åtta överlapp gjorde att 135 unika diarienummer återstod. Tidigare kod jämförde 135 unika poster direkt med källans 143 rader och underkände därför en i övrigt fullständigt läst sökning.

Efter PR #695 jämförs källtotalen med kumulativa råa resultatrader; unika län/diarienummer fortsätter användas för deduplicering och lagring. Okänd källtotal, färre lästa rader än rapporterat eller ej uttömd paginering ger fortsatt underkänt resultat. Persistenssteget kontrollerar råa rader och unika poster separat.

**Verifiering efter merge**
- [Snapshot storage tests #607](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066108336): hela testsviten passerade.
- [Diary history audit #75](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066108277): regressionstester och historikaudit passerade.
- Audit-artifact [15231096142](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066108277/artifacts/15231096142): 3 910 state records och 41 565 eventrader; inga duplicerade event-ID:n, eventnycklar utan state record, okända eventtyper eller borttagningsslutsatser. 18 äldre observation_count-mismatchar kvarstår som historikluckor och ska inte fyllas med påhittade retroaktiva events. Auditens `ok=true`.

**Liveverifiering efter merge (2026-11-27)**

- [Run #19](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46067066036), Blekinge/`av`/oktober 2026: 253/253 unika diarienummer, sex sidor, `pager_complete=true`, inga processfel. Den sista pager-DOM:en visade en bakåtriktad `Page$1`-ellipsis; den valdes inte. Detta verifierar vanlig flersidespaginering men inte framåtriktad fönsterövergång.
- [Run #20](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46067888304), Blekinge/`vattenverksamhet`/oktober 2026: källan rapporterade 18 träffar och 18 unika poster extraherades på en sida, `pager_complete=true`, inga dubbletter och inga pager-actions. Den tidigare avvikelsen 143 råa rader/135 unika poster kunde inte återtestas eftersom källresultatet nu var 18.
- Båda körningarna använde `diagnostics_only_no_persistence`; inga snapshots eller manifest publicerades.

**Liveprov #21 – åtta sidor och framåtriktat pagerfönster (2026-11-27)**

[GitHub Actions #21](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46068669201), Blekinge, frasen `an`, oktober 2026: källtotal 392 och 392 unika diarienummer extraherades över åtta sidor. Råa rader per sida: 50, 50, 50, 50, 50, 50, 50 och 42 (summa 392). Inga dubbletter av diarienummer eller case-ID. `pager_complete=true`, `reconciled=true`, noll processfel.

På logisk sida 5 valdes portalens framåtriktade ellips `Page$6`; diagnostiken visar både `response_seen=true` och `page_changed=true`. Efter fönsterförflyttningen visade portalen `<< ... 4 5 6 7 8`; bakåtriktade ellipsen `Page$3` efter `Page$First` valdes inte. Därefter hämtades sidorna 6–8 via numeriska länkar. Pager-/navigationsrader (två per sida) räknades inte som diarierader.

**Avgränsning:** liveverifieringen visar framåtriktad ellipsfunktion med `Page$6`, inte specifikt specialkommandot `Page$1`. Det ursprungliga 143 råa/135 unika-fallet med överlapp testades inte här, eftersom run #21 hade 392 råa och 392 unika poster utan dubbletter. Den framåtriktade `Page$1`-varianten och ett livefall med överlapp är därför fortsatt separata verifieringspunkter. Run #21 var diagnostics-only; inga snapshots eller manifest skrevs.

**Read-only inventory #42 – verifiering 2026-11-27**

Projektledarens [inventory #42](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/46064154483) verifierade 36 manifestrader och 36 motsvarande snapshotfiler; 36/36 intervall uppfyllde adapterkraven för kompletta query-intervall. Det är inte nationell täckning eller en uttömmande diarieförteckning. Adaptern hämtar inte handlingar eller bilagor.

Källans rättighetsbedömning och kundvisningsstatus ändras inte av PR #610, #647 eller #695. Senaste kompletta arkiverade observation ligger fortsatt kvar från 2026-11-16 och gäller endast Norrbotten, frasen `omgrävning av vattendrag`, registreringsperiod september 2026, 0 träffar.

**Historik**
Bevara metadata, dokument-ID, källa och hämtningstid. Månatliga snapshots kan bevara observationer som senare försvinner ur webbdiariet. Ofullständiga sökningar får inte behandlas som kompletta, och frånvaro är inte bevis för att ett ärende har tagits bort. Dokumentbilagor ska hanteras separat från metadata.

**Rättigheter**
Bedöm varje handling. Offentlighet innebär inte automatiskt fri kommersiell återpublicering. Länsstyrelsens tekniska begränsningar måste beaktas innan obevakad eller återkommande hämtning. Sekretess, personuppgifter, upphovsrätt och tredje mans rättigheter måste kontrolleras. Kundvisning är fortsatt inte godkänd generellt.

**Framtida användning**
Identifiera relevanta myndighetsärenden och beslut. Börja eventuell nationell täckningskontroll med en manuellt vald grupp i taget och utvärdera portalens belastning och felmönster. Aktivera inte schema och publicera inte automatiskt fullständiga dokument eller personuppgifter i kundprodukten.

### 4.18 Övriga identifierade källor

| Källa | Nuläge/rättighetsläge | Möjlig användning |
|---|---|---|
| SMHI öppna data | CC BY 4.0 SE enligt identifierade villkor; attribution och ändringsuppgift krävs | Väder, klimat och riskkontext |
| Copernicus Sentinel | Öppna Sentinel-villkor; portalens övriga innehåll kan ha andra villkor | Satellitbaserad förändringsanalys |
| SGU geologiska data | CC0 för geologiska data enligt identifierade villkor | Jordarter, berggrund och markförhållanden |
| SCB öppna data | CC0 för öppna data; API-gränser gäller | Regional och nationell statistik |
| Kolada API | Kommersiell användning tillåten enligt identifierade villkor; ange Källa: Kolada | Kommunala jämförelser |
| MSB WMS/geodata | Villkor måste kontrolleras per lager; WMS-åtkomst är inte återpubliceringsrätt | Risk- och beredskapsinformation |
| Life2Taiga | Gul; producent och licens för specifikt lager behöver klarläggas | Naturvårdsåtgärder |
| Sveaskog och SCA | Kräver uttryckliga rättigheter/avtal för aktuell användning | Eventuella datapartnerskap |
| Skogsindustrierna | Villkor måste klarläggas per tjänst/lager | Bransch- och skoglig kontext |
| Rovbase – historiskt uttag av döda rovdjur | Teknisk export mottagen och preliminärt kvalitetsgranskad 2026-11-18. Kommersiell användning, historisk lagring, bearbetning och kundvisning är inte bedömda; datakällan är ännu inte registrerad i `sources.yml`. | Intern analys och geografisk kvalitetssäkring efter rättighets- och källvillkorsgranskning |

## 5. Samlad väntelista och nästa åtgärd

| Spår | Vad som återstår | Rekommenderad uppföljning |
|---|---|---|
| Lantmäteriet Fastighetsindelning Direkt | Verifiera beslut, behörighet och tillåtna användningar i LM2026/171963 och LM2026/171968 | Kontrollera Geotorget och spara beslut/villkor |
| Lantmäteriet fastighetsprisregister | Separat uttag och användningsvillkor | Följ upp ansökan och dokumentera beslut |
| SLU Torvkarta | Ny produkt väntas i december 2026 | Kontrollera publicering, CC0, metadata och raster |
| SIS | Misslyckade metadataövervakningskörningar 13–14 november; särskild licenssektion | Felsök workflow och läs produktvillkor |
| NVR | Dagligt 30-dagarstest, fullständighet och dokumenterat godkännande | Kontrollera dagliga arkiv och exportjämförelser |
| Skogsstyrelsen avverkningsanmälningar | Fullständig ingestion och validerad baslinje | Jämför kompletta skanningar |
| Samråd | Verifiera snapshotstatus per lager | Kontrollera manifests, körningar och täckning |
| Miljöwebb Landskap | Verifiera täckning och senaste kompletta snapshots för Gräsmyr-piloten | Kontrollera måndagskörning, manifest, antal och lagervillkor || NVDB Viltolyckor | Verifiera frekvensdefinition, referensperiod och jämförbar historik | Kontrollera sju lager, produktmetadata och snapshots |
| NVDB vägnät/Lastkajen | Verifiera produktversion, beställningsvillkor och återkommande uppdatering | Dokumentera lokal baslinje och bygg versionsstyrt uppdateringsflöde |
| NVDB vägnät | Automatiskt uppdateringsflöde saknas | Planera versionsbaserad uppdatering |
| Viltdata älg | Nationell täckning saknas | Utöka från regional pilot efter källinventering |
| Naturvårdsverket | Exakta prioriterade lager och producentvillkor | Välj lager och dokumentera metadata |
| Vindbrukskollen | Nationell historik och fullständighet | Verifiera återkommande snapshotflöde |
| Länsstyrelsernas diarier | PR #610 (pager-riktning), #647 (pager-DOM-diagnostik), #695 (råa resultatrader kontra unika diarienummer), #700 och #701/#702 (liveevidens och överlämning) är mergade. Run #21 verifierade live 392 råa rader = 392 unika diarienummer över åtta sidor, inklusive framåtriktad fönsterförflyttning via `Page$6` och avvisning av bakåtriktad `Page$3`. Specifik framåtriktad `Page$1`-övergång är inte livebevisad; 143 råa/135 unika-överlappsfallet är inte återtestat. | Fortsätt med read-only diagnostik för ett livefall som faktiskt använder framåtriktad `Page$1` och, om källan åter erbjuder jämförbara data, ett fall med verkligt överlapp. Jämför inte olika källpopulationer som om de vore samma uttag. Granska metadata separat från dokument/bilagor |
| Rovbase | Fullständig kvalitetsrapport och administrativ koordinatvalidering återstår; 35 RT90-avvikelser och 32 poster med skyddsjakt enskilds initiativ behöver utredas. Rättighets-/användningsvillkor saknas i projektunderlaget. | Kör geografisk validering mot befintligt Lantmäteriet-GPKG; begär källförtydligande och bedöm lagring, analys och kundvisning separat. |

## 6. Hur snapshots och historik ska fungera

Varje insamlingskörning ska få ett unikt run-ID och registrera:
- source_id och dataset_id,
- käll-URL och produkt/lager,
- started_at, retrieved_at och snapshot_date,
- status: complete, partial eller failed,
- antal poster enligt källan och antal hämtade,
- paginering/checkpoint och eventuella begränsningar,
- geografisk täckning och CRS,
- filformat, storlek och SHA-256,
- källans egna datum och versionsuppgifter,
- kod-/insamlarversion.

### Regler för förändringshistorik

1. Identitet ska baseras på källa + stabilt käll-ID, inte enbart geometri eller fastighetsnamn.
2. Oförändrad post är en ny observation av samma objekt, inte en ny händelse.
3. Ändrade attribut eller geometrier ska bevaras som förändringshistorik.
4. En misslyckad eller ofullständig skanning får aldrig markera ej sedda objekt som inaktiva.
5. Försvunna objekt får bara bedömas efter en komplett och godkänd avstämning.
6. Första baslinjen får inte skapa aviseringar om historiska poster.
7. Källans händelsedatum, källans publiceringsdatum och Skogskolls första upptäckt ska hållas isär.
8. En snapshot av en tjänst innebär inte att källans data har uppdaterats vid samma tidpunkt.

## 7. Rättighetsmodell före kundpublicering

För varje exakt produkt/dataset ska följande bedömas separat:

- Teknisk åtkomst och autentisering.
- Kommersiell användning.
- Historisk lagring och cache.
- Bearbetning och kombination.
- Kundvisning.
- Vidaredistribution av originaldata.
- Vidaredistribution av härledda produkter.
- Attribution och krav på ändringsuppgift.
- Personuppgifter, sekretess och tredje mans rättigheter.
- API-kvoter, belastning, cache och andra tekniska villkor.

Status i källregistret är en operativ riskklassning, inte ett juridiskt utlåtande. Oklarheter ska utredas mot tillämplig rätt, produktvillkor och avtal. Ett oklart villkor är inte automatiskt ett totalförbud, men den berörda användningen ska inte aktiveras innan den är bedömd.

## 8. Hur data ska användas i Skogskoll

### 8.1 Fastighetsregistrering
Användaren söker och väljer fastighet, granskar geometri och bekräftar bevakningsområde. Manuell GeoJSON-import ska finnas som reserv.

### 8.2 Insamling
Källor körs med lämpliga intervall:
- händelsekällor: målet är upp till var sjätte timme där källan tillåter och behovet motiverar det,
- dagliga källor: exempelvis samråd eller fastighetsgeometrier där uppdateringsmönstret stödjer det,
- veckovisa källor: raster och långsammare geodata,
- månadsvisa eller behovsstyrda källor: statistik och vissa diarier.

Intervall ska anpassas efter källans faktiska uppdateringstakt, tekniska villkor och kostnad.

### 8.3 Matchning
PostGIS ska matcha observationer mot bevakningsområden med:
- ST_DWithin för radiebevakning,
- ST_Intersects för polygoner.

Matchningen är geografisk och ska inte beskrivas som ett juridiskt besked om ägande, rådighet eller exakt fastighetsgräns.

### 8.4 Händelser och aviseringar
När en relevant observation upptäcks:
1. kontrollera att insamlingen är komplett,
2. kontrollera identitet och om objektet är nytt eller ändrat,
3. jämför mot användarens bevakningsområden,
4. kontrollera valda händelsetyper och samtycke,
5. skapa en spårbar aviseringshändelse,
6. leverera e-post/push,
7. spara resultatet i historiken.

Aviseringar ska vara avstängda tills ingestion, databas, baslinje och källbeteende är verifierade.

## 9. Prioriterad färdplan

### Fas 1 – säkra befintliga flöden
- Verifiera avverkningsanmälningarnas fullständiga ingestion.
- Kontrollera samrådssnapshots per lager.
- Felsök SIS-metadataflödet.
- Fortsätt Torvkarta/SIS-uppföljning.
- Verifiera Trafikverkets veckosnapshots.
- Fullfölj NVR:s 30-dagarstest.
- Dokumentera NVDB:s lokala baslinje och plan för uppdatering.

### Fas 2 – slutför externa rättigheter
- Kontrollera Lantmäteriets beställningsbeslut och villkor.
- Dokumentera NVR:s godkännande, ändamål och villkor.
- Spara SLU:s skriftliga Torvkartabesked.
- Kontrollera SIS och andra rasterprodukters särskilda licenssektioner.
- Bedöm Trafikverkets Lastkajen-produkt separat.

### Fas 3 – gemensam historisk dataplattform
- Standardisera source_id/dataset_id och manifest.
- Säkerställ oföränderliga original och kontrollerade snapshots.
- Bygg datakvalitets- och fullständighetskontroller.
- Verifiera Supabase-adaptrar och transaktionella sidcommits mot ett separat testprojekt.
- Testa backup och återställning.

### Fas 4 – produktionssätt Skogskoll
- Slutför auth, RLS och PostGIS.
- Aktivera säker serverbaserad ingestion.
- Implementera fastighetssökning efter rättighetsbesked.
- Bygg historik och matchning mot verkliga observationer.
- Aktivera aviserings-outbox och e-post/push efter uttryckligt användarval.

### Fas 5 – bredda datainnehållet
Prioritera först avverkningsanmälningar, samråd, fastighetsgeometrier och genomförda avverkningar. Därefter skogliga raster, viltolyckor, naturvård, infrastruktur och relevanta myndighetsärenden.

## 10. Förvaltningsregler

Uppdatera dokumentet och källregistret när:
- en ny datakälla eller produkt läggs till,
- en endpoint, produktversion eller täckning ändras,
- en snapshotserie verifieras eller får avbrott,
- ett licensbesked, avtal eller myndighetsbeslut kommer,
- användningen ändras från intern analys till kundvisning eller vidare distribution,
- en datakälla tas ur drift.

Varje statusändring ska ha datum och evidens: workflow-run, manifest, produktmetadata, beslut eller skriftligt besked.

## 11. Samlad bedömning

Skog har etablerat ett brett underlag av myndighets- och geodatakällor och utvecklat flera viktiga insamlings- och historikflöden. De mest konkreta spåren är Skogsstyrelsens avverkningsanmälningar, samråd, Trafikverkets tre separata produktspår: Miljöwebb Landskap, NVDB Viltolyckor och NVDB vägnät/Lastkajen, samt NVR:s historiska olycksdata. Torvkartan har ett skriftligt kommersiellt användningsbesked från SLU. Lantmäteriets fastighetsprodukt är ett centralt externt beroende som kräver att beställningarnas exakta beslut och villkor verifieras.

Den viktigaste återstående förflyttningen är från separata prober och pilotflöden till en komplett, kvalitetssäkrad och rättighetsbedömd historisk dataplattform. Först därefter ska verkliga kundaviseringar aktiveras.

**Långsiktig målbild:** Skogskoll ska kombinera historiska observationer, myndighetsdata och geografisk matchning till en tillförlitlig, fastighetsspecifik bevakningstjänst för skogsägare.


### NVR – rättighetsbesked från Polismyndigheten (2026-11-15)
Polismyndigheten har bekräftat att NVR-materialet är offentlig information, att CSV-uttaget omfattar de djurposter myndigheten har tillgång till från 2015 och framåt och att återkommande hämtning/arkivering för egen geografisk analys och statistik är tillåten med källhänvisningen **Nationella viltolycksrådet**. Beskedet stödjer inte uttryckligen vidare distribution av rådata eller försäljning av en fristående rådatatjänst. Se [evidensanteckningen](source-rights-reviews/2026-11-15-nvr-public-information-attribution.md).

I bevakningsprototypen ska NVR visas som individuella händelser, inte som Trafikverkets aggregerade vägsegmentfrekvenser. Synlig källtext: **Källa: Nationella viltolycksrådet (NVR)**. En kontrollerad, skrivskyddad publiceringsendpoint med manifest och fullständighetsstatus krävs innan GitHub Pages kan läsa arkivet från OneDrive.


## Police–NVR – nationell NVDB-närmaste-väg-prototyp (2026-11-16)

En separat prototyp har lagts till i utvecklingsbranch `feat/national-nvdb-road-proximity`: `scripts/match_points_to_nvdb_roads.py`. Den kan läsa flera länsvisa GeoPackage-filer och söka efter vägnummerobjekt i ett lokalt, meterbaserat sökfönster runt varje WGS84-händelsekoordinat. Resultatet innehåller närmaste vägnummerobjekt, avstånd och alternativa vägkandidater.

Detta är endast geografisk granskningsinformation. Ett tomt sökfönster bevisar inte att väg saknas; källans geografiska täckning måste vara verifierad. Om en eller flera källfiler inte kan läsas klassas resultatet som partiellt. Temporal matchning, kandidatlista, score, status och `geographic_match_used` ska inte påverkas.

Prototypen är inte nationellt validerad eller produktionsintegrerad. Före nationell körning krävs inventering av Lastkajens faktiska filer och produktversion, verifiering av lager/CRS/täckning, länsgränser, prestanda, representativa manuellt bedömda testfall och separata användningsvillkor för lagring, bearbetning och kundvisning. Full nätverksrekonstruktion ska vara en undantagskontroll, inte standardmetod.


## NVDB – inventering av nationella länsarkiv (2026-11-16)

OneDrive-inventeringen omfattar 21 länsvisa GeoPackage-ZIP, totalt 10 677 114 317 byte. En första inspektionsmetod med `pyogrio.list_layers()` fallerade på samtliga arkiv med samma GDAL-fel för en geometriuppgift. Detta ska inte tolkas som att arkiven är skadade eller att vägdata saknas.

En alternativ read-only-metod har verifierats på Gotland och Västerbotten: fråga `gpkg_contents` via Pyogrio/GDAL:s SQLite-dialekt och öppna därefter endast `NVDB_DK_O_111_Vagnummer` med `pyogrio.read_info()`. Båda testade arkiv hade EPSG:3006 och obligatoriska fält `ELEMENT_ID`, `Europavag`, `Huvudnummer` och `Lankroll`. Antalet objekt var 6 203 respektive 26 902. Båda rapporterade `geometry_type: Unknown`; faktisk geometriinnehållsvalidering återstår.

Den read-only-inspektören i branch `fix/nvdb-direct-layer-inventory` har ändrats för att använda denna riktade metod, registrera CRS/geometriuppgift och markera katalog-/lagerläsfel som `partial`. Ändringen är ännu inte nationellt verifierad. Kör inventeringen mot samtliga 21 arkiv och granska resultatet innan nationell vägmatchning. Nationell matchning ska fortsatt vara review-only, och geografi får inte ändra temporal matchning, kandidatlista, score, status eller `geographic_match_used`.

Teknisk åtkomst och metadata-inspektion innebär inte att kommersiell lagring, bearbetning, kundvisning eller vidare distribution är godkänd.


## NVDB – nationell länsinventering och geometristickprov verifierade (2026-11-17)

Den nationella read-only-inventeringen av Lastkajens 21 länsvisa GeoPackage-ZIP är genomförd. Arkiven omfattar 10 677 114 317 byte (cirka 9,94 GiB) och samtliga 21 har status `compatible` i metadata-/schema-kontrollen för lagret `NVDB_DK_O_111_Vagnummer`. Metadataantalet är totalt **456 444 features**. Obligatoriska fält är `ELEMENT_ID`, `Europavag`, `Huvudnummer` och `Lankroll`.

Ett distribuerat geometristickprov om 500 features per län (totalt **10 500**) har därefter verifierats. Alla län hade CRS **EPSG:3006**, geometritypen **LineString**, 500/500 lästa stickprovsfeatures, 500 giltiga geometrier och noll null-, tomma eller ogiltiga geometrier samt noll stickprovsfel. Rapporten anger `completed`, 21 arkiv och 0 fel. Originalarkiven ändrades inte (`read_only=true`, `source_archives_modified=false`).

**Tolkning och begränsningar:** 456 444 är metadataantal för lagerobjekt, inte antal unika vägar eller vägkilometer. Stickprovet bekräftar inte varje geometri i hela materialet, fullständig geografisk täckning, nätverkskontinuitet eller kvaliteten på alla länsgränsöverlappningar. Det verifierar inte heller att en senare NVDB-version är jämförbar med denna baslinje. Nationell vägmatchning är fortfarande en pilot och ska vara review-only; geografi får inte påverka temporal matchning, kandidatlista, score, status eller `geographic_match_used`.

Teknisk kompatibilitet innebär inte att kommersiell lagring, bearbetning, kundvisning eller vidare distribution är godkänd. Dessa villkor ska bedömas separat för exakt produkt/lager och användning.

**Nästa steg:** kör en avgränsad nationell vägmatchningspilot med manuellt bedömda positiva, negativa och tvetydiga testfall. Mät prestanda, kontrollera länsgränser och täckning samt kör temporal regression före/efter utan att ändra temporal logik.


## NVDB – ZIP-baserad vägmatchningspilot (2026-11-17)

Efter merge av PR #409 och PR #410 har ZIP-läsningen verifierats lokalt i Windows mot de faktiska Lastkajen-arkiven för Norrbotten och Västerbotten. Matcharen läste båda ZIP-arkiven direkt via GDAL `/vsizip/`; ingen extraktion behövdes.

Pilotindata var `nvdb-nearest-road-review-v1.csv`. Den faktiska CSV-inläsningen och matcharkörningen omfattade **8 poster** (äldre arbetsanteckning om 9 poster var felaktig). Körningen rapporterade `status=completed`, 2 källor, 0 källinitialiseringsfel och 8 utdata. För samtliga poster rapporterades två lästa källor, noll misslyckade källor och `completed_with_candidates`.

Närmaste vägavstånd låg mellan **1,01 och 464,91 meter**. Antalet deduplicerade kandidater före maxgränsen varierade mellan 1 och 26; högst 5 kandidater returneras i kandidatlistan per post. Detta är tekniskt lyckad matchning, inte ännu en manuell kvalitetsbedömning av att varje väg är rätt olycksplatsväg.

Användaren jämförde 39 icke-geografiska fält rad för rad mellan indata och utdata: **0 skillnader**. Det bekräftar att matcharskriptet bevarade övriga indatafält. Det är inte ett separat test av en framtida temporal matchningspipeline.

Resultatet är fortsatt review-only. Källfel ska ge `partial_source_read`, aldrig negativ evidens. Geografiska kolumner får inte ändra temporal kandidatlista, score, status eller `geographic_match_used`. Ingen nationell produktionskörning eller kundvisning är aktiverad.

**Nästa steg:** manuell kartgranskning av de åtta resultaten, särskilt fallet med längst avstånd; därefter fler manuellt bedömda testfall och fler län innan en bredare nationell pilot.



## NVDB – GeoJSON-export för manuell väggranskning (2026-11-17)

Den verifierade tvålänspiloten omfattade 8 händelser. För att möjliggöra manuell granskning av om närmaste väg och alternativa kandidater är geografiskt rimliga har matcharen i branch `feat/nvdb-road-review-geojson` fått ett valfritt argument `--geojson-output`. Det skapar en separat WGS84 GeoJSON FeatureCollection med händelsepunkter och valda NVDB-vägkandidaters faktiska linjegeometrier. Egenskaperna anger radnummer, kandidatordning, om kandidaten är närmast, vägnummer, vägroll, avstånd, NVDB-element-ID och källfil.

CSV-utdata behåller sitt befintliga schema; geometrierna skrivs bara till den separata GeoJSON-filen. Indata och originalarkiv ändras inte. GeoJSON är lokalt granskningsunderlag och ska inte användas som automatisk bekräftelse av olycksväg eller som kundvisning. Ingen temporal matchningslogik ändras. PR #411 är sammanslagen i main. Den lokala exporten har därefter körts mot Norrbottens och Västerbottens ZIP-arkiv: 8 händelser och 43 GeoJSON-features. Resultatet är fortsatt review-only.


### NVDB – nationell geografisk validering (2026-11-17)

Den första ZIP-baserade vägmatchningspiloten omfattar åtta Luleåhändelser och två länsarkiv. Matcharen har nu en separat rapportbyggare under utveckling: `scripts/build_nvdb_validation_report.py`. Den skapar en JSON-sammanfattning och en deterministisk granskningskö med alla flaggade händelser samt ett stickprov av övriga händelser per källfil. Rapporten är avsedd att göra kvalitetssäkringen skalbar; den mäter ännu inte faktisk träffsäkerhet.

Nationell kvalitetssäkring kräver ett oberoende manuellt bedömt referensurval, verifierad täckning för samtliga län, benchmark av körtid/minne och kalibrering av avstånds-/tvetydighetströsklar. Kandidatfilernas proveniens får inte användas som bevis för geografisk täckning. Geografisk evidens ska fortsatt hållas skild från temporal matchning och får inte automatiskt bekräfta olycksväg eller kundvisning.


### NVDB – nationell geografisk validering (2026-11-17)

PR #412 är sammanslagen i main och CI-verifierad (Police–NVR matching and geographic evidence tests #24 samt Snapshot storage tests #470, båda `success`). Rapportbyggaren `scripts/build_nvdb_validation_report.py` skapar JSON-sammanfattning och separat granskningskö från matchnings-CSV. Alla flaggade händelser behålls; övriga tas med genom deterministiskt stickprov per förekommande källfil.

Nästa steg är lokal körning mot den befintliga åttahändelsepiloten och manuell granskning av utdata. Nationell validering kräver därefter oberoende manuellt bedömda testfall, verifierad källtäckning, prestandamätning och kalibrering. Rapporten mäter inte faktisk träffsäkerhet utan manuellt facit. Geografisk evidens ska fortsatt hållas skild från temporal matchning och får inte automatiskt bekräfta olycksväg eller kundvisning.


### NVDB – nationell egenskapsanalys (2026-11-17)

Arbetet prioriterar nu nationell datadriven egenskapsanalys framför manuell radgranskning av åttahändelsepiloten. En fristående extraktor i branch `feat/nvdb-national-feature-analysis` skapar händelse- och kandidatnivåtabeller samt JSON-sammanfattning. Den beskriver avståndsgap mellan närmaste kandidater, vägnummer, vägroll, kandidatantal, sökstatus och källproveniens. Den skapar inga rätt/fel-etiketter och ändrar inte temporal matchning. Se [NVDB – nationell egenskapsanalys](nvdb-national-feature-analysis.md).

Nästa steg är CI-verifiering och körning mot pilotens CSV, därefter benchmarkad nationell matchning. Utan oberoende facit kan analysen identifiera samvariation och återkommande mönster men inte mäta faktisk träffsäkerhet. Källfel och partiella länsresultat ska redovisas separat.


### NVDB – nationell egenskapsanalys PR #413 sammanslagen (2026-11-17)

PR #413 är sammanslagen i main (merge commit `408b098bbfa405d8cfe58f8e4c40f3e2295a18f8`). Den nya `scripts/build_nvdb_candidate_features.py` skapar händelse- och kandidatnivåtabeller samt en JSON-sammanfattning från NVDB-matchningens CSV. Egenskaperna omfattar bland annat närmaste/näst närmaste avstånd, gap och kvot, vägnummer, vägroll, kandidatantal, element-ID, källproveniens och sökstatus. Tre riktade tester har lagts till och kopplats till Police–NVR-workflowen.

Arbetsinriktningen är nationell statistisk egenskapsanalys i stället för manuell granskning av enskilda pilotrader. Extraktionen ger beskrivande variabler, inte facit eller automatiska matchningsbeslut. Nationell matchningskörning, prestandamätning och analys av återkommande mönster återstår. Ingen temporal matchningslogik ändras.


## Rovbase – första dataintag och kvalitetskontroll (2026-11-18)

Ett originaluttag från Rovbase mottogs och arkiverades oförändrat i OneDrive under `Skogskoll/Rovbase/raw/rovbase_originaluttag_2026-11-18.zip`. Arkivet är 65 735 567 byte och SHA-256 är `81be641c5c5bb18f396cd0a14240533f6b012e7f06941a91ed7115e9dc3556eb`. Fyra artfiler innehåller totalt 15 561 unika `RovbaseID`: björn 9 620, lodjur 4 652, varg 855 och järv 434.

Initial kvalitetskontroll finns i OneDrive `Skogskoll/Rovbase/quality/`: Markdown- och JSON-rapport, art-/årstabell med antal och andelar (162 art-årsrader), koordinatavvikelsefil för 35 RT90-rader samt ett Python-skript för geografisk kontroll. Kontrollrapporten identifierar 866 osäkra dödsdatum, 6 189 saknade individ-ID, 50 saknade kön och 5 904 saknade verifierade åldersvärden. 32 poster har dödsorsaken `Skyddsjakt enskilds initiativ`, vilket behöver stämmas av mot tidigare uppgift från källägaren.

Befintliga administrativa gränser har identifierats i OneDrive och ska återanvändas: Lantmäteriets `kommun-lan-rike_2025.gpkg` (lager `kommun`, `lan`, `rike`, EPSG:3006; 290 kommunpolygoner) samt SCB:s årsvisa `Kommun_2016.gml`–`Kommun_2026.gml`. Polygonkontrollen är ännu inte körd. 35 RT90-poster skiljer mer än 10 meter mellan en oberoende transformation med antagandet EPSG:3021 och leverantörens SWEREF99-kolumner; avvikelsen är en granskningssignal, inte ett fastställt koordinatfel.

**Begränsning:** Rovbase är ännu inte registrerad i `data-platform/config/sources.yml`. Tekniskt mottaget uttag innebär inte att kommersiell användning, historisk lagring, bearbetning, kundvisning eller vidare distribution är godkänd. Nästa steg är att köra `validate_rovbase_geography.py` lokalt mot befintlig OneDrive-GPKG, granska avvikelserna och inhämta källägarens förtydliganden innan produktionsflöde eller kundanvändning planeras.


## Rovbase – geografisk validering (2026-11-18)

Den första lokala polygonkörningen mot Lantmäteriets befintliga `kommun-lan-rike_2025.gpkg` slutfördes för 15 561 unika Rovbase-poster. Samtliga transformerade ursprungskoordinater och levererade SWEREF99-koordinater träffade exakt en kommunpolygon och exakt en länspolygon. Körningen gav 9 396 granskningsrader, men merparten berodde på en systematisk normaliseringsmiss: Rovbase-namn som `Filipstad` jämfördes med polygonlagrets `Filipstads kommun`. Det tidigare skriptet tog bort suffixet `kommun` men inte genitiv-s, vilket gav 9 379 kommunnamnsflaggor. Dessa är inte bekräftade geografiska avvikelser.

Valideringsskriptet i OneDrive har korrigerats för en begränsad genitiv-s-ekvivalens och sex riktade namnmatchningstester passerade. En ny full körning återstår. 35 koordinatpar har mer än 10 meters skillnad mellan oberoende transformation och leverantörens SWEREF99-koordinat; antagandet RT90 = EPSG:3021 måste bekräftas med Rovbase. Tre länsnamnsavvikelser och kvarvarande kommunavvikelser ska granskas efter omkörningen. Valideringen använder 2025 års administrativa gränser och fastställer inte historisk kommunindelning för äldre händelser.

Resultatet är fortsatt intern datakvalitetskontroll. Rovbase är inte registrerad i `data-platform/config/sources.yml`, och teknisk åtkomst/lagring är inte godkännande för kommersiell bearbetning, kundvisning eller vidare distribution. Ingen produktionsimport ska göras innan den korrigerade körningen och rättighetsbedömningen är klara.


## Nationell ÄFO-avskjutning

Nationella totalsummor per ÄFO är en separat produkt från regionala ÄJO-förändringssnapshots. Fällda älgar beräknas genom att summera `ShotTotal` över alla underliggande ÄJO-rader; avskjutningsmål genom att summera `AssignedTotal`. Portalens tvådelade HTML-Summa används endast som kontroll. Saknade värden får aldrig behandlas som noll. ÄFO-geometri matchas med sammansatt `afo_id`.


## Skogsstyrelsen – ärendebaserad förändringskontroll och månadssnapshot

En särskild arbetsmodell och första månatliga kontroll finns dokumenterad i [SKOGSSTYRELSEN_CASE_CHANGE_MONITORING.md](SKOGSSTYRELSEN_CASE_CHANGE_MONITORING.md). Den täcker planerade avverkningsanmälningar, Samråd (punkt/linje/polygon) och utförda avverkningar, men den första implementationen är avgränsad till Gräsmyr-piloten med 10 km radie.

- Samråd: dagligt pilotflöde med paginering och tre separata lager; månadskontrollen gör en extra fullständig avstämning inom samma scope.
- Utförda avverkningar: befintlig full-/deltaarkivering återanvänds för en månatlig snapshot inom samma scope.
- Planerade avverkningsanmälningar: den befintliga sex­timmarsproben är begränsad till metadata och högst tre sidor. Månadskontrollen upprepar proben men är ännu inte en fullständig snapshot.
- Inget av dessa flöden får tolka frånvaro i en senare körning som bevis på borttagning, avbokning eller utförd avverkning.
- `Inkomdatum` är ett inkomstdatum, inte verifierat ändringsdatum. Editor tracking och eventuella editDate/lastEditDate-fält måste kontrolleras separat.
- Nationell täckning, fullständiga planned-harvest snapshots och kundvisning är inte etablerade av denna kontroll.

## Skogsstyrelsen månadskontroll – driftutfall och publicering

Den första manuella körningen (2026-11-22, [run #4](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45031069869)) lyckades med tester, Samråd point/line/polygon-insamling, snapshot av utförda avverkningar och planned-harvest probe. Probe-rapporten sparades som Actions-artifact.

Snapshotfiler skapades i runnern men kunde inte publiceras till `main`: repository rules kräver pull request (GH013). Korrigerings-PR byter därför direktpush mot automatisk skapande/uppdatering av en separat data-PR. Data-PR:n ska granskas manuellt innan snapshots blir del av main. Se [driftrapporten](SKOGSSTYRELSEN_CASE_CHANGE_MONITORING.md).


### Första lyckade månadskontroll – 2026-11-22

Run #6 genomförde samtliga insamlings- och publiceringssteg. [Data-PR #491](https://github.com/dahlinrobert-lgtm/Skog/pull/491) granskades och mergades till `main` 2026-11-22 kl. 14:38:33 UTC (merge commit `e83b9d3059f91099497ad65d66dd35015d0c4cec`). Snapshotfilerna är beständiga i huvudgrenen.

- Samråd: 0 punktobjekt, 11 linjeobjekt och 12 områdesobjekt efter exakt cirkelfilter inom Gräsmyr 10 km.
- Utförda avverkningar: 1 631 objekt i aktuell kontroll; inga nya, saknade eller geometriändrade ID:n. En 479-byte deltafil representerar oförändrat läge och ska inte tolkas som tomt lager.
- Planerade avverkningsanmälningar: endast 300 av uppskattningsvis 132 594 poster lästes; fullständig scan saknas.
- Inga frånvarobaserade borttagningsslutsatser eller kundlarm görs. Rättighetsgrinden är oförändrad.


### Beständig publicering verifierad – PR #491/#492 mergade

Run #6:s snapshotdata publicerades till `main` genom PR #491. Dokumentationsuppdateringen i PR #492 är också mergad. Publiceringskedjan är därmed verifierad för den första Gräsmyr-pilotkörningen. Detta innebär inte att en lång historisk tidsserie eller nationell täckning är etablerad.

Planerade avverkningsanmälningar är fortsatt begränsade till 300 poster av cirka 132 594 i den befintliga proben. Fullständig paginerad insamling och validering återstår.


### Samråd och Life2Taiga – PR-baserad publicering verifierad efter merge (2026-11-22)

Publiceringsfixarna är mergade:
- [Samråd workflow-fix #494](https://github.com/dahlinrobert-lgtm/Skog/pull/494), merge commit `740a481436004537c277b5bdc91e004ab4f6627f`.
- [Life2Taiga workflow-fix #495](https://github.com/dahlinrobert-lgtm/Skog/pull/495), merge commit `88bd4bad06496340d3aec1f3f6ebab83d37049a1`.

Verifierade körningar efter merge:
- [Samråd run 45037391885](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45037391885): tester, point/line/polygon-insamling, event-bundle och PR-skapande passerade.
- [Life2Taiga run 45037447855](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45037447855): tester, källhämtning, GeoJSON-validering och PR-skapande passerade.

Körningarna skapade följande öppna data-PR:er:
- [Samråd snapshots #496](https://github.com/dahlinrobert-lgtm/Skog/pull/496)
- [Life2Taiga data #497](https://github.com/dahlinrobert-lgtm/Skog/pull/497)

Körningarna utlöstes av push till `main` efter merge. De bekräftar därför att insamling och PR-publicering fungerar efter merge, men ännu inte att cron-schemaläggningen har fungerat i en senare schemalagd körning. Data-PR:erna kräver manuell granskning. Detta ändrar inte källornas rättighetsstatus eller tillstånd för kundvisning.


### Data-PR #496 och #497 mergade – 2026-11-22

De två automatiskt skapade data-PR:erna har granskats och mergats:
- Samråd pilot snapshots [PR #496](https://github.com/dahlinrobert-lgtm/Skog/pull/496), merge commit `f442d6a24832a347319bd7c70fa08e331b2a0674`, 15:20:45 UTC.
- Life2Taiga naturvårdspolygoner [PR #497](https://github.com/dahlinrobert-lgtm/Skog/pull/497), merge commit `467322df3f1c591717e58b0f650717471d2b80cc`, 15:21:08 UTC.

Data från dessa PR:er är nu beständig i `main`. Den tidigare verifieringen av workflowen var push-utlöst efter merge av kodfixarna; faktisk cron-verifiering efter dessa ändringar återstår. Mergad data är inte i sig ett godkännande för kommersiell kundvisning.


### Dokumentationsstatus efter PR #498 – 2026-11-22

PR #498 är mergad till `main` med merge commit `21cfa30af358588eb6889d27f78b4e8bffc1fa9a`. Kundgränssnittstester efter merge passerade i [run 45038321932](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45038321932).

Samråd-data-PR #496 och Life2Taiga-data-PR #497 är båda mergade till `main`. Publiceringsfixarna #494/#495 har verifierats med push-utlösta körningar, men faktisk schemalagd drift efter fixarna återstår att bekräfta. Ingen kundvisningsrätt följer av att data finns i `main`.


### Planerade avverkningsanmälningar – regional verifieringssnapshot publicerad (2026-11-22)

Ersättnings-PR [#502](https://github.com/dahlinrobert-lgtm/Skog/pull/502) mergades till `main` 2026-11-22 kl. 15:50:22 UTC (merge commit `62a4d0d471409ae4af544128bc1dcef6bf30ae94`). Den äldre PR #485 stängdes utan merge eftersom den låg efter aktuell `main` och riskerade att skriva över nyare gemensamma data.

- Snapshot inom det regionala verifieringsområdet (Gräsmyr, 10 km): 165 objekt, 165 unika ID:n, källstatus `ok`, hämtad 2026-11-22 13:20:19 UTC. Snapshoten är inte en initial baslinje; föregående snapshot var `20261121T155530Z.json`. Antalet var 165 både före och efter och delta innehöll inga tillägg, ändringar eller borttagningar.
- Change analysis läste 381 snapshots utan oläsbara snapshots och laddade 1 631 genomförda geometrier.
- Händelsepaketet innehåller 188 observationer/händelser/evidensposter, 11 relationer och 165 uppföljningskedjor. Det består av 165 planerade-avverkningsobservationer och 23 Samrådsobservationer. Senare Samrådsdata och relationer från aktuell `main` bevarades.
- En daterad gzip-snapshot av genomförda avverkningar från 2026-11-22 lades till som arkiv. Befintlig aktuell genomförd-avverkningsdata från `main` behölls.

Detta verifierar en lyckad, avgränsad publicering för fullständighets- och jämförbarhetsvalidering via PR. Det verifierar inte nationell täckning eller fullständig paginering av planerade avverkningsanmälningar. Inga frånvarobaserade borttagningsslutsatser eller kundlarm får dras från denna enskilda körning. Rättighets- och kundvisningsstatus är oförändrad.

**Nästa steg:** fullständig paginering och fullständighetskontroll av planerade avverkningsanmälningar, följt av minst två kompletta jämförbara körningar. Fortsätt samtidigt verifiera faktisk schemalagd drift och PR-publicering.


### Komplett paginering av planerade avverkningsanmälningar – kod mergad (2026-11-22)

PR [#504](https://github.com/dahlinrobert-lgtm/Skog/pull/504) mergades till `main` 2026-11-22 kl. 16:02:26 UTC (merge commit `f75f5ac0832c4823da18fe88de1f516b5d7774f5`). Den lägger till en separat manuell komplett snapshot för fullständighetsvalidering inom ett geografiskt testområde (Gräsmyr, 10 km):

- `scripts/snapshot_harvest_notifications_pilot.py`: ArcGIS `returnIdsOnly` följt av object-ID-batcher, count- och ID-inventeringskontroll både före och efter hämtning, strikt batchvalidering och avbrott vid källförändring eller ofullständighet. En misslyckad körning skriver inte latest-manifest och raderar/ersätter inga tidigare snapshots.
- `.github/workflows/skogsstyrelsen-complete-harvest-pilot.yml`: manuell `workflow_dispatch`, separat data-PR och artifact. Flödet är fristående från den befintliga sex­timmarsproben.
- `tests/test_snapshot_harvest_notifications_pilot.py`: tester för scope, object-ID-batchning, saknade ID:n och transfer-limit.
- Riktade PR-checkar passerade: [run 45040997464](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45040997464) och [run 45040997430](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45040997430). PR-checken körde testerna men hoppade avsiktligt över insamling och data-PR.

**Status:** implementation och skyddstester är mergade/verifierade. Den första kompletta källhämtningen har ännu inte körts. Scope är endast Gräsmyr 10 km; nationell paginering är inte etablerad. Nästa steg är manuell körning av workflowet, granskning av data-PR och manifest, därefter en andra komplett körning med samma scope. Ingen kundvisning eller alerting aktiveras.


### Första kompletta Gräsmyr-snapshoten arkiverad (2026-11-22)

Efter fixen av tokenautentiseringen i PR #506 lyckades workflow-körning [#5 / 45042577564](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45042577564). Data-PR [#507](https://github.com/dahlinrobert-lgtm/Skog/pull/507) mergades 2026-11-22 16:15:13 UTC (merge commit `565a1134ac973bcf963e5269681792bb726a4054`). Main verifierades på samma commit.

Arkiverade filer:
- `data/skogsstyrelsen/harvest_notifications/grasmyr/latest.json`
- `data/skogsstyrelsen/harvest_notifications/grasmyr/snapshots/grasmyr_10km_20261122T161347Z.geojson.gz`

Manifestet visar en komplett read-only-hämtning för Gräsmyr 10 km, fångad 2026-11-22 16:13:47 UTC. ArcGIS returnerade 165 ID:n; 165 objekt hämtades; 165 ID:n var unika; count före/efter var 165/165 och ID-inventeringen var stabil. `complete_scan=true`. Objektbatchstorlek 200. Okomprimerad GeoJSON var 303 866 byte och SHA-256 var `21df361fbef8b0151e7a01e06d2377fe1f5cb42a1d5265217c1e7b7ea3d6bbee`. Workflow producerade dessutom ett artifact på 92 642 byte.

Detta är första kompletta arkiverade observationen, inte ännu en förändringsserie. En andra komplett körning med samma scope behövs innan differenser kan klassas som förändringar. Ingen frånvaro får betraktas som borttagning, och inga kundlarm eller kunddatabas-skrivningar är aktiverade. Nationell täckning och kommersiell kundvisningsrätt är inte verifierade.

**Nästa steg:** gör en andra komplett körning vid senare tillfälle och jämför ID-inventering, antal och objektinnehåll. Behåll befintlig sex­timmarsprobe separat.


### Prestanda: strömmad analys av genomförda avverkningar (2026-11-22)

PR [#509](https://github.com/dahlinrobert-lgtm/Skog/pull/509) ersatte analysens fullständiga historikmaterialisering med strömmad arkivhantering.

- `iter_completed_archive_transitions` läser arkivkedjan stegvis och behåller ett rekonstruerat tillstånd i taget. Deltaarkivens `added` och `updated` används för att begränsa vilka objekt som behöver geometri- och tidskontroller. Fulla kontrollpunkter jämförs mot föregående jämförbara tillstånd.
- `read_latest_completed_archive` rekonstruerar endast det senaste giltiga arkivtillståndet för den aktuella analysen.
- Första fullständiga arkivet är fortsatt baslinje, inte historiskt larm. Saknade basarkiv, brutna delta-kedjor och scopeändringar får inte tolkas som borttagningar eller förändringshändelser.
- Arkivparens jämförbarhetsräknare och diagnostik för saknat/ändrat scope bevaras.
- Vid ändringen fanns 379 genomförda-avverkning-arkiv, totalt cirka 194,8 MB komprimerat (38 större kontrollpunkter och 341 små deltaarkiv).

Verifiering på PR-grenen:
- [Completed evidence transition tests](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134864) – success.
- [Completed snapshot storage tests](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134796) – success.
- [Full snapshot storage test suite](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134896) – success.
- [Geometric union tests](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134822) – success.
- [Monthly source audit tests](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45044134806) – success.

**Operativ verifiering efter arkivkedjefixen PR #514:** riktade arkiv-/evidenstester, full testsvit och audit passerade. Main-monitor-run [#45048859162](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45048859162) avslutades `success` efter 30m22s; samtliga steg inklusive analys och data-PR-publicering passerade. Analysen läste 383 planerade snapshots utan oläsbara filer, 165 planerade objekt och 1 631 genomförda objekt. PR [#515](https://github.com/dahlinrobert-lgtm/Skog/pull/515) uppdaterade Gräsmyr-observationen och mergades i `db4aca33642812ee69a6bff5cf7083b50f320de6`.

**Arkivrekonstruktion och historik:** analysen rekonstruerade 381 genomförda arkiv och jämförde 370 övergångar. Tio övergångar exkluderades på grund av saknat/ändrat query scope. Den korrigerade analysen återfann 702 unika `new_completed_detection_overlap`-händelser; de är satellitbaserade överlappskandidater för manuell granskning, inte bevis för utförd avverkning. Planerade ID:n jämfördes mellan observationerna 16:42 och 17:20 UTC och var exakt samma 165 ID:n. Antalet genomförda objekt var 1 631 i båda observationerna, men fullständig ID-/manifestjämförelse för genomförda polygoner återstår. Ingen frånvaroklassning eller kundavisering aktiveras.


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

## Övergripande mål: nationell insamling per relevant datakälla

Skog ska på sikt ha en verifierad nationell insamling för varje relevant datakälla och separat produkt/lager, i den omfattning källan faktiskt erbjuder och tillåter. Nationell insamling är ett mål för dataplattformen – det innebär inte att varje källa automatiskt ingår i Skogskolls första kundprodukt.

Gräsmyr 10 km används som kontrollerad pilotgeografi för att verifiera metod, fullständighet, historik och drift. En lyckad pilot får inte beskrivas som nationell täckning. En nationell kartvy, katalogpost, metadata-probe eller ett enstaka urval räknas inte heller som fullständig nationell insamling.

### Nationell acceptansgrind per källa och produkt/lager
1. **Omfattning:** dokumentera nationell geografi, tillgängliga objekt, tidsperiod, filter, undantag och källans egna begränsningar.
2. **Fullständighet:** verifiera full paginering/uttagsmetod, stabila objekt-ID:n, unika poster och avstämning mot källans antal eller annan oberoende kontroll.
3. **Proveniens:** spara original/snapshot, körnings-ID, tidpunkt, scope, antal, status och SHA-256 där det är relevant.
4. **Historik:** bevara tidigare observationer; partial/failed körningar får inte ersätta senaste kompletta snapshot eller skapa falska borttagningar.
5. **Jämförbarhet:** minst två kompletta jämförbara observationer innan förändringar, frånvaro eller nyhet tolkas.
6. **Drift:** verifiera återkommande körning, felhantering, återhämtning, lagring och återställning.
7. **Rättigheter:** bedöm separat teknisk åtkomst, lagring, bearbetning, kommersiell användning, kundvisning och vidare distribution.

Täckning ska redovisas separat för varje lager. Exempelvis ska Skogsstyrelsens Samråd punkt-, linje- och polygonlager inte slås ihop till ett enda odifferentierat fullständighetsbesked. Trafikverkets olika produkter, Länsstyrelsernas olika tjänster och NVR:s olika dataset ska likaså hållas åtskilda.

### Aktuell pilotstatus – Skogsstyrelsens planerade avverkningsanmälningar

Den manuella fullständighetspiloten 2026-11-22 (Actions run #8) hämtade hela ID-inventeringen för Gräsmyr 10 km: ID:n före/efter 165/165, hämtade geometrier 165, unika ID:n 165, stabil ID-inventering under skanningen och complete_scan=true. Snapshot SHA-256: 21df361fbef8b0151e7a01e06d2377fe1f5cb42a1d5265217c1e7b7ea3d6bbee.

Snapshot och manifest arkiverades i PR #524, som mergades 2026-11-22. Detta verifierar en komplett pilotobservation i ett 10 km-område. Det verifierar inte nationell täckning eller förändringsanalys mellan två observationer.

**Nästa steg:** ta en andra komplett jämförbar Gräsmyr-snapshot och granska därefter nationell uttagsdesign, kapacitet, paginering och belastning innan geografisk uppskalning. Fortsätt separat fullständighetskontroll av Samråds tre lager. Ingen källrätt eller kundvisningsrätt uppstår genom teknisk verifiering.

## Skogskoll – worker metadata och snapshot-envelope-persistens (mergad i main via PR #538)

ArcGIS-adapterns metadatafunktion är nu kopplad till worker/store-flödet. Metadata hämtas och valideras före scan-start, lagras tillsammans med run-/scan-identiteten och jämförs vid återupptagning. En ändrad metadataidentitet avslutar den gamla sessionen i stället för att blanda två olika query-/schemaförutsättningar.

Migration 005 inför ett internt snapshot_envelopes-register. Det återanvänder poll_runs och scan_sessions, medan envelope-posten bevarar snapshot-ID, käll-/produkt-/lageridentitet, fångsttid, status, coverage, schema-/identitetsversion, comparability key, rights-status och full JSON-envelope. Registrering kräver terminala körningsposter och validerar att metadata motsvarar det som sparades vid scan-start. RLS är aktiverat utan kundpolicyer.

Detta är en intern proveniens- och jämförbarhetsmekanism, inte en kundfeed. PR #538 är mergad till `main` (merge commit `38f2474ff75fc5d34dc491da059178c266590b58`). CI passerade: 85/85 UI-tester, begränsad read-only source probe (300/300 unika ID:n) samt migration 005 och SQL-smoketest i disponibel PostgreSQL/PostGIS. Ingen live Supabase-anslutning eller produktionsmigration har gjorts. Livehämtning av den nya metadatafunktionen mot ArcGIS återstår. Kundvisning för Skogsstyrelsens avverkningsanmälningar inväntar fortsatt lagerkontroll enligt källstatusrapporten; teknisk persistens ger inte kundvisningsrätt.


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

## Skogskoll – isolerat syntetiskt worker-smoketest (förberett 2026-11-23)

Workerflödet återanvänder `runScanBatch` och den befintliga Supabase-adaptern. En identitetsinkonsekvens har rättats: normaliserade observationsposter binds nu till den injicerade källans `source.key`, så att en syntetisk testkälla inte kan skriva poster under Skogsstyrelsens produktionsidentitet. Standardkällan behåller sin befintliga identitet.

Det manuella testet använder den reserverade identiteten `skogskoll:synthetic:worker-smoke-test`, två fasta fixture-ID:n och en syntetisk metadataendpoint under `.invalid`. Det utför start, en atomisk sidcommit, finish och snapshot-envelope-registrering i `skogskoll-test`. Workflowet kräver explicit manuell bekräftelse och får aldrig köras mot produktion.

Detta är beständiga testskrivningar, inte en rollback-transaktion. Testets poll runs, scan sessions, seen IDs, observations, historikrader och immutable snapshot envelopes behålls för spårbarhet. Ingen automatisk radering görs. Ingen ArcGIS-hämtning, kundmatchning, kundfeed eller avisering ingår. Livekörningen är ännu inte genomförd.

## 2026-11-23 – Syntetiskt worker-smoketest mergat

PR [#551](https://github.com/dahlinrobert-lgtm/Skog/pull/551) är mergad till main i commit `15380835ff6488393738c0552ba8ef5ddc1d4d5f`. Både [customer UI tests #45254523110](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45254523110) och [source probe #45254522745](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45254522745) passerade på PR-committen.

Workflowet och skriptet finns nu på main. De kräver manuell dispatch och explicit bekräftelse, använder endast syntetiska fixtures och har en separat kontroll som låser Supabase API-host till det verifierade `skogskoll-test`-projektet. Det livebaserade worker-testet är ännu inte kört; därför är RPC start, atomisk sidcommit, finish och snapshot-envelope-registrering via den verkliga adaptern ännu inte verifierade.

Nästa steg är att inhämta uttryckligt godkännande innan workflowet startas. Testet skapar beständiga syntetiska poster i testdatabasen och raderar dem inte. Ingen produktionsskanning eller kundavisering ingår.

## 2026-11-23 – Live syntetiskt worker-smoketest passerat

GitHub Actions [körning #45259733480](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45259733480) genomfördes på `main` och avslutades `completed/success`. Workerresultatet var `complete`, med två hämtade syntetiska poster på en sida (`fetchedCount=2`, `pagesFetched=1`). Källidentitet: `skogskoll:synthetic:worker-smoke-test`; fixture: `skogskoll-worker-smoke-v1`; scan ID: `1a53c3b2-fad4-47d1-afb4-9340dc50f15c`.

Detta verifierar workerflödet mot det dedikerade Supabase-testprojektet med syntetisk källa och befintlig adapter/RPC-kedja för snapshotregistrering, start, atomisk sidcommit och finish. Loggen anger `alertsEnabled=false` och `productionSourceUsed=false`. Inga ArcGIS-anrop eller kundaviseringar ingick.

Testdata behålls avsiktligt. Oberoende read-only kontroll av de enskilda databastabellerna och snapshot-envelope i Supabase återstår; workflowets lyckade workerresultat är inte i sig en separat SQL-inventering.

Nästa steg: inspektera scan ID och de två stabila fixture-ID:na i Supabase-testprojektet, verifiera observationer/historikrader samt envelope-status och bedöm därefter idempotens vid omkörning. Produktionsingestion och kundaviseringar förblir avstängda.


## 2026-11-23 – Read-only SQL-verifiering för syntetiskt worker-test

Migration 006 ger medvetet service_role direkt SELECT endast på `scan_sessions` och `poll_runs`. Direktläsning av observations-, historik-, seen-ID- och snapshot-envelope-tabellerna är spärrad. Därför kan Actions-loggen inte ensam ge en oberoende inventering av samtliga skrivna rader.

En SELECT-only kontrollfråga har lagts till i `skogskoll/db/diagnostics/verify-synthetic-worker-smoke.sql`. Den kontrollerar scan ID, poll run, de två syntetiska observations-ID:na, seen-ID-ledger, historikrader, snapshot envelope och antal. Den ska köras i Supabase SQL Editor mot `skogskoll-test` och gör inga ändringar.


## 2026-11-23 – Oberoende SQL-antal verifierade för syntetiskt worker-test

Användaren körde den aggregerade SELECT-kontrollen i `skogskoll-test`. Resultatet var `seen_id_count=2`, `observation_count=2`, `history_row_count=2` och `snapshot_envelope_count=1`. Detta matchar de två fasta fixture-ID:na och en snapshot-envelope och bekräftar att motsvarande rader finns i databasen.

Kontrollen verifierar endast antal. De separata resultatuppsättningarna för scan/poll-status, observationsfält, historikens `event_type` och snapshot-envelope-fälten har inte delats och ska inte betraktas som verifierade. Nästa steg är att granska SQL-diagnostikens frågor 1, 2, 4 och 5. Ingen idempotens-omkörning ska göras före den granskningen. Testdata behålls; inga grants ändras och produktion/aviseringar förblir avstängda.


## 2026-11-23 – Detaljerad read-only SQL-granskning av första syntetiska worker-körningen
Användarens SQL-resultat från `skogskoll-test` verifierar för scan `1a53c3b2-fad4-47d1-afb4-9340dc50f15c`:

- Scan `status=complete`, `source_count=2`, `next_offset=2`, `fetched_count=2`.
- Seen-ID-ledgern innehåller de två förväntade fixture-ID:na med offset 0 och 1.
- Två observationer finns; båda är `active=true` och har förväntade fixture-attribut/sekvensnummer.
- Två historikrader finns, båda `event_type=baseline`, kopplade till poll-run `b7ce384f-d9fb-4240-ab6e-2bdee386a287`.
- Ett snapshot-envelope finns med `status=complete`, `customer_visibility=not_assessed`, `rights_evidence_ref=null`, produkt `synthetic_worker_smoke` och scope `synthetic-fixture-only-v1`.
- Aggregerade antal: 2 seen IDs, 2 observationer, 2 historikrader, 1 envelope.

Poll-run-statusen är ännu inte verifierad i det delade materialet: fråga 1:s resultatrad är horisontellt avklippt innan poll-kolumnerna. Nästa steg är att kontrollera den delen av resultatraden. Därefter kan en kontrollerad idempotensomkörning göras. Ingen omkörning, privilege-ändring, produktionsinsamling eller kundavisering har gjorts.


## 2026-11-23 – Poll-run-status verifierad för första syntetiska worker-körningen

Den fullständiga SQL-resultatraden för scan `1a53c3b2-fad4-47d1-afb4-9340dc50f15c` verifierar poll run `b7ce384f-d9fb-4240-ab6e-2bdee386a287` med `status=success`, `fetched_count=2`, `inserted_count=2`, `updated_count=0` och `finished_at=2026-11-23 20:28:53.695946+00`.

Därmed är första worker-körningens scan och poll run kompletta/lyckade. Tillsammans med tidigare resultat är två aktiva observationer, två `baseline`-historikrader och ett `complete` snapshot-envelope med `customer_visibility=not_assessed` verifierade.

**Nästa steg:** en andra manuell syntetisk worker-körning mot enbart `skogskoll-test` för idempotens. Samma två fixture-ID:n och samma innehåll ska ge en ny scan/poll-run och ett nytt snapshot-envelope, men inte skapa fler observationer eller historikrader; posterna ska klassas `unchanged`. Detta måste verifieras efter körningen och är ännu inte ett observerat resultat. Behåll testdata och befintliga grants; ingen produktion eller kundavisering.


## 2026-11-23 – Repeated synthetic worker run verified by independent SQL

Supabase SQL Editor results for the latest synthetic run verify scan `879f0071-68e4-462a-a0ff-216c10a8c6cf` as `complete` with 2/2 fetched, and linked poll run `6613004d-8f05-4de1-8c39-964014148eed` as `success` with `inserted_count=0` and `updated_count=0`. The latest scan has 2 seen IDs. Aggregate counts are 2 current observations, 2 history rows, and 3 snapshot envelopes across the three complete synthetic runs.

Both observations remain active and retain their original `first_seen_at`; `last_seen_at` and `last_run_id` advance to the latest poll. The two retained history records remain `baseline` events linked to the initial poll run. No new history rows were created by the repeated unchanged content. All three snapshot envelopes are complete and remain `customer_visibility=not_assessed` with `rights_evidence_ref=null`.

This verifies idempotency for repeated identical synthetic fixtures in the test project. It does not certify production ingestion, source rights, customer visibility or alert delivery.


## 2026-11-23 – Kontrollerat syntetiskt worker-test med ändrad observation verifierat

PR [#560](https://github.com/dahlinrobert-lgtm/Skog/pull/560) utökade det befintliga syntetiska worker-workflowet med scenariot `change_feature_001`. [GitHub Actions-körning #4](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45270531634) kördes manuellt på `main` (commit `30a96696ae97179d3e60e33a2a1479020c128bee`) och avslutades `completed/success`. Loggen visar fixture-variant `change_feature_001`, scan `9fddb92c-8ea0-444c-b4aa-9b8cff79d019`, `status=complete`, två hämtade poster på en sida, förväntat ändrat ID `worker-smoke-feature-001`, `alertsEnabled=false` och `productionSourceUsed=false`.

Användarens read-only SQL-resultat från Supabase-projektet `skogskoll-test` verifierar den beständiga databaspersistensen:

- Senaste scan: `complete`, `source_count=2`, `page_size=2`, `next_offset=2`, `fetched_count=2`; snapshot registrerad.
- Kopplad poll run `7f5345d3-8f2c-46a1-a935-db87f1f92cb5`: `success`, `fetched_count=2`, `inserted_count=0`, `updated_count=1`.
- Senaste scan har 2 seen IDs; databasen har 2 aktuella observationer, 3 historikrader och 4 snapshot envelopes.
- `worker-smoke-feature-001` har nu `sequence=101`; `worker-smoke-feature-002` är oförändrad med `sequence=2`. Båda är fortsatt aktiva.
- Historiken innehåller de två ursprungliga `baseline`-raderna från den första poll run samt exakt en ny `changed`-rad för feature 001, kopplad till den senaste poll run. Baslinjeraderna har bevarats.
- Samtliga fyra snapshot envelopes har `status=complete`, `customer_visibility=not_assessed` och `rights_evidence_ref=null`.

**Verifierad slutsats:** den kontrollerade ändringsvägen fungerar i det isolerade testprojektet. En befintlig observation uppdaterades, exakt en `changed`-historikrad lades till, den andra observationen och de ursprungliga baslinjeraderna bevarades och den fjärde kompletta snapshot-envelope registrerades. Testposterna är beständiga och ska behållas; ingen rensning genomfördes.

Detta verifierar inte produktionsingestion, källrättigheter, kundvisning, kundmatchning eller larmleverans. Ingen produktionskälla eller kundavisering användes. Testprojektets avgränsning, befintliga behörigheter och historik ska behållas.

**Nästa steg:** fortsätt med befintlig worker-/adapterarkitektur och välj nästa avgränsade validering först efter kontroll av aktuell källstatus och rättigheter. Aktivera inte produktionsingestion eller kundaviseringar enbart på grundval av detta syntetiska test.


## Länsstyrelsernas Älgdata – nationell ÄFO-avskjutning (uppdaterad 2026-11-25)

Den separata insamlaren i `alg-grasmyr` äger den nationella insamlingen. Skog ska återanvända dess arkiverade snapshots och dashboard som källflöde i stället för att bygga en parallell collector.

Två kompletta workflow-körningar är nu verifierade via sina jobb och arkiverade artifact: [run 43952789564](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/43952789564) för 2026-11-16 (artifact ID `14271201667`) och [run #13 / 45273303393](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45273303393) för 2026-11-23 (artifact ID `14867345764`). Båda gav 129/129 unika aktuella ÄFO-ID:n, report 3, säsong 2026/2027, `boundary_mode=current` och 3 237 råa ÄJO-rader. Dashboarden för 2026-11-23 summerar `ShotTotal=57 687` och `AssignedTotal=79 704`; värdena verifierades mot råmaterialet.

Aktuell `alg-grasmyr/main` har nu dashboarden `data/national_afo_dashboard.json` med `snapshot_date=2026-11-25`, `report_id=3`, `boundary_mode=current`, 129/129 ÄFO och 129/129 med data. Dashboardens blob-SHA är `58ec8e1d66170b9bb97400d8d9501490940332de`; den uppdaterades av bot-commit [62ece755](https://github.com/dahlinrobert-lgtm/alg-grasmyr/commit/62ece75597cb249f6ab618ad12a9a1aec3c46650). Oberoende summering av de 129 dashboardraderna ger `ShotTotal=58 016` och `AssignedTotal=79 727`, med 0 rader som saknar `area_rows_available`. De senaste dashboardvärdena är kumulativa säsongsvärden, inte individuella fälthändelser eller fältdatum.

Två jämförbara kompletta Actions-run-ID:n är verifierade och länkade i PM-repo PR [#79](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/79), som mergades 2026-11-25: 43952789564 (2026-11-16) och 45273303393 (2026-11-23). Jämförelsen visar samma 129 ÄFO-ID:n, 0 saknade och 0 tillkomna, med jämförbarhetsnyckeln `report=3|season=2026/2027|boundary=current|afo_count=129`. PM-repots källdokumentation klassar profilen som `pilot_recurring`; nästa read-only inventory behövs för att verifiera att samma status publicerats i aktuell read model. Den kompletta 2026-11-25-uppdateringen är fortsatt endast commit-/dashboardevidens; dess separata Actions-run-ID är inte fastställt. Koden kräver exakt match mellan katalogens ID:n och JaktAdm:s aktuella boundary-ID:n.

**Status:** två kompletta jämförbara workflow-körningar är verifierade (2026-11-16 och 2026-11-23) med identiska 129 ÄFO-ID:n; inga ID:n saknades eller tillkom. Den separata 2026-11-25-dashboarden har också 129/129 aktuella ÄFO men är här styrkt via commit-/snapshot-evidens, inte ett fastställt Actions-run-ID. PM-repo PR #79 föreslår därför `pilot_recurring` utifrån de två länkade körningarna; ingen production-status. Den fullständiga råa ÄJO-radjämförelsen är dokumenterad nedan. Aggregerade säsongsvärden får inte beskrivas som dagliga fälldatum eller individuella händelser. Insamlingen är tekniskt verifierad, men kundvisning, vidare distribution och rätt till historisk lagring/bearbetning ska bedömas separat med attribution. Ingen Skogskoll-worker, kundfeed eller avisering har aktiverats.

**Nästa steg:** kör/invänta nästa read-only inventory efter merge av PM-repo PR #79 och #80 och verifiera att Älgdata visas som `pilot_recurring`. Fortsätt bevara jämförbara nationella snapshots i alg-grasmyr och granska framtida förändringar med samma stabila identitet och fail-closed-kontroller. Gör separat rättighetsbedömning före produktintegration.


## Länsstyrelsernas Älgdata – teknisk risk och portalvillkor (uppdaterad 2026-11-27)

Senaste nationella insamling [run 46013595922](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/46013595922) avslutades completed/success 2026-11-27. Den omfattade 129/129 ÄFO för report 3, säsong 2026/2027 och aktuella gränser. Tre kompletta jämförbara körningar är verifierade (2026-11-16, 2026-11-23 och 2026-11-27).

Collectorn använder den publika statistikportalens webbgränssnitt och POST-rutten `/LoadData/GetData`, sekventiellt för 129 ÄFO, med upp till tre försök per område. Denna rutt är observerad i portalens klientflöde men är inte dokumenterad som ett publikt API-kontrakt. I de granskade officiella sidorna hittades ingen publicerad rate limit, minsta anropsintervall eller throughput-/SLA-specifikation. Tre försök per ÄFO och sekventiell körning är verifierat klientbeteende, inte leverantörsgränser.

Länsstyrelsens [öppna data-sida](https://www.lansstyrelsen.se/vasterbotten/om-oss/vara-tjanster/oppna-data.html) anger att Älgdata-databasen kan användas fritt, utan angivna villkor, och listar XLSX som format. Älgdatas [statistikportal](https://algdata-apps.lansstyrelsen.se/algdata-apps-stat/) beskriver export av synlig statistik till Excel. Detta är användnings-/exportinformation, inte ett tekniskt API-avtal eller en rate-limit-specifikation. Kundvisning av härledd produkt, historisk lagring och vidare distribution ska fortsatt bedömas separat.

**Riskbeslut:** riskbedömningen är fortsatt partial. Inga parallella anrop eller aggressiva retries införs. Behåll nuvarande sekventiella flöde och fail-closed-publicering; begär leverantörsbesked om tekniska gränser innan uppskalning. Ingen kundfeed eller avisering aktiveras av denna bedömning.

## Första jämförelsen av nationella ÄFO-snapshots (2026-11-21–2026-11-23)

Dashboardversionerna från alg-grasmyr har jämförts för samma säsong (2026/2027) och samma 129 unika `afo_id`:

| Mått | 2026-11-21 | 2026-11-23 | Differens |
|---|---:|---:|---:|
| Kumulativt rapporterade fällda (`ShotTotal`) | 56 715 | 57 687 | +972 |
| Avskjutningsmål (`AssignedTotal`) | 79 704 | 79 704 | 0 |
| ÄFO med högre fälltal | – | 109 | – |
| ÄFO oförändrade | – | 20 | – |
| ÄFO med lägre fälltal | – | 0 | – |

Antalet råa ÄJO-rader per ÄFO är oförändrat i dashboardmetadata. `FinishedReporting`-antalet ändras i 10 områden, inklusive en minskning i ÄFO 14-005 (5 till 4). Rapportstatus är alltså inte monoton och ska inte behandlas som en historisk händelse i sig. Största ökningar på ÄFO-nivå är 25-003 (+76), 25-006 (+55), 25-004 (+46), 25-005 (+45) och 07-001 (+23).

Detta är en jämförelse av ÄFO-dashboardaggregat. Den fullständiga råa ÄJO-radjämförelsen är nu verifierad och dokumenterad i avsnittet nedan. Bortfall i framtida snapshots får inte automatiskt bli borttagningshändelser. Värdena är kumulativa säsongsuppgifter och kan inte placeras på exakta fälldatum.

**Nästa steg:** fullständig ÄJO-rad-jämförelse och separat rättighetsbedömning innan Skogskoll-integration.


## 2026-11-23 – Nationell ÄJO-råjämförelse färdigställd

Den befintliga nationella snapshotarkitekturen i alg-grasmyr återanvänds; Skog bygger ingen parallell insamlare. PR [#83](https://github.com/dahlinrobert-lgtm/alg-grasmyr/pull/83) och workflow [#45283539790](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45283539790) verifierade jämförelsen mellan 2026-11-21 och 2026-11-23 för samma säsong (2026/2027), boundary_mode=current och 129/129 ÄFO.

- 3 237 råa ÄJO-rader per snapshot.
- 2 841 oförändrade rader; 396 rader med ändrade källattribut.
- 0 tillkomna portal-ID:n och 0 ID:n saknade i senare snapshot.
- ShotTotal ändrades på 378 rader; kumulativ nationell ökning +972 (56 715 till 57 687).
- FinishedReporting ändrades på 42 rader: 41 Nej -> Ja, 1 Ja -> Nej.
- Källsnapshotsen var oförändrade. Rapporten är ett härlett granskningsresultat, inte en ny insamlingskälla.

Ändringar avser kumulativa säsongsrapporter, inte enskilda fälldatum eller händelser. FinishedReporting är en muterbar rapportstatus, inte en historisk händelse. Frånvaro ska inte tolkas som borttagning.

**Nästa steg:** separat rättighetsbedömning för historisk lagring, bearbetning, kommersiell användning, kundvisning och vidare distribution. Ingen produktintegration eller kundpublicering ska ske innan dessa dimensioner har stöd i exakta villkor eller skriftlig evidens.
**Nästa steg:** fortsätt med framtida jämförbara snapshots och separat rättighetsbedömning innan eventuell Skogskoll-integration.


### Rå ÄJO-rad-jämförelse – verifierad 2026-11-23

Den nationella snapshotinsamlingen och dess arkiv ägs av det separata repot [alg-grasmyr](https://github.com/dahlinrobert-lgtm/alg-grasmyr). Skog ska konsumera dessa verifierade snapshots/dashboard och inte bygga en parallell insamlare.

Alg-grasmyr PR #83 är mergad. Den nya skrivskyddade analysen använder portalens ID i `drillDownToAjoReport`, avgränsat inom respektive `afo_id`, som stabil ÄJO-identitet. Full jämförelse av 129 ÄFO mellan 2026-11-21 och 2026-11-23 passerade i [Actions run 45283539790](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45283539790):

- 3 237 råa ÄJO-rader per datum.
- 2 841 oförändrade rader och 396 rader med ett eller flera ändrade attribut.
- 0 tillkomna och 0 saknade portal-ID:n.
- `ShotTotal` ändrades på 378 rader.
- `FinishedReporting` ändrades på 42 rader: 41 från Nej till Ja och 1 från Ja till Nej.
- Kumulativt dashboardvärde för `ShotTotal` ökade från 56 715 till 57 687 (+972); `AssignedTotal` var oförändrat 79 704.

Flera attribut kan ändras på samma ÄJO-rad. Detta är förändringar mellan kumulativa säsongsrapporter, inte enskilda fälthändelser eller exakta fälldatum. Analysen ändrar inte originalsnapshots. En rad som saknas i ett senare uttag ska klassas som obekräftad frånvaro, inte borttagning, avbokning eller genomförande.

Detaljer, fältfördelning och reproducerbar körinstruktion finns i [alg-grasmyr/docs/NATIONAL_AJO_ROW_DIFF.md](https://github.com/dahlinrobert-lgtm/alg-grasmyr/blob/main/docs/NATIONAL_AJO_ROW_DIFF.md). Fortsatt användning i Skogskoll kräver separat kontroll av exakt kommersiell användning, kundvisning och distribution; ingen worker eller kundavisering har aktiverats.


### Länsstyrelserna – eldningsförbud i skog och mark (EXT)

**Käll-ID:** `lansstyrelsen.fire_ban`  
**Metadata-ID:** `53514d5d-b1ea-4162-bc56-58e496f0f4f7`

- WebbGIS: https://ext-webbgis.lansstyrelsen.se/lst_eldningsforbud/
- FeatureServer: https://ext-geodata-nationella-visning.lansstyrelsen.se/arcgis/rest/services/LST/LST_eldningsforbud_EXT/FeatureServer
- Geodatakatalogens metadata: https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/srv/api/records/GetMetaDataById?id=53514d5d-b1ea-4162-bc56-58e496f0f4f7
- Metadata enligt användarens skärmbild: skapad 2020-05-13, reviderad 2026-08-26; underhåll anges som årligen och kontinuerligt. Beskrivningen säger att karttjänsten också tillhandahålls via WMS och Map Service.
- Metadata beskriver fem statusvärden: eldningsförbud, inget eldningsförbud, skärpt eldningsförbud, annat eldningsförbud och ej angivet. Den anger även uppgifter om beslutsfattare, startdatum, besluts-/informationslänk och kommunstatus.
- **Viktig semantik:** saknad information eller statusen ej angivet betyder inte att eldningsförbud saknas. Metadata beskriver även att kommuner kan ha egna förbud/regler enligt annan lagstiftning; den här tjänsten får därför inte beskrivas som en fullständig förteckning över alla lokala eldningsregler.
- Metadata-skärmbilden visar inga tillämpliga användnings- eller åtkomstvillkor. Den maskinläsbara metadatarecorden och eventuella lager-/komponentvillkor är inte oberoende verifierade. Detta ska inte tolkas som ett generellt juridiskt godkännande för historisk lagring, bearbetning, kommersiell användning eller kundvisning.
- Geografisk täckning, lager-ID:n, fält, stabila objekt-ID:n, maxRecordCount och pagineringsstöd är ännu inte verifierade mot FeatureServer.

**Implementerad första etapp (connector, inte insamling):**

`data-platform/scripts/inspect_lansstyrelsen_fire_ban_service.py` gör en manuell metadata-only-inspektion av FeatureServer-roten och de lager/tabeller som annonseras. Den rapporterar schema, fält, geometri, extent, spatial reference, objekt-ID/global-ID-fält, maxRecordCount och pagineringskapacitet. Den har timeout, sekventiella anrop och ett tak på 25 lager-/tabellmetadataanrop som standard (högst 50 efter uttrycklig parameterändring).

Connectorn frågar **inte** efter feature-poster eller geometrier, skapar inga snapshots och har inget workflow/schedule. Standardläget skriver inte någon fil; `--out` kan användas för att spara metadataresultatet manuellt.

**Planering:** schemaläggning och operativa snapshots ska tidigast övervägas från **2027-01-24**. Detta är ett planerat datum, inte en aktiverad körning. Första operativa snapshoten ska vara en tyst baslinje utan historiska larm. Före den tidpunkten krävs metadata-probe, verifierad scope/identitet/paginering, fullständighetsstrategi, källvillkor och separat beslut om lagring/publicering.

Kör manuellt efter merge när tjänsten är tillgänglig:

    python data-platform/scripts/inspect_lansstyrelsen_fire_ban_service.py
    python data-platform/scripts/inspect_lansstyrelsen_fire_ban_service.py --out /tmp/lansstyrelsen-fire-ban-metadata.json

Test:

    python -m unittest discover -s tests -p "test_inspect_lansstyrelsen_fire_ban_service.py" -v

Ingen featuredata hämtas av dessa kommandon.


### Viltdata – första nationella differensanalys (2026-11-25)

Den första jämförelsen mellan de två kompletta snapshotsen från 2026-11-18 är genomförd och dokumenterad i [viltdata-kill-statistics-diff-20261118.md](viltdata-kill-statistics-diff-20261118.md).

- Baslinje: `20261118T204420Z`, Actions [#44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179).
- Senare observation: `20261118T220720Z`, Actions [#44408345762](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44408345762).
- Båda snapshots har 49 arter, 21 län, 550/550 lyckade statistikförfrågningar och 552 råfiler verifierade med byteantal och SHA-256.
- Samma täckning verifierades: 73 255 observationsnycklar per snapshot. 73 252 var oförändrade och 3 ändrades; inga nycklar tillkom eller saknades.
- Samtliga tre ändringar avser Älg 2026: nationellt 18 158→18 163, län 7 1 025→1 026 och län 17 2 014→2 018. Nationell differens +5 motsvarar de två redovisade länsdifferenserna tillsammans.
- Båda snapshots innehöll 3 364 null-värden och 24 950 explicita nollvärden. Null och noll har hållits åtskilda.

Detta är en jämförelse av rapporterade kumulativa årsserievärden, inte individuella fälthändelser eller fälldatum. Den första snapshoten är tyst baslinje; inga historiska larm skapas. Originaldata är oförändrade. Rättigheter för permanent lagring, bearbetning, kommersiell användning och kundvisning är fortsatt inte bedömda/godkända.

**Nästa steg:** invänta rättighetsbesked och gör nästa differens först när ytterligare en komplett, integritetskontrollerad snapshot finns. Ofullständiga körningar får aldrig användas som baslinje eller diffunderlag.


### Samråd – historik i event bundle (PR #612 mergad, 2026-11-25)

De daterade gzip-snapshotsen i `data/samrad_snapshots/` är fortsatt råhistorikens sanningskälla. PR [#612](https://github.com/dahlinrobert-lgtm/Skog/pull/612) återanvänder dessa i den befintliga event-bundle-byggaren. Endast strukturellt kompletta snapshots tas med; partiella/okända snapshots används inte för frånvarobedömning. Händelser bevaras när ett objekt inte längre returneras och visar första/senaste observerade tidpunkt. Oläsbara arkivfiler stoppar byggandet. Regressionstestets textassertion korrigerades i commit `1833f172` utan att ändra historiklogiken. Detta är en härledd historikvy, inte en ny rådatakälla eller ett juridiskt godkännande. Kommersiell användning och kundvisning för Samråd förblir separata, villkorade bedömningar enligt källregistret.

### Samråd – snapshotarkiv och historik publicerade (2026-11-25)

PR [#613](https://github.com/dahlinrobert-lgtm/Skog/pull/613) mergades till `main` 2026-11-25 16:20:51 UTC med merge commit `e224a7fd9102095059eb60e8293a4296ab79be3b`. PR:n publicerade det uppdaterade pilotarkivet och den härledda event-bundlen efter att PR #615 hade korrigerat historikbyggarens hantering av ett korrekt tomt lager.

Verifierad körning efter #615, [Collect Samråd pilot snapshots #47](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45650638344), rapporterade 26 arkiverade snapshots, 21 Samråd-observationer och 21 Samråd-händelser. Event bundle contract [#22](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45650638711) och snapshot storage tests [#552](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45650638347) passerade. Själva Samråd-körningen fick ändå failure i sista create/update-PR-steget, trots att insamling och bundle-byggande passerade och automationens PR-branch uppdaterades. PR #613 granskades och mergades manuellt.

Manifestet för körningen var `success` / `complete_for_configured_scope`: punktlager 0 poster och 0 sidor, linjelager 9 poster inom scope och 1 sida, polygonlager 12 poster inom scope och 1 sida. `source_total_reconciled=false`, varför detta inte är nationell täckning eller avstämning mot källans totala antal. Den tekniska publiceringen ändrar inte rättighetsbedömningen för kommersiell användning, kundvisning eller vidare distribution.

**Kvar att verifiera:** nästa körning ska särskilt kontrollera att create/update-PR-steget avslutas framgångsrikt. Fullständighet gäller endast det konfigurerade pilotområdet.


### Samråd – run #48 och PR-automation verifierade, snapshot mergad (2026-11-25)

[Collect Samråd pilot snapshots #48](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45656496498) kördes manuellt från `main` och samtliga steg passerade, inklusive skapande av [data-PR #619](https://github.com/dahlinrobert-lgtm/Skog/pull/619). Detta verifierar att create/update-PR-steget fungerade i run #48 efter felet i run #47.

Manifestet för run #48 anger `success` och `complete_for_configured_scope` för Gräsmyr-pilotens befintliga 10 km-scope. Lagerresultat: points 0 poster och 0 sidor; lines 18 poster hämtade i envelope, 9 inom scope och 9 utanför; areas 14 hämtade, 12 inom scope och 2 utanför. Inga saknade geometrier eller geometrifel. `source_total_reconciled=false`; detta är inte nationell fullständighetsverifiering.

Snapshoten `data/samrad_snapshots/samrad_20261125T164133Z.json.gz` är 400 407 byte och har SHA-256 `fe502340f2fc3301e9cb9bc486a0292867c0c8de6f83bd26befa8701c7876c5f`. Event-bundle-byggandet rapporterade 27 arkiverade Samråd-snapshots, 21 Samråd-observationer och 21 Samråd-händelser. Totalt innehöll bundle 186 observationer och 186 händelser. PR #619 granskades och mergades 2026-11-25 16:44:28 UTC (merge commit `e4aaf853f4b16e79c4b744784dabd3bb3295d8e5`); den nya daterade snapshoten är verifierad i `main`.

Detta ändrar inte källans rättighetsstatus. Teknisk åtkomst och arkivering är inte kommersiellt tillstånd, kundvisningsrätt eller distributionsrätt. Historikregeln kvarstår: frånvaro i senare snapshot får inte klassas som avbokning, borttagning eller genomförd åtgärd.

**Nästa kontroll:** verifiera nästa schemalagda Samråd-körning och dess PR-automation. Nationell täckning och avstämning mot källtotaler är fortfarande inte verifierade.


## 2026-11-25 – Samråd: PM-027-manifest verifierat och historikfråga avgränsad

Projektledarens read-only inventory #16 verifierade Samråds separata manifest för det konfigurerade Gräsmyr 10 km-scope: 21 poster (0 punkter, 9 linjer, 12 polygoner), uttömd paginering i samtliga lager och noll saknade/felaktiga geometrier. Inventoryn föregick Skog PR [#619](https://github.com/dahlinrobert-lgtm/Skog/pull/619). Efter PR #619 pekar Skog `main`-manifestet på snapshoten från 2026-11-25 16:41:33.484740 UTC; 27 daterade snapshotfiler finns i arkivet. Ny projektledarinventory krävs för att verifiera att den senaste manifestversionen har nått read model/publiceringen.

Den härledda event bundle-historiken följs separat i [issue #639](https://github.com/dahlinrobert-lgtm/Skog/issues/639). Frågan gäller varför 27 arkiverade snapshots motsvarar tre Samråd source runs och 21 händelser i aktuell bundle, samt varför två tidigare observerade linjeobjekt saknas. Detta är ännu inte fastställt som en bugg; äldre snapshots kan inte uppfylla dagens fullständighetskrav. Nästa steg är en read-only eligibility-inventering. Daterade gzip-snapshots är fortsatt råhistorikens sanningskälla och ska inte ändras.

Rättighetsstatus, nationell täckning och kundvisningsstatus ändras inte av denna tekniska verifiering.


### 2026-11-25 – PM-031 read-only inventering av Samråd-arkivet

[PR #643](https://github.com/dahlinrobert-lgtm/Skog/pull/643), [read-only inventory run #3](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45676077199), klassificerade samtliga 27 daterade gzip-snapshots mot den oförändrade produktionsfunktionen `samrad_snapshot_is_complete()`. Resultatet är 3 historikberättigade snapshots (2026-11-25 15:19:17, 16:03:41 och 16:41:33 UTC), 24 äldre snapshots exkluderade och 0 oläsbara filer. De tre godkända snapshotarnas 21 stabila lager-/objekt-ID:n och 21 case/event-ID:n matchar aktuell event bundle exakt.

De 24 äldre snapshotarna saknar `records_outside_scope`, `records_missing_geometry` och `records_geometry_error` per lager. Detta är en faktisk begränsning i det äldre snapshotformatet, inte ett bevis för att räknarna ska sättas till noll. Collector-versionen i commit [3dd2fd0](https://github.com/dahlinrobert-lgtm/Skog/commit/3dd2fd0389e920d85bc7cd28acf6abcfca14be9d) hoppade tyst över features med saknad geometri och geometrifel och sparade bara `records_fetched`, `records_in_scope` och `pages`. `status=success` för de äldre lagren visar därför inte att inga features tappades före snapshoten. De sparade feature-geometrierna är strukturellt läsbara och giltiga, men detta kan inte styrka vad som eventuellt filtrerades bort.

Tre äldre ärendegrupper finns i arkivet men saknas i aktuell bundle: `S 9480-2021` (linjeobjekten `28009` och `47112`), `S 9481-2021` (linjeobjekten `28726` och `47734`) samt `S 8667-2021` (linjeobjekt `49488`). De är historiska kandidater, inte verifierade kompletta observationer. De får inte återföras till event bundle utan oberoende fullständighetsbevis.

**Beslut:** ingen ändring av historikbyggaren eller fullständighetsgrinden. Ingen adapter får anta att saknade räknare betyder noll. De 24 äldre originalarkiven bevaras oförändrade och hålls utanför frånvarobedömning. PM-031:s filinventering är klar; eventuell komplettering kräver separat bevarad körningsevidens från de äldre insamlingarna. Detta påverkar inte rättighetsstatus, kundvisning eller nationell täckning.


### Samråd – snapshot från 2026-11-25 17:26 UTC publicerad efter PR #629

Samråd data-PR [#629](https://github.com/dahlinrobert-lgtm/Skog/pull/629) mergades till `main` 2026-11-25 20:22:32 UTC (merge commit `29f0d38a649584e308d0a04391a44d0f2f15176d`). Aktuell `main` verifierades mot merge committen.

Senaste manifestet pekar på `data/samrad_snapshots/samrad_20261125T172634Z.json.gz` (400 407 byte; SHA-256 `c65398097cfa2fc9881457790a31432ea41984dbd67537adad627bf3103125ff`). Manifeststatus är `success` / `complete_for_configured_scope`. Pagineringen är uttömd för punkt-, linje- och polygonlagren; inga saknade eller felaktiga geometrier rapporteras. Inom befintligt Gräsmyr-scope på 10 km: 0 punkter, 9 linjer och 12 polygoner. Linjelagret hämtade 18 poster i envelope (9 utanför scope); polygonlagret hämtade 14 (2 utanför scope). `source_total_reconciled=false`, så resultatet innebär inte nationell täckning eller full avstämning mot källans total.

Run [45664696922](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45664696922) byggde och validerade event bundle samt skapade PR #629. Workflowloggen rapporterade 28 arkiverade Samråd-snapshots och 21 Samråd-observationer/händelser. Snapshotarkivet är fortsatt råhistorikens sanningskälla och event bundle är en härledd vy.

Projektledarens [PM-027 read-only inventory #18](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45697167605), körd efter PR #629, verifierade att read model nu pekar på `data/samrad_snapshots/samrad_20261125T172634Z.json.gz` via `data/samrad_latest_manifest.json`. Artifacten inventerade 28 daterade snapshots och rapporterade 0 punkter, 9 linjer och 12 polygoner inom det konfigurerade Gräsmyr-scope på 10 km; pagineringen var uttömd och inga saknade/felaktiga geometrier rapporterades. Inventeringen var metadata-only; manifestets SHA-256 räknades inte om. `source_total_reconciled=false`, så nationell täckning eller avstämning mot källtotal är inte verifierad.

Publiceringen och read-only-verifieringen ändrar inte Samråds rättighetsstatus. Kommersiell användning, kundvisning och vidare distribution ska fortsatt bedömas separat. PM-031:s 24 äldre snapshots förblir exkluderade från verifierad historik och frånvarobedömning.


#### Snapshot 2026-11-25 – körning #33 (tekniskt komplett och arkiverad i main)

[Workflow run #33](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340) passerade samtliga steg efter merge av PR #659. Manifestet anger `complete`, 34 lager och 7 674 features inom Gräsmyr-pilotens ungefärliga 75 × 75 km-envelope: Miljöwebb 27 lager / 2 396 features och NVDB Viltolyckor 7 lager / 5 278 features. NVDB-lager-ID:n 3, 5, 7, 9, 11, 13 och 15 verifierades. För varje lager matchar `downloaded_feature_count` `source_object_id_count`; detta verifierar uttaget mot tjänstens objekt-ID-inventering för pilot-envelope, inte nationell täckning eller källans globala total (`source_object_count=null`).

Manifest SHA-256: `a80b7561de79c376ef1d6598d3f486d686f9d025cf943c34cbda5617fbe14b04`. Artifact ID `15063734584`, 11 986 466 byte, SHA-256 `877e917b1bb18109a42966f1a2b37a239e1dbcb174acb47818211e3be9dad345`, utgång 2027-02-23 21:35 UTC. [Data-PR #660](https://github.com/dahlinrobert-lgtm/Skog/pull/660) mergades 2026-11-25 21:44:22 UTC (merge commit `5ed1a0b62373b1e78a2f994f384a5e4c24506ef0`). Aktuell `main` verifierades därefter: snapshotkatalogen innehåller manifest samt katalogerna `miljowebb/` och `viltolyckor/`; manifestet är `complete` med 34 lager och 7 674 features. PR:n omfattade 35 filer (manifest + 34 gzip-GeoJSON). Detta är en första arkiverad baslinje, inte en historisk jämförelseserie. Nästa kompletta körning behövs för jämförelse över tid; baslinjen ska inte generera historiska frånvarolarm.

Körningen ändrar inte rättighetsbedömning eller tillåten kundvisning. NVDB Viltolyckor är fortsatt aggregerad olycksfrekvens per vägsegment, inte individuella olyckshändelser. Miljöwebb och NVDB Viltolyckor ska bedömas separat per produkt/lager.


## PM-027 – Trafikverkets två produktprofiler registrerade (2026-11-25)

Projektledarrepots [PR #80](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/80) mergades 2026-11-25 22:13:35 UTC (merge commit `7450cd72f66a13544289d01e7afaf38f60aab4f5`). Den registrerar två separata profiler med samma befintliga Trafikverket-workflow och samma kompletta run #33, men med separata produkt-/lageruppsättningar:

- `trafikverket.miljoweb_landskap`: 27 lager, 2 396 features.
- `trafikverket.nvdb.wildlife_collision_frequency`: 7 lager, 5 278 features.

Båda är baseline inom Gräsmyrs ungefärliga 75 × 75 km-envelope. En andra komplett körning med samma envelope och exakta lager-ID:n krävs innan återkommande pilotdrift kan hävdas. Detta är inte nationell täckning och source total är inte verifierad. NVDB Viltolyckor avser aggregerad olycksfrekvens per väglänk, inte enskilda olyckor. Rättighets- och kundvisningsbedömningar är oförändrade.

Nästa steg är en read-only inventory efter merge av PR #79 och #80 för att verifiera den publicerade read model-statusen. Därefter ska nästa Trafikverket-snapshot jämföras med respektive produktbaslinje. Ingen ny collector eller historikmodell behövs.


## PM-027 – read-only inventory #20 (2026-11-25)

[Project manager read-only inventory #20](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45712438496) avslutades success med 3/3 repositories och 0 fel. Artifact ID `15068286448`, SHA-256 `09f860249d451b64f581c4ce67983e66a425e2d4cb5b0f3b91a070173fa80212`, observationstid `2026-11-25T22:21:10.992689Z`.

Den publicerade read model klassar Samråd och Älgdata som `pilot_recurring` (3 respektive 2 jämförbara kompletta körningar). Miljöwebb Landskap och NVDB Viltolyckor är separata `baseline`-profiler med en komplett körning vardera.

**Begränsning:** Skogs `source_snapshot_evidence` innehåller i artifact #20 fortfarande endast avverkningsanmälningar och Samråd. Älgdata samt de två Trafikverket-produkterna har alltså profilklassning och workflowmetadata men ännu ingen egen adapterpost för senaste försök och snapshotinventering. Detta ska inte förväxlas med att snapshoten saknas. Nästa steg är att utöka befintlig metadata-only-adapter och tester, med exakt workflowkoppling per repository och manifest-/dashboardmetadata. Älgdatas dashboard-commit får inte omvandlas till ett gissat Actions-run-ID. Trafikverkets två produkter ska valideras separat mot tjänstnyckel, lager-ID:n och featuretotaler i manifestet. Inga featurecollections ska hämtas.

Inventeringen läste 52 source_id (15 operations-block, 37 utan) och PM-backloggen med 10 uppgifter. Duplicerade PM-ID:n PM-023, PM-024 och PM-027 flaggades och förblev separata.

Rättigheter och kundvisning är oförändrade. PM-027 som helhet är fortfarande öppen.


## PM-027 – adapterevidens verifierad i inventory #25 (2026-11-26)

[Project manager read-only inventory #25](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45866881837) avslutades success 2026-11-26 17:20 UTC: 3/3 repositories, 0 fel. Artifact ID `15141206837`, digest `sha256:d055bee4f6e4a163e7536ca2b2a9e7434c78eacef365c02e6fe10849cfd1604b`. Insamlingen är read-only; inga featurecollections hämtades och inga källrepositorier skrevs.

Skogs `source_snapshot_evidence` har fem separata adapterposter: avverkningsanmälningar, Samråd, Älgdata, Miljöwebb Landskap och NVDB Viltolyckor. Inventory #25 visar Älgdata-dashboard 2026-11-26 med 129/129 ÄFO (report 3, säsong 2026/2027, current boundaries) och senaste exakta workflowförsök [45837084941](https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/45837084941). Samråds senaste försök [45864838781](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45864838781) är success; senaste kompletta snapshot är fortsatt 2026-11-25 inom 10 km-piloten.

Trafikverkets två produkter är separat validerade mot manifestet 2026-11-25: Miljöwebb 27 lager/2 396 features och NVDB Viltolyckor 7 lager/5 278 features. Båda är baseline i Gräsmyrs ungefärliga 75 × 75 km-envelope. De har ännu inget verifierat latest-attempt-run-ID: GitHub Actions workflow inventory saknar sökvägen `.github/workflows/trafikverket-weekly-snapshots.yml`, trots att workflowfilen finns i Skogs `main`. Detta ska utredas utan att fabricera run-ID. Global källtotal och nationell täckning är inte verifierade; Viltolyckor avser aggregerad frekvens per vägsegment, inte enskilda olyckor.

PM-027 förblir P0/öppen. Fem adapterposter innebär inte full täckning av målet om en daglig rapport över alla relevanta källor/produkter/lager. Nästa steg är att återställa/verifiera Trafikverkets workflowregistrering, köra ny inventory och fortsätta käll-för-käll-mappning. Rättigheter, kundvisning, historisk lagring och vidare distribution är oförändrade.


## PM-027 – Trafikverkets latest-attempt verifierad i inventory #26 (2026-11-26)

[Project manager inventory #26](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/actions/runs/45869038578) verifierade PR #83:s fallback. För både `trafikverket.miljoweb_landskap` och `trafikverket.nvdb.wildlife_collision_frequency` returnerar adaptern nu exact-path latest attempt: Skog Actions [run #33](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/45705661340), completed/success, workflow `.github/workflows/trafikverket-weekly-snapshots.yml`, discovery `repository_run_history_exact_path_fallback`. Äldre exakt match är run #32. PR #83 merge commit i projektledarrepos är `915eed8bc554855b6a76308fc0928f254a6ba131`.

Detta ändrar endast upptäckt/rapportering av workflowförsök; snapshotdata, Skogs workflow och rättighetsstatus ändras inte. Produktbaslinjerna är fortsatt 2026-11-25: Miljöwebb 27 lager/2 396 features och NVDB Viltolyckor 7 lager/5 278 features, båda inom Gräsmyrs ungefärliga 75 × 75 km-envelope. De är fortfarande baseline med en komplett körning vardera; global källtotal och nationell täckning är inte verifierade. NVDB Viltolyckor avser aggregerad frekvens per vägsegment.

Inventory #26 var read-only: 3/3 repos, 0 fel, inga featurecollections hämtade och inga källrepo-writes. PM-027 förblir öppen tills full käll-/produkt-/lagerkartläggning och återkommande jämförbara snapshots är verifierade. Kommersiell användning, lagring, bearbetning, kundvisning och vidare distribution är oförändrade.

## Polismyndighetens officiella händelse-API – parallell utvärdering (2026-11-27)

Polisens officiella API `https://polisen.se/api/events` utvärderas parallellt med befintlig Brottsplatskartan-insamling. Polisens dokumentation anger att API:et innehåller 500 aktuella notiser som representerar ett urval av polisens utryckningar. Innehållet är preliminärt och kan uppdateras. Koordinaterna representerar läns-/kommuncentrum och får inte behandlas som exakta händelsepositioner.

Polismyndighetens IT-kansli bekräftade 2026-11-27 i diarienummer A698.287/2026 att det inte finns mer händelsedata att tillhandahålla än det som publiceras på webbplatsen. Det officiella API:et är därmed en strukturerad åtkomstväg till publicerade notiser, inte en åtkomstväg till ett större internt händelseregister.

Utvärderingen använder separata, dagliga snapshots från båda källorna under 30 kalenderdagar från första lyckade officiella snapshot. Målet är minst 25 lyckade snapshots. Rådata, ID:n och historik hålls separata. Överlappning och kompletterande poster bedöms senare med kandidatmatchning och manuellt granskat urval. Inga poster slås samman automatiskt och inga kundlarm eller kundvisningsfunktioner ändras under piloten.

Polisens API-regler ska följas: korrekt User-Agent, HTTPS, minst 10 sekunder mellan anrop, högst 60 anrop per timme och 1 440 per dygn. HTTP 404 är permanent och webbskrapning ska inte användas när API finns. Den separata workflowen gör ett anrop per dygn och arkiverar den fullständiga aktuella listan immutable i Azure under ett eget prefix. Norrbottenposter räknas via `location.name`; koordinaterna används inte som exakta händelsepositioner.

Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution bedöms separat. Se [utvärderingsprotokollet](police-source-evaluation.md) och [Polisens händelseflöde](police-events-norrbotten.md).



## Länsstyrelsens diarier – PR-baserad publicering (2026-11-27)

Efter att [daglig workflow #143](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46066600104) misslyckades vid direktpush med GH013 har [PR #709](https://github.com/dahlinrobert-lgtm/Skog/pull/709) mergats. Både `.github/workflows/lansstyrelsen-diary-search.yml` och `.github/workflows/lansstyrelsen-monthly-snapshots.yml` använder nu `peter-evans/create-pull-request@v7`.

Flödena serialiseras genom gemensam concurrency group `lansstyrelsen-diary-archive` och använder samma PR-branch `automation/lansstyrelsen-diary-history`, eftersom båda uppdaterar `data/lansstyrelsen-diary/`. Den dagliga sökningen rebuildar state/events mot senaste `main` och auditerar resultatet före PR-skapande. Månadskörningen lägger till sina immutable snapshots och manifestrader. Ingen workflow pushar längre direkt till `main`.

PR-validering kör tester men skippar Chromium-installation, källsökning, persistence och publicering. CI passerade på PR #709: daglig diarievalidering [#147](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073226420), månadssnapshotvalidering [#21](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073226402) och diariehistorikaudit [#81](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073226313).

Post-merge liveverifiering [daglig run #148](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073390751) pågår. Ingen ny snapshot räknas som publicerad förrän dess data-PR har granskats och mergats. Källans söklogik, snapshot-/historikformat och rättighetsstatus är oförändrade.


## Länsstyrelsens diarier – diagnostics-only högvolymspaginering (2026-11-27)

Två nya manuella diagnostics-only-körningar utökade den tekniska pagineringsutvärderingen utan att ändra källarkivet:

- [Run #24](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073035588) körde `vattenverksamhet` för oktober 2026 i Skåne, Halland och Västra Götaland. Källtal och unika extraherade diarienummer var 14/14, 11/11 och 46/46; ett sidsteg per intervall.
- [Run #25](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073391186) körde bred testfras `an` för oktober 2026 i Norrbotten, Västerbotten och Jämtland. Resultat: 848, 874 och 820 unika diarienummer på 17, 18 respektive 17 sidor. Pagineringen följde flyttande ellipsfönster via `Page$6`, `Page$11` och `Page$16`; 16/17/16 postbacks gav bekräftade sidbyten. Inga duplicerade diarienummer eller case-ID:n hittades.

Båda körningarna var uttryckligen diagnostics-only och persisterade inga resultat. Arkivets 36 kompletta query-intervall, 36 snapshotfiler och två län är oförändrade. Testfrasen `an` är en teknisk pagination-probe, inte en godkänd produktionssökfras. Resultaten bevisar inte nationell/fullständig diarietäckning eller att leverantörens rate limits/SLA är kända. `risk_assessed=false` kvarstår.

Projektledarens [PM-PR #106](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/106) har registrerat evidensen. Post-merge daglig [run #148](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073390751) avslutades med HTTP 500 / Runtime Error vid Västra Götaland / `vattenverksamhet`, WebForms `Page$6`, efter 240 extraherade rader. 37 av 38 queryintervall lyckades, men batchen avbröts före persistence och PR-skapande; ingen ny snapshot eller delmängd publicerades. Det tidigare kompletta arkivet är oförändrat. PR-publiceringsvägen är därmed fortfarande inte liveverifierad med en komplett data-PR.


### Liveförsök #148 – fail-closed vid källans HTTP 500

Artefakten från [run #148](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073390751) innehåller 38 queryintervall: 37 lyckade och ett misslyckat. Felet inträffade för Västra Götaland / `vattenverksamhet` vid postback `Page$6`; Länsstyrelsens webbserver svarade HTTP 500 efter 240 extraherade källrader. Källtotal saknades och sidan ändrades inte. Batchen avbröts före persistence och PR-skapande. Inga delresultat publicerades; de 36 tidigare kompletta manifestintervallen och snapshots är bevarade.

Ingen automatisk retry/backoff infördes eftersom provider rate limits och återhämtningspolicy är okända. Nästa felsökning bör vara en avgränsad diagnostics-only-reproduktion av samma län/fras, inte en bredare produktionsinsamling. `risk_assessed=false` kvarstår.


## Länsstyrelsens diarier – ytterligare högvolymspaginering, grupp 04 (2026-11-27)

[Diagnostics-only run #28](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46076543847), grupp 04 (Uppsala, Stockholm, Södermanland), oktober 2026 och teknisk testfras `an` gav 684/684, 2 740/2 740 respektive 661/661 unika diarienummer på 14, 55 respektive 14 sidor. Totalt 4 085/4 085 över 83 sidor. Samtliga tre intervall var kompletta och avstämda; inga processfel.

Artefakt [15234882262](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46076543847) bekräftar numerisk paginering och framåtriktade sidfönsterellipser med `Page$6`, `Page$11`, `Page$16` och fortsatta femsidiga steg. Bakåtriktade ellipser valdes inte. Alla 80 sidövergångar hade registrerat svar och ändrat sida (13 Uppsala, 54 Stockholm, 13 Södermanland).

Ingen framåtriktad `Page$1`-ellips observerades live. `Page$1` förekom som normal sidlänk tillbaka till resultatsida ett. Den specialvariant som testas syntetiskt är därför fortsatt obekräftad live. Inga sidöverlapp observerades; 143 råa rader/135 unika kvarstår som separat testfall. Körningen var `diagnostics_only_no_persistence` och ändrade inte de 36 arkiverade kompletta query-intervallen eller snapshots. `an` är en teknisk testfras, inte godkänd produktionsfråga.


## Länsstyrelsens diarier – tvåfras-diagnostikrun #30 (2026-11-27)

[Run #30](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46078595702) kördes från main efter [PR #715](https://github.com/dahlinrobert-lgtm/Skog/pull/715) med Blekinge, oktober 2026 och två separata fraser: `naturvårdsbränning` och `vattenverksamhet`. Jobbet, fokuserade valideringstester, insamling och artifact-upload avslutades `success`.

Artefakt [15236172620](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46078595702/artifacts/15236172620) (SHA-256 `10d9395022af39d07ac7c7fe140993790a0c704b68e9d4f9f0d2c55c83e83487`) visar:

| Sökfras | Källtal | Unika diarienummer | Sidor | Avstämning |
|---|---:|---:|---:|---|
| `naturvårdsbränning` | 0 | 0 | 0 | Komplett, avstämd |
| `vattenverksamhet` | 18 | 18 | 1 | Komplett, avstämd |

Summary rapporterar 2/2 förväntade intervall, 2/2 avstämda och inga intervall-/processfel. För `vattenverksamhet` visar sidans diagnostik 18 råa matchande rader och inga duplicerade diarienummer eller case-ID:n.

**Begränsning:** denna körning bekräftar exekvering av två fraser, inte högvolymspaginering eller den framåtriktade `Page$1`-specialvarianten. Ett intervall gav inga sidor och det andra endast en sida utan pagerkontroller. Det historiska fallet 143 råa rader/135 unika reproducerades inte. Ingen snapshot, manifestpost eller historik skrevs; källarkiv och rättighetsstatus är oförändrade.

**Nästa steg:** använd endast en exakt dokumenterad äldre sökparameteruppsättning eller ett konkret intervall som tidigare producerat 143/135 för ny avgränsad diagnostik. Undvik fler generiska upprepningar som inte kan ge ny pager- eller överlappsevidens.


## Länsstyrelsen – live-reproduktion utan datumfilter, run #1

Run [#1](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46079282744) (2026-11-27) genomfördes framgångsrikt via det diagnostics-only-workflow som tillkom i PR #718. Den använde Blekinge och två separata sökfraser utan registreringsdatumfilter.

| Sökfras | Källtal | Råa rader | Unika diarienummer | Dubbletter | Sidor |
|---|---:|---:|---:|---:|---:|
| `naturvårdsbränning` | 0 | 0 | 0 | 0 | 0 |
| `vattenverksamhet` | 143 | 143 | 126 | 17 | 3 |

`vattenverksamhet` gick via `Page$2` och `Page$3`. Överlapp: 4 diarienummer mellan sida 1–2, 12 mellan sida 1–3 och 1 mellan sida 2–3. Totalt 17 dubbla diarienummer och 17 dubbla case-ID:n. Alla tre sidor lästes och de 143 råa raderna stämdes av mot källtalet.

**Tolkning:** källtalet 143 från historisk körning #142 återkommer, men inte den tidigare observerade fördelningen 135 unika/8 överlapp. Run #1 visar 126 unika/17 dubbletter. Det visar att resultatmängd eller sidöverlapp varierar mellan körningarna; det bevisar inte varför. Vanliga numeriska sidargument användes, ingen ellips eller framåtriktad `Page$1` observerades.

Körningen var read-only/diagnostics-only och skrev ingen snapshot eller historik. Artefakt [#15236345745](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46079282744/artifacts/15236345745), SHA-256 `e8d373ddc11b1f742ff0cc5d2d6d78abef87148d099bad2f4f31e60c29eb80c4`.

**Nästa steg:** jämför postidentiteterna i artefakten från run #1 med historiska run #142. Fastställ därefter om skillnaden 135/8 kontra 126/17 beror på förändrad källdata eller sidvisning. Framåtriktad `Page$1` förblir obevisad.



## Länsstyrelsen – unbounded diagnostics run #2 (2026-11-27)

[Run #2](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46080208217) kördes från `main` efter PR #721 och avslutades success. Samtliga steg passerade: frasvalidering, Chromium, fokuserade pager-/diarietester, live-sökning och artifact-upload. Artefakt [15237355728](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46080208217/artifacts/15237355728), SHA-256 `7f3668b74555e19fdb0f3e3366baa1f8efbacf1e3c55373130d4294ca0597a40`.

För Blekinge utan registreringsdatumfilter:
- `naturvårdsbränning`: 0/0, bekräftat nollresultat.
- `vattenverksamhet`: källtal 143, 143 råa rader över tre sidor, 131 unika diarienummer och 12 upprepningar. Av dessa upprepningar ligger 3 på sida 2 och 9 på sida 3; inga dubbletter på sida 1. Samma 12 upprepade diarienummer motsvarar 12 upprepade case-ID:n.
- Alla tre sidor lästes; `total_reconciled=true` och inga query-/batchfel. Sidbytena `Page$2` och `Page$3` ändrade sidornas signatur.

Jämfört med run #1 (126 unika) har run #2 116 diarienummer gemensamma, 10 endast i run #1 och 15 endast i run #2. De 116 gemensamma diarienumren har oförändrade case-ID:n, status, datum och rubriker i artefakterna. Detta är en ny observation av ändrad resultat-/sidfördelning, inte bevis för att de 10/15 ärenden har skapats eller försvunnit. De 12 sidöverlappen bör behandlas som käll-/pagerbeteende och inte som separata händelser.

Run #2:s resultat har noll överlapp mellan de tre **deduplicerade** sidlistorna efter insamlarens unika extraktion, men råa siddiagnostikrader visar 3 upprepningar sida 2 och 9 sida 3. Bevara därför rå siddiagnostik när överlapp analyseras; summera inte enbart resultatlistans unika poster.

Körningen var diagnostics-only: inga snapshots, manifest, state eller events ändrades. Source status och källregister är oförändrade. Rättighetsbedömningar är oförändrade.

**Nästa steg:** ingen kodändring ännu. Den andra reproduktionen visar att instabiliteten kvarstår i sidindelningen (run #1: 126 unika/17 upprepningar; run #2: 131/12) samtidigt som det gemensamma urvalets metadata är stabilt. Undersök först om skillnaderna kan förklaras av källans ändrade sökresultat/sortering eller genom att jämföra de råa sid-ID-listorna från båda artefakterna. Undvik en fjärde körning innan den jämförelsen är gjord. Håll all frånvaro och identitetsdifferens utanför historiska events.


## Länsstyrelsen – analys av rå sidordning mellan unbounded run #1 och #2 (2026-11-28)

Efter merge av dokumentations-PR #722 har de fullständiga rådiagnostikartefakterna för [run #1](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46079282744) och [run #2](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46080208217) jämförts på sid- och diarienummernivå för Blekinge / `vattenverksamhet`.

**Sidöverlapp per körning:**

| Sidpar | Run #1 | Run #2 |
|---|---:|---:|
| 1–2 | 4 | 3 |
| 1–3 | 12 | 9 |
| 2–3 | 1 | 0 |
| Unika diarienummer i unionen | 126 | 131 |
| Råa rader | 143 | 143 |

De råa listorna innehåller 50/50/43 diarienummer per sida i båda körningarna. Dubbletterna är mellan sidor, inte upprepade rader inom en enskild sidas ID-lista. Run #1 har 17 upprepade identiteter (4+12+1) och run #2 har 12 (3+9+0).

Av 116 gemensamma diarienummer låg 43 kvar på sida 1, 45 kvar på sida 2 och 22 kvar på sida 3. Sex gemensamma ärenden flyttade från sida 3 i run #1 till sida 1 i run #2: `3389-2026`, `3708-2026`, `3717-2026`, `3765-2026`, `3769-2026` och `3913-2026`. 10 diarienummer finns endast i run #1 och 15 endast i run #2. Alla 116 gemensamma poster har identiskt case-ID, status, datum och ärenderubrik i båda artefakterna.

Den relativa ordningen för de 116 gemensamma identiteterna ändrades också: vid jämförelse av deras sammanfogade sidordning finns 1 374 omkastade par av 8 256 möjliga par (16,6 %). Detta är en jämförelse av observerad ordning, inte en förklaring till varför portalen ändrade den.

**Kodgranskning:** `scripts/search_lansstyrelsen_diary_browser.py` läser den ordning som redan renderas i resultatgriden och anger ingen egen sorteringsordning. Collectorn använder portalens `caseID` som primär identitet och diarienummer som fallback; redan sedda identiteter dedupliceras, medan råa diarienummer och siddiagnostik bevaras. De observerade överlappen är därmed synliga i artefakten och förklarar skillnaden mellan 143 råa rader och 126/131 unika poster. Pagineringen nådde tre sidor i båda körningarna med lyckade sidbyten `Page$2` och `Page$3`.

**Bedömning:** evidensen visar instabil ordning och sidplacering i källans renderade resultat mellan två tidpunkter. Den isolerar inte om orsaken är en ändrad ärendemängd, portalens sorteringsordning eller annan server-/databasvariation. Ingen kodändring motiveras nu: dedupliceringen skyddar mot dubbla events och källans 143 råa rader stäms av. Ändringar mellan körningar får inte tolkas som borttagningar eller skapa historiska events. Behåll diagnostics-only som verifieringsmetod; undvik fler identiska körningar tills en konkret hypotes eller ett nytt källbeteende motiverar dem.

**Nästa steg:** fortsätt med ordinarie daglig körning och kontrollera att den fortfarande fail-closed vid ofullständiga resultat och att upprepade case-ID:n inte skapar dubbla historikposter. Ingen ny unbounded probe eller sorteringsändring planeras utan ny evidens.

## Länsstyrelsen – jämförelse av historiska och nya Blekinge-resultat

En direkt jämförelse av diarienummerlistorna i artefakterna från [historisk run #142](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46011210069/artifacts/15203258666) och [unbounded run #1](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46079282744/artifacts/15236345745) har genomförts för `vattenverksamhet`.

| Mått | Historisk #142 | Ny run #1 |
|---|---:|---:|
| Källtal | 143 | 143 |
| Råa rader per sida | 50 / 50 / 43 | 50 / 50 / 43 |
| Unika diarienummer | 135 | 126 |
| Överlapp sida 1–2 | 5 | 4 |
| Överlapp sida 1–3 | 0 | 12 |
| Överlapp sida 2–3 | 3 | 1 |
| Totala upprepningar | 8 | 17 |

Av diarienumren i de båda körningarnas unioner återfinns 119 i båda. 16 finns endast i den historiska listan och 7 endast i den nya. Båda körningarna använde `Page$2` och `Page$3`; de råa sidstorlekarna och källtalet var alltså lika, men sidornas innehåll och överlappsmönster skiljde sig.

**Tolkning:** detta är evidens för att källans resultat-/sidfördelning inte var identisk vid de två tillfällena. Artefakterna visar inte om orsaken är ändrad ärendemängd, sorteringsordning eller portalens sidvisning. Skillnaderna får inte tolkas som borttagningar och ska inte skapa historiska events. Ingen kodändring eller historikskrivning har gjorts. Framåtriktad `Page$1` har inte observerats i någon av dessa två körningar.


## Länsstyrelsen – återtest av tidigare HTTP 500, diagnostics-only run #31 (2026-11-27)

[Workflow run #31](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46080266678) återanvände exakt den tidigare felande sökningen från daglig run #148: grupp `group_07`, kategori B, frasen `vattenverksamhet`, registreringsperiod oktober 2026 och alla tre län (Skåne, Halland, Västra Götaland). Körningen avslutades `completed/success`; samtliga fokuserade tester, liveinsamling och artifact-upload passerade.

Artefakt [15237021862](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46080266678/artifacts/15237021862), SHA-256 `4bc6d1c17b5b703b8751006e005252464ef3c8d7a6b55b1c2ed8d1ffccf81d1a`, innehåller:
- Skåne: 14/14 unika diarienummer, komplett och avstämt.
- Halland: 11/11, komplett och avstämt.
- Västra Götaland: 46/46, komplett och avstämt.
- Sammanfattning: 3 förväntade/observerade/avstämda intervall, 0 misslyckade intervall och 0 processfel.

**Tolkning:** HTTP 500-felet från Västra Götaland i run #148 kunde inte reproduceras när samma sökning kördes igen. Detta är evidens för en lyckad återhämtning vid ett senare försök, men inte bevis för att felet var rent tillfälligt eller att källan är stabil över tid. Run #31 var uttryckligen `diagnostics_only_no_persistence`; inga snapshots, manifest, state eller events skrevs och rättighetsstatus ändras inte.

**Nästa steg:** betrakta 500-felet som icke-reproducerat i en avgränsad omkörning, men behåll en öppen operativ risk. Ingen generell retry/backoff eller uppskalning införs utan evidens för leverantörens tekniska gränser. Vid nästa naturliga körning ska fel, län, sökparametrar, sidsteg och eventuell partiell extraktion bevaras separat. Först efter flera kompletta jämförbara återkommande körningar kan diariet omprövas för stabil återkommande drift.

## Polismyndighetens officiella API – kontroll av första schemalagda körningen (2026-11-28)

GitHub Actions schedule-historiken för Skog-repot granskades genom samtliga 467 tillgängliga schemalagda körningar från 2026-10-24 till 2026-11-28. Ingen körning för `.github/workflows/polisen-official-api-evaluation.yml` hittades. Däremot finns ordinarie schemalagda körningar för Brottsplatskartan-flödet `.github/workflows/police-events.yml`, senast 2026-11-27, med success. Orsaken till att den officiella workflowen inte har någon synlig körning är inte fastställd.

Workflowen saknade tidigare `workflow_dispatch`. En separat PR lägger till den manuella triggern utan att ändra schemat, API-anropet eller snapshot-/uploadlogiken. Efter merge ska en manuell körning från `main` utföras och dess loggar, Azure-objekt och manifest verifieras. 30-dagarsperioden börjar först vid första lyckade, fullständigt verifierade snapshot.

PM-027:s nuvarande Azure OIDC-identitet är dokumenterad med åtkomst endast till containern `project-manager`; den har inte verifierad läsbehörighet till `police-events`. Skogs befintliga OIDC-identitet har bred Storage Account-scope och delas av andra workflows; den ska inte återanvändas av projektledaren. Föreslagen lösning är en separat PM-identitet med `Storage Blob Data Reader` på endast `police-events`, federerad till PM-repot och ett särskilt GitHub Actions environment. Azure-identitet och RBAC är ännu inte konfigurerade eller live-verifierade.

Ingen snapshot, manifest, historik, källpost, kundvisning eller rättighetsstatus ändrades i denna granskning.

## Polismyndighetens officiella API – första verifierade snapshot (2026-11-28)

Den manuella körningen [Police official API evaluation snapshots #1](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46134508242) genomfördes från `main` efter merge av [PR #725](https://github.com/dahlinrobert-lgtm/Skog/pull/725). Workflow-run ID: `46134508242`; commit: `0c0f2f4a9c235a91b69dd252a5e5464428b160b2`; event: `workflow_dispatch`; status `completed/success`.

Capture-steget rapporterade `status=complete`, **500 poster**, varav **43 Norrbottenposter** (`location.name=Norrbottens län`), hämtade `2026-11-28T10:18:33.505969+00:00`. Azure OIDC-inloggningen lyckades. Uploaderloggen rapporterade:
- blob: `polisen-official/runs/46134508242/attempt-1/snapshot.json.gz`
- råstorlek: `179666` bytes
- rå SHA-256: `b1dbd8e467d9987115d493034f0d264ab4d9887664c658ebf32a583c4412498a`
- `snapshot_verified=true`, 500 poster och 43 Norrbottenposter.

Verifieringsgräns: uploaderkoden laddar ned den komprimerade blobben i samma jobb, gzip-dekomprimerar och jämför rå byte count samt SHA-256 innan den skapar `manifest.json`. Jobbloggen visar därefter `snapshot_verified=true`, och hela steget avslutades success. Manifestobjektets exakta JSON-innehåll och Azure-systemmetadata har däremot inte lästs separat i denna granskning, eftersom aktuell ansluten GitHub-/SharePoint-integration inte erbjuder Azure Blob-läsning. Detta ska inte beskrivas som en oberoende Azure-manifestinspektion.

**Utvärderingsstart:** första lyckade, kompletta och uploader-verifierade snapshot är 2026-11-28. 30 kalenderdagarsperioden räknas från denna snapshot; målet är minst 25 lyckade dagliga snapshots. Denna första snapshot är baslinje och ska inte skapa retroaktiva händelser eller kundlarm. Nästa dags snapshot behövs för att börja bedöma kontinuitet och förändringar.

Ingen sammanfogning med Brottsplatskartan-historiken görs. API:ets 500 aktuella poster är ett begränsat publicerat urval, inte ett komplett historiskt polisregister. Koordinater behandlas inte som exakta händelsepositioner. Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution förblir separata rättighetsgrindar.


## Nationell avverkningsinsamling – stabilitet vid skanning (2026-11-28)

Den nationella insamlaren `scripts/monitor_national.py` har kompletterats med en andra oberoende ArcGIS `returnIdsOnly`-inventering efter att samtliga feature-batcher har hämtats. Den första och andra ID-mängden måste vara identiska. En förändring under skanningen, dubbletter i ID-inventeringen, dubbla feature-ID:n eller oväntade feature-ID:n gör att körningen avbryts innan `latest.json.gz` eller en daterad snapshot skrivs. Den befintliga kontrollen av saknade ID:n och riktade retry behålls.

Testerna utökas för batchning över 250 poster, stabil andra inventering, förändrad inventering, dubbletter och oväntade ID:n. Workflowen kör testjobbet vid pull request men kör inte nationell insamling i PR-event. Vid schemalagd eller manuell körning skapas en data-PR för ändrade arkivfiler i stället för direkt push till `main`. Befintligt schema (1:a och 16:e varje månad kl. 05:47 UTC), snapshotformat, arkivvägar och full-/deltaformat behålls.

Detta är en skyddsåtgärd mot att en rörlig källinventering publiceras som en skenbart komplett snapshot. En skillnad mellan två ID-inventeringar bevisar inte att objekt har avregistrerats eller avverkats och ska inte skapa borttagningshändelser eller larm. Ändringen startade ingen insamling och ändrar inte rättighets- eller kundvisningsstatus. PR #729 är mergad till `main` (merge commit `36b1abf62dea09106d8bca13c6e0a528df13d121`). PR-körningens testjobb avslutades `success`; arkivjobbet var `skipped` på PR-event, vilket bekräftar att ingen nationell insamling startades av testkörningen. Faktisk insamling, senaste arkivmanifest och schemalagd drift efter ändringen är ännu inte verifierade.


## Nationell avverkningsinsamling – uppföljning av ett saknat ID (2026-11-28)

Körning [#7](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46143160009) hämtade 133 467 av 133 468 ID:n. Ett ID saknades efter det tidigare riktade återförsöket. Testjobbet var godkänt, insamlingssteget misslyckades och publiceringssteget kördes inte. Loggen anger att senaste kända kompletta data bevarades.

Det enskilda bortfallet är inte bevis för avregistrering, borttagning eller avverkning. Ingen ofullständig snapshot ska publiceras och historiska objekt ska inte tas bort på denna grund.

Uppföljningsändringen på branch `fix/national-harvest-missing-id-diagnostics` gör upp till tre individuella försök per saknat ID och sparar försök/status/senaste felorsak i kördiagnostiken. Om ett ID fortfarande inte kan hämtas avbryts hela snapshoten fortsatt före skrivning. Ändringen fyller inte luckan med data från föregående snapshot. Enhetsfallen täcker både återhämtning och fortsatt olöst ID. Orsaken hos källsystemet är ännu okänd. PR #731 är mergad och CI samt första nationella körningen efter merge verifierades i Actions #10; se avsnittet nedan för resultat och lagringsbedömning.


## Nationella avverkningsanmälningar – första kompletta snapshot och lagringsgranskning (2026-11-28)

[Workflow #10](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46144482820) kördes efter merge av PR #731. Test- och arkivjobbet avslutades `success`. ArcGIS-lagret gav 133 468 ID:n före och efter hämtningen; inventeringarna var identiska. Alla 133 468 features hämtades, med 0 saknade, 0 dubbla och 0 oväntade ID:n. Inga individuella återförsök behövdes.

Körningen skapade full snapshot `data/national/snapshots/20261128T124344Z.json.gz` (104 609 996 byte) och uppdaterade `data/national/latest.json.gz` (104 609 986 byte). Diagnostiken rapporterade 133 468 added, 0 updated och 0 removed. Data-PR [#733](https://github.com/dahlinrobert-lgtm/Skog/pull/733) mergades 2026-11-28 12:57:31 UTC; merge commit `24d1cdf17e7cc523dff3d4241a56a251ceb808b2`.

**Lagringsbedömning:** GitHub varnade eftersom båda filerna överstiger 50 MiB. De är cirka 99,76 MiB, endast cirka 242 KiB under GitHubs hårda gräns på 100 MiB. GitHub API rapporterade repo-storlek 671 115 KB. De fyra nuvarande filerna under `data/national/` (latest samt tre daterade snapshots) omfattar cirka 387 MiB. Uppdateringar av `latest.json.gz` skapar dessutom nya Git-objekt i historiken. GitHub-dokumentationen rekommenderar att stora genererade filer lagras utanför Git, exempelvis i objektlagring. [GitHub: About large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) och [Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits).

**Rekommenderad målbild:** Azure Blob Storage för oföränderliga daterade full-/delta-snapshots och GitHub endast för kod, tester, dokumentation samt ett litet manifest/pekare med snapshot-ID, status, antal, byte count och SHA-256. En flytt kräver separat verifierad container/behörighet, upload, readback-audit och restore-test. Befintlig gemensam Azure-identitet har bred Storage Account-scope enligt `STORAGE_INVENTORY.md`; den ska inte återanvändas eller få ändrad RBAC utan separat konsekvensanalys. Rättigheter till historisk lagring och kundvisning måste bedömas separat.

Befintliga Git-snapshots och historik ska bevaras. Ingen historikomskrivning eller borttagning görs. Befintlig Git-publicering ska inte stängas av förrän Azure-flödet är verifierat end-to-end och övergången är godkänd. Gzip-binärernas interna innehåll/hash och restore har inte oberoende verifierats efter PR #733.

**Nästa steg:** utveckla en separat, avgränsad Azure-arkiveringslösning med immutable snapshots, SHA-256/byte count, readback-audit och restore-test. Ingen kundavisering eller ändrad källrättighetsstatus följer av denna snapshot.
