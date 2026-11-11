# Polisens händelseflöde – Skogskoll

Separat observationsarkiv över offentligt publicerade polishändelser i Norrbottens län. Materialet är ett komplement, inte officiell brottsstatistik eller ett komplett register över polisens insatser.

## Pipeline och lagring

- `scripts/ingest_police_events.py` hämtar Brottsplatskartans API med `area=Norrbottens län`.
- `data/police_events/events.csv` innehåller den senaste normaliserade versionen per händelse-ID.
- Råa händelsepayloads och versionshistorik lagras som oföränderliga körningssegment i Azure Blob Storage, i containern `police-events`.
- Segmentnamn följer `runs/{run_id}/attempt-{attempt}/raw_events.jsonl.gz`; ett manifest sparas bredvid varje segment.
- Uppladdningssteget verifierar råbytes och SHA-256 genom att läsa tillbaka och kontrollera segmentet innan körningen fortsätter.
- Råsegment skapas i en isolerad temporär fil i GitHub Actions. Insamlingsskriptet kräver nu uttryckligen `--raw-output` för att förhindra att råhistorik av misstag skrivs tillbaka till Git.
- `data/police_events/wildlife_candidates.csv` är en bred textbaserad kandidatutvinning.
- `data/police_events/wildlife_incidents.csv` innehåller separata olyckskandidater med käll-ID, publiceringsdatum, möjlig händelsetid, plats, djurslag, extraktionsmetod och granskningsstatus.
- `data/police_events/run_quality_report.json` sammanfattar arkivets omfattning och kvalitetsindikatorer.

## Körning

Workflowen **Police events archive (Norrbotten)** körs dagligen. En manuell körning med `full=true` hämtar tillgänglig historik; standardkörningen hämtar de fem senaste API-sidorna. Varje körning får ett separat Azure-segment.

## Begränsningar och metod

- Extraktionen av enskilda viltolyckskandidater är en förenklad parser och inte en fullständig kopia av någon annan sammanfattningsparser.
- Sammanfattningar kan innehålla flera separata olyckor. Extraktionen kan missa eller felaktigt dela upp händelser. Alla poster är granskningskandidater, inte verifierade olyckor. Uttryckliga antal utan individuell plats/tid får låg konfidens.
- Publiceringsdatum är inte nödvändigtvis olycksdatum. NVR-matchning ska använda faktiskt händelsedatum/tid när det kan beläggas.
- Flera djur i samma kollision får inte räknas som flera olyckor.
- Polis- och NVR-poster bevaras separat. Matchningar ska lagras i en separat korsreferenstabell med poäng, metodversion och granskningsstatus.
- Geografin är avgränsad till Norrbottens län i denna första kopia. Västerbotten och övriga Polisregion Nord kräver separat utbyggnad och validering.
- En lyckad körning eller ett visst antal poster bevisar inte att API-historiken är komplett.

## Källor

- Brottsplatskartan API: https://brottsplatskartan.se/sida/api
- Ursprungsdata publiceras av Polismyndigheten.
