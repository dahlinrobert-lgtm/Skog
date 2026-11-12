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


## Lantmäteriet Belägenhetsadresser – verifierad Luleå-pilot 2026-11-12

A local, authenticated pilot download was completed for municipality 2580 (Luleå) from the STAC collection `belagenhetsadresser`.

- STAC item update: `2026-11-12T11:39:18.362000Z`.
- Declared CRS: EPSG:3006 (SWEREF 99 TM).
- ZIP size: 2,550,332 bytes; matches the STAC-declared size.
- ZIP member: `belagenhetsadresser_kn2580.gpkg` (11,018,240 bytes).
- ZIP SHA-256: `49F791F99F1B829B8E655FDF835EA7752C944DC114E9A609F127D551704E0620`.
- GeoPackage feature layer: `belagenhetsadress`, POINT geometry column `adressplatspunkt`, EPSG:3006.
- Attribute table `adressplatsanmarkning` contained zero rows in this municipality snapshot.

The feature layer contained 32,372 rows and 32,372 distinct, non-empty `belagenhetsadress_objektidentitet` values. All rows had an address-area name, address number, postal code and municipality name; 61 rows lacked postal locality. The observed type/status counts were:

- `Gatuadressplats`: 32,294; `Byadressplats`: 78.
- `Gällande`: 32,315; `Reserverad`: 57.

Field coverage relevant to place interpretation:

- `kommundel_faststalltnamn` was populated on all rows but had only the value `Luleå` in this municipal extract; it therefore does not distinguish Luleå neighbourhoods in this snapshot.
- `adressomrade_faststalltnamn` was populated on all rows and contains street/address-area names (for example Professorsvägen, Snövägen, Docentvägen and Storgatan).
- `gardsadressomrade_faststalltnamn` was empty on all rows.
- `popularnamn` was populated on 17 rows only (including Nytorget, Köpmantorget and several hospital/entrance labels).
- `anlaggningstyp` was populated on 105 rows, all observed as `Avloppspumpstation`; `anlaggningstext` was populated on 104 rows.
- 57 reserved addresses are not equivalent to current, valid addresses and must be treated separately from `Gällande`.

This is a verified local pilot snapshot, not a national acquisition or a statement that the product contains all named places. The ZIP and extracted GeoPackage remain in the user's OneDrive working area; no raw geodata or credentials are committed to this repository. Ordinary Python SQLite could inspect table metadata and attributes, but spatial SQL functions such as `ST_MinX` were not available in the local SQLite connection. Coordinate extent and geometry validation remain pending a GeoPackage-aware GIS library/tool.

### Consequences for the existing matching pilot

Police event text is often richer in context than the NVR row (neighbourhood/area, street, road number, local facility/building/place name), while its published geographic point can be imprecise and can refer to a summary containing multiple incidents. The NVR record is a separate coordinate-based comparison source. Therefore:

1. Reuse the existing Police archive, `wildlife_candidates.csv` and `wildlife_incidents.csv`; do not create a second Police collection or treat extracted rows as confirmed incidents.
2. Keep each extracted incident statement and its original text, parent Police event ID, publication date, inferred occurrence date/time and date-basis metadata. A summary-level coordinate must not be copied to every incident statement.
3. Treat Lantmäteriet Belägenhetsadresser as the primary **address** reference, not as a complete gazetteer of neighbourhoods, facilities, buildings, named places or road sections. Its Luleå pilot's `kommundel_faststalltnamn` value is only the municipality name, and its `popularnamn` coverage is sparse.
4. Generate separate candidate types for address, named road/place, official road number, junction and locality/area. Use NVDB for explicit road-number references. Use a separately validated named-place/locality source for areas and facilities; the OSM address-only extract is not sufficient for this purpose.
5. Keep address-point matches distinct from road-line and area/polygon matches. Do not turn a nearest address point into the asserted collision location when the Police text only names a neighbourhood or road section.
6. Compare Police incident candidates with NVR event-level points using occurrence time/date, species, municipality/locality context and geometry-appropriate distance/overlap. Preserve ambiguous, unmatched and count-only candidates.
7. Publish a separate, versioned candidate/match table with source snapshot/checksum, reference object ID, geometry type, distance/overlap, method version, evidence and review status. Never alter Police source records or NVR source coordinates.

The next implementation gate is to run the existing Police candidate extractor against the already archived dataset and inspect the Luleå subset of individual, time-bearing incident statements. Then test address-name and road/place candidate generation against the verified Luleå address snapshot, while explicitly measuring the cases that require a named-place/area or NVDB reference. Do not set distance thresholds or declare automatic matches before a manually reviewed sample exists.
