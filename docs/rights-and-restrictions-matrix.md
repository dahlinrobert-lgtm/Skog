# Rättighets- och begränsningsmatris – Skog

**Registerdatum:** 2026-11-02  
**Status:** Första operativa versionen  
**Koppling:** Kompletterar [Öppna data och kommersiell användning](open-data-and-commercial-use.md) och `data-platform/config/sources.yml`.

> Operativt granskningsstöd, inte juridiskt utlåtande. Bedöm alltid exakt handling, datamängd, produkt, version och användning. Rätten att få ut en handling, rätten att behandla innehållet och rätten att publicera/sälja det vidare är tre olika frågor.


## 0. Överordnad tolkningsprincip – rättsordningen går före källregistrets luckor

Denna princip gäller för hela Skog, alla källor och alla senare rättighetsbedömningar.

**Frånvaro av en särskild uppgift, licenstext eller uttrycklig beskrivning i en källpost innebär inte i sig att användningen är förbjuden.** Källregistret är ett hjälpmedel för att dokumentera vad som har kontrollerats; det är inte en uttömmande förteckning över alla rättigheter och skyldigheter som följer av lag.

Om en specifik källa eller situation inte uttryckligen behandlas ska bedömningen göras utifrån den generella rättsordningen, tillämpliga rättsprinciper och relevanta rättskällor. En okänd eller tom registeruppgift är en kunskapslucka – inte automatiskt ett förbud, men inte heller ett automatiskt tillstånd.

### 0.1 Normhierarki och företräde

Följande är en förenklad orientering. EU-rätten har en särskild ställning och kan inte utan vidare placeras som ett vanligt steg i den svenska normtrappan.

1. **EU-rätt:** EU:s primärrätt och bindande sekundärrätt gäller inom EU:s befogenhetsområden. EU-rättens företräde innebär att en motstridig nationell bestämmelse i ett område som omfattas av EU-rätten kan behöva lämnas utan avseende. Bedömningen måste göras med hänsyn till EU-rättens tillämpningsområde och Sveriges konstitutionella regler om överlåtelse av beslutanderätt.
2. **Sveriges grundlagar:** regeringsformen, tryckfrihetsförordningen, yttrandefrihetsgrundlagen och successionsordningen. Vanliga lagar och lägre föreskrifter får inte strida mot grundlag.
3. **Riksdagsordningen:** har en särskild ställning mellan grundlag och vanlig lag.
4. **Lagar:** beslutade av riksdagen.
5. **Förordningar:** beslutade av regeringen med stöd av normgivningsmakten.
6. **Myndighetsföreskrifter och kommunala/regionala föreskrifter:** bindande endast inom respektive organs behörighet och bemyndigande, och får inte strida mot överordnade regler.
7. **Allmänna råd, vägledningar, handböcker, webbtexter och interna rutiner:** normalt inte bindande föreskrifter. De kan vara vägledande för tolkning och myndighetspraxis men kan inte ändra lag eller skapa ett förbud utan rättsligt stöd.

Domstolar och andra offentliga organ ska enligt regeringsformens regler om normprövning inte tillämpa föreskrifter som strider mot överordnad författning (11 kap. 14 § och 12 kap. 10 § RF).

### 0.1.1 Tolkningsprinciper när regler möts eller är tysta

Normhierarkin avgör vilken regel som har företräde vid normkonflikt. När regler på samma nivå överlappar, eller när en regel inte uttryckligen behandlar en viss detalj, behöver även vanliga juridiska tolkningsprinciper användas:

- **Lex superior:** en regel på högre normnivå har företräde framför en motstridig regel på lägre nivå.
- **Lex specialis:** en mer specialiserad regel kan ha företräde framför en mer generell regel inom det område som specialregeln faktiskt reglerar.
- **Lex posterior:** en senare regel på samma normnivå kan ha företräde framför en äldre motstridig regel, beroende på lagstiftningens utformning och övergångsregler.
- **EU-rättens företräde:** inom EU-rättens tillämpningsområde ska motstridig nationell rätt hanteras enligt principen om EU-rättens företräde.
- **Systematisk och ändamålsenlig tolkning:** bestämmelser ska läsas i sitt sammanhang, mot lagens syfte, definitioner, undantag och relevanta förarbeten/praxis – inte isolerat eller genom att anta att tystnad betyder förbud.

