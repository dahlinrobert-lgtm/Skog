# Öppna data och kommersiell användning – Skog

**Registerdatum:** 2026-11-01  
**Syfte:** Bedöma vilka datakällor som kan användas i en kommersiell skoglig data- och analystjänst.  
**Omfattning:** Skog-repot, Skogskoll och den gemensamma data-plattformen.

> Detta är ett operativt granskningsregister, inte ett juridiskt utlåtande. Bedömningen gäller de publicerade villkor som identifierats vid kontrolldatumet. Den måste verifieras mot exakt produkt, metadata, version och eventuellt avtal innan kommersiell publicering.

## 1. Grundprincip

Bedöm alltid den exakta datamängden och produkten – inte bara myndigheten eller API-leverantören. Registrera separat:

1. Rätt att använda kommersiellt.
2. Rätt att lagra historiska kopior.
3. Rätt att bearbeta och kombinera data.
4. Rätt att visa eller distribuera bearbetat material till kunder.
5. Rätt att distribuera originaldata vidare.
6. Tekniska API-/tjänstevillkor, inklusive autentisering, anropsbegränsningar, cache och tillgänglighet.
7. Sekretess, personuppgifter, upphovsrätt och tredje mans rättigheter.

En öppen licens ger inte automatiskt rätt att återpublicera tredjepartsinnehåll som råkar finnas i samma tjänst. Offentlig åtkomst till en handling är inte heller i sig en generell återanvändningslicens.

## 2. Statusnivåer

| Status | Betydelse | Åtgärd |
|---|---|---|
| Grön | Kommersiell användning är tillåten enligt identifierad öppen licens | Följ attribution och tekniska villkor |
| Villkorad grön | Kommersiell användning tillåten, men produkt-/datasetvillkor måste bekräftas | Spara produktmetadata och kontrollera villkor |
| Gul | Oklart eller beroende av handling, personuppgift eller avtal | Ingen extern publicering före granskning |
| Röd | Kräver uttryckligt avtal/vidareförädlingsrätt eller är inte öppet | Ingen kommersiell användning före skriftligt klartecken |

Status i registret är en riskklassning för projektet, inte ett bindande juridiskt besked.

## 3. Första bedömning av källorna

| Källa | Preliminär status | Viktigaste villkor / risk |
|---|---|---|
| Skogsstyrelsen – geodata, brandområden och återvätningsavtal | Villkorad grön | CC0 som huvudregel för myndighetens geodata, om inget annat anges; verifiera exakt produkt/lager |
| Skogsstyrelsen – statistikdatabas | Grön för statistikdata | CC0; rapporter/analyser är CC BY; foton/illustrationer omfattas inte |
| Lantmäteriet – listade öppna data | Grön för listade produkter | CC0, inklusive kommersiell användning |
| Lantmäteriet – avgiftsbelagd fastighets-/geodata | Röd före avtal | Kommersiell vidareförädling och återförsäljning kan kräva särskilt avtal |
| Lantmäteriet – NGP | Villkorad grön | Konsumentvillkor måste accepteras; kontrollera producent, dataset och personuppgifter |
| SMHI – öppna data | Grön med attribution | CC BY 4.0 SE; ange källa och ändringar; använd dokumenterade tjänster och undvik onödig belastning |
| Copernicus Sentinel | Villkorad grön | Sentinel-data får reproduceras, distribueras och bearbetas; annat portalinnehåll har separata villkor |
| Länsstyrelsernas diarier | Gul, per handling | Offentlig handling är inte automatiskt fri att återpublicera; sekretess, GDPR och tredje mans rättigheter |
| Naturvårdsverket – listade öppna data | Villkorad grön | Öppna data får användas fritt; kontrollera informationsansvarig och tredjepartsrättigheter |
| Life2Taiga – naturvårdsåtgärder | Gul | Fastställ producent, projektvillkor och rätt att lagra/återpublicera geometrier |
| SLU Torvkarta 1.0 | Gul | SLU är produktansvarig; öppen nedladdning men licens för kommersiell återanvändning måste bekräftas, särskilt p.g.a. Lantmäteriets höjddata som modellunderlag |
| Skogsstyrelsen – Ståndortsindex SIS | Villkorad grön | Skogsstyrelsens geodata omfattas normalt av CC0; kontrollera produktbeskrivningens särskilda licens-/erkännandesektion |
| SGU – geologiska data | Grön | CC0 sedan 9 juni 2024; bilder, illustrationer och annat webbmaterial kan ha separata villkor |
| Sakfråga | Gul, avtalsgranskning | API-åtkomst fastställer inte automatiskt rätt att återanvända bilagor eller dokument kommersiellt |
| Sveaskog / SCA | Röd utan skriftligt tillstånd | Privata företagsdata ska inte behandlas som öppna data |

