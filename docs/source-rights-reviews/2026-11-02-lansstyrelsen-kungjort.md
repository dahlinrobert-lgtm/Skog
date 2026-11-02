# Källspecifik rättighetsgranskning – Länsstyrelsen och Kungjort

**Granskningsdatum:** 2026-11-02  
**Status:** Preliminär rättslig screening – inte juridiskt utlåtande eller publiceringsgodkännande  
**Omfattning:** Länsstyrelsernas diarier/ärendehandlingar samt Kungjort/Premex kommunala protokoll- och beslutsdokument-API.

## Sammanfattning

| Källa | Intern teknisk insamling | Historisk lagring | Härledning/analys | Kundvisning/vidaredistribution | Status |
|---|---|---|---|---|---|
| Länsstyrelsernas diarier | Endast efter kontroll av åtkomst, sekretess, dataskydd och tjänstevillkor | Villkorad per post/handling och ändamål | Villkorad; minimera personuppgifter och håll isär dokumenttyper | Endast efter kontroll per handling och innehåll | **Gul – record-by-record** |
| Kungjort/Premex API | Pilot först efter API-villkor och personuppgifts-/sekretesskontroll | Kräver uttryckligt avtalsbesked om historik och retention | Kräver rätt att bearbeta OCR/text och metadata | Kräver uttryckligt avtalsbesked samt rättigheter till original/bilagor | **Gul – avtal krävs** |

Ingen av källorna ska markeras som generellt godkänd för kommersiell återpublicering. Ett offentligt originaldokument, ett API-uttag, OCR-text och bilagor kan ha olika rättsliga och avtalsmässiga förutsättningar.

## 1. Länsstyrelsernas offentliga diarier och ärendehandlingar

### Vad som kan användas som utgångspunkt

- En diarieförd handling kan vara en allmän handling om den förvaras hos myndigheten och är inkommen eller upprättad. Offentlighet gäller med förbehåll för sekretess.
- Sekretessprövningen kan gälla enskilda uppgifter eller delar av en handling. Ett utlämnande med maskering är inte ett godkännande av att samla in en tidigare omaskerad version.
- Myndighetsbeslut och myndighetsuttalanden omfattas av upphovsrättslagens särskilda regel i 9 §, men den regeln gör inte automatiskt bilagor eller inbäddat material fria.
- Kartor, fotografier, konsultunderlag, tekniska rapporter och andra tredjepartsbilagor ska bedömas separat. Databas-/katalogskydd och GDPR kan också vara relevanta.
- Rätten att begära ut en handling är inte samma sak som en generell rätt att massinsamla och publicera diariedata eller handlingstext i en kommersiell tjänst.

### Rekommenderad behandling i Skog

1. Lagra i första hand minimerad ärendemetadata: myndighet, diarienummer/ärende-ID, datum, ärendetyp, status, geografisk referens när den är relevant, käll-URL och hämtningstid.
2. Behandla personnamn, privata kontaktuppgifter och fritext som personuppgifter tills motsatsen är utredd. Undvik att ta in dem i den sökbara kundprodukten om de inte behövs.
3. Hämta endast handlingar från en åtkomstväg där åtkomst och villkor är klarlagda. Bevara maskeringar och dokumentera vilken version som erhölls.
4. Klassificera varje dokumenttyp separat: myndighetsbeslut, myndighetsyttrande, inkommet remissvar, konsultutredning, karta, foto och övrig bilaga.
5. Publicera inte hela handlingar eller bilagor automatiskt. Visa hellre metadata, korta sakliga sammanfattningar och länk till originalet när återpubliceringsrätten är oklar.
6. Spara ett granskningsspår för varje dokument som går vidare till kundvisning: rättighetsbedömning, sekretess-/personuppgiftskontroll, källa, dokument-ID och beslutad publiceringsnivå.

### Stoppunkter

- Ingen insamling eller publicering av uppgifter som omfattas av sekretess.
- Ingen kundvisning av personuppgifter utan dokumenterat ändamål och rättslig grund samt bedömning av nödvändighet och proportionalitet.
- Ingen återpublicering av kartor, fotografier eller tredje mans bilagor utan licens eller annan rättslig grund.
- Ingen generell slutsats om att alla länsstyrelser eller alla län har samma diarietjänst, fält, täckning eller villkor.

## 2. Kungjort/Premex – kommunala protokoll och beslutsdokument

### Rättighetslager som måste hållas isär

1. **Kommunens originalhandling:** offentlighet och sekretess enligt TF/OSL; upphovsrättslig bedömning av text och bilagor.
2. **Kungjorts API och metadata:** avtalsvillkor, API-begränsningar, kostnader, stabila ID:n, retention och tillåten användning.
3. **OCR-/extraherad text:** rätt att lagra, bearbeta, indexera, sammanfatta, visa utdrag ur och distribuera texten.
4. **Bilagor:** kartor, bilder, konsultmaterial och inkomna handlingar kan ha separata rättighetsägare och licenser.
5. **Härledda produkter:** sökindex, klassificering, geografisk matchning, trendmått och AI-sammanfattningar behöver bedömas utifrån både källrättigheter, personuppgifter och avtalsvillkor.

