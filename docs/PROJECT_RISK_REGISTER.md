# Skog/Skogskoll – projektets risk- och kontrollregister

**Senast bedömt:** 2026-11-24  
**Ägare av beslut:** Användaren  
**Förvaltning:** Projektledaren håller registret uppdaterat vid nya risker, verifierade kontroller, driftincidenter, slutförda uppgifter och överlämning.

## Syfte och tolkning

Registret synliggör risker som kan påverka datakällor, historik, driftkostnad, återställning eller kundprodukt. Det är en kuraterad styrningsvy, inte ett automatiskt säkerhetsintyg eller en realtidsmonitor.

- **Verifierat** betyder att konkret evidens finns för just den angivna kontrollen.
- **Delvis verifierat** betyder att vissa komponenter är kontrollerade men att omfattning eller återkommande drift saknas.
- **Ej inventerat/okänt** betyder att kontrollen inte får antas finnas eller saknas.
- **Öppen åtgärd** betyder att en GitHub-issue finns; den är inte därmed genomförd.
- Risknivå är preliminär prioritering för uppföljning, inte en kvantifierad sannolikhetsmodell.

## Risköversikt

| ID | Område | Preliminär nivå | Status | Ägare/uppföljning |
|---|---|---:|---|---|
| R-01 | Belastning, åtkomst och tillgänglighet hos externa datakällor | Hög | Gemensam källvis kontrollinventering återstår | PM-029 · [#576](https://github.com/dahlinrobert-lgtm/Skog/issues/576) |
| R-02 | Daglig upptäckt av stale/partial/failed snapshots och avvikelser | Hög | Krav fastställt; rapportinventering återstår | PM-027 · [#575](https://github.com/dahlinrobert-lgtm/Skog/issues/575) |
| R-03 | Kostnadsökning och kapacitetsgränser | Medel | Azure-budget finns; samlad uppföljning över tjänster återstår | PM-030 · [#577](https://github.com/dahlinrobert-lgtm/Skog/issues/577) |
| R-04 | Förlust, korruption eller otillräcklig återställning av data/system | Hög | Delvisa skydd verifierade; tvärgående restore-täckning återstår | PM-031 · [#578](https://github.com/dahlinrobert-lgtm/Skog/issues/578) |
| R-05 | Felaktig kommersiell användning eller kundvisning av källdata | Hög | Källspecifik bedömning pågår; 0 källor uttryckligen godkända för kundvisning i senaste rapport | PM-025 och källregistret |
| R-06 | Missvisande kundinformation genom okänd kvalitet, täckning eller jämförbarhet | Medel | Snapshotmetadata-/jämförbarhetskontrakt etableras; kundnära kvalitetsvisning återstår | PM-022, PM-027 och PM-025 |
| R-07 | Historikförlust eller falska borttagningsslutsatser vid partiella körningar | Hög | Styrande fail-closed-principer dokumenterade; ska verifieras per flöde | PM-022/PM-023 och källspecifika tester |

## Detaljerade risker och kontroller

### R-01 – Externa datakällor kan belastas eller bli otillgängliga

**Risk:** För hög anropsfrekvens, samtidighet, aggressiva retries eller stora uttag kan belasta en extern tjänst, leda till throttling/blockering eller göra att källägaren begränsar åtkomsten. Tjänstens kapacitet och villkor varierar.

**Verifierat nuläge:** Projektets styrdokument kräver källspecifik kadens och att daglig rapportering inte innebär daglig hämtning. Källstatusrapporten anger bland annat att Länsstyrelsens diarier kräver utredning av tekniska begränsningar före återkommande drift. En gemensam, fullständig inventering av alla klienters rate limits, samtidighet och retry-policy är ännu inte verifierad.

**Förebyggande kontroll som ska verifieras/införas:** källspecifika anropsbudgetar; timeout; begränsad parallellitet; retry-budget; exponential backoff med jitter; respektera Retry-After; paus/circuit breaker vid upprepade 429/503; checkpoints och återstart utan omhämtning av onödiga delar.

**Reservplan:** pausa berörd källa, behåll senaste kompletta snapshot, markera status stale/partial/failed, eskalera till manuell kontroll och återuppta först inom dokumenterade gränser.

**Nästa steg:** read-only inventera befintliga HTTP-klienter, adapters, scheman och källvillkor. Se [PM-029](https://github.com/dahlinrobert-lgtm/Skog/issues/576).

### R-02 – Otillräcklig överblick över snapshot- och insamlingsstatus

**Risk:** En misslyckad eller partiell körning kan förbises, eller gammal data kan uppfattas som aktuell om senaste försök och senaste kompletta observation blandas ihop.

**Verifierat nuläge:** PM-027 finns dokumenterad i backloggen. Projektledarsidan har read-only inventering av GitHub issues/PR, workflow-körningar och källregister, men full koppling till snapshotmanifest och senaste kompletta observation är ännu inte verifierad.

**Förebyggande kontroll:** en daglig read-only sammanställning som visar senaste kompletta snapshot separat från senaste försök, källans kadens, aktualitet, scope, antal, jämförbarhet, avvikelser och evidenslänkar.

**Reservplan:** okända värden visas som okända; partial/failed/stale får tydlig varning och får aldrig skapa borttagningsslutsatser.

**Nästa steg:** inventera befintliga rapporter, workflows och snapshotkontrakt innan minsta utökning byggs. Se [PM-027](https://github.com/dahlinrobert-lgtm/Skog/issues/575).

### R-03 – Kostnads- och kapacitetsökning

**Risk:** Växande snapshots, databas, artifacts, workflowkörningar eller API-anrop kan öka kostnad eller nå kvoter/kapacitetsgränser.

**Verifierat nuläge:** AI_HANDOVER dokumenterar en Azure-budget på 200 SEK/månad med aviseringar vid 50/75/90 procent. Budgetavisering är inte ett hårt kostnadstak. Storage Account är dokumenterad som Sweden Central/LRS. Samlad uppföljning av faktisk kostnad och kapacitet för Supabase och GitHub Actions är inte verifierad.

**Förebyggande kontroll:** följ faktisk debitering, prognos, lagringstillväxt, databasstorlek/compute, workflowminuter, artifact-retention och API-anropsvolym där leverantörerna erbjuder mätvärden. Återanvänd befintliga budgetlarm.

**Reservplan:** utred kostnadsdrivare och pausa icke-kritiska test-/pilotkörningar efter mänskligt beslut. Gallra inte historik automatiskt.

**Nästa steg:** inventera befintliga kostnadskällor och mätvärden read-only. Se [PM-030](https://github.com/dahlinrobert-lgtm/Skog/issues/577).

### R-04 – Otillräcklig backup eller återställningsförmåga

**Risk:** Radering, korruption, felpublicering eller driftavbrott kan göra historik eller driftmiljö otillgänglig om backup och restore inte är heltäckande och testade.

**Verifierat nuläge:** NVR-backup med SHA-256-kontroll och runbook har dokumenterats. Azure Blob-versionering och soft delete (14 dagar) är dokumenterade; Azure Backup, point-in-time restore, Change Feed och immutability var inaktiverade vid senaste konfigurationsinventering. Detta är inte ett bevis på att övriga datakällor saknar backup; deras täckning är inte samlad här.

**Förebyggande kontroll:** inventera system/data, backupkälla, retention, behörighet, RPO/RTO och återställningsordning. Kör isolerade restore-test och verifiera manifest/checksummor.

**Reservplan:** stoppa skrivningar vid misstänkt korruption, bevara original och loggar, återställ till separat miljö och verifiera innan kontrollerad återgång.

**Nästa steg:** read-only inventera befintliga backup-/restore-flöden och välj första tvärgående restore-test. Se [PM-031](https://github.com/dahlinrobert-lgtm/Skog/issues/578).

### R-05 – Källrättigheter och kundvisning

**Risk:** Teknisk åtkomst eller rätt att hämta data kan felaktigt tolkas som rätt att lagra historik, bearbeta, kommersialisera, visa för kund eller vidare distribuera.

**Verifierat nuläge:** Källstatusrapporten kontrollerad 2026-11-23 anger 0 uttryckligen godkända källor för kundvisning. Rättighetsbedömning ska göras separat per exakt produkt/lager och användning.

**Förebyggande kontroll:** håll teknisk åtkomst, historisk lagring, bearbetning, kommersiell användning, kundvisning och redistribution som separata fält med dokumenterad evidens, attribution och datum.

**Reservplan:** håll produkt/lager utanför kundflödet tills rättighetsfrågan är dokumenterat avgjord; exponera inte rådata som standard.

**Nästa steg:** fortsätt källspecifik bedömning i källregistret och PM-025. Inga generella licensslutsatser får dras från ett enskilt leverantörsbesked.

### R-06 – Missvisande kvalitet eller proveniens i kundinformation

**Risk:** En händelse kan presenteras utan tillräcklig information om källa, observationstid, fullständighet, geometri, dubbletter, jämförbarhet eller osäkerhet.

**Verifierat nuläge:** PM-022 etablerar snapshot-envelope och jämförbarhetsmetadata. Kundnära kvalitetsindikatorer och presentation är inte verifierade som färdig funktion.

**Förebyggande kontroll:** visa källa, produkt/lager, observationstid, upptäcktstid, körningsstatus, geografiskt scope, jämförbarhet och kända kvalitetsbegränsningar; skilj observation från tolkning/indikator.

**Reservplan:** märk osäkra poster som preliminära/granskningskrävande eller dölj dem från kundflödet enligt beslutad produktpolicy.

**Nästa steg:** återanvänd PM-022:s befintliga metadata-/snapshotkontrakt när PM-027 och PM-025 utformas. Ingen parallell kvalitetsmodell.

### R-07 – Historikförlust eller falska borttagningsslutsatser

**Risk:** Partiella uttag, ändrat scope eller saknad jämförelsebas kan felaktigt tolkas som att ett objekt försvunnit eller ändrats.

**Verifierat nuläge:** AI_HANDOVER och källstatusrapporten dokumenterar att partial/failed inte får användas för borttagningsslutsatser och att första kompletta baslinjen ska vara tyst. Snapshot-envelope och append-only-principer finns i den befintliga arkitekturen; täckning och tester ska verifieras per flöde.

**Förebyggande kontroll:** fail-closed på fullständighet, scope-hash och jämförbarhet; bevara föregående kompletta snapshot; skilj händelsedatum, publiceringsdatum och första upptäckt.

**Reservplan:** undertryck frånvaro-/borttagningshändelser och flagga granskningsbehov tills två jämförbara kompletta observationer finns.

**Nästa steg:** inkludera negativa regressionstester i berörda källflöden och PM-022/PM-023-acceptans.

## Förvaltningsregel

Projektledaren ska vid planering, delmål, färdig uppgift, PR-granskning/merge, driftändring och överlämning bedöma om riskregistret behöver uppdateras. Varje ändring ska länkas till kod, issue, workflow, konfiguration eller annan evidens. Om ingen ändring krävs dokumenteras bedömningen som sådan enligt den befintliga dokumentationsgrinden. Risker får inte markeras som åtgärdade enbart för att en issue stängts eller PR mergats; acceptanskriterier och faktisk verifiering krävs.
