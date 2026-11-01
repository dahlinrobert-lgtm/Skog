# Länsstyrelsernas geodata – kommersiell användning och praxis

**Kontrolldatum:** 2026-11-01  
**Omfattning:** Vindbrukskollen, Åtgärder i vatten, Life2Taiga, grön infrastruktur och EBH.

## 1. Viktig huvudregel

Länsstyrelsernas Geodatakatalog anger att licenstypen finns i metadata för varje datamängd. En generell GIS-policy om CC0 är en normal utgångspunkt för externt publicerad länsstyrelseproducerad geodata, men den ersätter inte kontroll av den enskilda datamängdens metadata, producent och eventuella tredjepartsrättigheter.

Källor:
- https://gis.lansstyrelsen.se/geodata/geodatakatalogen/
- https://ext-dokument.lansstyrelsen.se/Gemensamt/GDK/Manual/Lansstyrelserna_Geodatakatalog_manual_intern.pdf

## 2. Granskade datakällor

| Datakälla | Licens/status | Viktig begränsning |
|---|---|---|
| Vindbrukskollen – landbaserade vindkraftverk och projekteringsområden | CC0 1.0 enligt metadata | Datakvalitet varierar; uppgiftslämnare ansvarar för uppgifterna. Bakgrundskartor har separata upphovsrättsvillkor. |
| Åtgärder i vatten | Länsstyrelsen anger fri kopiering, bearbetning och distribution med källangivelse | Gemensamt system med HaV; kontrollera exakt API/produkt och åtgärdsstatus. |
| Life2Taiga – naturvårdsåtgärder | Licens inte verifierad för vårt externa FeatureServer-lager | Projektpartners och värd för tjänsten är inte automatiskt rättighetsinnehavare. |
| EBH – externt lager över potentiellt förorenade områden | CC BY 4.0 för externt publicerat lager | Begränsat urval, inte fullständig inventering; interna EBH-stödet är inte öppet för allmänheten. |
| Grön infrastruktur – småvatten värdekärnor, Västra Götaland | CC0 1.0 enligt datasetmetadata | Regionalt lager; inte nationell täckning. |
| Grön infrastruktur – barrskog värdetrakter, Västerbotten | CC BY 4.0 enligt datasetmetadata | Regionalt planeringsunderlag, inte formellt skydd. Attribution krävs. |

### Vindbrukskollen

Metadata för landbaserade projekteringsområden anger CC0 1.0, nationell täckning och kontinuerlig uppdatering. WMS-tjänsten uppdateras dagligen och ATOM-flödet tillhandahåller Shape/GeoPackage. Metadata anger att informationen uppdateras av användare, förvaltning och projektörer och att Länsstyrelserna inte ansvarar för att uppgifterna är korrekta.

Viktigt: Energimyndighetens sida anger att bakgrundskartorna i Vindbrukskollen är upphovsrättsskyddade och endast får nyttjas i tillståndsprocessen; annan användning kräver särskilt tillstånd. Skog ska därför hämta och använda själva CC0-datamängden, inte återpublicera kartbilder eller bakgrundskartor.

Källor:
- Metadata: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=c816bd1e-bc6c-487f-a962-770f05f677b6_C
- Energimyndigheten: https://www.energimyndigheten.se/energisystem-och-analys/el--och-varmeproduktion/vindkraft/vindbrukskollen/

### Åtgärder i vatten

Länsstyrelsens öppna data-sida anger att data från Åtgärder i vatten får kopieras, bearbetas och distribueras gratis med Länsstyrelsen som källa. Systemet är gemensamt med Havs- och vattenmyndigheten och samlar restaureringsåtgärder i vatten, bland annat biotopvård, fiskvägar, återintroduktioner och utrivning av vandringshinder. Allmänheten kan söka utan inloggning; registrering/redigering kräver behörighet.

För Skog är detta relevant som en nationell åtgärdskälla, men lagra källans statusfält och skilj mellan planerad, pågående, färdigställd och status saknas. En registrerad åtgärd är inte automatiskt en oberoende verifierad effekt.