Se den maskinläsbara källförteckningen i data-platform/config/sources.yml för produktposter, granskningsstatus och källvillkor.

## 4. Särskilt viktiga källvillkor

### Skogsstyrelsen

Skogsstyrelsen anger att dess geodata är CC0 om inget annat anges. Det ger i normalfallet möjlighet att använda, bearbeta, lagra och distribuera materialet kommersiellt. Den exakta produkten/lagerbeskrivningen måste ändå kontrolleras. Statistikdatabasen har CC0-villkor för statistikdata, medan rapporter och analyser är CC BY och foton/illustrationer inte får återanvändas utan tillstånd.

- Geodatavillkor: https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/villkor/
- Öppna data: https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/oppna-data/
- Statistikvillkor: https://skogsstyrelse.se/statistik/bra-att-veta-om-statistiken/anvandningsvillkor/

### Lantmäteriet

Lantmäteriets uttryckligen listade öppna geodata är CC0 och får användas kommersiellt. Detta får inte blandas ihop med avgiftsbelagda produkter. För avgiftsbelagda geodata kan kommersiell vidareförädling och spridning till kunder kräva ett särskilt vidareförädlar-/återförsäljaravtal. Kommersiell slutanvändning är inte samma sak som rätt att distribuera data vidare.

- Öppna data: https://www.lantmateriet.se/sv/geodata/vara-produkter/avgiftsfria-produkter/oppna-data/
- Villkor och avgifter: https://www.lantmateriet.se/sv/geodata/vara-produkter/Villkor-och-avgifter/
- NGP: https://www.lantmateriet.se/sv/nationella-geodataplattformen/om-ngp/avtal-och-villkor/

### SMHI

SMHI:s öppna data omfattas av CC BY 4.0 SE. Kommersiell användning och bearbetning är tillåten, men SMHI ska anges som källa och ändringar ska anges. SMHI anger också att dokumenterade API:er ska användas och att onödig masshämtning och upprepade anrop ska undvikas. Konsekvensbaserade vädervarningar och meddelanden har separata villkor: de får användas kommersiellt men får inte ändras.

- Villkor: https://www.smhi.se/data/om-smhis-data/villkor-for-anvandning

### Naturvårdsverket

Naturvårdsverket har en katalog över öppna miljö- och geodata. Öppna data får användas fritt, men när informationsansvaret ligger hos en annan organisation – exempelvis länsstyrelse, kommun eller vattenvårdsförbund – måste den organisationens rättigheter kontrolleras. Utgå därför från datasetets producent och metadata, inte enbart från att det finns i Naturvårdsverkets katalog.

- Öppna data: https://www.naturvardsverket.se/verktyg-och-tjanster/data-databaser-och-sokregister/tillgangliggorande-av-oppna-data/
- Datakatalog: https://oppnadata.naturvardsverket.se/

### SGU

SGU anger att samtliga geologiska data som myndigheten tillhandahåller är öppna data under CC0 sedan den 9 juni 2024. Detta omfattar kommersiell användning, bearbetning och återanvändning. Skilj dock geologiska dataprodukter från webbplatsens bilder, illustrationer, filmer och annat material som kan ha separata villkor.

- Licensvillkor: https://www.sgu.se/produkter-och-tjanster/geologiska-data/om-geologiska-data/licensvillkor/
- Upphovsrätt och material: https://www.sgu.se/produkter-och-tjanster/kundservice/upphovsratt-for-sgus-produkter-och-material/

### Copernicus Sentinel

EU:s rättsliga meddelande för Sentinel-data tillåter fri och öppen användning, inklusive reproduktion, distribution, kommunikation till allmänheten, bearbetning och kombination med andra data, så länge användningen är laglig. Det finns begränsningar bland annat för säkerhet, tredje mans rättigheter och risk för störning av tjänster. Copernicus Data Space Ecosystem skiljer uttryckligen mellan Sentinel-data och annat innehåll på portalen; det senare kan vara begränsat till icke-kommersiell användning. Använd därför Sentinel-data via den relevanta datalicensen och återanvänd inte portalens övriga material under samma antagande.

- Sentinel legal notice: https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice
- Data Space terms: https://dataspace.copernicus.eu/terms-and-conditions

### Skogsstyrelsens brandområden och återvätningsavtal

Dessa lager är registrerade som separata datakällor eftersom de har egna produktbeskrivningar, attribut och semantik. Skogsstyrelsens generella geodatavillkor anger CC0 om inget annat anges. Innan kundpublicering ska respektive lager metadata och produktbeskrivning kontrolleras. Återvätningsavtal beskriver avtalade områden och ska inte tolkas som bevis på att fysiska åtgärder har genomförts.

