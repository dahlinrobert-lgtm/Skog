# Source review – naturvårdande skötsel

Senast granskad: 2026-11-01

## Syfte och klassificeringsgräns

Skogsstyrelsen beskriver naturvårdande skötsel som åtgärder i naturskog eller kulturpräglad skog som bevarar eller gynnar biologisk mångfald. Exempel är friställning av grova lövträd, naturvårdsbränning, småbränder, borttagning av gran eller främmande trädslag, buskröjning, återställning av hydrologi, skogsbete, hamling, lövängsskötsel, myrslåtter, skapande av luckor samt skapande av död ved.

Detta är åtgärder med ett dokumenterat naturvårdssyfte. Vi ska inte blanda in produktionsinriktad röjning/gallring, viltvård som enbart gynnar jaktbart vilt eller vanlig skogsproduktion. Klassificeringen ska baseras på källans beskrivning och sammanhang, inte enbart på ord som "röjning" eller "gallring".

## Källor och bedömning

### 1. Life2Taiga – första fungerande historikspåret

- Källa: Länsstyrelsernas publika FeatureServer, \`WP_2_Restoration_measures\` (lager 13).
- Status: insamling och baslinje publicerade i \`data/lifetaiga-naturvardsatgarder/\`.
- Första livekontroll 2026-11-01: 338 objekt, 337 med polygongeometri och ett attributobjekt utan geometri.
- Kategorier: kontrollerad bränning, brandefterliknande åtgärder och skogsstängsling.
- Begränsning: Life2Taiga är ett projektregister och täcker inte all naturvårdande skötsel i Sverige. Attributen ger inte i sig en säker planerad/genomförd-status.

### 2. Skötseldos / VIC Natur – relevant men inte en tillförlitlig nationell totalsanning

Skötseldos har hanterat planerade och genomförda åtgärder i skyddade områden och kopplat åtgärder till skötselområden. Det gör systemet mycket relevant för exempelvis bete, slåtter, röjning med naturvårdssyfte och restaureringsåtgärder.

Riksrevisionens granskning 2024 visar dock tydliga täcknings- och kvalitetsproblem:

- 10 av 21 länsstyrelser uppgav att de rapporterade in alla genomförda åtgärder.
- 9 rapporterade en del men inte allt och 2 rapporterade inte alls.
- Skötseldos planerades att avvecklas under 2026 och ersättas av nya system; i rapporten var ersättningen ännu inte beslutad.
- Naturvårdsverkets senare återrapportering beskriver att arbete med nästa generations IT-stöd pågår och att uppgifterna fortsatt är osäkra och svåra att jämföra mellan län och år.

**Beslut:** bygg inte en beroendeintegration mot Skötseldos utan att först verifiera dagens ersättningssystem, åtkomst, exportmöjligheter och datamodell. Behandla äldre Skötseldos-data som ojämn historisk rapportering, inte som ett komplett nationellt register.

### 3. Länsstyrelsernas Geodatakatalog – nästa huvudsakliga sökspår

Länsstyrelsernas Geodatakatalog innehåller metadata om både gemensamma och länsspecifika datamängder. REST- och WMS-länkar förekommer. Nästa inventering ska söka per län och efter åtgärdsteman:

- naturvårdsbränning och brandefterliknande åtgärder
- bete, slåtter, hamling och restaurering av ängs- och betesmarker
- restaurering av skogliga livsmiljöer och Natura 2000
- restaurering av vattendrag och våtmarker (hålls åtskilt från återvätningsavtalslagret)
- invasiva arter och naturvårdande röjning
- skapande av död ved, veteranisering och friställning av gamla träd

Varje träff ska få en källpost med ansvarig organisation, tjänste-URL, geometri, fält, täckning, aktualitet, licens och tydlig statussemantik. WMS-only är inte tillräckligt för händelsearkivering; prioritera REST/OGC API eller nedladdningsbar vektordata.

### 4. Skogsstyrelsens öppna geodata – skydd och avtal, inte automatiskt utförda åtgärder

Skogsstyrelsen tillhandahåller bland annat biotopskydd, naturvårdsavtal, nyckelbiotoper och objekt med naturvärden. Dessa är värdefulla för kontext och för att tolka varför ett område kan omfattas av naturvård, men de är inte i sig bevis på att en fysisk skötselåtgärd har utförts.

Naturvårdsavtal kan innehålla villkor om naturvårdande skötsel, men avtalsgeometri och avtalsvillkor ska hållas skilda från registrerade händelser som visar vad som faktiskt gjorts.

## Föreslagen ordning för nästa källarbete

1. Inventera Geodatakatalogens REST-/nedladdningsbara datamängder med ovanstående sökord och sammanställ täckning per län.
2. Undersök status för ersättaren till Skötseldos hos Naturvårdsverket och om en maskinläsbar export kan erhållas.
3. Lägg till källspecifika arkiverare först när objektidentitet, geometri, datum och planerad/genomförd-semantik är verifierade.
4. Behåll en gemensam händelsemodell men låt varje källa behålla sina råattribut och ursprungliga statusvärden.

## Referenser

- Skogsstyrelsen: Naturvårdande skötsel – https://skogstyrelsen.se/bruka-skog/naturvard/
- Länsstyrelsernas Geodatakatalog – https://gis.lansstyrelsen.se/geodata/geodatakatalogen/
- Riksrevisionen, RiR 2024:11, Förvaltningen av skyddad natur – https://www.riksrevisionen.se/granskningar/granskningsrapporter/2024/forvaltningen-av-skyddad-natur.html
- Skogsstyrelsen: Ladda ner geodata – https://www.skogsstyrelsen.se/e-tjanster-och-kartor/karttjanster/geodatatjanster/ladda-ner-geodata/
- Naturvårdsverket: Återrapportering av medelsanvändning och resultat för skydd av och åtgärder för värdefull natur 2023–2025 – https://www.naturvardsverket.se/49904a/globalassets/media/publikationer-pdf/7200/978-91-620-7201-8.pdf
