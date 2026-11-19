# AI-projektledare v2b – teknisk design för Git-historik

**Status:** Designförslag – ingen persistens aktiverad och inga skrivbehörigheter tillagda  
**Beslutad målbild:** separat Git-branch, indefinite retention (2026-11-19)  
**Säkerhetsgräns:** inventeringsjobbet ska förbli read-only. Designen nedan är inte ett godkännande att arkivera riktiga inventeringar.

## 1. Mål och icke-mål

Målet är att kunna bevara oförändrade inventeringskörningar med verifierbar proveniens, utan att en ofullständig körning kan bli baslinje för frånvaroslutsatser.

Ingår:
- separat branch `project-manager-history`;
- en katalog per unik Actions-körning;
- manifest och SHA-256 för inventering och rapport;
- append-only-beteende och fail-closed;
- syntetisk testning av skriv-/återläsningslogik.

Ingår inte:
- automatisk eller schemalagd körning;
- historisk jämförelse (v2c);
- LLM/API eller agentåtgärder;
- skrivbehörighet i nuvarande inventeringsjobb;
- arkivering av riktiga inventeringar innan separat aktiveringsbeslut.

## 2. Branch- och katalogmodell

Föreslaget branchnamn: `project-manager-history`. Branch skapas först efter separat aktiveringsgodkännande och efter att branch ruleset verifierats.

Katalog per Actions-run:
```
runs/YYYY/MM/DD/<run_id>/
  inventory.json
  report.md
  manifest.json
```

`run_id` ska härledas från GitHub Actions `run_id` (numeriskt) tillsammans med repository-identitet. Samma run får aldrig skapa två olika kataloger. Om katalogen redan finns ska persistens avbrytas som dubblett – inte skriva över eller uppdatera innehållet.

## 3. Manifest v1

Manifestet är UTF-8 JSON, deterministiskt serialiserat (sorterade nycklar, stabil indentering, avslutande LF). Föreslagna fält:

| Fält | Betydelse |
|---|---|
| `manifest_schema_version` | Heltal, börjar på 1 |
| `run_id` | GitHub Actions run ID som sträng |
| `run_attempt` | Actions run attempt |
| `repository` | `owner/name` |
| `source_branch` | Branch som inventerades |
| `source_commit_sha` | Commit som checkout/inventering avsåg |
| `generated_at` | Inventeringens UTC-tid |
| `archived_at` | Arkiveringens UTC-tid |
| `artifact_name` | Förväntat Actions-artifactnamn |
| `files.inventory_json` | Relativ sökväg, byte, SHA-256 |
| `files.report_md` | Relativ sökväg, byte, SHA-256 |
| `coverage.issues` | Status, sidor, poster, truncation |
| `coverage.pull_requests` | Status, sidor, poster, truncation |
| `comparison_eligible` | true endast om båda listorna är complete |

Manifestets checksummor beräknas över exakta byte av de två filer som arkiveras. Manifestet ska inte innehålla token, issue-/PR-body, kommentarer eller andra fält som inte redan ingår i den avgränsade inventeringen.

## 4. Persistensflöde – avsedd jobbisolering

1. Inventeringsjobbet körs som i dag och behåller `contents: read`, `issues: read`, `pull-requests: read`, `actions: read`.
2. Det laddar upp artifact `skogskoll-project-manager-report` (fortsatt 14 dagar; endast transport).
3. Ett separat persistensjobb hämtar artifact från samma workflow-run och validerar att exakt `inventory.json` och `report.md` finns.
4. Det validerar JSON, repository, run metadata och coverage. Saknad fil, felaktigt JSON, oväntad repository-identitet eller API-/artifactfel stoppar körningen.
5. Det skapar manifest och verifierar SHA-256 innan Git-operation.
6. Det kontrollerar att målkatalogen inte redan finns. Befintlig katalog ger idempotent no-op endast om alla byte och manifest exakt matchar; annars hårt fel. Inga befintliga filer skrivs över.
7. Det skapar en ny commit på historikbranchen med endast den nya run-katalogen.
8. Det läser tillbaka de tre filerna och jämför SHA-256 innan jobbet rapporterar framgång.

