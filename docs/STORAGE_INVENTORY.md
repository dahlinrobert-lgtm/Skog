# Lagringsregister – vad finns var?

**Senast inventerat:** 2026-11-24  
**Status:** Första samlade inventering med kompletterande lokal miljö- och schemaläggningskontroll 2026-11-24. Inventeringen är fortfarande avgränsad; ej kontrollerade lagringsplatser är fortsatt markerade som ej inventerade. Poster märkta *bekräftad* bygger på känd sökväg eller verifierad projekt-/molnkonfiguration. *Delvis känd* betyder att projektet eller lagringen är känd men exakt sökväg/container ännu inte är dokumenterad. *Ej inventerad* betyder att platsen måste kontrolleras.

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
| GH-12 | Viltdata – nationell avskjutningsstatistik snapshots | GitHub Actions artifacts | Workflow `.github/workflows/viltdata-kill-statistics-manual.yml`; runs [44394070179](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44394070179) och [44408345762](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44408345762); artifacts `14470426808` och `14475804318` | Två kompletta körningar live-verifierade 2026-11-18 | Snapshots `20261118T204420Z` och `20261118T220720Z`; båda omfattar 49 arter, 21 län, 550/550 statistikförfrågningar och 552 SHA-256-verifierade filer. Senaste artifact 423 705 byte, ZIP SHA-256 `31ef0b6ac7c16fa524adaa9f1e5ed9037f19bd3a9cb714bdea16e6ad8264e0b2`, retention till 2026-12-18 22:24:19 UTC. Tillfälliga granskningsunderlag, inte permanent historik/backup; Azure-skrivning och återläsning återstår. |

