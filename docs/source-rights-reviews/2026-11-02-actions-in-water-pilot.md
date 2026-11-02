# Pilotgranskning – Åtgärder i vatten

**Datum:** 2026-11-02  
**Status:** Förberedande verifiering – ingen automatisk insamling ännu  
**Källa-ID:** `lansstyrelsen.actions_in_water`

## 1. Syfte

Verifiera om Åtgärder i vatten kan användas som första end-to-end-pilot för Skogs källhantering, snapshots, proveniens och GeoJSON-export. Piloten ska börja med ett litet, reproducerbart testuttag. Den ska inte påverka befintliga produktionsflöden.

## 2. Vad som är verifierat

- Länsstyrelsens öppna-data-information anger att Åtgärder i vatten-data får kopieras, bearbetas och distribueras kostnadsfritt med Länsstyrelsen som källa.
- Informationen beskriver systemet som en gemensam databas för Länsstyrelserna och Havs- och vattenmyndigheten.
- Publicerade format anges som JSON, REST, XLSX, Shapefile och WMS.
- Den publika sökingången är `https://atgarderivatten.lansstyrelsen.se/Atgarder/Hitta`; informationssidan är `https://www.atgarderivatten.se/`.
- Äldre användarmanual beskriver publik sökning utan inloggning och en hierarki där projekt kan innehålla en eller flera åtgärder. Manualen är från 2017 och ska inte användas som auktoritativ beskrivning av dagens API eller fältmodell.

## 3. Viktig avgränsning: flera åtkomstytor kan ha olika villkor

Den öppna-data-text som hittats gäller den beskrivna datamängden och anger källangivelse. En separat tredjepartsinventering beskriver dessutom ett Swagger-API för punkt/linje/polygon och anger CC0 1.0 för just den API-källan. Det är en användbar teknisk ledtråd, men inte tillräckligt underlag för att anta att hela Åtgärder i vatten-databasen, alla API-endpoints eller samtliga bilagor omfattas av CC0.

Därför ska piloten hålla isär:
1. den publika sök- och detaljvyn,
2. eventuell Swagger/REST-geodatatjänst,
3. filnedladdningar (t.ex. XLSX/Shapefile),
4. WMS-kartbilder,
5. eventuella foton, dokument och andra bilagor.

Varje åtkomstyta ska kopplas till sin egen metadata, licensuppgift och tekniska begränsningar. Utgå inte från att WMS-bild, geometri, attribut och bilagor har identiska villkor.

## 4. Kvar att verifiera innan hämtkod skrivs

- Exakt officiell Swagger/OpenAPI-URL och API-version.
- Vilka endpoints som är publika och om de kräver nyckel, session eller annan autentisering.
- Om API:t returnerar punkt-, linje- och polygongeometrier, och vilket koordinatsystem som används.
- Fältdefinitioner, kodlistor, null-värden och stabila objekt-ID:n.
- Pagination, filter, max antal poster, rate limits och rekommenderat hämtningsintervall.
- Om uppdateringstid eller ändringsdatum finns per objekt och om borttagna objekt kan upptäckas.
- Om den CC0-uppgift som förekommer i en tredjepartsinventering uttryckligen avser ett visst geodata-API/lager. Spara i så fall den officiella metadata-/licenstexten som bevis innan den registreras som gällande licens.
- Om projekt, åtgärd och geometri är separata entiteter och hur relationerna representeras.

Inget av detta ska fyllas i genom gissning. Okända API-detaljer är en avgränsad teknisk kunskapslucka, inte i sig ett förbud mot att använda de delar som redan har tydligt publicerade återanvändningsvillkor.

## 5. Pilotens tekniska upplägg när endpointen är verifierad

### Steg A – litet testuttag
- Hämta en begränsad sida eller ett litet geografiskt urval.
- Spara oförändrat råsvar med hämtningstid, endpoint, HTTP-status och kontrollsumma.
- Spara aldrig autentiseringstoken, cookies eller andra hemligheter i snapshot eller manifest.

### Steg B – normalisering
- Behåll källans ursprungliga objekt-ID och råfält.
- Skapa separata interna ID:n först när det finns ett dokumenterat behov.
- Behåll relationen mellan projekt och åtgärd; slå inte ihop dem till en enda post utan att dokumentera transformationen.
- Spara geometri oförändrad i rålagret och dokumentera eventuell reprojektion i härlett lager.

### Steg C – snapshot och manifest
Varje uttag ska minst dokumentera:
- `source_id`: `lansstyrelsen.actions_in_water`
- `retrieved_at` i UTC
- exakt endpoint och filter/urval
- API-version och källans uppdateringstid om de finns
- antal projekt, åtgärder och geometrier om dessa kan räknas separat
- filstorlek och SHA-256
- licens-/attributionsreferens som gällde vid hämtningen
- insamlingskodens version och eventuella fel/bortfall.

### Steg D – exporttest
Skapa GeoJSON endast från ett testuttag och inkludera ett separat manifest. Attribution ska vara synlig i manifestet och exportens metadata, inte upprepas i varje feature om det inte behövs. Exempel på preliminär attribution enligt publicerade öppna-data-villkor:

> Källa: Länsstyrelsen – Åtgärder i vatten (gemensamt system med Havs- och vattenmyndigheten).

Den exakta attributionstexten ska följa den produkt-/API-metadata som slutligen verifieras.

## 6. Kvalitets- och tolkningsregler