Källor:
- Öppna data: https://www.lansstyrelsen.se/stockholm/om-oss/vara-tjanster/oppna-data.html
- Databas: https://atgarderivatten.lansstyrelsen.se/Atgarder/Hitta
- Information: https://www.atgarderivatten.se/
- FAQ: https://www.atgarderivatten.se/faq/

### Life2Taiga

Projektet är ett EU LIFE-samarbete med 17 länsstyrelser, Naturvårdsverket och finska Metsähallitus, koordinerat av Länsstyrelsen i Västmanlands län. Projektinformationen visar naturvårdsbränningar som genomförts och planeras. Den bekräftar dock inte i sig en återanvändningslicens för vårt specifika externa FeatureServer-lager.

Status kvarstår **gul**. Vi behöver fråga projektkoordinatorn eller identifierad dataägare om licens för just lagret och om den omfattar kommersiell användning, historisk lagring, bearbetning och kundvisning.

Källa:
- https://www.lansstyrelsen.se/uppsala/natur-och-landsbygd/skyddad-natur/skotsel-av-skyddad-natur/life2taiga.html

### EBH – potentiellt förorenade områden

Det externa EBH-lagret har CC BY 4.0 enligt Länsstyrelsernas dokumentation. Detta är en viktig skillnad från interna EBH-stödet, som endast är tillgängligt för länsstyrelserna och Naturvårdsverket.

Det externa lagret:
- exkluderar objekt som inte har kommunicerats och vissa avförda objekt,
- visar antal fastigheter i stället för fastighetsbeteckningar,
- är inte en heltäckande bild av landets förorenade områden,
- innehåller koordinater som kan vara uppskattade eller osäkra.

Det får användas kommersiellt med attribution enligt CC BY 4.0, men vi bör beskriva det som ett urval av potentiellt/konstaterat förorenade objekt, inte som fullständig sanerings- eller föroreningsstatus för en fastighet.

Källor:
- Metadata: https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/srv/api/records/1f7fca9c-4a72-4d72-b2fd-f4fb9c4e44c9
- Licensöversikt i Länsstyrelsedokument: https://www.lansstyrelsen.se/download/18.1b1d393819324610c374a9f7/1732520045019/Klimatp%25C3%25A5verkan%2520p%25C3%25A5%2520f%25C3%25B6rorenade%2520omr%25C3%25A5den%2520och%2520milj%25C3%25B6farlig%2520verksamhet.pdf
- Förklaring av attribut: https://ext-dokument.lansstyrelsen.se/Gemensamt/Geodata/Externa%20dokument/EBH/2024-06-12%20F%C3%B6rklaring%20LST%20Potentiellt%20f%C3%B6rorenade%20omr%C3%A5den%20externt.pdf

### Grön infrastruktur

Metadata visar varför vi inte får anta en enda licens för alla Länsstyrelsedata:
- Småvatten värdekärnor i Västra Götaland anges som CC0 1.0.
- Barrskog värdetrakter i Västerbotten anges som CC BY 4.0.

Det senare lagret beskriver landskapsavsnitt med högre täthet av biologiska värden och är ett planeringsunderlag, inte en formell skyddsform. För kundvisning och analyser krävs attribution enligt CC BY 4.0.

Källor:
- Småvatten: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=b58be26d-ab66-4dd3-9894-fe2b8eb9fdf1_C
- Barrskog Västerbotten: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=5e0d327e-d888-4946-bf5a-30e87036679b_C

## 3. Hur kommersiella tjänster redovisar användningen

Två konkreta exempel visar hur vi kan utforma Skogs transparens:

### MapAndMove
https://mapandmove.se/datakallor

MapAndMove redovisar datakällor lager för lager och skiljer mellan CC0, CC BY, oklara villkor och egna analyser. De visar källan nära varje mått och förklarar hur rådata hämtas, kontrolleras, bearbetas och uppdateras. De skriver också uttryckligen när en siffra är en egen beräkning och inte en myndighetsuppgift.

