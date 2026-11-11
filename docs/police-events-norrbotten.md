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


## Geografisk matchning mot NVR

Det operativa analysmålet är att koppla polisens dagliga, textbaserade viltolyckshändelser till NVR:s olycksposter med exakta koordinater. Källorna ska inte behandlas som om de hade samma geografiska precision:

- NVR är den geografiska referensen för koordinatsatta olyckor. NVR:s djurposter måste vid behov aggregeras till en olyckshändelse så att flera djur från samma kollision inte blir flera olyckor.
- Polisens platsuppgifter kan vara ortnamn, vägnummer, väg-/gatunamn, sträckor mellan platser eller fritext. Polisens generella händelsekoordinat får inte automatiskt betraktas som olycksplatsens exakta koordinat, särskilt för sammanfattningar med flera händelser.
- Ursprunglig platsbeskrivning, käll-ID, publiceringstid, möjlig olyckstid, textutdrag och payloadversion ska bevaras. Geokodade resultat lagras separat från källposten.

### Matchningsmodell

1. Extrahera enskilda olyckspåståenden ur polisens händelsetext. En sammanfattning med flera olyckor ska ge separata kandidater; antal utan individuell plats eller tid är inte individuellt matchbara.
2. Tolka platsreferensen och klassificera dess geometri: punkt, vägsträcka, ort/område eller olöst fritext. Geokodning ska ge källa, metod, precision/utbredning och status – inte bara latitud/longitud.
3. Skapa kandidatpar mot NVR med tidsfönster, djurslag och geografiskt avstånd/överlapp. För en vägsträcka används avstånd till linje/sträckgeometri; för en ort eller ett område används dess utbredning och lägre geografisk säkerhet.
4. Spara varje möjligt par med matchningspoäng, delkomponenter, metodversion och granskningsstatus. En matchning är inte en bekräftad identitet enbart för att tid och plats ligger nära.
5. Håll statusarna åtskilda: bekräftad, sannolik, möjlig, avvisad och ej matchningsbar. Tillåt att en polispost innehåller flera olyckor och att flera NVR-djurposter hör till en olycka.

### GIS- och Power BI-underlag

Det långsiktiga utdataformatet bör vara separata, relationsbara tabeller: polisens händelser/versioner, extraherade polisolyckskandidater, geokodade platsreferenser/geometrier, NVR-olyckor (aggregerade från djurposter) och matchningskandidater. GIS ska kunna visa NVR-punkter, polisens geokodade punkter/linjer/områden och matchningsrelationer. Power BI ska kunna använda samma nycklar och tabeller utan att behöva återskapa geokodning eller matchningslogik i DAX.

Ingen automatisk matchning ska presenteras som säker innan den har validerats mot ett granskat urval. Publiceringsdatum får inte ersätta olyckstid när den senare kan utläsas, och polisens koordinat på sammanfattningsnivå får inte kopieras till varje olyckskandidat.
