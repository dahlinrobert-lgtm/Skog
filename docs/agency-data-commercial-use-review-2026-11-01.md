# Naturvårdsverket, SGU och kommersiell praxis – 2026-11-01

## Syfte
Fördjupad granskning av konkreta datamängder från Naturvårdsverket och SGU som kan vara relevanta för Skog, samt exempel på hur andra digitala tjänster redovisar licenser och källor. Operativ rättighetskontroll, inte juridiskt utlåtande.

## 1. Naturvårdsverket – verifierade produkter

Naturvårdsverket anger att öppna data får användas fritt och att källa gärna ska anges. Om informationsansvaret ligger hos en annan organisation, exempelvis länsstyrelse, kommun eller vattenvårdsförbund, tillkommer den organisationens upphovsrätt. Kontrollera därför producent och informationsansvarig per produkt.

Källa: https://www.naturvardsverket.se/verktyg-och-tjanster/data-databaser-och-sokregister/tillgangliggorande-av-oppna-data/

### Nationella Marktäckedata NMD2023
- Produktbeskrivning för NMD2023 tilläggsskikt anger uttryckligen CC0 1.0.
- Data får användas, återanvändas, distribueras och aggregeras.
- Rekommenderad källangivelse: ”NMD2023, Naturvårdsverket”.
- Naturvårdsverket anger användning hos offentliga och privata aktörer, bland annat för skoglig planering, biologisk mångfald och riskkartering.
- Produktionen/kompletteringen av NMD2023 fortsätter under 2026; dokumentera exakt version och täckning.

Källor:
- https://www.naturvardsverket.se/verktyg-och-tjanster/kartor-och-karttjanster/nationella-marktackedata
- https://geodata.naturvardsverket.se/nedladdning/marktacke/NMD2023/Tillaggsskikt/NMD2023_Produktbeskrivning_till%C3%A4ggsskikt_Markanvandning.pdf

Bedömning: **Grön för den produktversion som uttryckligen omfattas av CC0**, med rekommenderad attribution och versionsspårning.

### Våtmarksinventeringen VMI
- Geodatakatalogens metadata för ”Våtmarksinventeringen VMI: vektoriserade objekt 2021-” anger CC0 1.0.
- Metadata beskriver successiv digitalisering och vektorisering av äldre inventeringsunderlag. Täckning och aktualitet kan därför skilja mellan län.
- Historiskt inventeringsunderlag; beskriv det inte som en fullständig eller helt aktuell våtmarkskartering utan kontroll av version och täckning.

Källor:
- https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=cea7ad91-0b2c-4534-8f45-80e92ad4cc9d_C
- https://geodata.naturvardsverket.se/nedladdning/VMI/

Bedömning: **Villkorad grön** för den metadataregistrerade datamängden. Kontrollera länsvisa leveranser och aktuell metadata.

### Naturtypskartan NNK och Naturvårdsregistret
En extern digital tjänst, ekokrati, redovisar NNK som CC0 med hänvisning till produktbeskrivningen §3.1 och Naturvårdsregistret som CC0 enligt nationell dataportal. Tjänsten anger även hur källan anges i enskilda datapaket. Detta är en användbar sekundär kontroll, men Skog ska spara och kontrollera den officiella produktbeskrivningen/metadata för den version vi hämtar.

Källor:
- https://app.ekokrati.se/docs/data-sources
- https://www.naturvardsverket.se/verktyg-och-tjanster/data-databaser-och-sokregister/tillgangliggorande-av-oppna-data/

Bedömning: **Villkorad grön** tills exakt officiell metadata och produktversion har sparats.

## 2. SGU – verifierade produkter

SGU anger att alla geologiska data som myndigheten tillhandahåller sedan 9 juni 2024 är öppna data under CC0. Detta gäller geologiska dataprodukter – inte automatiskt bilder, illustrationer, logotyper eller allt webbplatsmaterial.

Källa: https://www.sgu.se/produkter-och-tjanster/geologiska-data/om-geologiska-data/licensvillkor/

Följande produktbeskrivningar anger uttryckligen CC0 1.0:

| Produkt | Innehåll / möjlig relevans för Skog | Produktvillkor |
|---|---|---|
| Jordarter 1:25 000–1:100 000 | Jordart och markegenskaper; underlag för markgenomsläpplighet, erosionskänslighet och naturvärdesanalys | CC0 1.0 |
| Jordarter 1:1 miljon | Grov nationell jordartsöversikt | CC0 1.0; avsedd för översikt, använd försiktigt i analys |
| Jorddjupsmodell | Översiktligt jorddjup; relevant för hydrologi och mark-/grundvattenanalys | CC0 1.0 |
| Grundvattenförekomster | Avgränsade grundvattenförekomster i vattenförvaltningen | CC0 1.0 |
| Stränders jordart och eroderbarhet | Jordart och eroderbarhet längs stränder | CC0 1.0 |
| Vattenkvalitetsdata per grundvattenförekomst | Sammanställda vattenkvalitetsvärden | CC0 1.0 |

