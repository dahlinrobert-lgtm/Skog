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

**Prioritet:** Hög

**Nuvarande läge**
Ett Lastkajen-material har bearbetats lokalt. Projektanteckningar anger ett attributindex med 455 812 poster, geometrier och attribut, EPSG:3006, SHA-256-kontroller och spatialt R-tree-index.

**Historik**
Detta är en lokal baslinje, inte ännu ett verifierat automatiskt uppdaterings- och förändringsflöde.

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

### 4.12 Viltdata – älgstatistik

**Prioritet:** Medelhög

**Nuvarande läge**
Separat projekt `alg-grasmyr` har regionala pilotflöden och snapshots. Nationell insamling är ett framtida steg, inte något som ska beskrivas som färdig.

**Historik**
Målet är daterade snapshots och bevarade källvärden, definitioner och områdesindelningar.

**Rättigheter**
Kontrollera villkor per leverantör och datamängd.

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
API- och webbaserad åtkomst har undersökts. Projektet har testat kommun- och länsvisa ärendeflöden. Erfarenheten är att äldre nyheter/händelser inte alltid finns kvar i källan; månatliga snapshots har därför identifierats som viktiga.

**Historik**
Bevara metadata, dokument-ID, källa och hämtningstid. Dokumentbilagor ska hanteras separat från metadata.

**Rättigheter**
Bedöm varje handling. Offentlighet innebär inte automatiskt fri kommersiell återpublicering. Sekretess, personuppgifter, upphovsrätt och tredje mans rättigheter måste kontrolleras.

**Framtida användning**
Identifiera relevanta myndighetsärenden och beslut. Publicera inte automatiskt fullständiga dokument eller personuppgifter i kundprodukten.

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
| Trafikverket | Verifiera veckosnapshots och Lastkajen-produktens villkor | Kontrollera senaste workflow och produktmetadata |
| NVDB vägnät | Automatiskt uppdateringsflöde saknas | Planera versionsbaserad uppdatering |
| Viltdata älg | Nationell täckning saknas | Utöka från regional pilot efter källinventering |
| Naturvårdsverket | Exakta prioriterade lager och producentvillkor | Välj lager och dokumentera metadata |
| Vindbrukskollen | Nationell historik och fullständighet | Verifiera återkommande snapshotflöde |
| Länsstyrelsernas diarier | Dokument-/personuppgiftsbedömning och beständig arkivering | Fortsätt metadataflödet, avgränsa dokumenthantering |

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

Skog har etablerat ett brett underlag av myndighets- och geodatakällor och utvecklat flera viktiga insamlings- och historikflöden. De mest konkreta spåren är Skogsstyrelsens avverkningsanmälningar, samråd, Trafikverkets miljö- och viltolycksdata, NVDB och NVR:s historiska olycksdata. Torvkartan har ett skriftligt kommersiellt användningsbesked från SLU. Lantmäteriets fastighetsprodukt är ett centralt externt beroende som kräver att beställningarnas exakta beslut och villkor verifieras.

Den viktigaste återstående förflyttningen är från separata prober och pilotflöden till en komplett, kvalitetssäkrad och rättighetsbedömd historisk dataplattform. Först därefter ska verkliga kundaviseringar aktiveras.

**Långsiktig målbild:** Skogskoll ska kombinera historiska observationer, myndighetsdata och geografisk matchning till en tillförlitlig, fastighetsspecifik bevakningstjänst för skogsägare.
