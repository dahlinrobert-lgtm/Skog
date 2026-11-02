# Rättighets- och begränsningsmatris – Skog

**Registerdatum:** 2026-11-02  
**Status:** Första operativa versionen  
**Koppling:** Kompletterar [Öppna data och kommersiell användning](open-data-and-commercial-use.md) och `data-platform/config/sources.yml`.

> Operativt granskningsstöd, inte juridiskt utlåtande. Bedöm alltid exakt handling, datamängd, produkt, version och användning. Rätten att få ut en handling, rätten att behandla innehållet och rätten att publicera/sälja det vidare är tre olika frågor.

## 1. Översiktlig matris

| Datatyp | Rättslig utgångspunkt | Kommersiell användning |
|---|---|---|
| Sekretessbelagda uppgifter | Tryckfrihetsförordningen 2 kap. och offentlighets- och sekretesslagen (2009:400). Sekretess gäller uppgifter och kan innebära att delar av en handling maskeras. | **Nej** för sekretessbelagda uppgifter. Begär maskerad version. Lagra eller publicera inte sekretessbelagda uppgifter i Skog. |
| Personuppgifter | GDPR (EU) 2016/679, dataskyddslagen (2018:218), eventuell registerförfattning. Kräver ändamål, rättslig grund, uppgiftsminimering, lagringsminimering och säkerhet. | **Villkorad.** Offentlighet är inte i sig rättslig grund för kommersiell behandling. Minimera, pseudonymisera eller aggregera. Dokumentera rättslig grund innan behandling/publicering. |
| Känsliga personuppgifter och uppgifter om lagöverträdelser | GDPR artiklarna 9–10 och kompletterande svensk lagstiftning; OSL kan också vara tillämplig. | **Stopp som huvudregel.** Kräver särskilt rättsligt stöd och särskild bedömning. Undvik att härleda sådana uppgifter genom att kombinera öppna datakällor. |
| Myndighetsproducerade kartor/geodata | Upphovsrättslagen (1960:729), särskilt 1, 9, 26 a och 49 §§, samt licens- och produktvillkor. Kartor och databaser kan ha eget skydd; 26 a § har undantag för vissa verk, däribland kartor. | **Per produkt/lager.** CC0/CC BY eller uttryckligt villkor kan medge kommersiell användning. Offentlig handling eller myndighetsägande räcker inte ensamt. |
| Tredjepartskartor, ortofoton och geometrier | Upphovsrättslagen, licens/avtal och lagen (2022:818) 1 kap. 10 § 2 om tredje mans upphovsrätt. | **Inte automatiskt tillåtet.** Kräver rättighet som täcker kommersiell användning, historik, bearbetning och kundvisning. WMS-åtkomst är inte återanvändningslicens. |
| Forskningsdata | Lag (2022:818), särskilt 1 kap. 4 och 6 §§ samt 4 kap. 3 §; GDPR, etikprövningsregler, avtal och immateriella rättigheter kan också gälla. | **Villkorad.** Forskningsdata i lagens mening ska tillgängliggöras avgiftsfritt, men det gör inte alla forskningsresultat, rapporter, kartor eller filer fria att återpublicera. |
| Forskningspublikationer, rapporter och figurer | Upphovsrättslagen och avtal med förlag, forskare, lärosäte och finansiär. Undantagen i 9 och 26 a §§ är ingen generell fri licens för forskningsverk. | **Normalt inte fri återpublicering.** Länka eller citera inom lagens ramar. Återpublicera inte rapporter, figurer eller kartor utan licens/tillstånd. |
| Myndighetsbeslut och myndighetsuttalanden | Upphovsrättslagen 9 §; TF/OSL styr åtkomst och sekretess. Bilagor kan ha annan rättighetsstatus. | **Ofta möjligt** att återge beslutstext efter kontroll av sekretess och personuppgifter. Granska kartor, foton, yttranden och bilagor separat. |
| Protokoll, diarietexter och OCR-/API-utdrag | TF/OSL, GDPR, upphovsrättslagen 9 och 26 a §§ där tillämpliga, API-/avtalsvillkor och tredjepartsrättigheter. | **Per dokument och avtalskedja.** Skilj original, OCR-text, leverantörsmetadata och bilagor. Avtala om historik, kundvisning, utdrag, export och distribution. |
| Databaser och registeruttag | Upphovsrättslagen 49 § om katalog-/databasskydd, GDPR, OSL och registerförfattningar. | **Villkorad.** Enskilda fakta kan vara fria, men databasen kan ha katalogskydd. Kontrollera systematisk extraktion och återanvändning av väsentliga delar. |
| Avtal, remissvar och material från företag/privatpersoner | Avtalsrätt, upphovsrätt, lagen (2018:558) om företagshemligheter, OSL och GDPR. | **Per handling.** Myndighetens innehav upphäver inte automatiskt tredje mans rättigheter. Var särskilt försiktig med affärshemligheter, konsultkartor och tekniska bilagor. |