Produktbeskrivningar:
- Jordarter 1:25 000–1:100 000: https://resource.sgu.se/dokument/produkter/jordarter-25-100000-beskrivning.pdf
- Jordarter 1:1 miljon: https://resource.sgu.se/dokument/produkter/jordarter-1miljon-beskrivning.pdf
- Jorddjupsmodell: https://resource.sgu.se/dokument/produkter/jorddjupsmodell-beskrivning.pdf
- Grundvattenförekomster: https://resource.sgu.se/dokument/produkter/grundvattenforekomster-beskrivning.pdf
- Stränders jordart och eroderbarhet: https://resource.sgu.se/dokument/produkter/stranders-jordart-eroderbarhet-beskrivning.pdf
- Vattenkvalitetsdata: https://resource.sgu.se/dokument/produkter/oppnadata/vattenkvalitetsdata-per-grundvattenforekomst-oppnadata-beskrivning.pdf

Bedömning: **Grön för de uttryckligen CC0-märkta produkterna**. Spara produktbeskrivning, version, datum och teknisk åtkomstinformation. För äldre observationsdata eller data som SGU endast är datavärd för, kontrollera separat om annan finansiär/ägare har rättigheter eller om CC0-villkoren uttryckligen omfattar datamängden.

## 3. Hur andra digitala tjänster redovisar myndighetsdata

Vi hittade två relevanta publika exempel. De är förebilder för transparens, men deras egna bedömningar är inte bindande licensbesked för Skog.

### MapAndMove – datakällor och licenser
https://mapandmove.se/datakallor

Tjänsten redovisar kartlager var för sig och namnger källmyndigheter och produkter. Exempel:
- SGU: berggrund, jordarter, brunnar och jorddjup.
- Naturvårdsverket och Länsstyrelserna: skyddad natur, Natura 2000, vattenskydd, riksintressen och strandskydd.
- Skogsstyrelsen: naturvärden, avverkningsanmälningar, skogliga grunddata, markfuktighet och brandområden.
- Egna bearbetningar: bland annat modellerade svamp-/bärindex och andra härledda analyser.
- Blandade licenser: CC0, CC BY och andra villkor redovisas separat. Tjänsten noterar även när licens är oklar eller när åtkomstvillkor inte är verifierade.

Lärdom: varje lager har identifierbar källa; egna modeller skiljs från observationer och myndighetsdata. Fastighetsgränser redovisas exempelvis separat som Lantmäteriets CC BY 4.0.

### ekokrati – data sources
https://app.ekokrati.se/docs/data-sources

Tjänsten har ett centralt datakälleregister med datakälla/produkt, licens och villkorslänk, status för kommersiell användning, om attribution krävs eller rekommenderas samt exakt källtext. Registret används även för att generera en attribution-fil (ATTRIBUTION.md) i varje datapaket. Användaren kan därmed se vilka källor som ligger bakom en viss analys.

## 4. Rekommenderad modell för Skog

1. **Internt källregister:** exakta dataset, producent, licens, produktversion, URL, kontrolldatum och begränsningar.
2. **Kundnära källförteckning:** kort källangivelse i kartlager/info-panel och en samlad sida ”Datakällor och licenser”.
3. **Analysproveniens:** varje härlett index/analys dokumenterar dataset och version, beräkningsdatum och modellversion.
4. **Nedladdningsbara analysresultat:** inkludera källförteckning/attribution i metadata eller medföljande fil när relevant.
5. **Licensstatus per lager:** märk ”kommersiell användning verifierad” först när exakt produktvillkor har sparats. Annars håll status villkorad/oklar och blockera extern publicering vid behov.

Föreslagen källtext:
- ”Källa: Naturvårdsverket – NMD2023, version [version].”
- ”Källa: SGU – Jordarter 1:25 000–1:100 000, produktversion [version].”
- ”Källa: Länsstyrelserna – [datamängd], [län/producent], licens enligt metadata.”

## 5. Nästa steg – Länsstyrelserna

Nästa granskning görs dataset för dataset i Länsstyrelsernas geodatakatalog. Börja med lager som redan används eller är relevanta i Skog: Life2Taiga, Vindbrukskollen, åtgärder i vatten, våtmarksinventering/grön infrastruktur, skyddade områden samt EBH-stödet/förorenade områden.

Katalogen anger att licensen finns i metadata för varje datamängd. GIS-policyn anger CC0 som normal utgångspunkt vid extern publicering om inget annat skäl finns, men enskilda dataset kan ha CC BY, tredjepartsrättigheter eller åtkomstvillkor. Metadata för Vindbrukskollen anger CC0, men har även kvalitetsreservationer: uppgiftslämnare ansvarar för sina uppgifter och användaren uppmanas att kontrollera informationen innan åtgärder vidtas.

Källor:
- https://gis.lansstyrelsen.se/geodata/geodatakatalogen/
- https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=c816bd1e-bc6c-487f-a962-770f05f677b6_C
- https://www.energimyndigheten.se/energisystem-och-analys/el--och-varmeproduktion/vindkraft/vindbrukskollen/
