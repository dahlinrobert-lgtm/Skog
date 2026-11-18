# Skogskoll – datakällor, åtkomst och användning

**Dokumentdatum:** 2026-11-14  
**Version:** 1.0  
**Omfattning:** Skogskoll kundprodukt och de datakällor i Skog-repot som kan användas av produkten.

> **Statusprincip:** Detta dokument skiljer mellan (1) teknisk åtkomst, (2) faktisk insamling/snapshot, (3) verifierad historik, (4) rätt att lagra och bearbeta, och (5) rätt att visa eller distribuera till kunder. En fungerande API-probe är inte bevis för fullständig historik eller kommersiella rättigheter.

## 1. Syfte och målbild

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
Skogsstyrelsens geodata anges generellt som CC0 om inget annat anges. Kontrollera ändå exakt lager, metadata och produktbeskrivning före extern användning.

**Framtida användning**
En ny avverkningsanmälan som matchar ett bevakat område ska kunna visas som en ny upptäckt händelse. En anmälan är inte bevis för att avverkning har genomförts.

**Nästa steg**
Slutför källverifiering och fullständig ingestion, etablera baslinje och jämför minst två kompletta körningar innan larm.

### 4.2 Skogsstyrelsen – samråd

**Prioritet:** Mycket hög  
**Datatyper:** punkt-, linje- och polygonlager.

**Nuvarande läge**
Separata lager och objektidentiteter har undersökts. Historisk insamling är ett prioriterat spår, men status för varje geometri-/lagers fullständiga produktionshistorik måste verifieras i respektive workflow och snapshotmanifest.

**Historik/tidsserie**
Målet är dagliga snapshots där källans ID, geometri, attribut, hämtningstid och källans egna datum bevaras. Försvunna objekt ska först klassas efter en komplett och godkänd skanning.

**Rättigheter**
Skogsstyrelsens generella CC0-villkor är utgångspunkt, med kontroll av varje specifik produkt.

**Framtida användning**
Visa samråd som kan beröra en fastighet och skilj tydligt mellan ärende, planerad åtgärd och genomförd åtgärd.

### 4.3 Skogsstyrelsen – skogliga grunddata och volym omdrev 3

**Prioritet:** Hög  
**Datatyp:** raster och tillhörande produktmetadata.

**Nuvarande läge**
Rasterprodukter har laddats ned eller undersökts och används som skogligt analysunderlag. Originalarkiv och metadata ska hållas åtskilda från bearbetade produkter.

**Historik/tidsserie**
Spara varje tillgänglig produktversion med produktnamn, version, publicerings-/produktionsdatum, hämtningstid, CRS, upplösning, filstorlek och SHA-256. Jämförelser mellan versioner ska göras först när deras semantik och täckning är jämförbara.

**Rättigheter**
Generella geodatavillkor anger CC0 om inget annat anges. Kontrollera den exakta produktens metadata.

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
Skogsstyrelsens generella CC0-villkor är utgångspunkt, men den särskilda produktbeskrivningens licens- och erkännandesektion ska kontrolleras.

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
- Två lokala fullständiga snapshots från 2026-11-13 har verifierats: vardera 49 arter, 21 län och 550/550 lyckade statistikförfrågningar. Båda innehöll 73 255 observationer.
- `scripts/viltdata_kill_statistics_diff.py` jämför endast kompletta snapshots med samma observationstäckning. Jämförelsen mellan dessa två körningar identifierade sju ändrade 2026-värden, samtliga `value_changed`; inga observationer blev nya eller saknade.
- Tio riktade tester för snapshot och diff passerade 2026-11-18.
- PR #422 är sammanslagen i `main`. Den manuella GitHub Actions-workflowen har live-verifierats i körning [#44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179): snapshot `20261118T204420Z`, 49 arter, 21 län, 550/550 lyckade statistikförfrågningar och noll fel. CI körde 10/10 riktade tester och verifierade 552 filer mot manifestets byteantal och SHA-256. Se [Viltdata – manuell nationell snapshot-workflow](viltdata-kill-statistics-workflow.md).

