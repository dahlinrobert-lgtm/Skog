# Lagringsregister – vad finns var?

**Senast inventerat:** 2026-11-17  
**Status:** Första samlade inventering. Poster märkta *bekräftad* bygger på känd sökväg eller verifierad projekt-/molnkonfiguration. *Delvis känd* betyder att projektet eller lagringen är känd men exakt sökväg/container ännu inte är dokumenterad. *Ej inventerad* betyder att platsen måste kontrolleras.

> **Syfte:** Detta är huvudregistret för var projekt, originaldata, historik, säkerhetskopior och arbetskopior lagras. Det ersätter inte källregistret i `data-platform/config/sources.yml` eller datakälledokumentationen i `docs/SKOGSKOLL_DATA_OVERVIEW.md`.

## 1. Lagringsprincip – önskat normalläge

| Plattform | Ska användas till | Ska normalt inte användas till |
|---|---|---|
| **GitHub** | Källkod, skript, tester, dokumentation, konfiguration, små manifest och scheman | Stora rådatafiler, rasterarkiv och frekventa stora snapshots |
| **Azure Blob Storage** | Automatiserade historiska arkiv, stora snapshots, rådata och långtidslagring för produktionsflöden | Aktiv kodutveckling |
| **OneDrive** | Originalfiler, manuella datauttag, större arbetsmaterial och överföring mellan dator och moln | Enda kopian av kritisk historik när Azure-arkivering är etablerad |
| **Datorns disk** | Klonade Git-repon, tillfällig bearbetning, cache och lokala arbetskopior | Enda kopian av data som ska bevaras |
| **USB-minne** | Frånkopplad backup/återställningskopia | Primär arbetsplats eller enda arkiv |

**Prioritering:** Molnet ska vara primär lagringsmiljö. GitHub ska bära kod och dokumentation; Azure ska bära automatiserade stora/historiska dataarkiv; OneDrive ska bära original och manuella arbetsfiler. Lokala kopior ska kunna återskapas från molnet så långt det är praktiskt möjligt.

## 2. Översikt – kända lagringsplatser