Dessa principer är inte en mekanisk genväg. De måste tillämpas på den konkreta normkonflikten och får inte användas för att skapa ett tillstånd som strider mot en tydlig bindande regel. Vid osäkerhet ska den faktiska frågan och den rättsliga grunden dokumenteras, inte ersättas med ett generellt antagande.

### 0.2 Avtal, licenser och metadata är inte en egen nivå i normhierarkin

Avtal och licenser är inte författningar och ska inte placeras mellan lag och förordning. De kan däremot skapa bindande rättigheter och skyldigheter mellan parter eller ge en rättighetshavare tillstånd till användning.

- Ett avtal, en API-term eller en licens kan precisera hur en tjänst får användas, men kan inte sätta tvingande lag eller grundlag ur spel.
- En metadatauppgift eller webbsida är bevisning om villkor och rättighetsanspråk, inte automatiskt en bindande norm för alla användare.
- Ett avtalsvillkor binder i första hand de parter som omfattas av avtalet och inom ramen för tillämplig rätt. Kontrollera om Skog faktiskt har accepterat villkoren och om leverantören har rätt att upplåta de aktuella rättigheterna.
- En öppen licens kan ge ett uttryckligt tillstånd som annars hade behövt inhämtas från rättighetshavaren. Den kan inte ge rätt till material som licensgivaren inte kontrollerar.

### 0.3 Hur okända eller ej omnämnda förhållanden ska bedömas

Använd följande ordning:

1. Identifiera den faktiska användningen: åtkomst, insamling, lagring, historik, bearbetning, kombination, kundvisning, export eller vidare distribution.
2. Identifiera tillämpliga generella regler, inklusive eventuella rättigheter, undantag och begränsningar.
3. Kontrollera om en särskild författning, ett giltigt avtal eller en licens faktiskt ändrar eller preciserar utgångspunkten.
4. Kontrollera om den som åberopar en begränsning har rättsligt stöd för den och om begränsningen omfattar just Skogs användning.
5. Om en källa inte nämner en viss användning: dra inte slutsatsen att den är förbjuden enbart av tystnaden. Bedöm den mot den generella lagen.
6. Om avgörande fakta saknas – exempelvis vem som äger ett kartlager, vilka villkor som accepterats eller om en personuppgift förekommer – dokumentera just den osäkerheten och avgränsa den berörda användningen. Stoppa inte automatiskt andra, separerbara delar av datat eller produkten.
7. Välj den minst ingripande åtgärd som hanterar den konkreta rättsliga risken: exempelvis visa metadata men inte bilagan, använd geometri men inte bakgrundskartan, aggregera personuppgifter eller länka till originalet.

### 0.4 Okänt är inte samma sak som förbjudet – och inte samma sak som godkänt

| Registerläge | Betydelse | Rätt arbetssätt |
|---|---|---|
| Inte omnämnt i källans villkor | Villkoren är tysta om just användningen | Pröva mot generell lag och avtalets faktiska omfattning; anta inte automatiskt förbud |
| Okänt / inte verifierat | Underlaget räcker inte för slutsats | Identifiera vilken konkret omständighet som saknas; begränsa endast den berörda delen om möjligt |
| Uttryckligt förbud | Giltigt och tillämpligt förbud har identifierats | Följ förbudet, om det inte strider mot överordnad rätt eller saknar tillämplighet |
| Uttryckligt tillstånd/licens | Rättighetshavaren har gett tillstånd inom angivet omfång | Använd inom licensens räckvidd och följ kvarvarande lagkrav |
| Lagstadgad rätt eller skyldighet | Rätten/skyldigheten följer direkt av tillämplig författning | Tillämpa lagen även om källans webbsida eller register inte nämner den |

### 0.5 Praktisk konsekvens för statusfärgerna