## 2. Fördjupade kontrollregler

### Sekretess
- Sekretesspröva på uppgiftsnivå. En handling kan lämnas ut med maskering.
- Hämta inte in eller lagra uppgifter som myndigheten bedömt omfattas av sekretess.
- Använd endast maskerad version när sådan lämnats ut.
- Dokumentera myndighetens beslut och vilken version som hämtats.
- Stoppa publicering om kombination av datakällor skapar ny sekretess- eller skyddsrisk.

### Personuppgifter
- GDPR gäller även uppgifter från offentliga handlingar och öppna API:er.
- Dokumentera ändamål och rättslig grund enligt artikel 6; bedöm särskilt artiklarna 9 och 10.
- Utforma insamlingen så att personnamn, privata kontaktuppgifter och irrelevant fritext inte hämtas.
- Använd organisationsnamn, ärende-ID, geografiska objekt och aggregerade mått när det räcker.
- Pseudonymisering är inte anonymisering. Bedöm om DPIA krävs vid omfattande/systematisk behandling.
- Lägg inte personuppgifter i publika GitHub-filer, loggar eller kundmiljöer utan dokumenterad grund och skydd.

### Kartor och geodata
- Kontrollera licens per produkt och lager, inte bara per WMS/ArcGIS-tjänst.
- Separera geometrier från bakgrundskartor, ortofoton, symboler och kartbilder.
- Spara producent, licens, metadata-URL, lager-ID, version och attribution.
- Bedöm kommersiell användning, historik, bearbetning, kundvisning och vidare distribution separat.
- Publicera inte skärmbilder från karttjänster som om de vore öppna geodata.
- Kontrollera underliggande data även när en härledd modellprodukt har egen licens.

### Forskningsmaterial
- Klassificera material som forskningsdata, publikation, kartprodukt, programvara eller annan produkt.
- Statliga universitet/högskolor tillämpar lagen (2022:818) endast i fråga om forskningsdata enligt 1 kap. 6 §.
- Avgiftsfri tillgång enligt 4 kap. 3 § är inte en generell upphovsrättslicens.
- Begär skriftligt besked om kommersiell användning, historisk arkivering, bearbetning och kunddistribution när villkoren är oklara.
- Särskilj forskningsresultatet från underliggande data och tredjepartsunderlag.

### Tredje mans rättigheter
- Identifiera dataägare/producent och eventuell API-/tjänsteleverantör separat.
- Kontrollera konsultrapporter, inventeringar, foton, kartor, remissvar och bilagor.
- API-avtal ger inte automatiskt rätt att återpublicera originalhandlingar.
- Spara dokument-ID och källhänvisning även när innehållet inte får återpubliceras.
- Begär skriftligt tillstånd när kommersiell kundvisning eller vidare distribution inte uttryckligen omfattas.

## 3. Tillämpning på prioriterade Skog-källor

| Källa/datamängd | Datatyp | Rättslig utgångspunkt | Kommersiell användning |
|---|---|---|---|
| Länsstyrelsernas diarier och beslut | Diarieposter, beslut, protokoll, bilagor | TF/OSL, GDPR, upphovsrätt 9/26 a §§ och tredje mans rättigheter | **Per handling.** Beslutstext kan ofta återanvändas efter kontroll; personuppgifter, sekretess och bilagor granskas separat. |
| Kommunala protokoll via Kungjort | Original, OCR-text, metadata, API-data | TF/OSL, GDPR, upphovsrätt, avtal och tredjepartsrättigheter | **Gul tills avtal och dokumentflöde är klarlagda.** Avtala om historik, OCR-text, kundvisning, utdrag, export och bilagor. |
| Länsstyrelsernas WMS/FeatureServer | Geometrier, attribut, kartbilder | Upphovsrätt, katalogskydd, licens per lager, OSL/GDPR vid behov | **Per lager.** WMS-åtkomst räcker inte; kontrollera metadata och skilj geodata från bakgrundskarta. |
| Vindbrukskollen | Projektgeometrier och attribut | CC0 där exakt lagermetadata anger det; kartkomponenter separat | **Villkorad grön för verifierade CC0-lager.** Inte automatiskt bakgrundskartor eller tredjepartsinnehåll. |
| SLU Torvkarta | Modellraster och produktmetadata | SLU:s skriftliga besked och rättigheter i underlagsdata | **Villkorad grön enligt skriftligt besked** med föreskriven attribution. Återpublicera inte Lantmäteriets rådata på samma grund. |
| Skogsstyrelsens geodata | Raster, vektorlager, produktbeskrivningar | CC0 om inget annat anges; produktbeskrivning och undantag | **Grön/villkorad grön per produkt.** Kontrollera licenssektion och tredjepartsunderlag. |
| Lantmäteriet Fastighetsindelning Direkt | Fastighetsgeometrier och fastighetsanknutna data | Produktspecifika villkor, GDPR och registerförfattningar | **Gul.** Avgiftsfri åtkomst innebär inte obegränsad kommersiell användning. Kräv produktvillkor och besked om kundvisning/härledda produkter. |
| Naturvårdsverket och SGU | Miljö- och geologiska geodata | Licens/metadata per produkt; CC0 där det uttryckligen gäller | **Grön/villkorad per dataset.** Kontrollera producent och tredjepartsinslag. |
| Life2Taiga och projektlager | Projektgeometrier och åtgärdsdata | Projektavtal, producentens rättigheter och eventuell myndighetslicens | **Gul tills rättighetsägare bekräftat.** Begär skriftligt besked för historik, analys och kunddistribution. |
| Sveaskog, SCA och privata aktörer | Företagsdata, kartor och inventeringar | Avtal, upphovsrätt, företagshemligheter | **Röd utan skriftligt tillstånd.** |

