# Skogskoll: fastighetssökning via Lantmäteriet

## Beslut

Använd Lantmäteriets officiella **Fastighetsindelning Direkt (OAPIF)** för en framtida sök- och geometriintegration. Bygg inte produktionsflödet på den interna endpoint som Min karta använder.

Produktinformation: https://geotorget.lantmateriet.se/geodataprodukter/fastighetsindelning-direkt-api  
API-bas: `https://api.lantmateriet.se/ogc-features/v1/fastighetsindelning`

Lantmäteriet anger att produkten är avgiftsfri, uppdateras dagligen och kräver beställd API-behörighet samt juridisk prövning/användningsvillkor. Geometrierna är översiktsunderlag och fastighetsgränserna är inte juridiskt gällande.

## Föreslaget användarflöde

1. Användaren söker på kommun, trakt och fastighetsbeteckning.
2. Appen visar kandidater med full beteckning och kommun, så att användaren kan välja rätt fastighet.
3. Backend hämtar områdesgeometrier för vald registerenhet.
4. Alla delområden visas på en karta. Användaren kan granska och bekräfta dem innan de sparas som bevakning.
5. Bevakningen lagras som Polygon/MultiPolygon i WGS84/EPSG:4326; flera fristående delar ska inte tappas bort.
6. Manuell GeoJSON-import finns kvar under Avancerat som reserv.

## Säkerhets- och CRS-krav

- **Inga API-nycklar i webbläsaren.** Autentisering och anrop till Lantmäteriet ska ske från en serverfunktion/proxy som kontrollerar behörighet.
- Kontrollera CORS, autentiseringsmetod, samtliga användningsvillkor och godkänd användning innan integration aktiveras.
- Läs CRS från OGC API-svaret/headers och dokumentationen. Koordinater i storleksordningen hundratusentals och miljoner är projicerade koordinater, inte longitud/latitud.
- Anta inte EPSG:3006 enbart från koordinatstorleken. Verifiera det uttryckligen och transformera med ett testat CRS-bibliotek.
- Lägg till tester med kända kontrollpunkter i Västerbotten/Norrbotten, validera polygonernas giltighet och kontrollera att resultatet hamnar på rätt plats innan lagring.
- Om samma registerenhet har flera områdesnummer ska geometridelarna samlas i MultiPolygon eller sparas som flera sammanhängande geometrier med gemensamt fastighets-ID.
- Visa tydligt att geometrierna är vägledande och inte juridiskt bevis på ägande eller exakt gräns.
- Spara datakälla, hämtningstid, källans objektidentitet och eventuell version/tidsstämpel så att en ändrad geometri kan upptäckas senare.

## Nuvarande status

Den statiska Skogskoll-prototypen sparar områden endast i webbläsarens localStorage. Den har ingen serverfunktion, ingen Lantmäteriet-behörighet och ingen automatisk fastighetssökning. Nästa implementeringssteg som kräver extern förutsättning är att ordna API-behörighet och godkänd användning. Därefter kan serveradapter och UI kopplas ihop utan att exponera hemligheter i klienten.
