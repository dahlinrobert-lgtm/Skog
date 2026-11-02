# Specifikation – attribution och proveniens i Skog

**Status:** Förslag till teknisk och produktmässig standard  
**Datum:** 2026-11-02  
**Syfte:** Säkerställa att källa, licens, bearbetning och insamlingshistorik kan följas från datainsamling till karta, analys, rapport, API och export.

## 1. Grundprincip

Attribution och proveniens ska följa data genom hela plattformen. Det ska inte vara beroende av att en utvecklare manuellt kommer ihåg att skriva en källrad i varje vy.

Skilj på:
- **Producent:** den som ursprungligen skapat eller ansvarar för datamängden.
- **Distributör/tjänsteleverantör:** den som tillhandahåller API, fil eller karttjänst.
- **Källa:** den specifika produkt, datamängd, tjänst eller handling som hämtats.
- **Licens/villkor:** den rättsliga grund som gäller för just denna produkt och användning.
- **Attribution:** den text eller länk som ska visas eller följa med data.
- **Bearbetning:** Skogs transformation, urval, klassificering, modell eller analys.
- **Snapshot/proveniens:** när och hur data hämtades, vilken version som användes och vilka källobjekt som ingick.

En myndighet kan vara distributör utan att äga alla rättigheter i materialet. Ett API kan exponera flera datamängder med olika villkor.

## 2. Föreslagna fält per källa eller produkt

Fälten nedan är en målbild för den fortsatta utbyggnaden. En del av dem har införts i ett frivilligt `provenance`-block för tre pilotkällor; övriga fält ska inte läggas in blint utan kontroll av schema och befintliga konsumenter. Okända värden ska anges som okända, inte fyllas med antaganden.

| Fält | Innebörd |
|---|---|
| `source_id` | Stabil intern identifierare. |
| `dataset_name` | Exakt produkt-/lagernamn, inte bara myndighetens namn. |
| `producer` | Ursprunglig producent/rättighetshavare, om känd. |
| `distributor` | API-/fil-/tjänsteleverantör, om annan än producenten. |
| `source_url` | Direkt länk till produkt, metadata eller dokumentation. |
| `dataset_version` | Källans version eller publiceringsdatum. |
| `licence_name` | Exakt licens eller villkorsnamn. |
| `licence_url` | Länk till licenstext eller produktspecifika villkor. |
| `licence_scope` | Vad licensen faktiskt omfattar: data, lager, bild, metadata eller API. |
| `attribution_text` | Färdig, kontrollerad attributionstext. |
| `attribution_url` | Länk som ska följa med attributionen. |
| `attribution_status` | `required`, `recommended`, `not_required` eller `unknown`. |
| `attribution_placement` | Exempelvis `map`, `layer_details`, `export_metadata` eller kombination. |
| `usage_assessment` | Separata bedömningar för hämtning, lagring, historik, bearbetning, kundvisning och vidare distribution. |
| `limitations` | Kända metod-, kvalitets-, täcknings- eller användningsbegränsningar. |
| `personal_data_note` | Dokumenterad bedömning om personuppgifter kan förekomma. |
| `third_party_components` | Bakgrundskartor, ortofoton, bilagor eller andra komponenter med separat rättighet. |
| `reviewed_on` | Datum för senaste kontroll. |
| `evidence_reference` | Länk till sparad metadata, villkor, e-postbesked eller rättighetsrapport. |

## 3. Proveniens per insamlad version

Varje snapshot bör kunna kopplas till:
- `source_id`
- hämtningstid i UTC
- källans publicerings-/uppdateringsdatum om det finns
- endpoint, lager-ID eller filnamn
- version/ETag/Last-Modified/checksumma när tillgängligt
- geografiskt och tematiskt urval
- insamlingsmetod och programversion
- licens-/metadatarevision som gällde vid hämtningen
- antal objekt, filstorlek och kontrollsumma
- eventuella avvikelser, fel eller bortfall

Spara inte hemligheter, autentiseringstoken eller personuppgifter i proveniensmetadata.

## 4. Härledda lager och analyser

Ett härlett lager ska bära referenser till alla källor som faktiskt påverkat resultatet. Dokumentera:
- vilka källor och snapshot-versioner som användes
- urval, join, aggregering, klassificering eller modell
- beräkningsdatum och kod-/modellversion
- om resultatet är observation, beräkning, uppskattning eller prognos
- kända felkällor, täckningsluckor och osäkerheter
- vem som ansvarar för analysen

Skilj alltid mellan myndighetens originaluppgift och Skogs tolkning. Skriv exempelvis ”Skogs analys baserad på data från X”, inte ”X bedömer”, om myndigheten inte faktiskt har gjort bedömningen.

## 5. Presentation i produkten

### Kartvy
- Visa kort attribution i eller direkt intill kartan.
- Om flera lager visas ska det gå att förstå vilka källor som gäller för aktiva lager.
- Bakgrundskarta och tematiska lager ska kunna redovisas separat.
- Attribution ska vara läsbar och inte döljas i en svårfunnen generell informationssida.

### Lagerinformation
Varje lager får en informationspanel med producent, produktnamn, källa, licens, attribution, uppdateringsdatum, metod och begränsningar.

