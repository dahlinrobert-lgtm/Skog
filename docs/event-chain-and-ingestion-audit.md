# Händelsekedjor och datainsamling – nulägesgranskning

**Datum:** 2026-11-02  
**Status:** Teknisk nulägesgranskning och rekommenderad målmodell  
**Syfte:** Göra datainsamling, historik och samband mellan källor till kärnan i Skogs bevakningsprodukt.

## 1. Sammanfattning

### Prioriterad ordning för händelsekedjan

1. **Avverkningsanmälningar** – primär ingång: registrering, ändringar, status och historik.
2. **Utförda avverkningar från en oberoende, icke-satellitbaserad källa** – ska kopplas till anmälan när sådan källa och dess metod har verifierats.
3. **Samråd och myndighetsärenden** – kompletterande händelser som kan knytas till ärende-ID, fastighet eller geografi. Skogsstyrelsens tre Samråd-geometrier finns redan som karttjänst och får nu en separat historisk pilotinsamling.
4. **Satellitbaserade förändringssignaler** – lägsta prioritet; används senare som kompletterande indikation, aldrig som krav för att en kedja ska kunna skapas.

**Viktig källavgränsning:** Det befintliga lagret som i repot kallas utförda avverkningar innehåller `Forebild`/`Efterbild`-fält och analysen beskriver det uttryckligen som satellitbaserad förändringsdetektion. Det är därför inte en oberoende verifiering av att en anmälan har verkställts. Lagret ska tills vidare klassas som satellitindikation och inte användas som prioriterad, verifierande källa i händelsekedjan. En framtida källa för registrerade/rapporterade utförda åtgärder måste bedömas separat.


Skog har redan flera viktiga byggstenar: återkommande hämtning, snapshots, deltaarkiv, historik för avverkningsanmälningar, insamling av utförda avverkningar och en rumslig/tidsmässig analys mellan planerade och utförda objekt.

Det som ännu saknas är ett gemensamt, källoberoende lager som binder ihop dessa observationer till **kanoniska händelser och händelsekedjor** och publicerar dem i ett enhetligt bevakningsflöde. De befintliga analyserna producerar användbara delresultat, men de är inte samma sak som en gemensam händelsemotor eller ett produktionssatt aviseringsflöde.

Den centrala produktkedjan bör vara:

`Källa → insamlingskörning → råpost/snapshot → normaliserad observation → matchning → kanonisk händelse → händelsekedja → bevakningsmatchning → avisering`

Varje steg ska gå att granska i efterhand. Originaluppgifter ska bevaras och Skogs tolkning ska lagras separat.

## 2. Vad som faktiskt finns i repot

### 2.1 Gräsmyrflödet

Workflow `.github/workflows/monitor.yml` körs schemalagt dagligen (05:17 UTC) och kör i ordning:

1. `scripts/monitor.py` – hämtar avverkningsanmälningar för konfigurerat område samt Sentinel-1- och Sentinel-2-scener.
2. `scripts/build_web_data.py` – förenklar geometrier för webbvisning.
3. `scripts/snapshot_completed.py` – hämtar utförda avverkningar inom konfigurerad radie och sparar historik.
4. `scripts/notification_history.py` – bygger historik och en härledd händelselogg för anmälningsposter.
5. `scripts/analyze_changes.py` – jämför planerade och utförda geometrier och skapar uppföljningskandidater.
6. Resultat och snapshots committas till repot.

Skydd som redan finns:
- Ett misslyckat uttag av avverkningsanmälningar avbryter körningen i stället för att skriva över senaste fungerande data med ett tomt resultat.
- Snapshotlagringen använder fullständiga checkpoints och deltan.
- Jämförelser görs bara mellan jämförbara frågeområden när scope-fingerprint finns.
- Saknade poster beskrivs som `not_returned`, inte som avverkade, avregistrerade eller borttagna.
- Satellitbaserade utförda avverkningar behandlas som indikationer som kräver granskning, inte som bevis.
- Överlappande utförda polygoner unioneras för unik täckningsberäkning så att samma yta inte dubbelräknas.