- Brandområden: https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaBrand/MapServer/0
- Återvätningsavtal: https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAtervatningavtal/MapServer/0
- Återvätningsavtal – produktbeskrivning: https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/atervatningsavtal---produktbeskrivning.pdf

### Life2Taiga

Naturvårdsåtgärdslager som används i projektet hämtas från en extern ArcGIS FeatureServer. Eftersom värdskap och dataägande inte nödvändigtvis är samma sak är licensen tills vidare okänd. Innan data används i en kommersiell produkt behöver projektets dataägare och eventuella finansierings-/partneravtal identifieras. Tills dess: ingen vidare distribution eller kommersiell publicering av råa geometrier.

- Layer 13: https://ext-hostedgeodata.lansstyrelsen.se/arcgis/rest/services/Hosted/Life2Taiga_v3_Extern/FeatureServer/13

### SLU Torvkarta 1.0

Torvkartan är nu identifierad som en SLU-produkt, inte som en generisk Skogsstyrelsen-produkt. Produktbeskrivningen (Anneli Ågren, 2022-09-28) beskriver två rasterlager: en klassad karta och en kontinuerlig karta. Upplösningen är 2 × 2 meter och koordinatsystemet SWEREF 99 TM. Den klassade kartan har klasserna vatten, mineraljord och torvdjup ≥30, ≥40 respektive ≥50 cm. Den kontinuerliga kartan beskriver organiska lagrets tjocklek i centimeter. Produktbeskrivningen redovisar även saknade områden där indata saknas och en RMSE på cirka ±19 cm för den kontinuerliga kartan.

SLU:s sida anger att kartorna kan laddas ned fritt via SLU:s filserver och att den nationella mosaiken är över 40 GB. Detta bekräftar teknisk åtkomst, men produktbeskrivningen anger inte uttryckligen en licens för kommersiell återanvändning. Kartan bygger dessutom på GSD-Höjddata grid 2+ © Lantmäteriet. Därför ska vi inte dra slutsatsen att all kommersiell återpublicering eller lagring är tillåten bara för att filerna är nedladdningsbara.

**Beslut:** Behåll gul status tills SLU bekräftar skriftligen att kommersiell användning, historisk arkivering, bearbetning och distribution av härledda raster/statistik är tillåten och anger hur Lantmäteriets underliggande data påverkar villkoren.

- Produktbeskrivning: https://www.slu.se/contentassets/2368b3706efb45799ce0427f00455068/produktbeskrivning_slu_torvkarta1.0.pdf
- SLU:s nedladdning: https://gis.slu.se/data/peat_1_0/
- REST: https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/Torvkarta_1_0/ImageServer
- Tjänster och konto: https://skogsdatalabbet.se/skogsdatalabbets-geodatatjanster/

### Skogsstyrelsen – Ståndortsindex SIS

SIS betyder ståndortsindex skattat utifrån ståndortsegenskaper. Det ska skiljas från SIH, som baseras på mätningar i det befintliga beståndet. Skogsstyrelsens aktuella produktbeskrivning är daterad 2026-10-02 och beskriver skattningar för gran respektive tall. Skattningen bygger på laserdata från två tidpunkter och andra referens-/miljövariabler. Skogsstyrelsens nedladdningskatalog listar separata produkter för Ståndortsindex SIS Gran och Tall.

Skogsstyrelsens generella geodatavillkor anger CC0 om inget annat anges. Den specifika produktbeskrivningen har en egen sektion om licens och erkännande. Vi har identifierat den sektionen, men behöver läsa dess exakta formulering innan vi markerar produkten som helt godkänd för kommersiell distribution. Preliminär status är därför villkorad grön, inte slutligt godkänd.

- Produktbeskrivning (2026-10-02): https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/raster-skogligagrunddata-standortsindexsis---produktbeskrivning.pdf
- Generella geodatavillkor: https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/villkor/
- Nedladdningskatalog: https://www.skogsstyrelsen.se/laddanergeodata
- REST: https://geodata.skogsstyrelsen.se/arcgis/rest/services/Skogsdatalabbet/SIS_1_0/ImageServer

### Gemensamma tekniska villkor för Skogsdatalabbets rastertjänster