### Analys och rapport
Varje analys visar källor som faktiskt ingår, relevanta bearbetningar, snapshotdatum och skillnaden mellan observation och härlett resultat.

## 6. Export och API

Attribution och proveniens ska följa med när användaren exporterar data eller tar emot API-resultat.

Rekommenderade format:
- CSV: README eller separat metadatafil med källor och licens.
- GeoJSON: `properties` eller separat manifest, utan att duplicera stora metadataobjekt i varje feature.
- GeoPackage: metadata-/beskrivningstabell och dokumentation.
- Raster: sidecar JSON/README eller inbäddade metadatafält när formatet stöder det.
- PDF-rapport: källförteckning, metod, datum och rapport-/underlags-ID.
- API: `sources`, `licences`, `attribution` och `generated_at` i svar eller responsmetadata.

Om en källa inte får vidareförmedlas ska exportfunktionen kunna utesluta just den källan eller det lagret. Det ska inte automatiskt blockera andra självständiga och tillåtna delar av exporten.

## 7. Föreslagen manifeststruktur

Illustrativt exempel – inte ett fastställt produktionsschema:

```json
{
  "manifest_version": "1.0",
  "generated_at": "2026-11-02T12:00:00Z",
  "artifact_id": "skog-report-example-001",
  "sources": [
    {
      "source_id": "example.authority.layer",
      "dataset_name": "Exempelprodukt – lager A",
      "producer": "Exempelmyndigheten",
      "source_url": "https://example.org/metadata",
      "licence_name": "CC0 1.0",
      "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/",
      "attribution_status": "recommended",
      "attribution_text": "Källa: Exempelmyndigheten",
      "retrieved_at": "2026-11-02T06:00:00Z",
      "snapshot_id": "snapshot-20261102-0600"
    }
  ],
  "processing": {
    "organisation": "Skog",
    "description": "Exempel på sammanställning av källdata",
    "method_version": "1.0",
    "result_type": "derived_analysis"
  }
}
```

## 8. Införandeordning

1. **Inventera:** identifiera exakt produkt/lager och befintliga metadatafält i `sources.yml`.
2. **Normalisera:** bestäm gemensamma fältnamn och tillåtna statusvärden; behåll bakåtkompatibilitet.
3. **Pilot:** använd tre redan registrerade källor med olika rättighetsläge:
   - `skogsstyrelsen.volume.omdrev3`: CC0 som utgångspunkt för Skogsstyrelsens egna geodata, med kontroll av exakt produkt.
   - `lansstyrelsen.actions_in_water`: publicerade villkor anger kopiering, bearbetning och distribution med källangivelse; kontrollera även API-specifika villkor.
   - `naturvardsverket.protected_areas`: central tjänst anger okända villkor; använd som test av hur okänd status och begränsad publicering representeras utan att felaktigt markera alla användningar som förbjudna.
4. **Manifest:** generera ett manifest för ett internt testuttag och kontrollera att attribution följer med. Förberedande verifiering och acceptanskriterier för Åtgärder i vatten finns i [pilotgranskningen](source-rights-reviews/2026-11-02-actions-in-water-pilot.md).
5. **UI:** bygg källpanel och kartattribution när datamodellen är verifierad.
6. **Export:** lägg till manifest i CSV/GeoJSON/GeoPackage/PDF efter formatens förutsättningar.

### 8.1 Befintliga registerfält – nulägeskontroll

Vid kontroll av `data-platform/config/sources.yml` den 2026-11-02 fanns källfält som `provider`, `rights.licence`, `rights.licence_url` och `rights.attribution`, men inga gemensamma fält för `attribution_text`, `attribution_required`, `producer` eller `distributor`. En valfri `provenance`-sektion har nu införts som pilot för tre källposter. Den befintliga `schema_version: 2` är oförändrad; äldre poster kan fortfarande sakna sektionen. Det är en bakåtkompatibel metadatautvidgning i registret, inte en ändring av den kanoniska datamodellen. Innan fler källor får sektionen behöver vi kontrollera eventuella konsumenter av `sources.yml`.

## 9. Validering och CI

Ett enkelt registertest finns i `data-platform/scripts/validate_source_registry.py` och körs av `.github/workflows/validate-source-registry.yml` när källregistret, validatorn eller workflow-filen ändras. Testet kontrollerar YAML-syntax, schema_version 2, obligatoriska grundfält, unika source_id och struktur/statusvärden för valfria provenance-block. Det kontrollerar inte att en licensbedömning är juridiskt riktig eller att en källa faktiskt har lämnat ett tillstånd.

`provenance` är frivilligt i nuläget. Nya poster kan införas stegvis. En status `pending_dataset_review` betyder att attributionstexten är preliminär och inte ett godkänt villkor.

## 10. Acceptanskriterier

- Varje publicerat lager har identifierbar producent, produkt/källa och rättighetsstatus.
- Attribution visas när den krävs och rekommenderas där det är lämpligt.
- Okända licensfält framställs inte som tillstånd eller förbud.
- Härledda resultat kan spåras till sina ingående källor och snapshot-versioner.
- Exporter innehåller relevant käll- och licensinformation.
- Bakgrundskartor och tredjepartskomponenter redovisas separat.
- Ett hinder för en källa blockerar inte automatiskt oberoende lager med egen rättslig grund.

