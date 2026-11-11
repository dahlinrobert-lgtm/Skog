# Polisens händelseflöde – Skogskoll

Separat arkiv över offentligt publicerade polishändelser i Norrbottens län. Det är ett kompletterande observationsmaterial, inte officiell brottsstatistik eller ett komplett register över polisens insatser.

## Pipeline

- `scripts/ingest_police_events.py` hämtar Brottsplatskartans API med `area=Norrbottens län`.
- `data/police_events/events.csv` innehåller senaste normaliserade versionen per händelse-ID.
- `data/police_events/raw_events.jsonl` är ett append-only versionsarkiv. Nya händelser och ändrade payloads sparas med hämtningstid och SHA-256.
- `data/police_events/wildlife_candidates.csv` är en textbaserad kandidatutvinning för viltolyckor. Den är avsiktligt preliminär och ska inte tolkas som verifierade olyckor.
- GitHub Actions kör daglig uppdatering. En manuell körning kan hämta hela tillgängliga historiken.

## Start

Kör workflowet **Police events archive (Norrbotten)** manuellt med `full=true` för historisk bootstrap. Därefter hämtar schemakörningen de fem senaste API-sidorna och sparar nya eller ändrade poster.

## Begränsningar och metod

- Detta första steg kopierar insamlingsmönstret från `Lulea-statistik/Lulea-polishandelser`, men inte dess kommuninferens, sammanfattningsparser eller kvalitetsgranskade händelseklassificering.
- Sammanfattningar kan innehålla flera separata olyckor. Textmatchningen kan missa olyckor eller ge falska träffar; därför heter filen `wildlife_candidates.csv`.
- Publiceringsdatum är inte nödvändigtvis olycksdatum. NVR-matchning ska använda faktiskt händelsedatum/tid när det kan beläggas.
- Flera djur i samma kollision får inte räknas som flera olyckor.
- Polis- och NVR-poster bevaras separat. Matchningar ska lagras i en separat korsreferenstabell med poäng, metodversion och granskningsstatus.
- Geografin är avgränsad till Norrbottens län i denna första kopia. Västerbotten och övriga Polisregion Nord kräver en separat utbyggnad och validering.

## Källor

- Brottsplatskartan API: https://brottsplatskartan.se/sida/api
- Ursprungsdata publiceras av Polismyndigheten.
