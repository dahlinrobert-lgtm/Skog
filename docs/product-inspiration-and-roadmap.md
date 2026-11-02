# Produktinspiration – Naturkartan, Skogsmonitor och Skog

**Datum:** 2026-11-02  
**Status:** Rekommenderad produktinriktning och prioriterad backlog  
**Omfattning:** Inspiration och funktionsanalys – inte kopiering av gränssnitt, texter eller proprietära data.

## 1. Slutsats

Det finns tydliga delar att inspireras av, men Skog bör inte bli en kopia av någon av tjänsterna.

- **Naturkartan:** förebild för begriplig källredovisning, attribution och hur bearbetade data beskrivs.
- **Skogsmonitor:** förebild för att kombinera flera källor till en begriplig temakarta och för att redovisa metod, validering och osäkerhet.
- **Skog:** bör särskilja sig genom tidsdimensionen: snapshots, förändringar, historik, källspårbarhet och bevakning.

En relevant kompletterande marknadsreferens är Skogsradar, som samlar skogliga lager, fastighetsfunktioner, skogsbruksplan, historiska flygbilder och larm. Den visar att användare kan uppskatta ett sammanhållet arbetsflöde från karta till planering och bevakning. Vi bör dock prioritera Skogs egna styrkor i datainsamling och historik före att bygga en fullständig skogsbruksplan.

## 2. Vad vi bör lära av referenserna

### Naturkartan – källor som en del av produkten

Naturkartan redovisar datakällor och licenser separat och beskriver också när data bearbetas, exempelvis Lantmäteriets höjddata som används för höjder och höjdprofiler.

**Översatt till Skog:**
- Varje kartlager ska ha en informationspanel med producent, distributör, produkt, licens/villkor, attribution, uppdateringsdatum, geografisk täckning och kända begränsningar.
- Visa källangivelse direkt i kartan när det krävs, inte bara i en generell källförteckning.
- Redovisa Skogs egen bearbetning separat från källans originaluppgift.
- Exporter ska bära med sig källa, licens, snapshot och bearbetningshistorik.

### Skogsmonitor – analys med synlig osäkerhet

Skogsmonitor kombinerar fjärranalys, skogshistorik, historiska kartor, inventeringar och öppna data. Viktigt är att deras metodbeskrivning skiljer mellan fältinventerade/högt säkerställda naturvärden, troliga naturvärden och potentiell äldre skog. De redovisar även att vissa klasser kan över- eller underskattas och att precisionen varierar geografiskt.

**Översatt till Skog:**
- Skilj mellan observerat, registrerat, modellerat, beräknat och prognostiserat.
- Visa datakvalitet och säkerhetsnivå per lager eller objekt.
- Visa datum för senaste källuppdatering och eventuell eftersläpning.
- Undvik att presentera en modellklassning som ett verifierat naturvärde.
- Ge användaren tillgång till metod och källor bakom en analys.

### Skogsradar – sammanhållet arbetsflöde

Skogsradar visar hur många datakällor kan samlas i en karta och kopplas till fastigheter, skogsbruksplan, historiska flygbilder och notiser.

**Översatt till Skog:**
- Bygg mot en gemensam karta och källmodell, men börja med bevakning och förändringar – inte med att återskapa alla funktioner för skogsbruksplan.
- Gör det enkelt att gå från nationell överblick till ett objekt, en fastighet eller ett bevakningsområde.
- Låt användaren spara områden och få relevanta larm när källdata förändras.

## 3. Nuläge i Skog – funktioner som redan finns

En genomgång av `docs/karta.html`, `docs/bevakning.html` och `docs/index.html` visar att flera grundfunktioner redan är byggda:

- Planerade och registrerade utförda avverkningar.
- Samråd.
- Geokodade naturvårdsbränningar och Life2Taiga-åtgärder.
- Testlager för skogsvolym och geografiska testområden.
- Radiefilter och flera radiealternativ.
- Färgläggning efter bland annat åtgärd, år, hektar, andel, skogstyp och avverkningstyp.
- Attributfilter, identifiering och popupinformation.
- Mätfunktioner och statistik/histogram för tid mellan anmälan och utförd avverkning.
- Matchningshistorik och separat bevakningsvy.

Det betyder att vi inte behöver börja om med kartan. Nästa steg är att förbättra informationsarkitekturen, lagerhanteringen och hur data förklaras.

## 4. Prioriterad utvecklingsplan

### P0 – Gör befintliga lager begripliga och jämförbara

1. **Enhetlig lagerkatalog**
   - Gruppera lager: Avverkning, Naturvårdande åtgärder, Naturvärden, Skogliga grunddata, Skador och risker, Infrastruktur och bakgrund.
   - Varje lager ska ha kort beskrivning, källa, uppdateringsdatum och status.
   - Visa om lagret är nationellt, regionalt eller bara ett testområde.
2. **Lagerinformation och datakvalitet**
   - Skilj mellan källa, observation och Skogs analys.
   - Visa status: officiellt register, fjärranalys, modell, manuell inventering eller Skog-beräkning.
   - Visa kända luckor och osäkerheter.
3. **Attribution**
   - Visa attribution i kartan och i lagerpanelen.
   - Koppla informationen till befintligt `sources.yml` och proveniensmanifest.
4. **Tidsstämpel**
   - Visa både källans uppdateringsdatum och när Skog senast hämtade data.

### P1 – Gör tidsdimensionen till Skogs tydligaste styrka

