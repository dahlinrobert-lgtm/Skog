# Källspecifik rättighetsgranskning – geodata från Länsstyrelserna, Vindbrukskollen och Naturvårdsverket

**Granskningsdatum:** 2026-11-02  
**Status:** Preliminär käll- och metadata-granskning; inte juridiskt utlåtande eller generellt publiceringsgodkännande.

## Sammanfattning

| Källa | Vad underlaget faktiskt stödjer | Rekommenderad status i Skog |
|---|---|---|
| Länsstyrelsernas WMS/geodatakatalog | Länsstyrelsernas öppna-data-sida anger att WMS-data kan kopieras, bearbetas och distribueras gratis med Länsstyrelsen som källa. Geodatakatalogen säger samtidigt att licenstyp anges i metadata för varje datamängd. | **Villkorat grön per datamängd/lager.** Registrera metadata/licens innan lagret aktiveras. |
| Vindbrukskollen – namngivet landbaserat dataset | Den exakta metadataregistreringen i källregistret anger CC0. Energimyndigheten anger att bakgrundskartorna är upphovsrättsskyddade och har särskilda användningsbegränsningar. | **Grön för verifierat CC0-datat; röd för återanvändning av bakgrundskartografi utan tillstånd.** |
| Naturvårdsregistret – skyddade områden | Nationell WMS/WFS/REST och nedladdningsbara data finns. Den centrala tjänsteposten i Planeringskatalogen visar dock uttryckligen "Villkor okända". Separata lagerposter kan ange CC0. | **Gul tills licensen verifierats på exakt nedladdningsbart lager/datamängd.** Tillgänglig tjänst räcker inte. |

## 1. Länsstyrelsernas geodatakatalog och WMS

Länsstyrelsernas officiella information om öppna data anger att data från WMS-tjänster kan kopieras, bearbetas och distribueras gratis med villkoret att Länsstyrelsen anges som källa. Den nationella geodatakatalogen anger samtidigt att licenstypen för geodata anges i metadata för varje datamängd.

Detta ska tolkas som en generell återanvändningsvägledning för de data som omfattas, inte som en generell licens för varje lager, varje kartbild eller varje inbäddad komponent.

### Regler för Skog

- Registrera metadata-ID, lager-ID, ansvarig organisation, licens/standardiserade användningsvillkor, metadata-URL och kontrolltidpunkt per lager.
- Om metadata saknar licens eller visar okända villkor: sätt status gul och begär besked från angiven informationsansvarig.
- Skilj mellan WMS-bild (renderad kartbild), WFS/REST-geometrier och nedladdningsbara data. En rätt att återanvända data innebär inte automatiskt rätt till kartbilder, symboler eller bakgrundskartor.
- Ange Länsstyrelsen som källa när de publicerade villkoren kräver det; ange även exakt datamängd och version.
- Kontrollera om lagret innehåller data från kommuner, konsulter eller andra producenter och om dessa har egna villkor.
- För historiska snapshots: spara licensmetadata tillsammans med varje insamlad version så att senare villkorsändringar kan spåras.