| GH-14 | Skog/Skogskoll – AI-projektledarens styrdokument | GitHub | `dahlinrobert-lgtm/Skog/docs/PROJECT_*.md` | Bekräftad i main 2026-11-18 (PR #431) | Sex dokument för regler/mandat, status, backlogg, roadmap, beslut och beroenden. Agenten är separat och ännu under implementation. |
| GH-15 | Skog/Skogskoll – AI-projektledaragent v1 | GitHub | `scripts/project_manager_agent.py`, `tests/test_project_manager_agent.py`, `.github/workflows/project-manager.yml`, `docs/PROJECT_MANAGER_AGENT.md` | Mergad i main 2026-11-18 (PR #432); manuell körning #5 verifierad | Read-only GitHub-inventering. Actions #44413951767: test- och inventory-jobb success; artifact #14479221503. Högst 3 sidor issues/PR och 50 workflowkörningar. Ingen schedule, LLM/API eller skrivbehörighet. |
| GH-13 | Viltdata – Azure-arkivverktyg | GitHub + Azure Blob | `scripts/viltdata_azure_archive.py`, `tests/test_viltdata_azure_archive.py`, `.github/workflows/viltdata-azure-archive.yml`; container `viltdata-kill-statistics` i `stskogkolldata` | Mergad i main 2026-11-18 (PR #427) | Manuell upload/audit/restore finns i main. PR-CI #476 och main-CI #483 passerade 322 tester vardera (8 arkivtester). Ingen riktig Viltdata-originaldata uppladdad. Upload kräver `rights_approved=true` (default false). Ingen schemaläggning. Azure live upload/audit/restore ej verifierade. Storage Account-region verifierad i Portal: `swedencentral` (Sweden Central). OIDC-tjänstehuvudnamnet `skogskoll-github-actions` har `Storage Blob Data Contributor` på Storage Account-scope (`This resource`), vilket är bredare än Viltdata-containern; samma identitet används av andra Skog-workflows. Rättighetsbedömning krävs före arkivering. |

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
| AZ-04 | Viltdata – avskjutningsstatistik | `stskogkolldata` / `swedencentral` (Sweden Central, verifierad i Azure Portal) | `viltdata-kill-statistics` | Container skapad; syntetisk write/readback verifierad | GitHub Actions #44401688469 skapade containern och skrev/läste syntetisk payload + manifest. 235 bytes, SHA-256 `3e5aaf7b3ce1607252a07b3bf1b7959d0c556f805aff3847666aa29a4a325063`. OIDC-identiteten kunde skapa container och skriva/läsa blobbar. RBAC verifierad i Azure Portal: `skogskoll-github-actions` har `Storage Blob Data Contributor` på Storage Account-scope (`This resource`), inte endast container-scope. Identiteten delas med andra Skog-workflows. Upload/audit/restore är ännu inte live-verifierade; inga Viltdata-original har laddats upp. Senaste kompletta snapshot är `20261118T220720Z`, temporärt GitHub Actions-artifact `14475804318`. Rättighetsbedömning krävs före historisk arkivering. Se `docs/viltdata-azure-storage.md`. |
| AZ-05 | Gemensam konto-/kostnadskonfiguration | `stskogkolldata` / `swedencentral` | Hela Storage Account | Verifierad i Azure Portal 2026-11-23 | Pay-As-You-Go-prenumeration aktiv; månadsbudget 200 SEK med aviseringar 50/75/90 %. Blobversionering behåller alla versioner; soft delete 14 dagar för blobbar/behållare; permanent borttagning avstängd. Azure Backup, point-in-time restore, Change Feed och immutability avstängda. LRS, TLS 1.2. Se `docs/azure-storage-operations.md`. |

**Övriga Azure-flöden:** Se respektive käll-/flödesdokumentation för polis-/viltolyckedata, backfill, audit och restore. Denna inventering av containrar och prefix är inte en fullständig inventering av varje blob. Lägg inte in hemligheter, SAS-token, connection strings eller credentials här.

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

| 2026-11-18 | Viltdata Azure: Storage Account `stskogkolldata`-region verifierad i Azure Portal som `swedencentral` (Sweden Central). IAM visar `skogskoll-github-actions` med `Storage Blob Data Contributor` på Storage Account-scope (`This resource`); identiteten delas med andra Skog-flöden, så scope ska inte ändras utan konsekvensanalys. | Användarens Azure Portal-skärmbilder; `docs/viltdata-azure-storage.md` |


| 2026-11-18 | AI-projektledarens sex styrdokument skapade i separat branch. Ingen ny extern lagringsplats eller datamängd; GitHub används för projektets styrdokument. | Branch `feature/ai-project-manager-foundation`; PR inväntar skapande/granskning |

| 2026-11-18 | Viltdata: andra kompletta nationella snapshotet verifierat. Snapshot `20261118T220720Z`, 49 arter, 21 län, 550/550 statistikförfrågningar, 552 rå-/metadatafiler SHA-256-verifierade och 73 255 datapunkter. Artifact ID `14475804318`, 423 705 byte, ZIP-SHA-256 `31ef0b6ac7c16fa524adaa9f1e5ed9037f19bd3a9cb714bdea16e6ad8264e0b2`, retention till 2026-12-18 22:24:19 UTC. | GitHub Actions #44408345762; manifest SHA-256 `ed7937c8f83657b51af98f88566cce675555d0a4d017111f3fb7a24ecdc72088` |
| 2026-11-18 | AI-projektledarens agent v1 mergad och liveverifierad: read-only inventering, tester och manuell artifactkörning #5. Artifact #14479221503, 31 063 byte; ingen ny extern datalagring utöver tidsbegränsat Actions-artifact. | PR #432; Actions #44413951767 |


## Planerad lagring – AI-projektledare v2b (ej aktiv)

| ID | Innehåll | Planerad plats | Beslut | Status |
|---|---|---|---|---|
| GH-16 | Projektledaragentens inventeringshistorik | Privat Skog-repo, separat branch `project-manager-history`, kataloger per `run_id` | Användaren har valt Git-branch och indefinite retention 2026-11-19 | **Planerad, ej skapad/aktiverad.** Ingen historikdata finns sparad där. Kräver separat persistence-jobb, begränsad skrivbehörighet, branchskydd, syntetisk verifiering och separat godkännande före aktivering. |

Indefinite retention betyder att ingen automatisk gallring eller tidsbaserad radering ska byggas in. Årlig manuell översyn rekommenderas, men innebär inte automatisk radering. Denna planerade post får inte beskrivas som aktiv lagring förrän branch, skydd och readback/restore har verifierats.


| 2026-11-23 | Gemensam Azure-konfiguration dokumenterad: aktiv Pay-As-You-Go-prenumeration, 200 SEK månadsbudget med 50/75/90 %-aviseringar, blobversionering och 14 dagars soft delete. Azure Monitor visade cirka 755–770 MiB och 310 transaktioner under vald 24-timmarsperiod. | `docs/azure-storage-operations.md`; användarens Azure Portal-skärmbilder |


## 7. Lokal utvecklingsmiljö och daglig inventering – verifierat 2026-11-24

Denna komplettering bygger på användarens read-only PowerShell-utdata, lokal Git-status och statisk granskning av `scripts/inventory-local-storage.ps1` från aktuell `main`. Ingen lokal inventeringsrapport har hämtats eller publicerats i GitHub i denna kontroll.

### 7.1 Utvecklingsmiljö

| Komponent | Verifierat läge |
|---|---|
| Windows | Windows 10 Home enligt produktfältet; OS build 26200 |
| Windows PowerShell | 5.1.26100.9818; `pwsh` hittades inte i PATH |
| Git | 2.56.0.windows.4 |
| Python huvudmiljö | Python 3.12.10, global installation |
| Python extra installation | Python 3.15.2, separat global installation |
| Node.js / npm | Båda hittades i PATH |
| GIS-kommandon | `ogr2ogr`, `gdalinfo` och `qgis` hittades inte i PATH; installation utanför PATH är inte utesluten |
| R | `Rscript` hittades inte i PATH |

Python 3.12 hade 42 installerade paket vid kontrollen. De åtta direkta beroendena i Skogs `requirements.txt` var installerade inom angivna versionsintervall; `pip check` rapporterade inga trasiga beroenden och `pip install --dry-run --no-index -r requirements.txt` visade samtliga krav som redan uppfyllda. Centrala paket inkluderar GeoPandas 1.2.0, Shapely 2.1.2, Pyogrio 0.13.0, PyProj 3.7.2, Pandas 3.1.1, NumPy 2.5.4, DuckDB 2.0.0 och Playwright 1.65.2.

Python 3.15 hade 8 installerade paket och klarade sin egen `pip check`, men kunde inte uppfylla Skogs fullständiga `requirements.txt` i lokal no-index-kontroll: Shapely saknades. Python 3.15 är därför inte verifierad som Skogs utvecklingsmiljö. Ingen `.venv`, `venv`, `env` eller `conda`-katalog hittades i Skogs projektträd. Endast `requirements.txt` hittades bland de kontrollerade vanliga beroendefilerna.

### 7.2 Lokala Git-projekt och arbetskataloger

| Repo | Lokal branch vid kontroll | Spårade filer | Ospårade poster |
|---|---|---|---:|
| Skog | `main`, synkroniserad med `origin/main` | Inga spårade ändringar rapporterade | 34 |
| bear-data | `audit/nvr-rt90-coordinate-recovery`, spårade origin-branch | Inga spårade ändringar rapporterade | 15 |

De ospårade posterna inkluderar lokala analysprogram, CSV/JSON-resultat, datauttag, cachekataloger och backupfiler. De har inte automatiskt klassats som skräp och får inte raderas eller läggas till i Git utan separat granskning. Det fanns ingen aktiv PowerShell-jobbpost i den aktuella sessionen.

### 7.3 Avgränsad lokal filinventering

| Område | Observerat innehåll | Omfattning |
|---|---|---:|
| `Skog/data` | 466 GZ, 2 576 JSON, 44 JSONL, 3 ZIP, 1 Parquet, 5 CSV, 8 NPZ, 3 MD och 1 GeoJSON | 3 107 filer, cirka 702,86 MiB |
| `Skog/data-platform` | YAML, Python, JSON, Markdown och en Python-bytecodefil | 11 filer |
| `road_network_endpoint_analysis` | CSV | 3 filer, cirka 9,08 MiB |
| `data/viltdata` | Ospårad lokal katalog | 2 154 filer, cirka 4,95 MiB |
| `data/police_events/external_import` | Ospårad lokal katalog | 1 fil, cirka 14,43 MiB |

Storlekarna kommer från PowerShells `Length / 1MB` och är avrundade. Sökningen var begränsad till angivna projektkataloger och är inte en fullständig diskinventering. Filinnehåll öppnades inte.

### 7.4 Befintlig Windows-schemaläggning

Aktiviteten `Skogskoll - local storage inventory` finns redan registrerad i Windows Task Scheduler.

| Egenskap | Verifierat värde |
|---|---|
| Status | Ready |
| Trigger | Dagligen, var 1 dag |
| Start | 2026-11-16 kl. 21:00 lokal tid |
| Körprogram | `powershell.exe` |
| Skript | `scripts/inventory-local-storage.ps1` |
| Senaste kontrollerade körning | 2026-11-23 21:00:01 |
| Senaste resultatkod | 0 |
| Missade körningar | 0 |
| Nästa körning vid kontrollen | 2026-11-24 21:00 |
| Anpassade rötter/output | Nej |
| Flyttbara diskar | Ja, `-IncludeRemovableDrives` |
| SHA-256 | Nej, `-HashFiles` används inte |

Skriptets standardrötter är GitHub-kloner under användarprofilen och `Skogskoll` under OneDrive-synkroten när den hittas. Om ingen OneDrive-rot hittas används lokal fallback under hemkatalogen. Standardutdata placeras i `Skogskoll\\_inventory` under OneDrive när OneDrive-roten finns, annars `storage-inventory` under hemkatalogen. Den faktiska aktuella outputkatalogen och de senaste rapporterna har ännu inte lästs/verifierats i denna komplettering.

### 7.5 Kodgranskningsfynd – risker att åtgärda

Den befintliga implementationen är avsedd att vara read-only för källdata och skapar tidsstämplade JSON-/Markdownrapporter. Statisk granskning identifierade dock följande risker:

1. Filenumereringen använder `Get-ChildItem -Recurse -ErrorAction SilentlyContinue`. Fel i enskilda underkataloger kan därmed döljas utan att hamna i rapportens `errors`.
2. Jämförelsen kan skapa `missing` för tidigare observerade filer även om aktuell enumerering varit partiell.
3. Föregående och aktuell uppsättning inventeringsrötter jämförs inte som ett stabilt scope. En utelämnad eller ändrad rot kan därför ge falska `missing`-poster.
4. JSON-rapporten innehåller datornamn, användarnamn och fullständiga lokala sökvägar. Rapporternas åtkomst och eventuell delning behöver bedömas.
5. SHA-256 är avstängt i den schemalagda aktiviteten. Resultatkod 0 bekräftar Task Schedulers körresultat, inte fullständig täckning eller integritet för rapportinnehållet.

**Skyddsprincip:** partiell eller scope-inkompatibel inventering får aldrig skapa borttagnings-/`missing`-slutsatser. Tidigare rapporter ska bevaras. Inga filer, schemalagda aktiviteter eller inventeringsinställningar har ändrats i denna kontroll.

### 7.6 Projektledaruppföljning

- GitHub issue [#597 – Härda lokal lagringsinventering mot partiella körningar och falska missing-händelser](https://github.com/dahlinrobert-lgtm/Skog/issues/597) samlar implementationens acceptanskriterier.
- Skog är registrerat som aktivt repo i projektledarens projektregister. Projektledarens befintliga read-only collector hämtar öppna issues/PR från aktiva projekt. Issue #597 kan därför visas i projektledarens arbetslista efter nästa kompletta inventering och publicerade dashboard-snapshot.
- Ingen separat projektledarwebbkomponent behövs för att skapa arbetskortet; dashboarden renderar redan `open_work_items`. Den aktuella webbpubliceringen har inte uppdaterats/verifierats i denna dokumentationsändring.
- Nästa steg är att granska senaste lokala JSON-/Markdownrapporten och dess faktiska outputplats, därefter implementera fail-closed-fullständighet och scope-kontroll i en separat kod-PR.

**Dokumentationsstatus:** Documented – nuläge och risker registrerade; implementation och rapportgranskning återstår.
