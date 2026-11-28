# Parallell utvärdering av Polisens händelsekällor

**Status:** teknisk utvärderingspilot, inte produktionsgodkännande  
**Startpunkt:** första lyckade snapshot från det officiella API-flödet  
**Planerad utvärderingsperiod:** 30 kalenderdagar  
**Geografiskt jämförelsescope:** Norrbottens län

## Syfte

Jämför två separata publiceringsflöden utan att ersätta eller slå samman befintlig historik:

1. **Brottsplatskartan API** – befintlig daglig insamling i `scripts/ingest_police_events.py`, med `area=Norrbottens län`.
2. **Polismyndighetens officiella händelse-API** – ny separat snapshotinsamling från `https://polisen.se/api/events`.

Utvärderingen ska avgöra om flödena publicerar samma händelseurval, om de kompletterar varandra och vilken källa som är mest användbar för Skogskolls ändamål. Källornas identiteter och råposter hålls separata under hela försöket.

## Bakgrund och verifierad källevidens

Polismyndighetens officiella API-dokumentation anger att API:et innehåller 500 aktuella händelsenotiser, alltså ett urval av polisens utryckningar. Notiser publiceras vanligtvis inom några timmar men tidpunkten varierar; innehållet bygger på inledande uppgifter och kan uppdateras. API-anrop utan argument returnerar de händelsenotiser som publiceras på polisen.se.

Dokumentationen beskriver fälten/koncepten händelsetid, plats och händelsetyp. Koordinaten är mittkoordinaten för kommunen eller länet, inte händelseplatsens exakta position. Sammanfattningar kan omfatta flera händelser.

Polismyndighetens IT-kansli bekräftade i e-post 2026-11-27, diarienummer **A698.287/2026**, att de händelser som publiceras på webbplatsen är vad som finns tillgängligt och att det inte finns ytterligare data att tillhandahålla genom den begärda API-åtkomsten. Det är inte ett besked om att det publika API:et saknas: Polisen har separat publicerat dokumentation för `/api/events`.

## Insamlingsupplägg

- Befintligt Brottsplatskartan-flöde lämnas oförändrat.
- Det officiella API:et hämtas separat en gång per dygn, 14 minuter efter ordinarie Brottsplatskartan-schemaläggning.
- Varje officiell hämtning arkiveras som en egen immutable snapshot i Azure Blob Storage, under prefixet `polisen-official/runs/{run_id}/attempt-{attempt}/`.
- Snapshot och manifest innehåller hämtningstid, antal poster, antal poster med `location.name=Norrbottens län`, byteantal och SHA-256.
- Den fulla aktuella API-listan bevaras i råsnapshoten. Norrbotten räknas separat ur fältet `location.name`; ingen filtrering eller omskrivning av råposterna görs.
- Ett misslyckat eller tomt svar ska ge misslyckad körning, inte en tom snapshot eller en slutsats om att händelser har försvunnit.
- Inga gamla snapshotar skrivs över. Inga händelser tas bort från den befintliga Brottsplatskartan-historiken.
- Inga automatiska kundlarm eller kundvisningsändringar kopplas till utvärderingen.

### Hänsyn till Polisens API-regler

Polisen kräver korrekt User-Agent och HTTPS, minst 10 sekunder mellan anrop, högst 60 anrop per timme och 1 440 per dygn. HTTP 404 ska behandlas som permanent. Webbskrapning är inte tillåten för konsumtion av data när ett API finns. Den nya workflowen gör därför endast ett dokumenterat HTTPS-API-anrop per dygn, använder en identifierbar User-Agent och har inga automatiska upprepade anrop vid fel.

## Matchning och jämförelse

Jämförelsen görs på händelsenivå, men olika käll-ID:n får aldrig antas vara samma identitet. Matchningskandidater ska baseras på en kombination av:

- händelsetid och publiceringstid, med separata tidsfält,
- händelsetyp/kategori,
- ort, kommun och län,
- rubrik och beskrivning,
- eventuell väg-/platsreferens i texten.