Begränsning: detta flöde är geografiskt avgränsat till konfigurationen i `config/area.json`. Webbgränssnittet använder `data/latest_web.json` och visar i huvudsak en aktuell datamängd, inte ett generellt nationellt händelseflöde.

### 2.2 Nationell insamling av avverkningsanmälningar

Workflow `.github/workflows/national-monitor.yml` körs den 1:a och 16:e varje månad (05:47 UTC) samt manuellt. `scripts/monitor_national.py`:

- hämtar samtliga ObjectID:n från Skogsstyrelsens avverkningsanmälningstjänst,
- hämtar objekten i avgränsade batcher,
- gör återförsök och avbryter om objekt saknas efter återförsök,
- sparar ett nationellt aktuellt uttag samt fullständiga snapshots/deltan,
- sparar räknare och insamlingsdiagnostik.

Detta är en viktig nationell historikbas, men den körs inte i samma frekvens som Gräsmyrflödet. I nuläget finns ingen motsvarande nationell, samordnad kedja i de granskade filerna för utförda avverkningar, satellitindikationer, samråd och andra åtgärder.

### 2.3 Historik och analys

`scripts/notification_history.py` skapar bland annat:
- `first_seen_at` och `last_seen_at`,
- källstatus `observed` eller `not_returned`,
- händelserna `first_observed`, `not_returned` och `record_changed`,
- referenser till före- och eftersnapshot.

Händelseloggen återskapas från sparade snapshots. Snapshots är alltså sanningskällan; händelseloggen är en härledd vy.

`scripts/analyze_changes.py` kopplar planerade objekt till utförda polygoner med rumsligt överlapp, tidsfönster och en heuristisk matchpoäng. Den redovisar bland annat:
- bästa kandidat och antal starka kandidater,
- överlapp och unik unionstäckning,
- tidsmässig rimlighet,
- uppföljningsstatus som `likely_completed`, `likely_partial` eller `awaiting_evidence`.

Viktigt: matchpoängen är en rangordningsheuristik, inte en sannolikhet. En rumslig överlappning är inte i sig bevis för att en viss anmälan ledde till en viss avverkning.

### 2.4 Vad som saknas för produktens kärna

I de granskade filerna hittades ännu inte en gemensam implementation som:
- ger alla källobservationer ett stabilt gemensamt ID och ett versionsspår,
- binder ihop flera observationer till en beständig kanonisk händelse,
- lagrar relationer mellan händelser med metod, evidens, säkerhet och granskningsstatus,
- bygger ett gemensamt flöde från flera datakällor,
- kopplar händelser till sparade användarbevakningar,
- skickar och loggar användaraviseringar med deduplicering och återförsök.

Det betyder inte att befintliga insamlingsflöden ska byggas om. De ska återanvändas som källspecifika insamlare och förses med en gemensam händelsemodell efter insamlingen.

## 3. Målmodell: skilj observation, händelse och händelsekedja

Det är avgörande att inte slå ihop tre olika saker:

### A. Källobservation

En post eller mätning som en källa faktiskt har lämnat ifrån sig vid en viss hämtning.

Exempel:
- avverkningsanmälan med ett visst käll-ID,
- en utförd-avverkning-polygon,
- en satellitscen eller en beräknad förändringssignal,
- ett samrådsärende,
- en registrerad naturvårdsåtgärd.

En observation ska alltid gå att spåra till källa, käll-ID, insamlingskörning och snapshot.

### B. Kanonisk händelse

Skogs beständiga representation av något som hänt, beslutats, registrerats eller observerats i verkligheten.

En kanonisk händelse kan ha en eller flera källobservationer kopplade till sig. Den ska inte ersätta originalposterna.

