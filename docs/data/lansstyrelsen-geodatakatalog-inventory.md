# Inventering av Länsstyrelsernas Geodatakatalog

## Syfte

Detta är ett upptäcktsflöde för att hitta möjliga datakällor om naturvårdande skötsel. Det är inte en åtgärdsinsamling och ska inte skapa historiska händelser.

## Teknisk metod

Katalogen bygger på GeoNetwork 4. Den publika söktjänsten används via:

- API: \`https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/srv/api\`
- Endpoint: \`POST /search/records/_search?bucket=metadata\`
- Fritextindex: \`anytext\`
- Mallposter filtreras bort med \`isTemplate = n\`.

Sökorden omfattar naturvårdsbränning, naturvårdande skötsel, naturvårdsåtgärder, slåtter, bete, hamling, död ved, veteranisering, skogsrestaurering, invasiva arter, ängs- och betesmark samt Natura 2000-skötsel.

## Resultatformat

Workflow-artifacten innehåller:

- \`catalogue-inventory.json\`: unika metadata-ID:n, titel, råa indexerade metadatafält och vilka sökord som gav träffen.
- \`catalogue-report.json\`: antal träffar per sökord och övergripande kvalitetsinformation.

Sökningen begränsas till 200 poster per sökord i första inventeringspasset. Om ett sökord har fler träffar flaggas det som avklippt och behöver följas upp med paginering eller mer precisa termer.

## Urvalskriterier för att gå vidare

Varje kandidat granskas manuellt innan en separat hämtare byggs:

1. Finns en maskinläsbar vektortjänst (ArcGIS REST, WFS eller OGC API Features), eller endast WMS?
2. Innehåller tjänsten faktisk geometri och stabil objektidentitet?
3. Finns datum för utförd åtgärd, och är datumets betydelse dokumenterad?
4. Går planerad, pågående och genomförd status att skilja åt?
5. Är åtgärdskategorin naturvårdande och inte produktionsinriktat skogsbruk?
6. Vilka län, förvaltare och geografiska områden täcks?
7. Vilken uppdateringsfrekvens, licens och attribution gäller?

Skyddsbeslut, skötselplaner, naturvärdesinventeringar och naturvårdsavtal är viktiga kontextkällor men får inte automatiskt klassas som utförda åtgärder.

## Kända skillnader mellan katalog och register

Länsstyrelsernas Geodatakatalog beskriver länsstyrelsernas egna geodata och tjänster. Naturvårdsregistrets öppna REST/WFS-tjänster kommer från Naturvårdsverket och beskriver skyddade områden. De två katalogerna ska inte blandas ihop.

## Källor

- Länsstyrelsernas Geodatakatalog: https://gis.lansstyrelsen.se/geodata/geodatakatalogen/
- GeoNetwork 4 Search API: https://docs.geonetwork-opensource.org/4.4/api/search/
- Geodatakatalogens API-dokumentation: https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/doc/api/index.html
- Naturvårdsregistrets metadata: https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=50FE77C1-43A0-445A-B56C-6B729E21DC67_C