## 4. Obligatoriska fält i källregistret

Bedöm följande separat i `data-platform/config/sources.yml` eller i dataset-/handlingsregistret:

- `access_basis`: offentlig handling, öppna data, licens, avtal eller annan grund.
- `secrecy_review`: not_applicable / checked / redacted / unresolved.
- `personal_data`: none_known / incidental / systematic / sensitive_or_criminal / unresolved.
- `gdpr_lawful_basis`: rättslig grund och dokumentationsreferens, eller not_applicable.
- `third_party_rights`: none_identified / licensed / permission_required / unresolved.
- `map_rights`: not_applicable / explicit_open_licence / authority_created_reviewed / third_party_or_unknown.
- `research_data_status`: not_research_data / research_data_under_2022_818 / research_publication / unresolved.
- `commercial_use`, `historical_storage`, `derivatives`, `customer_display`, `redistribution`: bedöms var för sig.
- `evidence_reference`, `reviewed_on`, `next_review_due`, `review_owner`.

Ett enda grönt/rött licensfält får inte ersätta dessa bedömningar. En källa kan vara fri att läsa och analysera men inte fri att återpublicera.

## 5. Kontrollflöde före kundpublicering

1. Identifiera exakt dataset, dokument, lager eller API-fält.
2. Kontrollera sekretess och eventuell maskering.
3. Identifiera personuppgifter och dokumentera rättslig grund, ändamål och minimering.
4. Kontrollera upphovsrätt, kartskydd, databasskydd, tredje mans rättigheter och avtal.
5. Bedöm lagring, historik, bearbetning, kundvisning och vidare distribution var för sig.
6. Registrera bevisunderlag, datum, status och nästa kontroll.
7. Publicera först när samtliga relevanta kontroller har godkänt utfall.

**Stoppregel:** Om sekretess, personuppgiftsgrund, kartlicens eller tredje mans rättigheter är oklara ska rådata och dokument inte publiceras externt. Även intern testning måste ha laglig grund och följa sekretess och tjänstevillkor.

## 6. Ajourhållning

- Granska vid ny datakälla, nytt lager, ny dokumenttyp eller ändrad användning.
- Kontrollera licens och villkor minst årligen samt vid ändrade metadata, API eller avtal.
- Gör ny bedömning när användningen går från intern analys till kundvisning eller vidare distribution.
- Spara tidigare bedömningar och villkorsversioner; skriv inte över historiken.
- Koppla varje ändring till ärende/commit och uppdatera både denna matris och källposten.

## 7. Rättskällor

- [Tryckfrihetsförordningen (1949:105), 2 kap.](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/tryckfrihetsforordning-1949105_sfs-1949-105/)
- [Offentlighets- och sekretesslag (2009:400)](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/offentlighets--och-sekretesslag-2009400_sfs-2009-400/)
- [Lag (2022:818) om den offentliga sektorns tillgängliggörande av data](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-2022818-om-den-offentliga-sektorns_sfs-2022-818/)
- [Upphovsrättslag (1960:729)](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/lag-1960729-om-upphovsratt-till-litterara_sfs-1960-729/)
- [Dataskyddsförordningen (EU) 2016/679 – GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [Dataskyddslag (2018:218)](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/dataskyddslag-2018218_sfs-2018-218/)
- [Swedish National Data Service – public access and secrecy in research](https://snd.se/en/research-data-support/introduction-legal-aspects-research/public-access-and-secrecy)

**Förvaltningsnotering 2026-11-02:** Första versionen av kontrollmatrisen. Komplettera med källspecifika beslut, licenser och skriftliga besked.