Exempel:
- en avverkningsanmälan,
- ett samråd kopplat till ett område,
- en satellitbaserad förändringsindikation,
- en registrerad utförd avverkning.

### C. Händelsekedja

En samling relaterade kanoniska händelser som tillsammans beskriver ett förlopp.

Exempel:
1. Avverkningsanmälan registreras.
2. Ett samråd eller myndighetsärende kopplas till samma område.
3. En satellitbaserad förändringssignal upptäcks.
4. En utförd-avverkning-post registreras.
5. Skog uppdaterar kedjans status och förklarar vilka delar som är belagda respektive osäkra.

Kedjan beskriver samband. Den får inte automatiskt hävda orsakssamband.

## 4. Föreslagen gemensam datamodell

Börja filbaserat och portabelt. Modellen kan senare flyttas till relationsdatabas utan att begreppen ändras.

### 4.1 `source_run` – varje insamlingskörning

| Fält | Betydelse |
|---|---|
| `run_id` | Stabilt ID för körningen |
| `source_id` | Källregister-ID |
| `started_at`, `finished_at` | Körningens tidsintervall |
| `status` | success / partial / failed |
| `scope_hash` | Fingerprint för exakt geografiskt och attributmässigt urval |
| `source_snapshot_at` | Källans egen tidpunkt, om den finns |
| `records_seen`, `records_valid`, `records_rejected` | Kontrollräknare |
| `snapshot_ref` | Fil-/objektreferens |
| `checksum` | Kontrollsumma |
| `diagnostics` | Fel, paginering, begränsningar och varningar |

En lyckad körning betyder inte automatiskt att den är komplett. Fullständighet ska bedömas utifrån källans pagination, scope och validering.

### 4.2 `source_observation` – oföränderlig källobservation

| Fält | Betydelse |
|---|---|
| `observation_id` | Stabilt plattforms-ID |
| `source_id` + `source_record_id` | Unik källidentitet |
| `run_id` | Insamlingskörning |
| `observed_at` | När Skog observerade posten |
| `source_created_at`, `source_updated_at` | Källans tider, null om okända |
| `valid_time` | När uppgiften gäller i verkligheten, om känt |
| `content_hash` | Identifierar ändrat innehåll |
| `raw_ref` | Referens till rådata/snapshot |
| `geometry_ref`, `geometry_crs` | Geometri och koordinatsystem |
| `quality_status` | Valideringsresultat |

Samma källpost kan ge flera observationer över tid. Det är så vi bevarar historiken.

### 4.3 `canonical_event` – händelsen som visas i flödet

| Fält | Betydelse |
|---|---|
| `event_id` | Beständigt kanoniskt ID |
| `event_type` | Exempelvis planned_harvest, consultation, change_signal, completed_harvest |
| `event_status` | Status i händelsens livscykel |
| `title`, `summary` | Begriplig presentation |
| `event_time_start`, `event_time_end` | Verklig händelsetid, om känd |
| `first_observed_at`, `last_observed_at` | Skogs observationstid |
| `geometry_ref` | Geografisk representation |
| `confidence_class` | verified / supported / indicative / uncertain |
| `interpretation_version` | Version av reglerna som skapade tolkningen |

### 4.4 `event_evidence` – belägg för händelsen

Kopplar en eller flera källobservationer till en kanonisk händelse.

Fält:
- `event_id`
- `observation_id`
- `evidence_role` – primary, corroborating, contradicting eller contextual
- `match_method`
- `match_score` – endast när en poäng faktiskt används
- `confidence_class`
- `reason_codes`
- `review_status`

### 4.5 `event_relationship` – relation mellan händelser

Fält:
- `from_event_id`, `to_event_id`
- `relationship_type` – same_area, possible_follow_up, supports, contradicts, supersedes, part_of
- `match_method`
- `evidence_refs`
- `confidence_class`
- `created_by_rule`, `rule_version`
- `review_status`

