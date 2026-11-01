# Hydrologisk restaurering – första insamlingsspåret

## Avgränsning

Det första automatiserade spåret arkiverar Skogsstyrelsens offentliga polygonlager för återvätningsavtal:

- Tjänst: `Geodataportal/GeodataportalVisaAtervatningavtal/MapServer`
- Lager: `ÅtervätningYta_Skogsstyrelsen` (ID 0)
- Källa: https://geodpags.skogsstyrelsen.se/arcgis/rest/services/Geodataportal/GeodataportalVisaAtervatningavtal/MapServer/0
- Produktbeskrivning: https://www.skogsstyrelsen.se/globalassets/sjalvservice/karttjanster/geodatatjanster/produktbeskrivningar/atervatningsavtal---produktbeskrivning.pdf

Skogsstyrelsens produktbeskrivning anger att lagret visar tecknade återvätningsavtal, har nationell geografisk täckning och uppdateras varje natt. Det är därför ett lämpligt första historikspår.

## Viktig tolkningsgräns

Lagret visar avtals-/förvaltningsområden. Det bekräftar inte i sig att dikespluggar har installerats eller att den fysiska åtgärden är färdigställd. Vi märker därför inte objekten som "utförd dikespluggning". Status och datum ska tolkas enligt källans dokumenterade attribut.

## Arkivering

- Fullt nuläge: `data/skogsstyrelsen-atervatning/current.json.gz`
- Förändringshistorik: `data/skogsstyrelsen-atervatning/history/events.jsonl`
- Senaste körningsrapport: `data/skogsstyrelsen-atervatning/latest-report.json` (Actions-artifact)
- Första körningen skapar baslinje och inga historiska förändringshändelser.
- Senare körningar registrerar tillagda, ändrade och från källan borttagna objekt.
- Objekt-ID och UUID bevaras tillsammans med samtliga källattribut och geometrier.

## Nationell dataprodukt för våtmarksåtgärder

Naturvårdsverkets nationella dataproduktspecifikation för Våtmarksåtgärder (version 1.2, 2024-08-09) omfattar även LONA, LOVA, den strategiska planen för EU:s jordbrukspolitik, SkötselDOS och Skogsstyrelsens återvätningsavtal. Den definierar bland annat hydrologisk restaurering och dikespluggning/igenläggning. Specifikationen anger GeoPackage och OGC API Features som distributionsformat, men tjänsteanropen var ännu inte ifyllda i den publicerade versionen som granskades. Vi ska därför fortsätta undersöka om en samlad nationell leverans nu finns, utan att anta att denna ArcGIS-tjänst täcker alla våtmarksåtgärder.

## Nästa steg

1. Kör första livehämtningen och verifiera antal objekt, attribut, geometrier och geografisk täckning.
2. Jämför med nationella våtmarksåtgärder via LONA/LOVA/SkötselDOS och med VISS, men håll planerade/möjliga åtgärder skilda från genomförda fysiska åtgärder.
3. Först efter verifiering byggs ett bredare nationellt våtmarksregister.
