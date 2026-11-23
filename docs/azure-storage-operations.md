# Azure – konto- och kostnadsdrift för Skog/Skogskoll

**Senast verifierad:** 2026-11-23  
**Verifieringsunderlag:** användarens skärmbilder från Azure Portal. Detta dokument beskriver observerat portalnuläge, inte en automatisk kontroll eller en garanti om framtida kostnad.

## Konto och prenumeration

- Storage Account: `stskogkolldata`.
- Prenumeration: `Azure subscription 1`.
- Prenumerations-ID: `e758647f-da18-4063-adfd-f1ce79d5d2af`.
- Prenumerationsstatus i Resource Manager: `Aktiv`.
- Kontotyp: StorageV2 (general purpose v2), standardprestanda.
- Region: `swedencentral` (Sweden Central).
- Redundans: LRS (lokalt redundant lagring).
- Publik blobåtkomst: inaktiverad på kontonivå (tidigare verifierat genom Azure-svaret `PublicAccessNotPermitted` för anonym blobläsning).
- Offentlig nätverksåtkomst: aktiverad; åtkomstomfång visades som alla nätverk. Detta är en nätverksregel och innebär inte anonym blobåtkomst.
- TLS-miniminivå: 1.2.
- GitHub Actions OIDC-identiteten `skogskoll-github-actions` har `Storage Blob Data Contributor` på Storage Account-scope (`This resource`). Identiteten delas av flera Skog-workflows. Ändra inte roll eller scope utan konsekvensanalys.

## Faktureringsbudget och varningar

- Prenumerationen uppgraderades till Pay-As-You-Go och visas som aktiv.
- Budgetnamn: `Skogskoll-budget`.
- Belopp: 200 SEK per månad.
- Återställningsperiod: månadsvis.
- Portalens visade budgetperiod: 2026-11-01 till 2030-10-31.
- Faktiska kostnadsaviseringar: 50 % (100 SEK), 75 % (150 SEK) och 90 % (180 SEK).
- Aviseringsmottagare konfigurerades för projektets två angivna e-postadresser.
- Åtgärdsgrupp: Ingen.
- Språk: standardinställning.

**Viktig begränsning:** Azure Cost Management-budgetar och deras aviseringar är uppföljnings-/notifieringsmekanismer, inte ett hårt kostnadstak. De stoppar inte automatiskt resurser eller hindrar debitering när budgeten överskrids. Pay-As-You-Go innebär att faktisk användning kan debiteras.

## Dataskydd – verifierad portalinställning

På Storage Account → Datahantering → Dataskydd:

| Funktion | Verifierat läge 2026-11-23 |
|---|---|
| Azure Backup för blobbar | Inaktiverat |
| Återställning till tidpunkt för behållare (point-in-time restore) | Inaktiverat |
| Mjuk borttagning för blobbar | Aktiverat, 14 dagar |
| Mjuk borttagning för behållare | Aktiverat, 14 dagar |
| Permanent borttagning för mjukt borttagna objekt | Inaktiverat |
| Blobversionering | Aktiverat |
| Versionsretention | Behåll alla versioner (ingen automatisk versionsgallring vald) |
| Change feed | Inaktiverat |
| Immutability på versionsnivå | Inte aktiverat |

En enskild blob `project-manager/snapshots/45002255351/dashboard-data.json` visade inget tidigare versionsobjekt i fliken Versioner vid kontrollen. Det motsäger inte att versionering är aktiverad; den aktuella filen hade helt enkelt inga tidigare versioner listade vid kontrolltillfället.

## Mätvärden – ögonblicksbilder 2026-11-23

- Used capacity visades vid två mättillfällen som cirka 754,7 MiB respektive 770 MiB.
- Transactions (Sum) visade 310 för den valda senaste 24-timmarsperioden.
- Diagrammet visade låg aktivitet under större delen av perioden och några korta toppar.
- Dessa är ögonblicksbilder från Azure Monitor, inte en långsiktig tillväxtserie eller fakturakontroll. Mätperioder/aggregationer måste hållas jämförbara innan förändringstakt beräknas.

## Beslut och driftprinciper

1. Behåll nuvarande grundskydd: blobversionering och 14 dagars soft delete för blobbar och behållare.
2. Aktivera inte generell gallring/radering av snapshots eller blobversioner utan separat konsekvensanalys. Historiska original och manifest ska bevaras enligt respektive arkivs retentionbeslut.
3. Aktivera inte Azure Backup, point-in-time restore, Change Feed eller immutability enbart på antagande; bedöm funktion, kostnad och återställningsbehov först.
4. Applikationens append-only-historik, snapshots, manifest och SHA-256-kontroller är separata från Azures versions- och soft-delete-skydd. Azure-skydd ersätter inte arkivets egna audit- och restore-test.
5. Kontrollera faktisk fakturering och budgetutfall efter en period av normal drift. Budgetaviseringar är inte kostnadstak.
6. Genomför ett avgränsat restore-test för en icke-produktionskritisk testblob innan återställningsförmågan betraktas som verifierad.
7. Följ lagringskapacitet och transaktioner över tid; gör inte kostnadsprognoser från en enda 24-timmarsbild.

## Kvarstående kontroller

- Verifiera att budgetaviseringarna faktiskt levereras till mottagarna (inklusive skräppost/allowlist för Azure-avsändaren).
- Följ faktisk debitering på prenumerationsnivå efter att Pay-As-You-Go varit aktiv under en hel faktureringsperiod.
- Undersök transaktionernas API-uppdelning om den behövs för kostnadsoptimering; API name-dimensionen har ännu inte verifierats.
- Planera och genomför ett separat återställningstest.
- Bedöm senare om versionslivscykelhantering behövs; ingen automatisk versionsradering är nu konfigurerad.

## Avgränsningar

Detta dokument bekräftar inte juridiska rättigheter för någon datakälla och ändrar inte status för Viltdata, Kungjort, polisdata eller andra dataset. Teknisk lagring/åtkomst är skild från historisk lagringstillåtelse, kommersiell användning, kundvisning och vidare distribution.
