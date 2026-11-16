# Länsstyrelserna – ÄFO-gränser och avskjutningsstatistik

**Kontrolldatum:** 2026-11-16  
**Syfte:** Underlag för nationell karta över rapporterad älgavskjutning per älgförvaltningsområde (ÄFO).

## 1. ÄFO-gränser – JaktAdm

Verifierad tjänst:
- WMS: `https://ext-geodata-applikationer.lansstyrelsen.se/arcgis/services/Jaktadm/lst_jaktadm_visning/MapServer/WMSServer`
- REST-tjänst: `https://ext-geodata-applikationer.lansstyrelsen.se/arcgis/rest/services/Jaktadm/lst_jaktadm_visning/MapServer`
- Feature layer: `MapServer/1`
- WMS-presentation: layer `0` (Älgförvaltningsområden)
- REST-fält som verifierats: `afo_id`, `namn_afo`, `forvaltare`.

GitHub Actions-proben fick HTTP 200 från WMS GetCapabilities och REST-frågan. REST-lager 1 returnerade 129 polygonobjekt. GeoJSON-frågan med `outSR=4326` testades även från GitHub Pages-origin och webbläsarens CORS-anrop lyckades.

### Täckningskontroll

Nationella Älgdata-katalogen innehåller 131 aktuella väljarkombinationer för säsongen 2026/2027. Två poster är inte aktiva geografiska områden:
- `01-099`: Stockholms län, ”Äfo ej specificerat”, katalogens senaste år 2011/2012.
- `21-014`: Gävleborgs län, ”Furuvik (Ej aktiv)”, katalogens senaste år 2024/2025.

När dessa två inaktiva/ospecificerade poster utesluts återstår 129 aktiva ÄFO-ID:n. De matchar de 129 polygonernas sammansatta `afo_id` i JaktAdm-lagret. Kopplingen ska göras med detta ID, inte med visningsnamn.

### Rättighetsbegränsning

Geodatakatalogens metadatareferens `6d4c42de-2b43-4b72-98ec-856d8adfaf29` gick inte att hämta under kontrollen (HTTP 502). Därför är exakt licens, bearbetningsrätt, extern visning och kommersiell användning för just detta lager **inte verifierade**. Teknisk åtkomst eller en publik WMS-tjänst ska inte tolkas som en generell kommersiell licens. Extern publicering ska invänta kontroll av metadata och villkor.

## 2. Avskjutningsstatistik – Älgdata

Verifierad rapportkonfiguration:
- Statistikportal: `https://algdata-apps.lansstyrelsen.se/algdata-apps-stat/`
- Rapport-ID: `3`
- Rapportnamn: `ÄFO`
- Rapportkonfigurationens nivå: `ReportLevel=2`
- `HuntingArea=0`: rapporten väljs på ÄFO-nivå utan att ett enskilt jaktområde behöver väljas.
- Gränsläge: nuvarande gränser (`TypeAFO=G`).
- Jaktår testat: `2026/2027`.

En faktisk portalhämtning för Västerbottens län, Sydöstra älgförvaltningsområdet (`afo_id=24-005`) returnerade en tabell över de registrerade jaktområdena inom ÄFO:t och en sammanfattande `Summa:`-rad. Exempel från sammanfattningsraden:
- Fällda totalt: `42 (2 408)`
- Avskjutningsmål totalt: `66 (3 394)`

De inledande värdena läses som värden för det valda jaktåret 2026/2027. Hela celltexten sparas oförändrad. Betydelsen av parentesvärdena tolkas inte i den här implementationen.

Rapportens API-svar och tabell kontrollerades. För den provade ÄFO-rapporten innehöll grafstrukturen 107 jaktområdeskolumner; sammanfattningsraden är därför lämplig som ÄFO-total utan att summera ett ofullständigt regionalt urval av ÄJO.

### Datatolkning

- Värdet är kumulativ rapportering för valt jaktår, inte en punkt eller exakt fältdag.
- ÄFO-totalen hämtas från portalens `Summa:`-rad över områdets registrerade jaktområden.
- Hela råcellen sparas, exempelvis `42 (2 408)`; endast det inledande värdet används som valt jaktårs tal.
- En saknad eller ofullständig rapport får inte tolkas som noll fällda djur.
- Regionala ÄJO-förändringssnapshots och nationella ÄFO-summor är två olika produkter och ska beskrivas separat.

## 3. Nationell insamling – status

En separat insamlare och ett dagligt GitHub Actions-flöde har lagts till i `dahlinrobert-lgtm/alg-grasmyr` på arbetsgrenen `feat/national-afo-avskjutning-snapshots`. Insamlaren:
- läser aktiva ÄFO-ID:n ur den nationella katalogen för valt jaktår,
- kontrollerar att ID-uppsättningen matchar JaktAdm:s polygon-ID:n,
- hämtar ÄFO-rapportens sammanfattningsrad för varje område,
- kräver att hela batchen lyckas innan snapshots och dashboard skrivs,
- vägrar skriva över ett avvikande snapshot med samma datum.

En enskild ÄFO-provkörning har passerat. Full nationell batch är under verifiering. Inga nationella snapshots ska betraktas som produktionsbaslinje förrän batchen visar 129/129 områden och har granskats.

## 4. Källhänvisning

- Statistik: **Källa: Länsstyrelsernas Älgdata statistikportal** – https://algdata-apps.lansstyrelsen.se/algdata-apps-stat/
- Geometri: **Källa: Länsstyrelserna – Älgförvaltningsområden (JaktAdm)** – https://ext-geodata-applikationer.lansstyrelsen.se/arcgis/rest/services/Jaktadm/lst_jaktadm_visning/MapServer

**Rättighetsstatus:** Teknisk åtkomst verifierad. Exakta villkor för lagring, bearbetning, extern visning och kommersiell användning av geometrierna och statistikprodukten måste bedömas separat.