| ID | Projekt/innehåll | Plattform | Plats | Status | Kommentar |
|---|---|---|---|---|---|
| GH-01 | Skog / Skogskoll | GitHub | [dahlinrobert-lgtm/Skog](https://github.com/dahlinrobert-lgtm/Skog) | Bekräftad | Kod, workflows, dokumentation, källregister, vissa snapshots och analysresultat. Undvik att lägga till stora rådatafiler. |
| GH-02 | Mark – land market intelligence | GitHub | [dahlinrobert-lgtm/mark](https://github.com/dahlinrobert-lgtm/mark) | Bekräftad | Privat repo. Storleken i GitHub-metadata var cirka 404 MB den 2026-11-15; bör granskas för stora filer/historik. |
| GH-03 | Gräsmyr markpilot | GitHub | [dahlinrobert-lgtm/mark_gr-smyr](https://github.com/dahlinrobert-lgtm/mark_gr-smyr) | Bekräftad | Privat repo. |
| GH-04 | Älgdata Gräsmyr | GitHub | [dahlinrobert-lgtm/alg-grasmyr](https://github.com/dahlinrobert-lgtm/alg-grasmyr) | Bekräftad | Publikt repo med insamlingsflöden och dokumentation för älgdata. |
| GH-05 | NVR / viltolyckor | GitHub | [dahlinrobert-lgtm/bear-data](https://github.com/dahlinrobert-lgtm/bear-data) | Bekräftad | Privat repo. Kod, validering, tester och dokumentation för NVR. Stora original-CSV ska inte läggas i Git. |
| GH-06 | RTS-spel | GitHub | [dahlinrobert-lgtm/rts](https://github.com/dahlinrobert-lgtm/rts) | Bekräftad | Privat repo. |
| GH-07 | Luleå-data | GitHub | [dahlinrobert-lgtm/Lulea-data](https://github.com/dahlinrobert-lgtm/Lulea-data) | Bekräftad | Repo finns; innehåll och aktiv status behöver inventeras. |
| GH-08 | Luleå-data 2 | GitHub | [dahlinrobert-lgtm/Lulea-data2](https://github.com/dahlinrobert-lgtm/Lulea-data2) | Bekräftad | Repo finns; innehåll och aktiv status behöver inventeras. |
| GH-09 | Befolkningsanalys | GitHub | [dahlinrobert-lgtm/analys-befolkning](https://github.com/dahlinrobert-lgtm/analys-befolkning) | Bekräftad | Repo finns; innehåll och aktiv status behöver inventeras. |
| GH-10 | Ny befolkningsanalys | GitHub | [dahlinrobert-lgtm/ny-analys-av-befolkning](https://github.com/dahlinrobert-lgtm/ny-analys-av-befolkning) | Bekräftad | Repo finns; innehåll och aktiv status behöver inventeras. Repo-storlek cirka 9 MB enligt GitHub-metadata. |
| GH-11 | Länsstyrelsernas diarier – månadsvisa observationer | GitHub | `dahlinrobert-lgtm/Skog/data/lansstyrelsen-diary/` | Bekräftad | Två avgränsade Norrbottenpiloter publicerade 2026-11-16: oktober och september 2026, kategori B, totalt tolv immutabla snapshots och tolv manifestposter. Nollresultatsnapshots är 0-byte-filer med separata manifestposter. En separat nationell discovery-workflow finns i `main` efter merge av PR #406; den sparar endast diagnostikartefakter i 30 dagar och skriver inte till snapshotarkivet. Workflowen är ännu inte live-testad. Se `docs/lansstyrelsen-monthly-snapshot-architecture.md`. Fortfarande inte nationell täckning eller godkännande för kundvisning. |
| GH-12 | Viltdata – nationell avskjutningsstatistik snapshot | GitHub Actions artifact | Workflow `.github/workflows/viltdata-kill-statistics-manual.yml`; run [44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179); artifact ID `14470426808` | Live-verifierad 2026-11-18 | Snapshot `20261118T204420Z`, 49 arter, 21 län, 550/550 statistikförfrågningar; 552 filer SHA-256-verifierade. Artifact 423 726 byte, SHA-256 `e7c4076bc5b62a0e05b58df6803b416e57e38b255a34b273efdc3e2678a2f069`, retention till 2026-12-18. Temporärt granskningsunderlag, inte permanent historik/backup; Azure-skrivning och återläsning återstår. |

| GH-13 | Viltdata – Azure-arkivverktyg | GitHub + Azure Blob | `scripts/viltdata_azure_archive.py`, `tests/test_viltdata_azure_archive.py`, `.github/workflows/viltdata-azure-archive.yml`; container `viltdata-kill-statistics` i `stskogkolldata` | Mergad i main 2026-11-18 (PR #427) | Manuell upload/audit/restore finns i main. PR-CI #476 passerade 322 tester (8 arkivtester); bred main-CI #483 passerade 322 tester. Ingen riktig Viltdata-originaldata uppladdad. Upload kräver `rights_approved=true` (default false). Ingen schemaläggning. Azure live upload/audit/restore, region och RBAC-roll/scope ej verifierade. Rättighetsbedömning krävs före arkivering. |

### GitHub – lokal arbetskopia

| Projekt | Lokal sökväg | Status |
|---|---|---|
| Skog | `C:\Users\dahli\GitHub\Skog` | Bekräftad 2026-11-14 |
| Övriga repo-kloner | `C:\Users\dahli\GitHub\...` | Delvis känd – exakta kloner/sökvägar ska inventeras på datorn |

GitHub-repots storlek i API-metadata är en grov repoindikator, inte en fullständig inventering av enskilda filer, LFS-objekt eller externa artefakter.

## 3. OneDrive

| ID | Projekt/innehåll | Sökväg | Status | Kommentar |
|---|---|---|---|---|
| OD-01 | NVR viltolyckor – original och arbetsmaterial | `OneDrive\Skogskoll\viltolycka_NVR` | Bekräftad | OneDrive rapporterade cirka 4,16 GB för mappen vid inventeringen 2026-11-15; innehåller originalexport, arbetsfiler, historik, testarkiv och diagnostik. |
| OD-02 | NVR årsuppdelade arbetsfiler | `OneDrive\Skogskoll\viltolycka_NVR\working\split-2015-2026` | Bekräftad | Cirka 107,2 MB; 14 objekt enligt OneDrive-metadata. |
| OD-03 | NVR historiska legacy-snapshots | `OneDrive\Skogskoll\viltolycka_NVR\history\legacy-event-snapshots` | Bekräftad | Cirka 18,7 MB; 2 objekt vid inventeringen. 2019-staging hade tidigare ett Windows-behörighetsfel; kontrollera aktuell status innan flytt/radering. |
| OD-04 | Skogsstyrelsens skogliga grunddata/volymraster | `OneDrive\Skogskoll\Skogliga grunddata - Volym (omdrev 1, 2008-2016)` | Bekräftad | Cirka 2,77 GB; 20 objekt enligt OneDrive-metadata. |
| OD-05 | Skogsstyrelsens skogliga grunddata/volymraster | `OneDrive\Skogskoll\Skogliga grunddata - Volym (omdrev 2, 2018-2025)` | Bekräftad | Cirka 4,66 GB; 21 objekt enligt OneDrive-metadata. |
| OD-06 | Skogsstyrelsens skogliga grunddata/volymraster | `OneDrive\Skogskoll\Skogliga grunddata - Volym (omdrev 3, 2025-)` | Bekräftad | Cirka 503 MB; 9 objekt enligt OneDrive-metadata. |
| OD-07 | NVDB/Lastkajen – nationella vägnät | `OneDrive\Skogskoll\Lastkajen` | Bekräftad | 21 länsvisa GeoPackage-ZIP i `Länsfiler NVDB data`, totalt 10 677 114 317 byte. Read-only metadata-/schemakontroll av `NVDB_DK_O_111_Vagnummer`: 21/21 compatible, 456 444 features totalt, obligatoriska fält finns. Distribuerat geometristickprov 2026-11-16/17: 500 per län (10 500 totalt), EPSG:3006, LineString, samtliga giltiga; 0 null/tomma/ogiltiga/fel. Inspektionsskript `inspect_nvdb_geometry_national.py` och JSON-rapport `nvdb-geometry-national-sample-20261116.json` finns i samma OneDrive-mapp. Stickprovet verifierar inte samtliga features eller fullständig nätverkstäckning. Separat `uploaded gpkg file\Norrbottens_län.gpkg` (1 203 462 144 byte) finns; relationen till ZIP-originalet är inte verifierad. |
| OD-08 | OpenStreetMap Sverige – original och derivat | `OneDrive\Skogskoll\openstreetmap` | Bekräftad | Cirka 1,11 GB; innehåller Sverige-PBF cirka 955 MB samt filtrerade PBF-filer, fältinventeringar och manifest. |
| OD-09 | Lantmäteriet – adresser och ortnamn | `OneDrive\Skogskoll\lantmateriet` | Bekräftad | Cirka 228 MB; underkatalogerna `belagenhetsadresser` och `ortnamn`. |
| OD-10 | Löpande lokala inventeringsrapporter | `OneDrive\Skogskoll\_inventory` | Bekräftad | Ny molnmapp skapad 2026-11-15 för JSON- och Markdownrapporter från PowerShell-skriptet. |
| OD-11 | Rovbase – originaluttag, kvalitetskontroll och valideringsskript | `OneDrive\Skogskoll\Rovbase` | Bekräftad 2026-11-18 | Originaluttaget `raw/rovbase_originaluttag_2026-11-18.zip` (65 735 567 byte; SHA-256 i kvalitetsrapporten) bevaras oförändrat. `quality/` innehåller Markdown-/JSON-rapport, ursprunglig och detaljerad årsvis fullständighets-CSV (162 art-årsrader), RT90-gransknings-CSV för 35 poster samt `validate_rovbase_geography.py`. `processed/` skapad men ännu tom i väntan på polygonvalidering. Totalt 15 561 poster i fyra artfiler. |

**NVR-regel:** Originalexporten ska bevaras oförändrad. GitHub innehåller kod, tester, dokumentation och manifest – inte den stora råexporten. SHA-256 och uttagsmetadata ska följa original och arkivkopior.

### OneDrive – verifierade detaljer i NVR-arbetsytan (2026-11-15)

Under `OneDrive\Skogskoll\viltolycka_NVR\working` finns bland annat `lulea-police-nvr` (cirka 47 MB), `nvdb-vagnummer` (cirka 185 MB), `ortnamn-deso-2025` (cirka 12 MB), `ortnamn-source` (cirka 156 MB), `split-2015-2026` (cirka 107 MB), samt separata restore-testmappar. Dessa är arbets-/testytor och ska inte automatiskt betraktas som auktoritativa arkiv.

I `history` finns `legacy-events-2015-2021`, `legacy-event-snapshots`, `runs` och `state`. Test- och restore-kopior ska hållas isär från produktionshistoriken.

**Storleksnotering:** OneDrive rapporterar mappstorlekar inklusive innehåll. Mappstorlekar ska inte summeras med alla underliggande filer en gång till. Storlekarna är ögonblicksbilder från inventeringsdatum och kan ändras.


## 4. Azure Blob Storage

| ID | Projekt/innehåll | Konto/region | Container | Status | Kommentar |
|---|---|---|---|---|---|
| AZ-01 | Kungjort – råarkiv | `stskogkolldata` / Sweden Central | `kungjort-raw` | Bekräftad | Privat container. JSONL.GZ-arkiv har migrerats med SHA-256-verifiering och återstartssäker överföring. |
| AZ-02 | Kungjort – ändringar | `stskogkolldata` / Sweden Central | `kungjort-changes` | Bekräftad | Privat container för förändrings-/deltaarkiv. |
| AZ-03 | Kungjort – metadata och tillstånd | `stskogkolldata` / Sweden Central | `metadata` | Bekräftad | Privat container; bland annat kontroll-/state-metadata. |
| AZ-04 | Viltdata – avskjutningsstatistik | `stskogkolldata` / region ännu ej avstämd (`westus2` visades av Azure CLI vid login) | `viltdata-kill-statistics` | Container skapad; syntetisk write/readback verifierad | GitHub Actions #44401688469 skapade containern och skrev/läste syntetisk payload + manifest. 235 bytes, SHA-256 `3e5aaf7b3ce1607252a07b3bf1b7959d0c556f805aff3847666aa29a4a325063`. OIDC-identiteten kunde skapa container och skriva/läsa blobbar. Exakt RBAC-roll/scope samt faktisk Storage Account-region ska verifieras i Azure Portal. PR-branch `feat/viltdata-azure-snapshot-archive` innehåller ännu ej live-verifierad upload/audit/restore-kod; inga Viltdata-original har laddats upp. Rättighetsbedömning krävs före historisk arkivering. Se `docs/viltdata-azure-storage.md`. |

**Andra Azure-flöden att kartlägga:** Skog-repot innehåller workflows för polis-/viltolyckedata, Azure-backfill, audit och restore. Exakta konton, containrar, prefix och aktuell produktionsstatus är ännu inte verifierade i detta register. Lägg inte in hemligheter, SAS-token, connection strings eller credentials här.

## 5. Lokal dator och USB

| ID | Innehåll | Plats | Status | Åtgärd |
|---|---|---|---|---|
| PC-01 | Skog-repo | `C:\Users\dahli\GitHub\Skog` | Bekräftad | Lokal utvecklingskopia. |
| PC-02 | Lokalt inventeringsskript | `scripts/inventory-local-storage.ps1` i Skog-repot | Bekräftad | Read-only inventering av valda rötter och valfritt USB. Rapporter sparas som standard i OneDrive `Skogskoll\_inventory` om OneDrive-synkroten finns. |
| PC-03 | GitHub-kloner på datorn | `C:\\Users\\dahli\\GitHub` | Bekräftad 2026-11-15 | Lokal inventering: 8 523 filer, cirka 2,396 GB. Omfattar samtliga filer under GitHub-katalogen, inte bara Skog-repot. |
| PC-04 | OneDrive-synkad Skogskoll | `C:\\Users\\dahli\\OneDrive\\Skogskoll` | Bekräftad 2026-11-15 | Lokal inventering: 385 filer, cirka 26,052 GB. Avser den lokalt synkade/åtkomliga mappens innehåll vid inventeringstillfället. |
| USB-01 | Flyttbar enhet D: | `D:\\` | Bekräftad som flyttbar enhet 2026-11-15 | Lokal inventering: 1 295 filer, cirka 3,211 GB. Volymnamn, fysisk enhetstyp och backupinnehåll behöver fortfarande identifieras innan den kan klassas som verifierad USB-backup. |
| PC-05 | Övriga diskar, nedladdningar och temporära data utanför ovanstående rötter | Datorns övriga diskar | Ej inventerad | Den första körningen omfattade endast GitHub, OneDrive\\Skogskoll och den detekterade flyttbara enheten D:. |

**Viktigt:** En lokal fil eller USB-kopia räknas inte som säkerhetskopia förrän den är identifierad, går att läsa och har jämförts med en känd originalkopia (helst SHA-256 för viktiga arkiv).

### Lokal inventering – verifierad baslinje 2026-11-15

PowerShell-körningen på datorn ROBERT slutfördes utan fel och skapade JSON- och Markdownrapporter i `OneDrive\\Skogskoll\\_inventory`. Sammanfattningen var:

| Inventerad rot | Antal filer | Storlek |
|---|---:|---:|
| `C:\\Users\\dahli\\GitHub` | 8 523 | 2,396 GB |
| `C:\\Users\\dahli\\OneDrive\\Skogskoll` | 385 | 26,052 GB |
| `D:\\` (detekterad flyttbar enhet) | 1 295 | 3,211 GB |
| **Totalt** | **10 203** | **31,659 GB** |

Detta var första baslinjen (`baseline`), med 0 inventeringsfel. Rapporten är en inventering av dessa tre lokala rötter – den är inte en fullständig inventering av hela datorn eller av allt innehåll i OneDrive-molnet. JSON-rapporten innehåller filmetadata per fil; SHA-256 var inte aktiverat. Fördelningen på första katalognivå visar att GitHub består av `Skog` (3 776 filer, cirka 1,504 GB) och `bear-data` (4 747 filer, cirka 1,069 GB). På D: är `skogskoll` och `X-JOBB` de klart största katalogerna. Inventeringen visar filstorlek och sökväg, men bevisar inte att kopior är identiska eller att någon av dem är en fungerande backup.

## 6. Vad som ska uppdateras när lagring ändras

Varje ny eller ändrad datamängd ska få en rad i detta register. Uppdateringen ska ske i samma arbetsmoment/PR som inför den nya lagringsplatsen, inte lämnas till ett senare tillfälle.

För varje post dokumenteras:
- **Vad:** projekt, datamängd, filtyp eller arkiv.
- **Var:** plattform, konto/repo, container, mapp och prefix.
- **Roll:** original, råarkiv, historik, bearbetad data, kod, arbetskopia eller backup.
- **Status:** aktiv, planerad, flyttad, ersatt, avvecklad eller behöver verifieras.
- **Ägare/ansvar:** projekt eller pipeline som använder lagringen.
- **Senast verifierad:** datum då platsen faktiskt kontrollerades.
- **Integritet:** manifest/checksumma när det är relevant.
- **Kopior:** var ytterligare kopior finns och vilken som är auktoritativ.

### Livscykelregler

1. **Ny lagring:** lägg till en ny ID-rad och ange om det är original eller kopia.
2. **Flytt:** ändra inte bara sökvägen. Markera den gamla platsen som flyttad/avvecklad och dokumentera ny plats samt flyttdatum.
3. **Ändring/ny version:** behåll historiken och ange versions-/snapshotprincip. Skriv inte över ett historiskt original.
4. **Radering:** ta inte bort registerposten. Markera den som avvecklad/raderad, ange datum och om arkivkopia finns.
5. **Backup:** ange separat var backupen finns, när den senast verifierades och hur återställning testats.
6. **Osäker plats:** märk *ej inventerad* eller *delvis känd* – gissa aldrig en sökväg.

## 7. Lokal inventering – användning

Skriptet `scripts/inventory-local-storage.ps1` är read-only och skapar en tidsstämplad JSON-rapport samt en kort Markdownrapport. Standardläget inventerar GitHub-kloner under `$HOME\GitHub` och `Skogskoll` under OneDrive-synkroten om de finns. USB-enheter kan inkluderas uttryckligen.

Exempel i PowerShell från Skog-repots rot:

```powershell
.\scripts\inventory-local-storage.ps1 -IncludeRemovableDrives
```

För en begränsad inventering av särskilda mappar:

```powershell
.\scripts\inventory-local-storage.ps1 -Roots @('C:\Users\dahli\GitHub','D:\Skogskoll') -OutputDirectory 'C:\Temp\storage-inventory'
```

Rapporter sparas som standard i OneDrive `Skogskoll\_inventory` när OneDrive-synkroten hittas, annars i `$HOME\storage-inventory`. Skriptet jämför med föregående rapport och klassar nya, ändrade och saknade filer. SHA-256 är avstängt som standard för att undvika onödig belastning. Aktivera endast vid behov och använd storleksgräns:

```powershell
.\scripts\inventory-local-storage.ps1 -IncludeRemovableDrives -HashFiles -MaxHashBytes 268435456
```

Installera daglig körning efter att Skog-repot har uppdaterats lokalt:

```powershell
.\scripts\install-local-storage-inventory-task.ps1
```

Standardtid är 21:00 lokal tid. Den aktuella installeraren skapar en bakgrundsuppgift med Windows-kontots lösenord (inte PIN) så att den kan köras även när användaren är utloggad. Lösenordet efterfrågas lokalt vid installation och sparas av Windows Task Scheduler som skyddade uppgiftsuppgifter; det skrivs inte till skript eller GitHub. Uppgiften har `WakeToRun`, `StartWhenAvailable` och tillåts köras på batteri. Väckt körning ur viloläge/hibernate kräver dessutom att Windows väckningstimers är aktiverade och att BIOS/UEFI/hårdvaran stöder väckning. En helt avstängd dator kan inte startas av Windows Schemaläggaren.

**OneDrive-begränsning:** OneDrive-synkklienten kör normalt inte i en utloggad session. Bakgrundsuppgiften skriver rapporterna till den lokala OneDrive-synkroniserade mappen (med profilbaserad sökvägsreserv om miljövariabeln saknas); uppladdningen till molnet sker först när OneDrive-klienten startar vid nästa inloggning. USB inventeras bara om minnet är anslutet och har en enhetsbokstav vid körningen. Ta bort schemaläggningen med `Unregister-ScheduledTask -TaskName 'Skogskoll - local storage inventory' -Confirm:$false`.

Rapporten kan innehålla personliga sökvägar och filnamn. Granska den innan den laddas upp till GitHub eller delas. Lägg inte råa inventeringslistor med privata filer i ett publikt repo.

## 8. Uppdateringsmodell och begränsningar

Detta dokument är den centrala manuella katalogen. Följande automatisering kan byggas stegvis:

- **GitHub:** workflow kan regelbundet läsa repo-/filmetadata och kontrollera att registrerade projekt och sökvägar finns. Ändringar i Git-repon kan också trigga validering.
- **Azure:** automatisk inventering av containers, blob-prefix, storlek, senaste ändring och metadata kräver en särskild read-only-identitet/roll. Den får inte kunna radera data.
- **OneDrive:** automatisk inventering kräver Microsoft Graph-åtkomst och avgränsade läsrättigheter till valda projektmappar.
- **Dator/USB:** GitHub Actions kan inte se datorns lokala diskar eller en USB-sticka. Det kräver ett lokalt PowerShell-inventeringsskript eller en schemalagd lokal körning som skickar en begränsad rapport till molnet.

**Nuvarande automationsstatus:** GitHub-, Azure-, OneDrive-, PC- och USB-platser är ännu inte samtliga kopplade till en automatisk inventering. Dokumentet ska därför inte beskrivas som automatiskt synkroniserat förrän dessa anslutningar är installerade och testade.

## 9. Ändringslogg

| Datum | Ändring |
|---|---|
| 2026-11-18 | Viltdata: manuell workflow live-verifierad. Nationell snapshot `20261118T204420Z` omfattar 49 arter, 21 län och 550/550 lyckade förfrågningar; 552 filer SHA-256-kontrollerade. Artifact ID `14470426808` med retention till 2026-12-18. Endast temporärt granskningsunderlag; Azure-lagring/återläsning återstår. |
| 2026-11-15 | Första samlade inventeringen skapad. Kända GitHub-repon, NVR-mappar i OneDrive, Kungjort-containrar i Azure samt känd lokal Skog-sökväg registrerade. |
| 2026-11-15 | OneDrive inventerat via Microsoft Graph: Skogskoll-roten, NVR, historik/arbetsytor, Omdrev 1–3, Lastkajen, OpenStreetMap och Lantmäteriet dokumenterade med rapporterade storlekar. Read-only PowerShell-skript med förändringsdetektion och installerare för daglig lokal/USB-inventering tillagda. OneDrive-mappen `_inventory` skapad. |
| 2026-11-16 | NVDB/Lastkajen: OneDrive-mappen `Lastkajen/Länsfiler NVDB data` inventerad via Microsoft Graph; 21 länsvisa GeoPackage-ZIP, 10 677 114 317 byte. Lager-/schema-/CRS-kontroll är ännu inte genomförd. Separat uppladdad Norrbotten-GPKG dokumenterad som oavstämd kopia. |
| 2026-11-16 | Länsstyrelsernas diarier: första verifierade publicerade pilotbaslinjen i Skog-repot. Körning #16 gav sex avstämda kategori B-intervall för Norrbotten oktober 2026; sex snapshotfiler och sex manifestposter publicerades i `data/lansstyrelsen-diary/`. Tre filer innehåller observationer och tre motsvarar explicita nollresultat. Endast avgränsad pilot; inte nationell täckning eller kundvisningsgodkännande. |
| 2026-11-16 | Bakgrundsinstalleraren uppdaterad för lösenordsbaserad Task Scheduler-körning vid utloggning, `WakeToRun`, missade körningar och profilbaserad OneDrive-sökväg. OneDrive-molnsynkronisering sker dock först när klienten körs efter nästa inloggning; hibernate-väckning kräver aktiverade väckningstimers och hårdvarustöd. |
| 2026-11-15 | Första lokala PowerShell-baslinjen verifierad på datorn ROBERT: 8 523 filer i GitHub (2,396 GB), 385 filer i OneDrive\\Skogskoll (26,052 GB) och 1 295 filer på flyttbar enhet D: (3,211 GB). Totalt 10 203 filer, 0 fel. D: är verifierad som flyttbar enhet men måste identifieras fysiskt innan den dokumenteras som USB-backup. JSON-granskningen visar dessutom Lastkajen 11,119 GB/24 filer och flera NVR-kopior på D:. SHA-256 saknas i baslinjen, så innehållslikhet är inte verifierad. |

---
**Arbetsregel för framtida ändringar:** När vi i ett arbetsflöde skapar, flyttar, byter namn på, ersätter eller raderar en viktig fil-/dataplats ska vi samtidigt uppdatera `docs/STORAGE_INVENTORY.md` och ändringsloggen.

## Ändringslogg

| Datum | Ändring | Underlag |
|---|---|---|
| 2026-11-17 | GH-11 uppdaterad från en till två verifierade Norrbottenpiloter (12 snapshots/manifestposter). Dokumenterat separat nationell discovery-workflow som endast lagrar tillfälliga diagnostikartefakter och inte skriver till snapshotarkivet. | GitHub Actions #16 och #17; PR #406 |
| 2026-11-17 | PR #406 mergad: nationell discovery-workflow finns nu i `main`. Den är manuell och diagnostik-only med 30 dagars artifact-retention; ingen snapshot-/manifestpublicering eller schemaläggning. Livebeteende och länsvalidering återstår. | PR #406; `.github/workflows/lansstyrelsen-national-diary-discovery.yml` |
| 2026-11-17 | NVDB/Lastkajen: read-only metadata-/schemainventering och geometristickprov verifierade för samtliga 21 länsarkiv. 456 444 metadatafeatures; 10 500 stickprovsgeometrier (500/län), EPSG:3006, LineString, samtliga giltiga och utan null/tomma/ogiltiga geometrier eller stickprovsfel. Inspektionsskript och JSON-rapport registrerade under OD-07. Fullständig geometri-/täckningsvalidering återstår. | Lokal read-only-körning; `inspect_nvdb_geometry_national.py`; `nvdb-geometry-national-sample-20261116.json` |
| 2026-11-18 | Rovbase-uttaget arkiverat i OneDrive `Skogskoll/Rovbase/raw`; `quality/` innehåller initial datakvalitetsrapport och JSON-resultat. `processed/` skapad men lämnas tom tills kvalitets- och koordinatvalidering är klar. | Rovbase originaluttag mottaget 2026-11-18; `ROVBASE_DATA_QUALITY_INITIAL.md` |
| 2026-11-18 | Rovbase: årsvis fullständighetsanalys utökad med procentandelar för sex kvalitetsvariabler (162 art-årsrader); originalarkivets SHA-256 dokumenterad. Ett read-only Python-skript för kommun-/länsvalidering mot befintligt Lantmäteriet-GPKG har lagts i `quality/`. Själva polygonkörningen återstår eftersom GPKG-binäret inte varit tillgängligt i denna körmiljö. | Rovbase kvalitetsrapport, `validate_rovbase_geography.py`, OneDrive kommunlager |


| 2026-11-18 | Rovbase: första geografiska körningen mot befintligt Lantmäteriet-GPKG slutfördes (15 561 poster). Den initiala granskningskön dominerades av ett systematiskt genitiv-s-problem i kommunnamnsmatchningen. `validate_rovbase_geography.py` uppdaterades i OneDrive med begränsad genitiv-s-ekvivalens; sex riktade normaliseringstester passerade. Korrigerad full körning återstår. Originalarkiv och första körutdata bevaras. | OneDrive `Skogskoll/Rovbase/quality/geographic-validation-2026-11-18/`; uppdaterat valideringsskript |
| 2026-11-18 | Viltdata registrerad i källregistret som pilot efter verifierad manuell nationell snapshot. GH-12 uppdaterad med körnings-ID, snapshot-ID, artifact-ID, storlek, SHA-256 och utgångsdatum. Rättigheter och permanent Azure-lagring är fortsatt ej bedömda/verifierade. | GitHub Actions #44394070179; snapshot 20261118T204420Z; artifact 14470426808 |
| 2026-11-18 | Viltdata: separat container `viltdata-kill-statistics` skapad via GitHub OIDC. Syntetisk payload och manifest uppladdade och återlästa; SHA-256/235 bytes verifierade. Azure CLI visade `westus2`, men Storage Account-resursens faktiska region och exakt RBAC-roll/scope måste fortfarande kontrolleras i Azure Portal. Inga källdata uppladdade. | GitHub Actions #44401688469; artifact 14474565285; `docs/viltdata-azure-storage.md` |


| 2026-11-18 | Viltdata: separat Azure-arkivverktyg för kompletta snapshots, djup audit och restore utvecklat i `feat/viltdata-azure-snapshot-archive`. Workflowen är manuell och upload kräver explicit rättighetsbekräftelse. PR/CI och liveverifiering återstår; inga källdata har laddats upp. | Branch `feat/viltdata-azure-snapshot-archive`; `scripts/viltdata_azure_archive.py`; workflow `.github/workflows/viltdata-azure-archive.yml` |


| 2026-11-18 | Viltdata: PR #427 mergad. Immutable upload, audit och restore finns i main. Fortsatt manuell drift; upload spärrad bakom `rights_approved=false` som standard. Inga källdata uppladdade; rättigheter och Azure-region/RBAC återstår. | PR #427, merge commit `7f4077b53ccb2d9d8308daa278d7fcb6674e79ee`; GH-13 |