Relationer ska vara riktade när tidsordning eller uppföljning kräver det. En geometrisk närhet ska inte ensam skapa relationen `caused_by`.

### 4.6 `event_chain` – sammanhållen berättelse

- `chain_id`
- `chain_type`
- `primary_area_ref`
- `started_at`, `last_activity_at`
- `chain_status`
- `summary`
- `confidence_class`
- `event_ids` eller separat kopplingstabell

En händelse kan ingå i mer än en kedja, exempelvis en åtgärd som påverkar både ett bevakningsområde och ett större myndighetsärende.

## 5. Matchningsregler: bygg samband stegvis

Använd en tydlig evidenshierarki. Matchning ska kunna förklaras med konkreta skäl.

| Evidens | Exempel | Rekommenderad tolkning |
|---|---|---|
| Samma käll-ID | Samma ObjectID i senare snapshot | Samma källpost/version över tid |
| Explicit korsreferens | Ärende-ID eller projektreferens i annan källa | Stark koppling |
| Verifierad geometriöverlappning | Polygoner överlappar betydande yta | Geografiskt samband, inte automatiskt samma händelse |
| Fastighetskoppling med verifierad geometri | Objekt ligger inom verifierad fastighetsgräns | Stark områdeskoppling |
| Rumslig närhet | Punkt eller polygon nära annat objekt | Kandidatkoppling |
| Tidsmässig rimlighet | Händelser sker i rimlig ordning | Stödjande evidens |
| Liknande namn eller fritext | Fastighetsbeteckning/ärendetext liknar | Svag kandidat, kräver kontroll |

Föreslagna nivåer:
- **Verifierad:** explicit stabil referens eller manuellt bekräftad koppling.
- **Starkt stöd:** flera oberoende belägg, exempelvis betydande geometriöverlappning och rimlig tidsordning.
- **Indikation:** en rimlig signal, exempelvis satellitförändring i närheten.
- **Osäker:** otillräckliga eller motstridiga uppgifter.

Matchpoäng får användas för sortering, men ska aldrig presenteras som statistisk sannolikhet om den inte är kalibrerad mot verifierade utfall.

## 6. Exempel: avverkningskedja

En möjlig kedja för samma område:

| Steg | Händelse | Evidensklass | Vad Skog får säga |
|---|---|---|---|
| 1 | Avverkningsanmälan registreras | Källregistrerad | En anmälan har registrerats |
| 2 | Samråd/ärende kopplas till området | Beror på kopplingen | Ett relaterat ärende finns |
| 3 | Satellitförändring upptäcks | Indikation | En förändringssignal har upptäckts |
| 4 | Utförd-avverkning-post registreras | Källregistrerad observation | Källan redovisar en utförd avverkning |
| 5 | Geometri och datum jämförs | Analytiskt stöd | Objektens geometrier/tider överensstämmer i angiven grad |

Även när alla fem steg finns ska Skog redovisa vilka samband som är säkra och vilka som är geografiska/tidsmässiga kandidater. En anmälan ska inte märkas som genomförd enbart för att en satellitsignal uppstår i närheten.

## 7. Datainsamling: rekommenderad prioritering

### P0 – stabilisera och exponera befintlig historik

1. Behåll Gräsmyrs dagliga pipeline och nationella anmälningsarkiv separat tills deras scope och kvalitet är tydliga.
2. Standardisera manifest för varje körning: source_id, scope_hash, tider, status, antal, checksumma och fel.
3. Gör snapshots och källobservationer till sanningskälla; bygg händelser som reproducerbara derivat.
4. Gör det möjligt att återskapa samma händelselogg från samma snapshots och samma regelversion.
5. Skapa en första gemensam händelseexport från de redan existerande avverkningsflödena.

### P1 – länka fler källor till samma förlopp