Källor:
- [Länsstyrelsen Värmland – Öppna data](https://www.lansstyrelsen.se/varmland/om-oss/vara-tjanster/oppna-data.html)
- [GIS på Länsstyrelserna – Geodatakatalogen](https://gis.lansstyrelsen.se/geodata/geodatakatalogen/)
- [GIS på Länsstyrelserna – Geodata och tjänster](https://gis.lansstyrelsen.se/geodata/)

## 2. Vindbrukskollen

### Datat och kartbakgrunden måste separeras

Energimyndighetens information anger att Vindbrukskollens data är öppna och kan hämtas genom bland annat Excel-export och SHAPE-filer. Samma information anger uttryckligen att bakgrundskartorna är upphovsrättsskyddade och att annan användning än i tillståndsprocessen kräver särskilt tillstånd från berörda rättighetsinnehavare.

I Skogs källregister finns ett namngivet landbaserat dataset med en separat metadataregistrering som anger CC0. Denna CC0-bedömning gäller den namngivna datamängden, inte automatiskt hela Vindbrukskollen, alla andra kartlager eller bakgrundskartorna.

### Rekommenderad hantering

- Använd nedladdningsbara geometrier/attribut från det CC0-registrerade datasetet.
- Lagra inte skärmbilder eller renderade kartbilder från Vindbrukskollens bakgrundskarta för återpublicering.
- Bygg kundkartor med egen eller separat licensierad bakgrundskarta.
- Spara datasetets metadata-ID, metadatarevision, hämtningstid, källversion och licens.
- Behandla användar-/projektörsrapporterade uppgifter som källdata med varierande kvalitet; CC0 säger inget om faktamässig riktighet.
- Håll projekteringsområden, enskilda verk, byggda verk och solcellsparker som separata objekttyper och statusar.

Källor:
- [Energimyndigheten – Vindbrukskollen](https://www.energimyndigheten.se/energisystem-och-analys/el--och-varmeproduktion/vindkraft/vindbrukskollen/)
- [Länsstyrelsernas geodatakatalog](https://gis.lansstyrelsen.se/geodata/geodatakatalogen/)
- [Metadata för namngivet landbaserat Vindbrukskollen-dataset](https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=c816bd1e-bc6c-487f-a962-770f05f677b6_C)

## 3. Naturvårdsregistret – skyddade områden

Naturvårdsregistret tillhandahåller nationella tjänster:
- WMS för kartvisning.
- WFS för nedladdning.
- REST API med GeoJSON.
- Nedladdningsbara data och dokumentation per skyddstyp.

Tjänsten omfattar flera olika skyddstyper och statusar. Metadata beskriver bland annat att beslut registreras löpande, att Skogsstyrelsens biotopskyddsbeslut överförs två gånger i veckan och att tjänsten uppdateras varje natt. Metadata anger också att tillträdesförbud har ofullständig ajourföring i vissa län.

**Viktig rättighetsreservation:** Den centrala tjänsteposten i Länsstyrelsernas Planeringskatalog anger "Villkor okända". Naturvårdsverket anger generellt att myndighetens öppna data får användas fritt, men också att när informationsansvaret ligger hos annan organisation kan den organisationens upphovsrätt tillkomma. Därför ska Skog inte sätta hela Naturvårdsregistret till CC0 enbart på grund av att WFS/REST är öppna. Enskilda lagerposter kan ange CC0; den kontrollen måste göras per datamängd och skyddstyp.

### Rekommenderad hantering

- Hämta och granska dokumentet "Beskrivning av öppna data" och metadata för varje nedladdningsbart lager.
- Registrera om informationsansvarig är Naturvårdsverket, Länsstyrelsen, Skogsstyrelsen eller annan producent.
- Kräv uttryckligt CC0/CC BY eller annan tydlig licens innan kommersiell återpublicering av respektive lager.
- Använd inte WMS-bilder som ersättning för licensierade vektordata.
- Spara fält för beslutsstatus, skyddstyp, beslutsdatum, laga-kraft-status och källans uppdateringstid. Skilj gällande beslut från beslutade/överklagade men ej lagakraftvunna objekt.
- Märk tillträdesförbud med täcknings-/aktualitetsreservation. Avsaknad av ett objekt får inte tolkas som att tillträde är tillåtet.
- Bevara historik som versionshistorik över myndighetsregistret, inte som en garanti för rättsligt gällande status idag.

Källor:
- [Planeringskatalogen – Öppna tjänster för data i naturvårdsregistret](https://ext-geodatakatalog-forv.lansstyrelsen.se/PlaneringsKatalogen/GetMetaDataById?id=50FE77C1-43A0-445A-B56C-6B729E21DC67_C)
- [Naturvårdsverket – Miljödata och öppna data](https://www.naturvardsverket.se/verktyg-och-tjanster/data-databaser-och-sokregister/tillgangliggorande-av-oppna-data/)
- [Naturvårdsregistret – beskrivning av öppna data (PDF)](https://geodata.naturvardsverket.se/nedladdning/naturvardsregistret/Naturvardsregistret_beskrivning_av_oppna_data.pdf)
- [Naturvårdsregistret WFS](https://geodata.naturvardsverket.se/naturvardsregistret/wfs?)
- [Naturvårdsregistret REST API](https://geodata.naturvardsverket.se/naturvardsregistret/rest/v3)

## 4. Publiceringsregler för kartprodukter i Skog

| Komponent | Standardbeslut | Villkor för kundvisning |
|---|---|---|
| CC0-geometri och attribut | Tillåt | Exakt datamängd/lager verifierat och metadata arkiverat |
| CC BY-geometri och attribut | Tillåt med attribution | Attribution, licenslänk och ändringsmarkering |
| WMS-renderad bild | Blockera som råmaterial för egen återpublicering om inte uttryckligt tillstånd/licens | Kontrollera både karttjänst och alla lager/bakgrundskomponenter |
| Bakgrundskarta/ortofoto | Blockera utan separat licens | Egen licens eller uttryckligt tillstånd |
| Blandad tjänst med okända lagerlicenser | Blockera extern publicering | Utred lager för lager |
| Historisk snapshot | Samma licenskrav som originaldata | Arkivera licens- och metadatarevision tillsammans med snapshot |

## 5. Slutsats

1. Länsstyrelsernas WMS-data kan ofta återanvändas, men lagrens metadata och rättighetsinformation ska styra.
2. Vindbrukskollens namngivna CC0-datamängd kan användas kommersiellt; bakgrundskartorna ska hållas utanför.
3. Naturvårdsregistrets öppna tjänster är tekniskt tillgängliga, men den centrala tjänsteposten anger okända villkor. Licensen måste därför verifieras på exakt nedladdningsbart lager innan kommersiell publicering.
4. För Skog bör alla snapshots bära licensmetadata, källversion, metadatarevision och producentkedja. Det är särskilt viktigt för historik och kundexport.
