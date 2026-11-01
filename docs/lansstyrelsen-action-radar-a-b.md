# Länsstyrelsen – åtgärdsradar för fysiska åtgärder och vattenverksamhet

**Avgränsning:** första sök- och klassificeringsversionen omfattar endast:
- **A – planerade fysiska åtgärder:** väg, ledningsdragning, schaktning, grävning, utfyllnad, massupplag, anläggningsarbete och liknande.
- **B – vattenverksamhet/hydrologi:** markavvattning, dikning, dikesrensning, trummor, kulvertar, broar över vattendrag, vattenområdesschaktning, våtmarksanläggning och vattendragsrestaurering.

Artskydd, naturreservatsdispenser, vindkraft, naturvårdsbränning och andra ärendetyper ingår inte i denna första version.

## 1. Juridisk avgränsning

### A. 12 kap. 6 § miljöbalken

En verksamhet eller åtgärd som kan komma att väsentligt ändra naturmiljön ska anmälas för samråd om den inte redan omfattas av tillstånds- eller anmälningsplikt enligt andra bestämmelser i miljöbalken. Tillsynsmyndighet kan vara Länsstyrelsen, Skogsstyrelsen eller Försvarsinspektören. Naturvårdsverkets vägledning nämner bland annat grävning, utfyllnad, avverkning/avbaning och uppförande av byggnader eller anläggningar.

Länsstyrelsens e-tjänst nämner bland annat större schaktning, vägar, anläggningar, upplag av massor, ledningsdragning, rennäringsanläggningar, vindkraft, prospektering och husbehovstäkter.

**Viktig avgränsning:** skogsbruksåtgärder som dikesrensning och anläggande av skogsbilväg kan i stället vara samrådsärenden hos Skogsstyrelsen. Vårt Länsstyrelsediarium ska därför inte betraktas som komplett register över skogsbrukets 12:6-samråd.

### B. 11 kap. miljöbalken – vattenverksamhet

Länsstyrelsen Västerbotten anger som exempel på anmälningspliktig mindre vattenverksamhet:
- anläggning av våtmark under 5 hektar,
- vissa fyllningar, grävningar, schaktningar och muddringar i vattenområde,
- bro eller trumma i mindre vattendrag,
- omgrävning av vattendrag under angivna förutsättningar,
- vissa vattenuttag,
- kabel, rör eller ledning i vattenområde.

Anmälan enligt 11 kap. 9 a § är inte samma sak som 12:6-samråd. En anmäld vattenverksamhet kan leda till försiktighetsmått, förbud eller krav på ansökan om tillstånd. Markavvattning har dessutom särskilda regler och ska inte klassas som vanlig dikesrensning.

Källor:
- Naturvårdsverket, samråd vid ändring av naturmiljön: https://www.naturvardsverket.se/vagledning-och-stod/samhallsplanering/samrad-vid-andring-av-naturmiljon/
- Länsstyrelsens e-tjänst för 12:6-samråd: https://www.lansstyrelsen.se/e-portal/sok-e-tjanster/anmal-samrad-for-atgarder-som-kan-paverka-naturmiljon.html
- Länsstyrelsen Västerbotten, vattenverksamheter som behöver anmälas: https://www.lansstyrelsen.se/vasterbotten/miljo-och-vatten/atgarder-och-verksamheter-i-vatten/vattenverksamhet/vattenverksamheter-som-behover-anmalas.html
- Havs- och vattenmyndigheten, anmälan om vattenverksamhet: https://www.havochvatten.se/arbete-i-vatten-utslapp-till-vatten-och-energiproduktion/vattenverksamhet-och-utslapp-till-vatten/anmalan-om-vattenverksamhet.html
- Skogsstyrelsen, skogliga åtgärder som kräver samråd: https://skogsvardsstyrelsen.se/lag-och-tillsyn/miljobalken-i-skogen/skogliga-atgarder-som-kraver-samrad/

## 2. Vad vi hittills har i diariet

Den befintliga sparade diariebasen innehåller 125 ärenden. Alla 125 har sökts fram med sökfrasen `naturvårdsbränning`. Detaljinsamlingen omfattar 50 ärenden. En kontroll av rubriker och handlingstitlar i dessa data gav endast ett svagt närliggande fynd till A/B – ett ärende om byggnation av spång inför naturvårdsbränning. Det är inte ett representativt urval för A/B och kan inte användas för att dra slutsatser om hur vanliga sådana ärenden är.

Slutsats: vi har redan tekniken för diarier och handlingshistorik, men vi har ännu inte gjort den riktade sökningen för väg, ledning, markarbete och vattenverksamhet. Sökningen måste breddas innan vi kan bedöma täckning och träffkvalitet.

## 3. Föreslagna sökfraser

Sökfraser finns i `config/lansstyrelsen-action-search-terms.yml`. Sökningen ska göras som separata frassökningar eftersom diariet söker i ärenderubriker och en bred boolesk sökning inte kan förutsättas.

Rekommenderade första testfraser:
- skogsbilväg
- vägbyggnad
- ledningsdragning
- schaktning
- utfyllnad
- massupplag
- vattenverksamhet
- markavvattning
- dikesrensning
- trumma
- våtmarksanläggning
- omgrävning av vattendrag

Arbetsflödet tillåter högst tio fraser per körning. Kör därför i två batchar och börja med Norrbotten och Västerbotten, därefter nationellt om träffkvaliteten är god.

## 4. Klassificering och bevisnivå

`scripts/classify_lansstyrelsen_action_leads.py` klassificerar ärenderubriker och handlingstitlar i två oberoende kategorier. Ett ärende kan tillhöra både A och B, exempelvis en skogsbilväg med en trumma över ett vattendrag.

Klassificeringen sparar:
- kategori och åtgärdstyp,
- vilken ärenderubrik eller handlingstitel som gav träff,
- datum för handlingen,
- administrativa processteg som anmälan, komplettering, yttrande, beslut, förbud och uppföljning,
- diarienummer och länk till ursprungsärendet.

Den hävdar inte att ett beslut är ett tillstånd eller att en åtgärd har utförts. Rubrik- och handlingstitlar är endast metadata. För starkare bedömning måste själva handlingen eller bilagan granskas.

Kör:
```bash
python scripts/classify_lansstyrelsen_action_leads.py
python -m unittest tests.test_lansstyrelsen_action_leads
```

## 5. Nästa datainsamlingssteg

1. Kör separata sökbatchar för A och B i Norrbotten och Västerbotten.
2. Jämför ärendeträffar med de faktiska handlingslistorna.
3. Identifiera ärenden där handlingstitlar visar kartbilaga, situationsplan, arbetsplan, ritning, komplettering, beslut eller kontrollrapport.
4. Prova att hämta dokument/metadata för ett begränsat urval innan större insamling.
5. Utvärdera om diariet har tillräcklig geografisk information eller om bilagor behöver hämtas och georefereras.

Ingen ny återkommande insamling eller automatiserad publicering av A/B-ärenden startas innan testbatcharna har validerats.
