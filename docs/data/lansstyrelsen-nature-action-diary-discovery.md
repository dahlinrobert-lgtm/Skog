# Nationell upptäckt av naturvårdsåtgärder i Länsstyrelsernas diarier

## Syfte

Identifiera diarieförda ärenden i samtliga län som kan innehålla planerade, beslutade eller genomförda naturvårdsåtgärder. Denna första fas är en upptäcktsinventering och publicerar endast körningsartifact; den skriver inte till den permanenta snapshot-historiken.

## Kategorier och sökfraser

| Kategori | Sökfraser |
|---|---|
| Våtmarker och hydrologi | våtmarksrestaurering, återvätning, dikespluggning, hydrologisk restaurering, igenläggning av diken, våtmarksanläggning |
| Naturvårdande skötsel i skog | naturvårdande skötsel, frihuggning, veteranisering, skapande av död ved, restaurering lövskog, skötselåtgärder skog |
| Vattendrag | biotopvård, vattendragsrestaurering, flottledsåterställning, utrivning vandringshinder, fiskväg, lekbotten |
| Ängs- och betesmark | ängsrestaurering, betesrestaurering, naturbetesmark, slåtter, hamling, restaurering betesmark |

Sökfraserna är en första pilotlista. Träffarna ska granskas innan vi lägger till fler synonymer, för att undvika att breda ord ger stora mängder irrelevanta ärenden.

## Körning

Workflowen `.github/workflows/lansstyrelsen-nature-action-discovery.yml` körs manuellt en kategori åt gången. Den använder den befintliga webbläsarbaserade diariekoden med `Alla län`, som söker varje läns diarium separat. Varje fras valideras mot källans rapporterade antal och fullständig paginering.

Resultatet sparas som ett 30-dagars GitHub Actions-artifact. Inga diarierader läggs automatiskt till i den permanenta snapshot-historiken i denna fas.

## Tolkningsregler

- En sökträff är en kandidat, inte ett verifierat naturvårdsprojekt.
- Skilj mellan ansökan, samråd, anmälan, beslut, villkor, tillsyn, genomförande och uppföljning.
- Ett beslut eller en beviljad åtgärd är inte bevis för att åtgärden utförts.
- Sökord som slåtter, röjning, gallring och dikesrensning kräver kontext för att avgöra om det rör naturvård eller annan verksamhet.
- Geografisk plats får inte härledas från enbart diariets län eller postort. Matchning mot fastighet, naturreservat eller geodata ska sparas som separat evidens med metod och säkerhet.
- Dubbletter mellan sökfraser ska slås samman på län + diarienummer, men alla matchande fraser ska bevaras.

## Nästa steg efter pilot

1. Kör de fyra kategorierna nationellt.
2. Jämför länstäckning, antal unika diarienummer, överlappning och sökfrasernas precision.
3. Granska ett urval av ärenden i varje kategori och klassificera ärendefas.
4. Först därefter besluta vilka fraser som ska ingå i månatliga snapshots och om de befintliga snapshotschemana ska utökas.
