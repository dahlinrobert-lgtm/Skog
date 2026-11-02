# Branschpraxis – källredovisning och öppen data

Granskningsdatum: 2026-11-02.

Detta dokument samlar exempel på hur tjänster redovisar myndighetsdata, kartunderlag och licenser. Branschpraxis är jämförelsematerial för produktdesign, inte rättsligt prejudikat eller bevis för att en annan aktörs användning är korrekt.

## Exempel

- [MapAndMove – Data sources and licences](https://mapandmove.se/en/datakallor): redovisar källor, licensfamiljerna CC0, CC BY 4.0 och ODbL samt skiljer mellan ursprungsdata och egna analyser.
- [Naturkartan – Data sources and attribution](https://www.naturkartan.se/nb/data): redovisar flera dataleverantörer och licensinformation på en samlad sida.
- [OnCoord – Usage Guidelines and Attribution](https://www.oncoord.com/location-intelligence/attribution.html): använder gemensam attribution för flera datakällor i en kommersiell geodatatjänst.
- [kart-api.se – Attribution](https://kart-api.se/docs/attribution/): beskriver maskinläsbar attribution i API-svar och HTTP-huvuden.
- [OpenStreetMap Foundation – Attribution Guidelines](https://osmfoundation.org/wiki/Attribution_Guidelines): beskriver synlig attribution i kartor och metadata vid distribution.

## Fördjupad observation: MapAndMove

MapAndMove är särskilt relevant eftersom deras redovisning är uppbyggd kring de faktiska kartlagren, inte bara en lista över leverantörer. Vid granskningen redovisade sidan omkring 146 lager. För ett lager kan de ange den ursprungliga produktens namn, licens, upplösning eller omfattning och hur den visas. De anger också metodbegränsningar, exempelvis när en risk är härledd ur en annan datamängd och inte direkt uppmätt.

De skiljer dessutom mellan tre kategorier:
- **Källdata:** licens och attribution följer respektive ursprungskälla.
- **Egna analyser och lager:** redovisas som MapAndMoves bearbetning, med grundkällan kvar som underlag.
- **Prognoser/framskrivningar:** märks särskilt och förklaras med antaganden och osäkerhet.

En särskilt användbar detalj är att de erbjuder ett samlat PDF-/CSV-underlag för valda källor med licens, länk, villkor, bearbetning, datum och underlags-ID. Det skapar spårbarhet även när användaren lämnar kartvyn.

MapAndMove anger i sina FAQ att deras egna analyser är CC0 medan källdatan följer sin egen licens. Deras användarvillkor reglerar samtidigt åtkomst till själva webbplatsen och förbjuder bland annat masshämtning/scraping av deras tjänst. Det illustrerar en viktig skillnad: att källdata är öppen betyder inte att man fritt får skrapa en annan aktörs sammanställda tjänst eller återanvända dess egna produktionsresurser.

Källor: [Datakällor och licenser](https://mapandmove.se/datakallor), [FAQ](https://mapandmove.se/faq), [Användarvillkor](https://mapandmove.se/anvandarvillkor).

## Fördjupad observation: Lantmäteriets villkorsindelning

Lantmäteriet skiljer uttryckligen mellan särskilt utpekade öppna geodataprodukter under CC0 och avgiftsbelagda produkter med olika användningskategorier. För avgiftsbelagda produkter skiljer de bland annat mellan kommersiell slutanvändning och kommersiell vidareförädling/spridning; vidare spridning kan kräva särskilt återförsäljar- eller vidareförädlaravtal. Detta är ett konkret exempel på varför en generell etikett som ”Lantmäteriet” inte räcker i källregistret: det måste vara exakt produkt och användningskategori.

Källor: [Öppna data](https://www.lantmateriet.se/oppnadata), [Villkor och avgifter](https://www.lantmateriet.se/sv/geodata/vara-produkter/Villkor-och-avgifter/).

## Lärdomar för Skog

1. Ha en publik käll- och licenssida med redovisning per datamängd.
2. Visa kort attribution i eller intill kartan.
3. Visa källor per lager och per analysresultat, inklusive felkällor och metodbegränsningar.
4. Förklara licensvillkor med länkar till licenstexten.
5. Skilj källdata, egna bearbetningar och prognoser/framskrivningar åt.
6. Låt attribution och proveniens följa med till export, rapporter och API-svar.
7. Skilj tematiska lager från bakgrundskartor, ortofoton och karttiles.
8. Skilj öppen produkt från avgiftsbelagd produkt och kommersiell slutanvändning från vidareförädling/spridning.

## Rättslig reservation

Att en annan aktör visar en källrad eller licenssida innebär inte att samma upplägg automatiskt ger Skog rätt att använda motsvarande data. Bedömningen måste göras för exakt datamängd och användning. Branschpraxis används för transparens och produktdesign; rättslig grund hämtas från tillämplig lag, giltig licens eller avtal och faktiska omständigheter.
