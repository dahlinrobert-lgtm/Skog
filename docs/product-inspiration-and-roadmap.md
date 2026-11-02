# Produktinspiration – Naturkartan, Skogsmonitor och Skog

**Datum:** 2026-11-02  
**Status:** Rekommenderad produktinriktning och prioriterad backlog  
**Omfattning:** Inspiration och funktionsanalys – inte kopiering av gränssnitt, texter eller proprietära data.

## 1. Produktpositionering – flödet är produkten, kartan är stödet

**Skog ska primärt vara en bevaknings- och underrättelsetjänst för skogsägare, inte en karttjänst.** Kundlöftet är att användaren ska kunna följa vad som händer i och omkring sin skog och få relevanta aviseringar utan att själv behöva bevaka myndighetsregister, karttjänster och satellitdata.

Det primära användarflödet är:
1. Användaren anger eller väljer fastighet/bevakningsområde och vilka händelser som är viktiga.
2. Skog hämtar och följer relevanta källor kontinuerligt.
3. Skog upptäcker nya, ändrade och potentiellt försvunna uppgifter.
4. Skog verifierar, matchar och berikar händelsen med andra källor.
5. Skog presenterar en begriplig händelse i ett samlat aktivitetsflöde.
6. Användaren får en avisering när händelsen passerar definierade relevans- och kvalitetsregler.
7. Kartan öppnas vid behov för geografisk kontext, inte som huvudsaklig destination.

**Unik konkurrensfördel (USP):** kontinuerlig datainsamling + historik + korsmatchning mellan källor + relevansbedömning + aviseringar. En karta kan många bygga; ett tillförlitligt och historiskt bevakningsflöde kräver en betydligt starkare data- och händelseinfrastruktur.

Referenserna ska därför användas selektivt:
- **Naturkartan:** förebild för begriplig källredovisning och attribution.
- **Skogsmonitor:** förebild för analys, datakombination och transparent osäkerhet – inte för att göra kartan till huvudprodukten.
- **Skog:** ska särskilja sig genom bevakningsflödet, historiken och aviseringarna.

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

## 4. Prioriterad utvecklingsplan – styr efter kundvärde i bevakningsflödet

### P0 – Tillförlitlig händelsemotor och relevanta aviseringar

1. **Händelsemodell**
   - Normalisera händelser från olika källor till gemensamma typer, statusar, tidsstämplar och geografiska objekt.
   - Behåll käll-ID, källstatus, första/senaste observation och snapshotreferenser.
   - Skilj mellan nyupptäckt, ändrad, inte längre returnerad och verifierat borttagen.
2. **Matchning mot bevakningsområden**
   - Koppla händelser till användarens fastigheter, polygoner och bevakningsradier.
   - Redovisa varför en händelse matchade: överlappning, avstånd, fastighetskoppling eller annan regel.
   - Visa osäker matchning som osäker; påstå inte fastighetsträff utan verifierad fastighetsgeometri.
3. **Kvalitet och deduplicering**
   - Slå ihop dubbletter från samma händelse/källa utan att förlora källreferenser.
   - Korsmatcha oberoende källor när det stärker eller motsäger en händelse.
   - Bevara originaluppgifter och skilj dem från Skogs slutsats.
4. **Aktivitetsflöde som primär startsida**
   - Sortera på relevant händelsetid, inte enbart hämtningstid.
   - Visa vad som hänt, var, när, varför användaren får informationen och hur säker uppgiften är.
   - Ge en kort sammanfattning och tydliga nästa steg/länkar till källunderlag.
5. **Aviseringsmotor**
   - Stöd e-post och push som kanaler.
   - Styr aviseringar på händelsetyp, område, allvar/relevans och kvalitetsnivå.
   - Undvik spam: gruppera relaterade händelser, deduplicera och ge användaren kontroll över frekvens.
   - Logga leverans, återförsök och varför en avisering skickades eller undertrycktes.
6. **Datakällornas driftsäkerhet**
   - Visa senast lyckad hämtning, täckning, fel och eftersläpning.
   - Skilj på att ingen ny händelse hittades och att källan inte kunde kontrolleras.

### P1 – Gör historik och förändring användbar i flödet

1. **Objektets historik**
   - Visa första/senaste observation, statusförändringar, geometriändringar och källans datum.
   - Bevara ursprungliga käll-ID:n och snapshots.
2. **Tidslinje och jämförelse**
   - Visa vad som tillkommit, ändrats eller försvunnit mellan två snapshots.
   - Skilj på nyupptäckt, ändrad källa, sannolikt borttagen och verifierat borttagen.
3. **Korsmatchade händelsekedjor**
   - Exempel: avverkningsanmälan → samråd/dispens → satellitförändring → registrerad utförd avverkning.
   - Visa länkar mellan händelser utan att göra korrelation till bevis för orsak eller genomförande.
4. **Sparade bevakningar**
   - Låt användaren följa fastigheter, polygoner och radier med egna händelsefilter.

### P2 – Analys som gör bevakningen mer värdefull

1. **Skogliga värde- och riskindikatorer** – använd flera delindikatorer och visa metod/osäkerhet; undvik ogenomskinlig totalpoäng.
2. **Landskapskontext** – konnektivitet, fragmentering och avstånd mellan värdefulla områden.
3. **Före/efter** – jämför satellitbilder, ortofoton och källgeometrier; förändringssignal är inte automatiskt bevis på avverkning.
4. **Rapport och export** – sammanställ händelser, källor, metod och osäkerhet för ett område eller en fastighet.

### P3 – Kartan som stödjande arbetsyta

1. Behåll kartan för geografisk kontext och snabb lokalisering av en händelse.
2. Gruppera befintliga lager och gör källinformation lätt att hitta.
3. Låt kartan följa vald händelse och aktuellt bevakningsfilter.
4. Lägg till avancerad lagerkatalog, tidsreglage och analysverktyg först när de förbättrar ett konkret bevakningsflöde.
5. Prioritera inte kartfunktioner som inte förbättrar upptäckt, förståelse eller uppföljning av en händelse.

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

Börja inte med en större kartombyggnad. Börja med **P0.1: händelse- och aviseringarnas kvalitet i det befintliga bevakningsflödet**.

Första genomförandet bör kartlägga varje händelsetyp från källa till användare: upptäckt → normalisering → matchning mot område → deduplicering/kvalitetskontroll → aktivitetsflöde → avisering. Identifiera vilka steg som redan finns och vilka som saknas. Därefter väljer vi en konkret händelsetyp och gör hela kedjan robust innan vi breddar.

Acceptanskriterier:
- Varje flödeshändelse kan spåras till ett källobjekt och en snapshot.
- Det går att förklara varför den matchade en bevakning.
- Ny, ändrad och saknad uppgift hålls isär.
- Dubbletter undertrycks utan att källspårbarhet går förlorad.
- Avisering skickas endast när en definierad relevansregel uppfylls.
- Misslyckad källhämtning visas som ett kontrollfel, inte som att inget har hänt.
- Kartan öppnas som geografisk förklaring till händelsen och är inte ett krav för att förstå flödet.

## 9. Referenser

- Naturkartan – datakällor och erkännanden: https://www.naturkartan.se/sv/data
- Skogsmonitor – om kartan, metod och datakvalitet: https://skogsmonitor.se/om-kartan/
- Skogsmonitor – kartan: https://skogsmonitor.se/kartan/
- Skogsradar – datakällor, licenser och årgångar: https://www.skogsradar.se/datakallor
- Skogsstyrelsen – nationella skogliga grunddataprodukter: https://www.skogsstyrelsen.se/en/digital-open-forest-data/national-forest-attribute-maps/