**Viktigt:** GitHubs `GITHUB_TOKEN` med `contents: write` är en repo-omfattande behörighet, inte en token som i sig begränsas till en enda branch. Därför måste skrivjobbet vara separat och branchskydd/rulesets hindra automationen från att uppdatera `main`, force-pusha eller radera historikbranchen. Om den faktiska kombinationen av token, ruleset och workflow inte kan verifieras ska persistens inte aktiveras. Ingen PAT med bredare rättigheter ska införas som genväg.

## 5. Kompletthet och jämförbarhet

- Både `collection_limits.issues.status` och `collection_limits.pull_requests.status` måste vara `complete` för `comparison_eligible=true`.
- Om någon lista är `truncated`, saknas eller har annan status får körningen fortfarande arkiveras som observation endast efter separat designgodkännande, men manifestet ska sätta `comparison_eligible=false`.
- API-fel före artifactproduktion ger ingen arkivering.
- En trunkerad inventering får aldrig användas för frånvarobaserade slutsatser.
- Saknade objekt i senare inventering betyder endast **ej observerad i detta uttag**.

## 6. Branchskydd och behörighetskontroller

### Read-only kontroll 2026-11-19

Resultatet är dokumenterat i [PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md](PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md): repository rulesets API returnerade `[]`; endpointen för klassisk branch protection på `main` returnerade HTTP 403 `Resource not accessible by integration`; `project-manager-history` returnerade 404 eftersom den ännu inte skapats. Nuvarande workflow YAML bekräftar endast read permissions och inget persistence-jobb. Därför är skyddet av `main` inte verifierat och livepersistens är blockerad.



Före någon skrivaktivering måste följande verifieras i GitHub:
- ruleset för `main` kräver PR och blockerar direkt push från Actions-identiteten;
- historikbranchen skyddas mot force-push och deletion;
- endast det avsedda persistensjobbet får `contents: write`;
- inventeringsjobbet har fortsatt endast läsbehörigheter;
- inga PAT, Azure credentials eller andra långlivade hemligheter behövs;
- workflowet får inte köras med skrivbehörighet på pull_request-kod eller från opålitliga forks.

Om GitHubs ruleset inte kan skilja tillräckligt mellan målbrancher och aktörens rättigheter ska alternativet omprövas innan persistens aktiveras.

## 7. Syntetisk testmatris

| Test | Förväntat resultat |
|---|---|
| Komplett inventory + report | Manifest skapas, båda SHA-256 stämmer |
| Issue-lista trunkerad | `comparison_eligible=false` |
| PR-lista trunkerad | `comparison_eligible=false` |
| Coverage saknas/okänd | Fail closed; ingen jämförbar baslinje |
| inventory.json saknas | Hårt fel, ingen commit |
| report.md saknas | Hårt fel, ingen commit |
| Felaktig JSON | Hårt fel, ingen commit |
| Repository mismatch | Hårt fel, ingen commit |
| Samma run ID + identiska byte | Idempotent no-op, ingen ny commit |
| Samma run ID + avvikande byte | Hårt fel, aldrig overwrite |
| SHA-256 mismatch vid readback | Jobbet misslyckas |
| Branch-head ändras mellan läsning och push | Ny fetch/rebase-lösning eller fail; aldrig force-push |
| Restore till tom katalog | Filer återställs och SHA-256 verifieras |

Testerna ska använda syntetiska fixtures och en temporär lokal Git-repository eller isolerad testbranch. De ska inte skapa riktig historikbranch eller använda produktionsskrivtoken.

## 8. Genomförandeordning

1. Implementera ren Python-modul för manifest, validering, checksumma och append-only-katalogkontroll; ingen GitHub-skrivning.
2. Lägg till enhetstester för hela testmatrisen med temporärt filsystem/Git-repo.
3. Kör riktade tester och befintlig bred CI.
4. Granska workflow- och GitHub-ruleset-modellen separat; verifiera om branchspecifik säkerhet faktiskt går att upprätthålla.
5. Presentera diff, testresultat och kvarstående risker för användaren.
6. Först efter separat uttryckligt godkännande: skapa historikbranch, sätt upp skydd och genomför syntetisk live-readback.
7. Först efter ytterligare separat godkännande: aktivera arkivering av riktiga inventeringar.

