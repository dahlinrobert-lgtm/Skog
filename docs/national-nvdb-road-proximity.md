# Nationell NVDB-närmaste-väg-matchning

**Status:** första kodprototyp i branch `feat/national-nvdb-road-proximity`  
**Avsikt:** geografiskt granskningsunderlag för Police–NVR, inte automatisk bekräftelse av olycksmatchning.

## 1. Syfte

Beräkna närmaste NVDB-vägnummerobjekt till en händelsekoordinat i WGS84. Metoden ska kunna köras över flera länsvisa NVDB-GeoPackage-filer utan att läsa in hela det nationella vägnätet i minnet.

Resultatet är separat geografisk evidens. Det får inte ändra:
- temporal kandidatgenerering,
- temporal score eller status,
- kandidatinkludering,
- `geographic_match_used`,
- manuell granskningsstatus eller beslut.

## 2. Första implementation

Skript: `scripts/match_points_to_nvdb_roads.py`

Indata:
- CSV med WGS84-koordinater (standardfält: `nvr_latitude_wgs84`, `nvr_longitude_wgs84`);
- en eller flera NVDB-GeoPackage-filer, angivna med upprepade `--nvdb-gpkg`;
- vägnummerlagret `NVDB_DK_O_111_Vagnummer` med fälten `ELEMENT_ID`, `Europavag`, `Huvudnummer` och `Lankroll`.

För varje koordinat:
1. Transformera WGS84 till varje källfils projicerade CRS.
2. Läs endast vägobjekt vars geometri/bounding box träffar ett kvadratiskt sökfönster med angiven radie.
3. Beräkna exakt geometriskt avstånd för de inlästa kandidaterna.
4. Behåll de närmaste vägobjekten och alternativa kandidaterna.
5. Skriv ett nytt CSV-resultat; indatans temporalfil ändras inte.
6. Om `--geojson-output` anges, skriv en separat WGS84 GeoJSON med händelsepunkter och de valda vägkandidaternas faktiska linjegeometrier. Händelser och vägkandidater märks med `feature_type`, radnummer, kandidatordning och granskningsstatus. GeoJSON-exporten ändrar inte CSV-indata eller temporal evidens.

Exempel:
```powershell
python scripts/match_points_to_nvdb_roads.py `
  --candidates path\to\candidates.csv `
  --nvdb-gpkg path\to\norrbotten.gpkg `
  --nvdb-gpkg path\to\vasterbotten.gpkg `
  --output path\to\road-review.csv `
  --geojson-output path\to\road-review-map.geojson `
  --search-radius-m 1000 `
  --max-candidates 5
```

Skriptet kräver projicerade meterbaserade koordinatsystem. Det avvisar geografiska CRS och projicerade CRS vars första två axlar inte använder meter.

## 3. Statusar och försiktighetsregler

- `completed_with_candidates`: en eller flera vägobjekt hittades inom sökradien.
- `completed_no_candidate_in_search_window`: inga vägobjekt hittades i det lokala sökfönstret. Detta bevisar inte att det saknas väg; källtäckningen måste vara känd.
- `partial_source_read`: minst en NVDB-källa kunde inte läsas. Resultatet är ofullständigt och får inte tolkas som negativ evidens.
- `missing_or_invalid_coordinates`: koordinat saknas eller ligger utanför giltiga WGS84-intervall.

Varje kandidat behåller källfil, `ELEMENT_ID`, vägnummer, `Lankroll` och avstånd. GeoJSON-exporten innehåller endast händelsekoordinat och valda vägkandidatlinjer i WGS84; den är ett lokalt granskningsunderlag och inte en bekräftad olycksväg. Dubbletter med samma element-ID/vägnummer/roll i överlappande länsuttag reduceras till den närmaste kopian.

Detta är närmaste-väg-evidens, inte bevis för att fordonet färdades på vägen. En närliggande parallellväg, planskild korsning, ramp eller lokal anslutning kan fortfarande skapa tvetydighet. Den första versionen gör ingen topologisk arvning av vägnummer till ramper och gör ingen nätverksruttning.

## 4. Nationell användning – vad som återstår

Koden kan ta emot flera länsvisa GeoPackage-filer, men nationell drift är inte verifierad. Innan nationell körning krävs:
- inventering av de faktiska Lastkajen-filerna, lager, fält, CRS, geografisk täckning och produktversion;
- verifiering att samtliga länsfiler har kompatibelt schema och fullständig täckning;
- kontroll av eventuella överlapp och luckor vid länsgränser;
- prestandatest på ett representativt urval av händelser och samtliga avsedda källfiler;
- manuell utvärdering av positiva, negativa och tvetydiga fall i flera geografiska miljöer;
- separat temporal regression som visar att befintliga kandidater, poäng och statusar är oförändrade;
- kontroll av NVDB-produktens villkor för lagring, bearbetning och kundvisning.

För stora nationella körningar kan upprepade bbox-läsningar per händelse bli kostsamma. Batchning eller ett lokalt spatialt index kan behövas efter mätning. Denna prototyp ska därför först köras på ett litet urval.

## 5. Nästa konkreta steg

1. Kör en liten Luleå-pilot med befintligt kandidat-CSV och en verifierad NVDB-GeoPackage.
2. Kontrollera att resultatet stämmer mot kända vägnummer och manuellt granskade fall.
3. Kör samma test med flera läns-GPKG och kontrollera gränsöverlapp.
4. Mät tid, antal lästa objekt, minne och antal ofullständiga källor.
5. Utöka därefter testurvalet geografiskt innan nationell användning övervägs.

Ingen nationell produktionskörning eller kundvisning är aktiverad genom denna implementation.