Resultatet ska klassificera:
- sannolik gemensam händelse,
- möjlig gemensam händelse – manuell granskning,
- unik i officiella Polisen,
- unik i Brottsplatskartan,
- ej jämförbar/sammanfattning med flera underhändelser.

Automatisk matchning får inte skriva om källposter eller skapa bekräftade relationer utan validering mot ett manuellt granskat urval. En sammanfattning med flera händelser ska inte matchas som en enskild olycka.

## Kvalitetsmått

### Innehåll och täckning
- antal poster per snapshot och antal Norrbottenposter,
- överlappning och unika poster per källa,
- fördelning per händelsetyp och kommun/län,
- saknade fält och dubbletter,
- antal sammanfattningar och hur ofta de innehåller flera händelser,
- textinnehåll och platsreferenser som kan stödja skogskollsanalys,
- ändringar av samma händelse mellan snapshots.

### Aktualitet
- skillnad mellan händelsetid och publiceringstid,
- skillnad mellan publiceringstid och första observerade snapshot,
- uppdateringsfrekvens och fördröjning,
- hur länge poster ligger kvar i det aktuella 500-postersurvalet.

### Teknisk tillförlitlighet
- lyckade/misslyckade körningar och HTTP-status,
- timeout och svarstid,
- schema-/fältförändringar,
- antal poster, ID-unikhet och oväntade tomma svar,
- råbytes, SHA-256 och manifestverifiering,
- snapshotkontinuitet och luckor,
- reproducerbarhet och förmåga att återskapa historik från arkivet.

### Geografisk kvalitet
- om ort/kommun/län kan utläsas ur text,
- koordinattyp och geografisk precision,
- om koordinaten är kommun-/länscentrum eller mer specifik,
- förekomst av vägnummer, vägnamn och platsbeskrivningar.

Polisens officiella API anger uttryckligen att koordinaten är ett områdescentrum. Den ska därför inte användas som exakt händelseposition.

## Period och beslutskriterier

Utvärderingsperioden är 30 kalenderdagar från första lyckade officiella snapshot. Målet är minst 25 lyckade dagliga snapshots. Misslyckade dagar dokumenteras som luckor och får inte fyllas med antagna data. Om färre än 25 snapshots lyckas förlängs perioden tills ett tillräckligt underlag finns eller tekniska hinder motiverar att piloten stoppas.

Efter perioden ska en rapport ge:
1. kvantifierad överlappning och källunika händelser,
2. kvalitet per fält och källornas geografiska precision,
3. aktualitet och uppdateringsmönster,
4. driftsäkerhet och snapshotintegritet,
5. kända begränsningar och felmoder,
6. rekommendation: behåll båda, välj en eller använd en som kompletterande källa.

Ingen källa får klassas som komplett polisregister. Polisen beskriver sitt eget innehåll som ett urval av utryckningar. 500-postersgränsen innebär också att historisk täckning måste bedömas utifrån de egna snapshots som faktiskt har samlats in.

## Rättigheter och publicering

Polisens öppna data-regler och publiceringsvillkor ska följas. API-åtkomst är inte i sig ett generellt beslut om kommersiell kundvisning eller vidare distribution. Bevara källa, hämtningstid och länk till originalnotis. Rätt till lagring, bearbetning, härledda analyser, kundvisning och vidare distribution bedöms separat innan produktionsanvändning.

## Officiella källor