### Elflödet
https://xn--elfldet-d1a.se/data-och-kallor

Elflödet redovisar för varje källa vad den används till, hur ofta den hämtas och vilken licens som gäller. För Vindbrukskollen anger tjänsten CC0 och förklarar att källan ändå anges för spårbarhet. Den beskriver även tekniska detaljer som ATOM-flöde, GeoPackage, koordinattransformation och kända dataluckor.

### Slutsats för Skog

Vi bör bygga samma transparens, men med skoglig proveniens:
- källa och datasetversion,
- licens och attribution,
- hämtningstidpunkt,
- om geometri/attribut är original eller bearbetade,
- status/konfidens och kända databegränsningar,
- vilken egen beräkning som lagts ovanpå myndighetsdata.

En enkel licenssida räcker inte ensam. Källinformationen bör följa med varje lager och varje nedladdningsbar rapport/analys.

## 4. Nästa kontroller

1. Kontakta Life2Taiga-koordinatorn och be om villkor för just FeatureServer-lagret.
2. Kontrollera exakt API-licens och schema för Åtgärder i vatten innan automatiserad bulkinsamling.
3. Kontrollera övriga Vindbrukskollen-delar separat, särskilt havsbaserade projekt och bakgrundskartor.
4. Sök fler regionala grön-infrastruktur-dataset med relevans för Norrbotten/Västerbotten; kontrollera CC0/CC BY per post.
5. Håll EBH till det externa CC BY-lagret; begär inte eller använd inte interna EBH-uppgifter utan separat behörighet/avtal.

## 5. Fördjupning: Life2Taiga – kontakt och rättighetsfråga

Den officiella projektsidan anger att Life2Taiga koordineras av Länsstyrelsen i Västmanlands län. Den publicerade kontaktvägen till projektledningen är **life2taiga@lansstyrelsen.se** (växel 010-224 90 00). Projektet omfattar 17 länsstyrelser, Naturvårdsverket och Metsähallitus; den publika kartan visar både genomförda och planerade naturvårdsbränningar.

Detta identifierar en relevant mottagare, men innebär inte att frågan redan är ställd eller att rättigheter är beviljade. För vårt externa lager:

`https://ext-hostedgeodata.lansstyrelsen.se/arcgis/rest/services/Hosted/Life2Taiga_v3_Extern/FeatureServer/13`

bör projektledningen bekräfta vem som äger/förvaltar datat och vilken licens som gäller för just detta FeatureServer-lager. Begär uttryckligt besked om:
- kommersiell användning i en abonnemangstjänst,
- regelbunden hämtning och permanent historisk lagring/snapshots,
- bearbetning, geometriunioner och egna härledda analyser,
- visning av originaldata och bearbetade data för kunder,
- nedladdning/export och vidare distribution,
- krav på attribution, versionsangivelse och eventuella begränsningar i API-användning.

**Registerstatus:** gul – kontaktväg identifierad, men skriftligt besked saknas. Ingen kommersiell insamling eller vidarepublicering ska startas innan svaret har dokumenterats.

Källor:
- https://www.lansstyrelsen.se/vastmanland/natur-och-landsbygd/skyddad-natur/skotsel-av-skyddad-natur/naturvardsbranning/life2taiga/life2taiga-english.html
- https://www.lansstyrelsen.se/uppsala/natur-och-landsbygd/skyddad-natur/skotsel-av-skyddad-natur/life2taiga.html

## 6. Regional inventering: Norrbotten och Västerbotten

### Västerbotten – Värdefulla naturområden (extern WMS/REST)

Länsstyrelsens publika information beskriver ett samlat underlag med främst skogsområden men även värdefulla våtmarker, vattendrag, fjäll- och havsmiljöer. Underlaget bygger på inventeringar över längre tid och anges uttryckligen inte vara heltäckande.