**Historik**
Bevara daterade snapshots, originalvärden, definitioner, artidentiteter och geografisk omfattning. Ofullständiga körningar får inte användas som baslinje eller diffunderlag. Första kompletta baslinjen ska inte skapa historiska larm. Manifestets `complete` anger teknisk insamlingsfullständighet, inte att alla rapporteringsår är slutrapporterade.

**Lagring**
Workflowen använder endast en tidsbegränsad GitHub Actions-artifact (30 dagar) för manuell granskning. Den verifierade artifacten från 2026-11-18 har ID `14470426808` och retention till 2026-12-18. Den är inte ett historiskt arkiv. Azure Blob Storage är nu tekniskt verifierat för syntetiska testobjekt. PR #424 är sammanslagen och workflowen `.github/workflows/viltdata-azure-storage-smoke-test.yml` kördes framgångsrikt i [run #44401688469](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44401688469). En separat container `viltdata-kill-statistics` skapades; syntetisk payload och manifest skrevs och lästes tillbaka. Payloaden omfattade 235 bytes och SHA-256 matchade exakt vid återläsning. Detta verifierar den använda OIDC-identitetens praktiska container-/Blob-åtkomst i körningen, men inte exakt RBAC-roll/scope eller formell resursregion. Azure CLI visade `westus2`; Storage Account-resursens faktiska location ska kontrolleras i Azure Portal innan dokumenterad Sweden Central-region ändras. Inga Viltdata-original har laddats upp. Se `docs/viltdata-azure-storage.md`. PR #427 är mergad i `main` (merge commit `7f4077b53ccb2d9d8308daa278d7fcb6674e79ee`). `scripts/viltdata_azure_archive.py` och `.github/workflows/viltdata-azure-archive.yml` tillhandahåller manuell upload, djup audit och restore. Upload kräver komplett manifest och SHA-256-verifierade originalfiler, använder create-only och är spärrad bakom `rights_approved` (default false). PR-CI [#476](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44404345303) passerade 322 tester inklusive 8 arkivtester; main-CI [#483](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44405429416) passerade 322 tester. Azure upload/audit/restore är inte live-verifierade och inga källdata har laddats upp.

**Rättigheter**
Teknisk åtkomst till den publika API-tjänsten är inte ett godkännande för permanent historisk lagring, kommersiell användning, bearbetning, kundvisning eller vidare distribution. Villkor ska kontrolleras för den exakta statistikprodukten och varje avsedd användning.

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
| Miljöwebb Landskap | Verifiera täckning och senaste kompletta snapshots för Gräsmyr-piloten | Kontrollera måndagskörning, manifest, antal och lagervillkor |
| NVDB Viltolyckor | Verifiera frekvensdefinition, referensperiod och jämförbar historik | Kontrollera sju lager, produktmetadata och snapshots |
| NVDB vägnät/Lastkajen | Verifiera produktversion, beställningsvillkor och återkommande uppdatering | Dokumentera lokal baslinje och bygg versionsstyrt uppdateringsflöde |
| NVDB vägnät | Automatiskt uppdateringsflöde saknas | Planera versionsbaserad uppdatering |
| Viltdata älg | Nationell täckning saknas | Utöka från regional pilot efter källinventering |
| Naturvårdsverket | Exakta prioriterade lager och producentvillkor | Välj lager och dokumentera metadata |
| Vindbrukskollen | Nationell historik och fullständighet | Verifiera återkommande snapshotflöde |
| Länsstyrelsernas diarier | Första pilotbaslinjen är publicerad för Norrbotten, oktober 2026, kategori B; återstående är reproducerbarhet, täckning och tekniska begränsningar | Upprepa avgränsad manuell månadskörning; dokumentera län/fras-täckning och granska metadata separat från dokument/bilagor |
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