Prioritera källor som ger kompletterande steg i en händelsekedja:
1. Avverkningsanmälningar.
2. Utförda avverkningar.
3. Satellitbaserade förändringsindikationer.
4. Samråd och myndighetsärenden.
5. Naturvårdsåtgärder och bränningar.

Varje ny källa ska först få en egen fungerande insamlings- och historikstrategi. Därefter kopplas den till händelsemodellen. En källa ska inte anses integrerad bara för att dess lager visas på kartan.

### P2 – skala geografiskt och operativt

1. Verifiera flera geografiskt spridda testområden.
2. Dokumentera regionala skillnader, täckning, bortfall och uppdateringsfrekvens.
3. Skala nationellt först när scope, pagination, återhämtning och lagringskostnad är mätta.
4. Skilj mellan källornas publiceringsfrekvens och Skogs kontrollintervall.
5. Bygg användarbevakningar och aviseringar ovanpå validerade händelser, inte direkt på råa källposter.

## 8. Regler för frånvaro, ändring och återkomst

Dessa regler är centrala för att undvika falska larm:

- `not_returned` betyder endast att posten inte returnerades i en senare, jämförbar och lyckad körning.
- `not_returned` får inte automatiskt bli `deleted`, `cancelled`, `expired` eller `completed`.
- En misslyckad eller partiell körning får inte skapa frånvarohändelser.
- Ett ändrat källobjekt ska skapa en ny observation och en ändringshändelse, men bevara tidigare innehåll.
- Om en post återkommer ska detta vara en separat återkomsthändelse, med referens till frånvaroperioden.
- Byte av frågeområde/scope bryter jämförbarheten om inte en särskild överlappningsanalys görs.
- En ny insamlingsbaseline ska normalt inte skicka retroaktiva användarlarm.

## 9. Aviseringar: koppla först efter händelsekvalitet

Aviseringsmotorn ska prenumerera på kanoniska händelser och kedjeförändringar, inte på varje nytt API-objekt.

Varje avisering ska ha:
- `notification_id` och `event_id`/`chain_id`,
- bevaknings-ID och matchningsorsak,
- regelversion och relevansnivå,
- kanal och mottagare,
- skapad/skickad/levererad/kvitterad status,
- idempotensnyckel,
- återförsöksstatus,
- undertryckningsorsak om avisering inte skickades.

Första versionen bör kunna skapa en intern aviseringskö och en granskningsbar logg. E-post och push aktiveras när mottagare, leverantör och autentisering är konfigurerade. Det ska inte skickas användarlarm direkt från ett oprövat matchningsresultat.

## 10. Föreslagen teknisk leveransordning

### Leverans 1 – gemensamt händelsekontrakt
Skapa scheman för `source_run`, `source_observation`, `canonical_event`, `event_evidence`, `event_relationship` och `event_chain`. Lägg till validering och små exempeldata.

### Leverans 2 – avverkningskedjan som första vertikala pilot
Återanvänd nuvarande snapshots och analys:
- nationella anmälningsposter som källobservationer,
- Gräsmyrs utförda polygoner och satellitförändringar som separata observationstyper,
- historikens ändringar/återkomster som livscykelhändelser,
- befintlig rumslig analys som kandidatgenerator för relationer.

Skriv en gemensam export som kan återskapas och innehåller evidens och osäkerhet.

### Leverans 3 – feed från kanoniska händelser
Låt bevakningsvyn läsa händelseexporten i stället för att själv kombinera källspecifika dataset. Visa händelsekedjan och källunderlaget i samma flödeskort.

### Leverans 4 – bevakningsmatchning och aviseringskö
Koppla kanoniska händelser till användarens bevakningsområden. Lägg till deduplicering, relevansregler, undertryckning och leveranslogg innan extern utskickskanal aktiveras.

## 11. Acceptanskriterier