- **Gul betyder utredningsbehov, inte automatiskt förbud.** Den ska ange vilken konkret fråga som är olöst.
- En gul status ska inte blockera en annan användning som kan skiljas från den olösta delen och som har stöd i generell lag eller separat licens.
- **Röd** ska reserveras för en identifierad rättslig eller avtalsmässig spärr, eller ett nödvändigt tillstånd som faktiskt saknas.
- **Grön** betyder att den granskade användningen har tillräckligt stöd; den är inte ett generellt godkännande för alla framtida användningar.
- Ett publiceringsstopp ska vara avgränsat till berörd uppgift, lager, fil, användningsform eller kundfunktion. Använd inte ett generellt stopp när risken kan isoleras.

### 0.6 Rättskällor och tolkningsstöd

- [Regeringsformen (1974:152)](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/svensk-forfattningssamling/regeringsform-1974152_sfs-1974-152/) – särskilt 8 kap. om normgivning samt 11 kap. 14 § och 12 kap. 10 § om normprövning.
- [Boverket – Regelhierarki](https://www.boverket.se/sv/lag--ratt/boverkets-forfattningar/processen-for-boverkets-regelskrivning/) – grundlag, lag, förordning och myndighetsföreskrifter.
- [Regeringen – Grundlagarna](https://www.regeringen.se/sa-styrs-sverige/grundlagar-och-demokratiskt-deltagande/grundlagarna/) – grundlagarnas ställning och EU.
- [EUR-Lex – EU:s normhierarki](https://eur-lex.europa.eu/legal-content/SV/TXT/?uri=LEGISSUM%3Anorms_hierarchy) – primärrätt och sekundärrätt.
- [SOU 2023:75 – normhierarki och normprövning](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/statens-offentliga-utredningar/starkt-konstitutionell-beredskap_hbb375/html/).

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

Varje källa i `data-platform/config/sources.yml` har nu ett separat block `compliance`. Fälten är en konservativ första screening och ska förfinas mot exakt dataset, handling, lager och avsedd användning:

- `secrecy_review`: sekretessprövning på handling-/uppgiftsnivå.
- `personal_data_review`: kontroll av personuppgifter och risk vid länkning/kombination.
- `gdpr_lawful_basis`: rättslig grund krävs om personuppgifter behandlas.
- `map_and_geodata_rights`: kontroll av produkt/lager, bakgrundskartor och underliggande data.
- `research_material_status`: kontroll om materialet är forskningsdata, publikation eller annan forskningsprodukt.
- `third_party_rights`: kontroll av producentkedja, bilagor och inbäddat material.
- `publication_gate`: stoppar extern publicering när relevant granskning är olöst.
- `assessment_scope`: åtkomst, lagring, härledningar, kundvisning och vidare distribution bedöms separat.
- `evidence_reference`, `reviewed_on`, `next_review`: spårbar dokumentation och ajourhållning.

Dessa fält är inte en juridisk garanti eller ett automatiskt godkännande. Standardvärdena är avsiktligt försiktiga och ska ersättas/kompletteras med källspecifika slutsatser när underlag finns.
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

## 8. Källspecifika fördjupningar

Följande rapporter innehåller mer detaljerade bedömningar för enskilda källor. De kompletterar matrisen och ska läsas tillsammans med respektive källpost i `data-platform/config/sources.yml`.

- [Länsstyrelsernas diarier och Kungjort/Premex – rättighetsgranskning 2026-11-02](source-rights-reviews/2026-11-02-lansstyrelsen-kungjort.md)
- [Länsstyrelsernas geodatatjänster, Vindbrukskollen och Naturvårdsregistret – rättighetsgranskning 2026-11-02](source-rights-reviews/2026-11-02-geodata-lansstyrelsen-vindbrukskollen-naturvardsverket.md)

**Viktig status:** Vindbrukskollens verifierade CC0-datamängd är skild från bakgrundskartorna. Länsstyrelsernas WMS-villkor ska tillämpas per datamängd enligt metadata. Naturvårdsregistrets centrala tjänstepost anger okända användningsvillkor; kommersiell publicering ska därför vänta tills exakt lagerlicens är verifierad.