- [Polisens API över händelser](https://polisen.se/om-polisen/om-webbplatsen/oppna-data/api-over-polisens-handelser/)
- [Polisens API-regler](https://polisen.se/om-polisen/om-webbplatsen/oppna-data/regler-for-oppna-data)
- [Polisens händelse-API](https://polisen.se/api/events)
- E-post från Polismyndighetens IT-kansli 2026-11-27, diarienummer A698.287/2026.
- Befintlig pipeline: [police-events-norrbotten.md](police-events-norrbotten.md).

## Initial live-run and Azure access gate (2026-11-28)

A read-only review of GitHub Actions schedule history retrieved all 467 scheduled runs currently exposed by the repository API (2026-10-24 through 2026-11-28). It found **no run** for `.github/workflows/polisen-official-api-evaluation.yml`. Existing scheduled runs for `.github/workflows/police-events.yml` are present and successful on 2026-11-22 through 2026-11-27. The official API workflow is present on `main`, but its expected daily execution has not yet been evidenced. The reason for the missing run is not established.

The workflow previously had only a `schedule` trigger, so an operator could not start a controlled first run from the Actions UI. PR adds `workflow_dispatch` without changing the daily schedule, API request, capture validation, storage path, or upload behavior. After merge, trigger one manual run from `main` and inspect its job logs and Azure objects before counting the first snapshot or starting the 30-day clock.

### Azure access boundary for PM-027

The PM repository's existing `project-manager-publisher` identity is documented as `Storage Blob Data Contributor` on the `project-manager` container only. It cannot be assumed to read the Skog `police-events` container. The Skog repository's existing `skogskoll-github-actions` identity is documented with `Storage Blob Data Contributor` at Storage Account scope and is shared by several workflows; it must not be reused in the PM repository or have its scope changed as part of this work.

Preferred design for PM-027 is a separate Entra service principal/federated credential restricted to the PM repository and a dedicated GitHub Actions environment, with `Storage Blob Data Reader` scoped only to container `police-events`. This is a required Azure administrator setup and live authorization check, not yet configured or verified. Until then, PM-027 must leave the official Police API's snapshot evidence as unknown rather than infer that no snapshots exist.

No source data, snapshot, manifest, history, customer view, alert, or rights status was changed by this investigation.

## Polismyndighetens officiella API – första verifierade snapshot (2026-11-28)

Den manuella körningen [Police official API evaluation snapshots #1](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46134508242) genomfördes från `main` efter merge av [PR #725](https://github.com/dahlinrobert-lgtm/Skog/pull/725). Workflow-run ID: `46134508242`; commit: `0c0f2f4a9c235a91b69dd252a5e5464428b160b2`; event: `workflow_dispatch`; status `completed/success`.

Capture-steget rapporterade `status=complete`, **500 poster**, varav **43 Norrbottenposter** (`location.name=Norrbottens län`), hämtade `2026-11-28T10:18:33.505969+00:00`. Azure OIDC-inloggningen lyckades. Uploaderloggen rapporterade:
- blob: `polisen-official/runs/46134508242/attempt-1/snapshot.json.gz`
- råstorlek: `179666` bytes
- rå SHA-256: `b1dbd8e467d9987115d493034f0d264ab4d9887664c658ebf32a583c4412498a`
- `snapshot_verified=true`, 500 poster och 43 Norrbottenposter.

Verifieringsgräns: uploaderkoden laddar ned den komprimerade blobben i samma jobb, gzip-dekomprimerar och jämför rå byte count samt SHA-256 innan den skapar `manifest.json`. Jobbloggen visar därefter `snapshot_verified=true`, och hela steget avslutades success. Manifestobjektets exakta JSON-innehåll och Azure-systemmetadata har däremot inte lästs separat i denna granskning, eftersom aktuell ansluten GitHub-/SharePoint-integration inte erbjuder Azure Blob-läsning. Detta ska inte beskrivas som en oberoende Azure-manifestinspektion.

**Utvärderingsstart:** första lyckade, kompletta och uploader-verifierade snapshot är 2026-11-28. 30 kalenderdagarsperioden räknas från denna snapshot; målet är minst 25 lyckade dagliga snapshots. Denna första snapshot är baslinje och ska inte skapa retroaktiva händelser eller kundlarm. Nästa dags snapshot behövs för att börja bedöma kontinuitet och förändringar.

Ingen sammanfogning med Brottsplatskartan-historiken görs. API:ets 500 aktuella poster är ett begränsat publicerat urval, inte ett komplett historiskt polisregister. Koordinater behandlas inte som exakta händelsepositioner. Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution förblir separata rättighetsgrindar.
