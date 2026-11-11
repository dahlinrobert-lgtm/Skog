# Polisens händelseflöde – Skogskoll

Separat arkiv över offentligt publicerade polishändelser i Norrbottens län. Det är ett kompletterande observationsmaterial, inte officiell brottsstatistik eller ett komplett register över polisens insatser.

## Pipeline

- `scripts/ingest_police_events.py` hämtar Brottsplatskartans API med `area=Norrbottens län`.
- `data/police_events/events.csv` innehåller senaste normaliserade versionen per händelse-ID.
- `data/police_events/raw_events.jsonl` är ett append-only versionsarkiv. Nya händelser och ändrade payloads sparas med hämtningstid och SHA-256.
- `data/police_events/wildlife_candidates.csv` är en bred textbaserad kandidatutvinning.\n- `scripts/extract_police_wildlife_incidents.py` delar ut relevanta textstycken och uttryckliga antal till separata olyckskandidater. Resultatet skrivs till `data/police_events/wildlife_incidents.csv` med käll-ID, publiceringsdatum, möjlig händelsetid, plats, djurslag, extraktionsmetod och granskningsstatus.
- GitHub Actions kör daglig uppdatering. En manuell körning kan hämta hela tillgängliga historiken.

## Start

Kör workflowet **Police events archive (Norrbotten)** manuellt med `full=true` för historisk bootstrap. Därefter hämtar schemakörningen de fem senaste API-sidorna och sparar nya eller ändrade poster.

## Begränsningar och metod

- Extraktionen av enskilda viltolyckskandidater är en separat, förenklad parser inspirerad av formatet i `Lulea-statistik/Lulea-polishandelser`; den är inte en fullständig kopia av deras sammanfattningsparser.
- Sammanfattningar kan innehålla flera separata olyckor. Extraktionen kan missa eller felaktigt dela upp händelser. Alla poster i `wildlife_incidents.csv` är granskningskandidater, inte verifierade olyckor. Uttryckliga antal utan individuell plats/tid får låg konfidens.
- Publiceringsdatum är inte nödvändigtvis olycksdatum. NVR-matchning ska använda faktiskt händelsedatum/tid när det kan beläggas.
- Flera djur i samma kollision får inte räknas som flera olyckor.
- Polis- och NVR-poster bevaras separat. Matchningar ska lagras i en separat korsreferenstabell med poäng, metodversion och granskningsstatus.
- Geografin är avgränsad till Norrbottens län i denna första kopia. Västerbotten och övriga Polisregion Nord kräver en separat utbyggnad och validering.

## Källor

- Brottsplatskartan API: https://brottsplatskartan.se/sida/api
- Ursprungsdata publiceras av Polismyndigheten.