Skogsdatalabbets REST- och WMS-tjänster kräver användarkonto. SLU anger att Torvkartan även kan laddas ned separat som klassat raster, uppdelade kontinuerliga raster eller nationell mosaik. Vi ska därför skilja mellan rätt att använda datan och de tekniska villkoren för tjänsten. Innan vi skalar upp veckosampling eller börjar lagra fullständiga nationella raster behöver vi bekräfta kontovillkor, exportbegränsningar, cache-/versionsmetadata, anropskvoter och rätt att arkivera upprepade versioner.

### Länsstyrelsernas diarier

Diarieuppgifter och handlingar måste bedömas på dokumentnivå. Sekretessprövning vid utlämnande, personuppgiftsregler, upphovsrätt och tredje mans rättigheter kan påverka både lagring och publicering. Spara källhänvisning och dokument-ID, men publicera inte automatiskt hämtade dokument eller personuppgifter i kundprodukten.

## 5. Rättslig ram

- Lag (2022:818) om den offentliga sektorns tillgängliggörande av data: https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2022818-om-den-offentliga-sektorns_sfs-2022-818/
- EU-direktiv 2019/1024 om öppna data och vidareutnyttjande av information från den offentliga sektorn: https://eur-lex.europa.eu/eli/dir/2019/1024/oj
- CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/deed.sv
- CC BY 4.0: https://creativecommons.org/licenses/by/4.0/deed.sv

Öppna datalagen främjar vidareutnyttjande, men upphäver inte sekretess, dataskydd, säkerhetsskydd eller immateriella rättigheter. Lagen innebär inte heller att varje myndighetshandling måste publiceras som öppna data.

## 6. Obligatoriska metadata per datakälla

Följande ska finnas i data-platform/config/sources.yml eller i ett separat produkt-/datasetregister:

- Stabilt source_id och separat dataset_id när en leverantör har flera produkter.
- Leverantör, produktnamn, endpoint/nedladdningsadress och ansvarig producent.
- Licensnamn, licensversion, licens-URL och datum då villkoren kontrollerades.
- Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution – bedömda separat.
- Attributionskrav och föreskriven attributionstext.
- API-/tjänstevillkor: autentisering, kvoter, anropsfrekvens, cache, SLA och tekniska begränsningar.
- Geografisk täckning, format, CRS, enheter, uppdateringsfrekvens och tidsstämpel.
- Eventuella personuppgifter, sekretessrisker, tredjepartsrättigheter och särskilda begränsningar.
- Granskningsstatus, granskningsdatum, ansvarig och nästa granskningsdatum.
- Dokumentation av ändringar i licens och villkor över tid.

## 7. Kontroller före kommersiell publicering

En datakälla får inte automatiskt gå från insamling till kundpublicering. Använd denna kontroll:

- [ ] Exakt produkt och producent identifierade.
- [ ] Licens och version sparade med datum.
- [ ] Kommersiell användning bekräftad.
- [ ] Historisk lagring/arkivering bekräftad.
- [ ] Bearbetning och kombination bekräftad.
- [ ] Kundvisning och vidare distribution bedömda separat.
- [ ] Attribution implementerad där det krävs.
- [ ] Personuppgifter, sekretess och tredjepartsrättigheter kontrollerade.
- [ ] API-/tjänstevillkor och belastningsbegränsningar dokumenterade.
- [ ] Eventuellt avtal sparat utanför publikt repo; inga hemligheter eller personuppgifter i Git.

## 8. Rekommenderad prioritering

1. **Först:** Skogsstyrelsens geodata och statistik – mest direkt relevanta och tydligast öppna villkor.
2. **Därefter:** SMHI och Copernicus – bra för tidsserier, miljö- och förändringsanalys.
3. **Parallellt:** Lantmäteriets specifika CC0-produkter. Håll avgiftsbelagd fastighetsinformation utanför kommersiell publicering tills rätt avtal finns.
4. **Nästa:** Naturvårdsverket och SGU – verifiera exakta dataset, licenser och tjänstevillkor.
5. **Separat spår:** Länsstyrelsernas diarier och Sakfråga – dokument-/avtalsgranskning innan publicering.
6. **Affärsdialog:** Sveaskog och SCA – efterfråga skriftliga villkor för åtkomst, historik, analys, kundvisning och vidare distribution.

## 9. Förvaltningsregel

Registret ska ses över när:
- en ny datakälla eller produkt läggs till,
- en endpoint eller produktversion ändras,
- leverantören ändrar licens eller API-villkor,
- användningen ändras från intern analys till kundvisning eller vidare distribution,
- ett avtal förnyas eller upphör.

**Viktig produktprincip:** Sälj i första hand den egna historiken, bearbetningen, analysen, bevakningen och programvarufunktionaliteten. Distribuera rådata vidare endast när rättigheterna uttryckligen tillåter det. Denna princip minskar risk men ersätter inte licenskontrollen.