Att originalprotokollet är offentligt innebär inte automatiskt att API-leverantörens uttag, OCR-produkt eller hela dokumentpaket får kopieras till en kommersiell tjänst. På motsvarande sätt kan ett API-avtal inte ge större rätt till tredjepartsmaterial än vad leverantören själv har.

### Punkter som ska bekräftas skriftligt före pilot

- Om kommersiell användning är tillåten för metadata, OCR-text, fulltext och dokumentfiler.
- Om historisk lagring och arkivering av dagliga snapshots är tillåten, inklusive retention efter avslutat avtal.
- Om texten får normaliseras, OCR-korrigeras, indexeras, klassificeras, sammanfattas och användas för härledda analyser.
- Om kundvisning av fulltext, utdrag, sökresultat, sammanfattningar och export är tillåten.
- Om original-PDF:er och bilagor får lagras, visas, cachas eller endast länkas.
- Om rättigheterna gäller både API-leverantörens material och underliggande kommunala dokument, och hur tredje mans material hanteras.
- Pris, anropsgränser, bulkuttag, paginering, daglig inkrementell synkronisering, stabila dokument-ID:n och ändrings-/raderingssignaler.
- Attribution, källhänvisning, ansvar för felaktig OCR och hantering av rättelser eller borttagna dokument.
- Om avtalet tillåter att Skog behåller redan insamlade metadata och härledda mått efter avtalets upphörande.

### Rekommenderad pilotdesign

- Börja med metadata och källänkar för de fem diskuterade kommunerna: Luleå, Umeå, Skellefteå, Örnsköldsvik och Sundsvall.
- Separera rå API-respons, originaldokument, OCR-text och Skogs egna härledningar i lagring och datamodell.
- Använd stabila dokument-ID:n och diarienummer som separata fält; anta inte att de är samma identifierare.
- Aktivera inte fulltextindexering, kundvisning eller export innan avtalet uttryckligen omfattar respektive användning.
- Behåll käll-URL och hämtningstid, och bygg stöd för rättelser, borttagna dokument och ändrade bilagor.

## 3. Gemensam publiceringsmodell

| Nivå | Innehåll | Standardbeslut |
|---|---|---|
| A – metadata | Källa, datum, diarienummer, dokumenttyp, status, URL | Villkorad efter sekretess- och personuppgiftskontroll |
| B – kort beskrivning | Myndighetens rubrik eller egen neutral sammanfattning | Villkorad; minimera personuppgifter och kontrollera avtalet |
| C – utdrag/OCR | Citat, textutdrag eller maskinextraherad fulltext | Blockerad tills rättigheter och personuppgiftsfrågor är klarlagda |
| D – original/bilaga | PDF, karta, foto, konsultunderlag | Blockerad tills rättighet till lagring och kundvisning är klarlagd |
| E – härledd analys | Klassificering, geografisk koppling, trend och aggregering | Separat bedömning av källvillkor, personuppgifter och risk för återidentifiering |

## 4. Rättsliga utgångspunkter och källor

- [Tryckfrihetsförordningen (1949:105), 2 kap.](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/tryckfrihetsforordning-1949105_sfs-1949-105/)
- [Offentlighets- och sekretesslag (2009:400)](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/offentlighets--och-sekretesslag-2009400_sfs-2009-400/)
- [Lag (2022:818) om den offentliga sektorns tillgängliggörande av data](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2022818-om-den-offentliga-sektorns_sfs-2022-818/)
- [Upphovsrättslag (1960:729)](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-1960729-om-upphovsratt-till-litterara_sfs-1960-729/)
- [IMY – Vidareutnyttjande av handlingar](https://www.imy.se/om-oss/vart-uppdrag/vidareutnyttjande-av-data/)
- [Swedish National Data Service – Public access and secrecy](https://snd.se/en/research-data-support/introduction-legal-aspects-research/public-access-and-secrecy)
- [Swedish National Data Service – Copyright and database protection](https://snd.se/en/research-data-support/introduction-legal-aspects-research/research-principal/copyright)
- [Kungjort API-specifikation](https://handlingar.kungjort.se/openapi.yaml)

## 5. Slutsats och nästa granskningssteg

Länsstyrelsedata kan inte ges ett generellt grönt klartecken; fortsätt med metadata-först och dokumentvis klassificering. Kungjort ska förbli avtalsberoende och pilotens fulltext-/dokumentfunktioner ska vara avstängda tills skriftliga villkor finns.

Nästa steg är att kontrollera faktiska API-villkor och exempelposter, identifiera vilka fält som innehåller personuppgifter eller tredje parts material samt dokumentera skriftliga svar från respektive leverantör/myndighet. Denna screening ska inte tolkas som ett rättsligt godkännande.