- En registrerad åtgärd är inte automatiskt bevis för att åtgärden är utförd eller fältverifierad.
- Bevara status som uppgift saknas/okänd; mappa inte automatiskt till planerad eller genomförd.
- Skilj mellan projektstatus, åtgärdsstatus och eventuell bedömning av funktion/resultat.
- Geometri kan representera en punkt, sträcka eller yta; analysen ska ta hänsyn till geometrityp och eventuell generalisering.
- Spara ändringshistorik genom återkommande snapshots. Radera inte en tidigare observation bara för att objektet saknas i en senare hämtning.
- Om ett objekt försvinner ska det först markeras som saknat i senare snapshot; klassificera det inte som borttaget förrän källans beteende eller ändringssignal styrker det.

## 7. Acceptanskriterier för pilot

Piloten är godkänd när:
1. officiell endpoint och dess villkor har dokumenterats,
2. ett litet testuttag kan hämtas reproducerbart,
3. rådata och manifest sparas med kontrollsumma,
4. stabila ID:n och relationer mellan projekt/åtgärd är förstådda,
5. ett GeoJSON-test kan skapas med korrekt proveniens,
6. testet visar att saknade statusvärden och osäker genomförandestatus bevaras,
7. ett andra uttag kan jämföras utan att historiken skrivs över.

## 8. Källor och evidens

- Länsstyrelsen, öppna data – Åtgärder i vatten och återanvändningsvillkor: https://www.lansstyrelsen.se/varmland/om-oss/vara-tjanster/oppna-data.html
- Officiell informationssida: https://www.atgarderivatten.se/
- Publik sökingång: https://atgarderivatten.lansstyrelsen.se/Atgarder/Hitta
- Äldre användarmanual (2017; endast vägledande för äldre användargränssnitt och begrepp): https://ext-dokument.lansstyrelsen.se/jonkoping/atgarderivatten/%C3%85iV%20-%20Manual%20-%20anv%C3%A4ndning%20och%20s%C3%B6kning.pdf
- Tredjepartsinventering av datakällor (teknisk ledtråd om Swagger/CC0, inte licensbevis): https://mapandmove.se/en/datakallor

**Beslutsregel:** Ingen produktionshämtning eller licensändring görs på grundval av tredjepartsinventeringen ensam. Nästa tekniska steg är att lokalisera och verifiera den officiella OpenAPI-beskrivningen från den publika tjänsten.


## 9. Verifierad officiell ArcGIS REST-tjänst (2026-11-02)

Länsstyrelsens officiella REST-katalog har mappen `atgarderivatten` med två relevanta MapServer-tjänster:

- `lst_aiv_read/MapServer`: lästjänst med lagren Punkt (0), Linje (1) och Polygon (2).
- `lst_aiv_search/MapServer`: söktjänst med vPunkt (0), vLinje (1) och vPolygon (2).

Den verifierade lästjänsten:
- URL: `https://ext-geodata-acc.lansstyrelsen.se/arcgis/rest/services/atgarderivatten/lst_aiv_read/MapServer`
- Spatial reference: EPSG:3006 (SWEREF 99 TM).
- Query formats: JSON, GeoJSON och PBF.
- Layer metadata visar stöd för pagination och query; MaxRecordCount är 2 000.
- Samtliga tre geometrier delar centrala identifieringsfält: `ProjektId`, `AtgardsInsatsId`, `FaktiskAtgardId`, namn, `Guid`, `LanIds`, `KommunIds`, `Haro` och `Varo`. Datumfältet `FaktiskAtgardFardigstalld` finns också.
- Lagren saknar attachments enligt lagerinformationen.

Detta är ett konkret REST-gränssnitt och ersätter behovet av att förlita sig på en obekräftad Swagger-URL för själva geometrierna. Den tidigare tredjepartsuppgiften om ett Swagger-API och CC0 är fortfarande separat evidens; den bevisar inte att just denna ArcGIS-tjänst har CC0. Källregistret behåller därför Länsstyrelsens publicerade återanvändningsvillkor med källangivelse som grund.

### Litet testuttag

Ett read-only testskript finns i `data-platform/scripts/collect_actions_in_water_sample.py`.

- Standardkörningen hämtar högst fem objekt per geometrityp.
- Skriptet sparar ArcGIS JSON i EPSG:3006 och en separat GeoJSON-export i EPSG:4326.
- Manifestet innehåller hämtningstid, endpoint, antal poster i källagret, antal provposter, SHA-256, attribution och uttryckliga begränsningar.
- Skriptet begränsar provstorleken till 100 per lager och har inget läge för fullständig bulkinsamling.
- Ingen autentisering, skrivning eller ändring av källdata används.

Kör lokalt från repositoryts rot:

```bash
python data-platform/scripts/collect_actions_in_water_sample.py
```

Ange exempelvis `--limit 10` för ett något större prov. Standardutdata hamnar under `data/snapshots/actions-in-water/<UTC-tid>/`.

### Kvar innan pilotens tekniska godkännande

1. Köra provhämtningen och kontrollera att alla tre lager returnerar data.
2. Kontrollera fältvärden, stabiliteten i ID/GUID och relationerna mellan projekt, åtgärdsinsats och faktisk åtgärd.
3. Jämföra ArcGIS JSON och GeoJSON för att verifiera geometri och koordinattransformation.
4. Kontrollera om tjänsten exponerar ändringsdatum eller andra signaler som kan användas för historik.
5. Köra ett andra prov och verifiera reproducerbar manifest- och snapshotstruktur.

Ingen schemalagd eller nationell insamling har aktiverats.