1. **Tidsreglage / jämför snapshots**
   - Välj två datum och se vad som tillkommit, förändrats eller försvunnit.
   - Skilj på nyupptäckt, ändrad källa, sannolikt borttagen och verifierat borttagen.
2. **Förändringslager**
   - Nya avverkningsanmälningar.
   - Nya eller ändrade naturvårdsåtgärder.
   - Registrerade utförda avverkningar.
   - Nya brand- och skadedetektioner.
3. **Objektets historik**
   - Visa första och senaste observation, tidigare status, geometriändringar och källans ändringsdatum.
   - Bevara ursprungliga käll-ID:n och snapshots.
4. **Källornas aktualitet**
   - Visa uppdateringsfrekvens, senast lyckad hämtning och eventuella avbrott.

### P2 – Analys som går utöver en vanlig lagerkarta

1. **Skogliga värde- och riskindikatorer**
   - Kombinera trädhöjd, volym, markfukt, trädslag, diken, naturvärden och historiska störningar.
   - Håll varje delindikator synlig och förklarad; undvik en ogenomskinlig totalpoäng.
2. **Landskapskontext**
   - Visa kluster, konnektivitet, fragmentering och avstånd mellan värdefulla skogsområden.
   - Skilj mellan registrerade naturvärden och modellbaserad potential.
3. **Före/efter**
   - Jämför satellitbilder, ortofoton och källgeometrier före och efter en registrerad åtgärd.
   - Visa bilddatum och källa; en förändringssignal är inte automatiskt bevis på avverkning.
4. **Rapport och export**
   - Skapa rapport för ett område eller en fastighet med karta, tidslinje, källor, metod och osäkerhet.
   - Exportera GeoJSON/CSV med manifest och proveniens.

### P3 – Bevakning och användarflöden

1. Spara fastigheter, polygoner och radiebevakningar.
2. Skicka larm när relevanta källor förändras.
3. Samla händelser i en tidslinje med länkar till källobjekt.
4. Lägg senare till anteckningar och egna områden – utan att blanda ihop användarens uppgifter med myndighetsdata.

## 5. Föreslagen informationsmodell för varje kartlager

Minimikrav i lagerpanelen:

| Fält | Exempel / förklaring |
|---|---|
| Namn | Avverkningsanmälningar |
| Typ | Officiellt register |
| Producent | Skogsstyrelsen |
| Distributör | Skogsstyrelsen |
| Källa | Produkt-/API-länk |
| Licens/villkor | Exakt bedömd villkorsgrund |
| Attribution | Färdig källrad |
| Geografisk täckning | Nationell / regional / test |
| Aktualitet | Senast uppdaterad hos källan |
| Senast hämtad | Senaste lyckade Skog-snapshot |
| Metod | Originaldata / bearbetning / modell |
| Kvalitet | Verifierad / varierande / okänd |
| Begränsningar | Kända fel, bortfall och eftersläpning |

## 6. Designprinciper

- Kartan ska vara arbetsytan; lagerpanelen ska inte överväldiga kartan.
- Lager ska kunna sökas och grupperas, inte bara listas i en lång checkboxlista.
- En aktiv analys ska alltid visa vilka lager som påverkar resultatet.
- Färger och symboler ska ha konsekvent betydelse mellan kartor.
- Tidsdimensionen ska vara lätt att förstå även för användare som inte känner till datakällorna.
- Mobil vy ska stödja samma kärnflöde: hitta område, slå på lager, se objekt, förstå källa och få larm.
- Källans originaluppgift, Skogs tolkning och användarens egna anteckningar ska visuellt och tekniskt hållas isär.

## 7. Vad vi inte bör kopiera eller bygga ännu

- Bygg inte en full skogsbruksplan med avdelningsregister och åtgärdsplanering innan det finns ett tydligt användarbehov och datamodell.
- Bygg inte en sammanvägd naturvärdespoäng utan validering och tydlig metod.
- Kopiera inte andra aktörers kartskikt, klassningar eller texter; använd deras metodredovisning som inspiration och bygg egna analyser från rättighetsgranskade källor.
- Lägg inte in nya lager bara för att de finns. Varje lager ska ha ett definierat användningsfall och uppdateringsstrategi.
- Prioritera inte visuell omdesign före källspårbarhet, aktualitet och förändringshistorik.

## 8. Rekommenderat nästa genomförande

Börja med **P0.1: en enhetlig lagerkatalog för den befintliga kartan**.

Det är en begränsad förbättring som kan genomföras utan att ändra datainsamlingens kärna. Den ger samtidigt grunden för källpanel, attribution, datakvalitet och senare tidsjämförelser.

Acceptanskriterier:
- Befintliga lager grupperas i tydliga kategorier.
- Varje lager har namn, beskrivning, källa, uppdateringsstatus och geografisk täckning.
- Befintliga kontroller och kartfunktioner fortsätter fungera.
- Testlager märks tydligt som test.
- Ingen källa får en mer långtgående licensstatus än vad källregistret stödjer.

## 9. Referenser

- Naturkartan – datakällor och erkännanden: https://www.naturkartan.se/sv/data
- Skogsmonitor – om kartan, metod och datakvalitet: https://skogsmonitor.se/om-kartan/
- Skogsmonitor – kartan: https://skogsmonitor.se/kartan/
- Skogsradar – datakällor, licenser och årgångar: https://www.skogsradar.se/datakallor
- Skogsstyrelsen – nationella skogliga grunddataprodukter: https://www.skogsstyrelsen.se/en/digital-open-forest-data/national-forest-attribute-maps/