- Varje händelse kan spåras till minst en källobservation och en insamlingskörning.
- Varje observation kan spåras till snapshot/rådata och källans original-ID.
- Samma snapshots och regelversion ger samma härledda händelser.
- En händelse kan ha flera källbelägg utan att originalposter skrivs över.
- Samband visar metod, evidens, säkerhetsklass och regelversion.
- Frånvaro efter misslyckad eller inkomplett hämtning skapar aldrig borttagningshändelse.
- En satellitindikation presenteras aldrig som bekräftad avverkning.
- Geometriska överlappningar dubbelräknas inte i arealberäkningar.
- Händelseflödet kan fungera utan att användaren öppnar kartan.
- Aviseringar är idempotenta och går att förklara i efterhand.

## 12. Genomförd första implementation

Följande finns nu i repot:

- `scripts/build_harvest_event_bundle.py` bygger ett deterministiskt händelsepaket från aktuell lyckad avverkningsanmälan och den befintliga notifikationshistoriken.
- En kanonisk händelse och en första uppföljningskedja skapas per källpost.
- Varje händelse har primärt källbelägg, original-ID, snapshotreferens, geometrireferens, källstatus, registreringsdatum och observationstider.
- Händelsetexten säger uttryckligen att en registrerad anmälan inte är belägg för utförd avverkning.
- Byggaren validerar paketet mot det gemensamma JSON-schemat innan det skrivs.
- Gräsmyrs ordinarie workflow kör byggaren efter historik och analys och committar `data/harvest_event_bundle.json`.
- CI testar både schemat och byggaren.

Detta är första vertikala snittet, inte den färdiga flerkälliga kedjan. Det producerar ännu ingen länk mellan anmälan och en oberoende registrerad utförd åtgärd.

## 13. Samråd som nästa insamlingskälla

Skogsstyrelsens Samrådslager används redan av kartan via tre ArcGIS REST-sublager:
- punkt: `MapServer/0`
- linje: `MapServer/1`
- polygon: `MapServer/2`

Kartan hämtade tidigare dessa lager vid behov. Nu finns även:
- `scripts/collect_samrad.py` – hämtar samtliga tre lager, paginerar med ObjectId-ordning, filtrerar till pilotområdets radie i EPSG:3006 och bevarar UUID, Beteckn och övriga källattribut.
- `data/samrad_latest.json` – senaste lyckade resultat.
- `data/samrad_snapshots/samrad_*.json.gz` – oföränderliga komprimerade snapshots.
- `.github/workflows/collect-samrad.yml` – daglig insamling samt manuell körning.
- `tests/test_collect_samrad.py` – tester för paginering, ID-deduplicering och geografisk avgränsning.

Insamlingen publicerar först när alla tre sublager har hämtats utan fel. Frånvaro i senare snapshots tolkas inte som avregistrering eller genomförd åtgärd.

Detta skapar den andra viktiga källfamiljen för händelsekedjor. Nästa implementation ska lägga till Samråd-poster som egna kanoniska händelser och länka dem till avverkningsanmälningar. Matchning ska i första hand använda explicita ärende-/korsreferenser; geometri, kommun och datum ska skapa kandidater med tydlig osäkerhet, inte automatiska bevis.

## 14. Nästa konkreta steg

1. Kör och verifiera Samråd-insamlingen för Gräsmyr; kontrollera antal per sublager, pagination och snapshotstorlek.
2. Normalisera Samråd-poster till händelser i samma event bundle.
3. Matcha Samråd mot avverkningsanmälningar med separata nivåer för explicit ID-match och rumslig/tidsmässig kandidat.
4. Identifiera en oberoende, icke-satellitbaserad källa för utförd avverkning, eller dokumentera att sådan källa saknas.
5. Lägg satellitbaserade förändringssignaler sist som valfri kompletterande evidens.
6. Koppla det validerade händelsepaketet till bevakningsflödet och därefter aviseringskön.

Ändra inte webbgränssnittet eller aktivera externa utskick innan flerkälliga samband kan förklaras och granskas.