Geodatakatalogens tjänstepost:
- Titel: `LstAC Natur Intressant Naturomr (extern) – Karttjänst`
- UUID: `32f86036-487e-4362-883b-8bd1ba8d9c3d`
- Ansvarig: Länsstyrelsen Västerbotten / Miljöanalysenheten
- Tjänster: WMS och ArcGIS REST
- Metadata anger att åtkomstrestriktioner ska kontrolleras i posterna för de ingående lagren.

Det är därför **inte** korrekt att tilldela hela karttjänsten en enda licens utifrån att den är publik. Nästa kontroll är att öppna varje ingående lagers metadatapost och kontrollera licens, producent och eventuell tredje parts data. Tills dess gul status.

Källor:
- https://www.lansstyrelsen.se/vasterbotten/natur-och-landsbygd/skyddad-natur/bevara-naturvarden-och-fa-ersattning.html
- https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/srv/api/records/GetMetaDataById?id=32f86036-487e-4362-883b-8bd1ba8d9c3d

### Västerbotten – skogliga värdetrakter i västra länsdelen

I januari 2026 publicerade Länsstyrelsen att nya preciserade skogliga värdetrakter och nätverk tagits fram väster om E45, kompletterande tidigare material för länets östra delar. Områdena omfattar skog både ovan och nedan gränsen för fjällnära skog.

Detta är relevant för skoglig landskapsanalys, men är ett kunskapsunderlag för planering – inte en skyddsform. Dessutom måste vi kontrollera metadata för just den nya västliga produkten. Den tidigare posten för barrskog värdetrakter med CC BY 4.0 får inte automatiskt anses täcka det nya datasetet.

Källa:
- https://www.lansstyrelsen.se/vasterbotten/om-oss/nyheter-och-press/nyheter---vasterbotten/2026-01-12-skogliga-vardetrakter-i-vasterbottens-vastra-delar-i-lansstyrelsens-karttjanst.html

### Norrbotten – våtmarksanalys inom grön infrastruktur

Länsstyrelsen Norrbotten beskriver en våtmarksanalys som underlag för att avgränsa värdetrakter. Analysen bygger på kända värdekärnor från våtmarksinventeringen och rikkärrsinventeringen, täthetsanalys och manuell bearbetning utifrån aktuell kunskap.

Geodatakatalogen pekas ut som platsen där metadata och dataset finns. Sök särskilt efter:
- `GI Andelsanalys alla våtmarker`
- `GI andelsanalys värdefulla våtmarker`

Detta är en intressant kandidat för skoglig mark- och landskapskontext. Licensen måste dock kontrolleras i den exakta metadataposten; den regionala informationssidan anger inte återanvändningslicensen.

Källa:
- https://www.lansstyrelsen.se/norrbotten/samhalle/planera-bygga-och-bo/gron-infrastruktur/kartor-och-underlag-for-planeringsarbete-med-gron-infrastruktur.html

### Samlad bedömning

| Dataset/kandidat | Relevans för Skog | Rättighetsläge | Rekommendation |
|---|---|---|---|
| Life2Taiga FeatureServer | Mycket hög – planerade/genomförda naturvårdsbränningar | Okänd | Begär skriftligt besked från projektledningen |
| Västerbotten Värdefulla naturområden | Hög – skog, våtmark, vatten och fjäll | Licens måste kontrolleras per ingående lager | Hämta inte för kommersiell vidarepublicering ännu |
| Västerbotten skogliga värdetrakter väst | Hög – landskapskontext för skog | Ny produkt, metadata/licens ej verifierad | Identifiera exakt metadatapost |
| Norrbotten GI våtmarksanalys | Medel/hög – våtmarkernas landskapsmönster | Exakt katalogpost och licens återstår | Identifiera post och kontrollera villkor |

Viktigt: att en datamängd är gratis att visa eller ladda ned är inte i sig ett besked om kommersiell vidareanvändning. För varje kandidat måste vi kontrollera licens, rättighetsinnehavare, åtkomstvillkor och eventuella tredjepartsinslag separat.
