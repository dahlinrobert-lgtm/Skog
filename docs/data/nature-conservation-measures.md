# Naturvårdande skötsel – första historikspåret

## Källa och avgränsning

Första källan är Länsstyrelsernas publika Life2Taiga FeatureServer-lager:

- Lager: \`WP_2_Restoration_measures\` (FeatureServer/13)
- URL: https://ext-hostedgeodata.lansstyrelsen.se/arcgis/rest/services/Hosted/Life2Taiga_v3_Extern/FeatureServer/13
- Projektinformation: https://www.lansstyrelsen.se/vastmanland/natur-och-landsbygd/skyddad-natur/skotsel-av-skyddad-natur/naturvardsbranning/life2taiga.html

Lagret innehåller restaureringsåtgärder inom Life2Taiga. Projektet omfattar 17 svenska länsstyrelser och finska Metsähallitus, men lagret är **inte** ett heltäckande nationellt register över all naturvårdande skötsel. Det ska inte beskrivas som nationell täckning.

## Vad vi kan läsa ut

Den befintliga fältinventeringen i \`lifetaiga-field-inventory.json\` visar bland annat:

- \`globalid\`: stabil identitet som används för historisk spårning.
- \`objectid\`: tekniskt käll-ID; inte historisk identitet.
- \`symbology\`: kategorier som exempelvis kontrollerad bränning och brandefterliknande åtgärder.
- \`area_ha\`, \`artal\`, \`atgardsdatum\`, \`lan\`, \`namn\`, \`arter\` och flera åtgärdsspecifika fält.

Fältnamn är inte i sig bevis för status. Vi bevarar samtliga källattribut och geometrier, men drar inte automatiskt slutsatsen att en åtgärd är genomförd utifrån \`artal\`, \`atgardsdatum\` eller kategorin. Planerad, pågående och genomförd status måste stödjas av dokumenterad källsemantik.

## Arkivering

- Fullständigt nuläge: \`data/lifetaiga-naturvardsatgarder/current.json.gz\`
- Append-only förändringshistorik: \`data/lifetaiga-naturvardsatgarder/history/events.jsonl\`
- Senaste körningsrapport: \`data/lifetaiga-naturvardsatgarder/latest-report.json\` (Actions-artifact)
- GlobalID används för att identifiera objekt mellan körningar.
- Nya, ändrade och från källan försvunna objekt registreras separat.
- Första körningen skapar baslinje; den räknar inte alla befintliga objekt som nya händelser.
- Exporten kontrollerar att samtliga annonserade OBJECTID hämtats och att GlobalID är unika.

Ett objekt som inte längre returneras markeras endast \`removed_from_source\`. Det betyder inte att åtgärden har avbrutits eller att geografin har upphört att gälla.

## Nästa verifiering

1. Kontrollera första livekörningens antal objekt, kategorifördelning och länsfördelning.
2. Kontrollera att geometrier och GlobalID är kompletta och stabila.
3. Jämför minst två dagliga snapshots innan vi bedömer förändringshistoriken.
4. Undersök därefter fler myndighetskällor för andra typer av naturvårdande skötsel, utan att blanda in produktionsinriktade skogsbruksåtgärder.
