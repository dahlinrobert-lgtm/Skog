# Manuell testprobe för Min kartas fastighetsgeometri

Detta är en **tillfällig, manuellt startad diagnostik** för att se om polygoninformationen som visas i Min karta går att läsa ut för ett objekt. Den är inte en officiell API-integration och får inte användas som produktionsberoende.

## Så testar du

1. Öppna https://minkarta.lantmateriet.se/ och sök fram fastigheten.
2. Öppna DevTools → Console.
3. Klistra in innehållet från `min-karta-geometry-probe.js` och kör det.
4. Klistra in `objektidentitet` från det anrop du såg i Network/Fetch/XHR.
5. Skriptet gör **ett enda GET-anrop**, visar svar och koordinatintervall i konsolen och laddar ned JSON för analys.

## Vad testet ger

- HTTP-status och toppnivånycklar i svaret.
- Geometrityp om den finns i vanligt GeoJSON-liknande format.
- Antal upptäckta koordinatpar och min/max-intervall.
- Råsvaret som JSON-fil för fortsatt test av geometri och CRS.

## Viktiga begränsningar

- Endpointen `/api/searchservice/fastighetsgeometri/v1` är en intern endpoint i Min karta, inte den dokumenterade produktions-API:en. Använd den bara för en avgränsad manuell teknisk kontroll; kontrollera villkor och tillstånd innan vidare användning.
- Inget anrop görs automatiskt vid sidladdning och skriptet loopar inte.
- Skriptet skickar ingen information till Skogskoll eller någon annan server. JSON-filen laddas ned lokalt i din webbläsare.
- Koordinatsystemet är **inte** fastställt av skriptet. Om koordinaterna är exempelvis i meter ska de inte behandlas som WGS84 [longitud, latitud].
- Min kartas fastighetsgränser är inte juridiskt gällande.
- Använd aldrig detta som underlag för att avgöra juridisk fastighetsgräns eller avverkningsrätt.

När JSON-filen finns kan vi inspektera svarets metadata och undersöka om geometri och CRS går att fastställa. Den officiella integrationen ska fortfarande använda Lantmäteriets godkända API-åtkomst.