## 9. Acceptanskriterier

- [x] Offline-modul för manifest och coverage-validering implementerad på PR-branch; CI-verifiering inväntas.
- [x] Syntetiska tester för SHA-256, determinism, trunkering, saknad/okänd coverage, felaktig JSON, repository mismatch, run metadata, timestamp och append-only-konflikter tillagda.
- [ ] Manifest är deterministiskt och innehåller run-/repo-/commit-/coverage-metadata (ska slutverifieras i CI).
- [ ] SHA-256 beräknas över exakta filbyte och verifieras efter återläsning.
- [ ] Inga existerande körningsfiler kan skrivas över.
- [ ] Dubblettkörningar hanteras utan att skapa divergerande historik.
- [ ] Ofullständig/trunkerad coverage kan inte bli jämförbar baslinje.
- [ ] Saknade filer, felaktig JSON, fel repository och checksummefel stoppar arkivering.
- [ ] Syntetiska tester och befintlig CI passerar.
- [ ] Read-only-jobbets behörigheter är oförändrade.
- [ ] Branchskydd och skrivisolering är verifierade innan någon persistens aktiveras.
- [ ] Användaren har separat godkänt aktivering.

**Nuvarande status:** endast design dokumenterad. Ingen kod för persistens, ingen ny workflow, ingen historikbranch, ingen skrivbehörighet och inga arkiverade inventeringar.


## 10. Första offline-implementationen

PR-branch innehåller `scripts/project_manager_history.py` och `tests/test_project_manager_history.py`. Modulen validerar JSON/repository/run metadata/tidsstämplar/coverage, bygger deterministiskt manifest med SHA-256 över exakta byte och jämför befintlig körningskatalog utan att skriva över. Den utför inga filskrivningar, Git-operationer, API-anrop eller nätverksåtkomst. CI körs via det befintliga read-only project-manager-workflowet. Resultat inväntas.


## 11. Restore-/round-trip-steg

PR #441 har mergats och CI passerat; offline-modulen kompletterar med `restore_run_files`: den verifierar manifestversion, exakt filuppsättning, tillåtna relativa filnamn, byteantal och SHA-256 innan återställning till en ny lokal katalog. Den vägrar skriva över en befintlig målkatalog och verifierar SHA-256 efter lokal readback. Detta är en lokal återställningshjälpare, inte Git-/GitHub-persistens och inte ett produktionsflöde. Syntetiska tester omfattar lyckad round-trip, manipulerade byte, befintlig målkatalog och path traversal.


## 12. Säkerhetsgranskning 2026-11-19

Read-only granskning av GitHub settings/API finns i [PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md](PROJECT_MANAGER_AGENT_V2B_SECURITY_AUDIT.md). Ingen repository ruleset returnerades. Klassisk branch protection för `main` gav 403 från GitHub-integrationen och kunde inte verifieras. Den planerade historikbranchen finns inte. Nuvarande workflow har endast read permissions. **Ingen livepersistens får byggas/aktiveras förrän repository-administratören verifierat main-skydd, Actions-bypass och avsedd historikbranchregel.**

## 13. Separat skrividentitet – designförslag (2026-11-19)

Se [PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md](PROJECT_MANAGER_AGENT_V2B_WRITE_IDENTITY_DESIGN.md). Föreslagen modell är en GitHub App installerad endast på Skog, med Contents read/write och endast obligatorisk Metadata read. Tokenen är fortfarande repository-scoped, inte branch-scoped. `Protect main` kräver PR och saknar bypass; Appen ska inte ha Administration eller Pull requests-write och ska inte finnas i bypass-listan. Historikbranchens ruleset ska blockera deletion och non-fast-forward men tillåta vanlig fast-forward append. `Restrict updates` ska inte användas eftersom det skulle stoppa append-commits eller kräva en bred bypass. Append-only på filnivå måste upprätthållas av deterministisk arkiveringskod och negativa tester. Inga credentials eller skrivjobb har skapats. Liveaktivering kräver separata negativa GitHub-tester och uttryckligt godkännande.
