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
