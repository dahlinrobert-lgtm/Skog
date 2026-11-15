# Police–NVR geographic match model (design v0.1)

**Status:** design proposal; not implemented in the matching pipeline  
**Scope:** internal Luleå Police–NVR pilot, review-only  
**Branch:** `feat/police-nvr-geographic-match-model`

## 1. Purpose

Build an explainable model that evaluates whether an NVR event coordinate is geographically compatible with an informal Police incident description. Police text is often short and written under time pressure. A road name in the text should therefore be interpreted as a practical road context, not as a requirement that the coordinate falls on the exact NVDB line feature carrying that road number.

The model is intended to rank candidate pairs for human review. It must not confirm or reject a collision automatically.

## 2. Core separation

Keep these stages distinct:

1. **Temporal candidate generation** – existing logic, unchanged.
2. **Police-text interpretation** – extract road number/name, locality, between-endpoints wording, direction and other location cues.
3. **Road-context construction** – construct one or more candidate road corridors/segments from NVDB.
4. **Geographic evidence** – measure the NVR coordinate against each candidate corridor and its named place references.
5. **Combined review score** – combine temporal, species, road-context, distance and place evidence without changing the temporal result.
6. **Human review** – preserve alternatives and source evidence; no automatic confirmation.

The original Police and NVR source rows remain unchanged. All derived outputs must retain source IDs, input versions, run ID and model version.

## 3. Road-context interpretation

### 3.1 Direct road match

If the NVR point lies close to a road feature with the explicitly stated road identity, record direct-road evidence.

### 3.2 Ramp attached to a named road

A feature classified as an exit/entrance ramp may be treated as part of the named major-road context when a verifiable network relationship shows that it connects to that road. The output must retain both:
- physical NVDB feature identity and feature type;
- inherited/associated road identity and the evidence used to establish the association.

A nearby ramp is not sufficient by itself. Spatial proximity alone must not create a network connection.

### 3.3 Connector between two major roads

Where a connector or interchange ramp links two named major roads (for example E4 and E10), retain both road identities as possible contexts when supported by the network topology. Do not arbitrarily assign the connector to only one road.

If the Police text names one of the roads, that road receives the explicit-text relationship; the other remains a connected alternative. If the text does not distinguish them, preserve the ambiguity for review.

### 3.4 Road segment between two places

For wording such as “riksväg 97 mellan Södra Sunderbyn och Notviken”, construct candidate geometry from the stated road network and both place anchors. Do not bridge disconnected road components. Preserve all plausible anchor-pair/route alternatives where more than one is possible.

### 3.5 Road near a place / cross-level wording

For wording such as “E4, Norra Rutvik” or “E4 i höjd med Måttsund”, interpret the locality as a search context along the named road, not as an exact point at a settlement label. Ortnamn points may be cartographic label placements; they are not exact settlement centres, boundaries or incident positions.

## 4. Coordinate selection and candidate corridors

The geographic model should not choose a road route merely because it is closest to the NVR point. That would use the outcome being evaluated to select its own reference and could bias the distance evidence.

Instead:

1. Build road-context alternatives from the Police text, NVDB attributes and verified topology.
2. Select/retain alternatives using road identity, named anchors and network connectivity only.
3. Measure the NVR coordinate to every retained alternative.
4. Keep the nearest distance per alternative and the alternative's road/feature lineage.
5. If multiple alternatives remain plausible, retain all of them and mark the result ambiguous.

A corridor width or distance threshold is a diagnostic parameter, not a claim that the underlying incident coordinate is exact.

## 5. Provisional review score (not a probability)

A future implementation may use a 0–100 ordinal score as a review-priority aid. The initial proposed allocation is:

| Evidence group | Maximum | Proposed interpretation |
|---|---:|---|
| Temporal fit | 30 | Based on absolute time difference; reuse the raw time delta and the existing temporal category, not the existing ordinal score as if it were a probability |
| Species | 15 | Known species agreement; unknown/missing is neutral/weak, not a conflict |
| Road-context relationship | 25 | Direct named road, verified connected ramp, or verified connector between named roads |
| NVR coordinate to candidate corridor | 20 | Distance to the independently constructed corridor, with coordinate quality retained |
| Place-name consistency | 10 | Named NVDB/Ortnamn context supports the Police text |

The weights and thresholds are hypotheses for evaluation, not validated parameters. Avoid double-counting correlated evidence: road-context relationship and distance should be stored separately and inspected together. Known species conflicts remain governed by the existing temporal candidate rules and must not be silently overridden by geography.

Suggested descriptive bands for a future review UI are **high / medium / low / insufficient evidence**. These labels must not be called probabilities or calibrated confidence until a manually labelled evaluation set supports calibration.

A missing layer, unavailable topology, missing coordinate or failed enrichment is **unknown evidence**, not negative evidence. It must not automatically lower a candidate to “no match”.

## 6. Required output evidence

For each Police–NVR candidate pair, retain at least:

- original Police candidate ID and NVR year-qualified event ID;
- exact Police source text and parsed cue fields;
- temporal delta, temporal band and species evidence;
- NVR coordinate and coordinate-quality/source fields;
- candidate road corridor ID and source NVDB element IDs;
- direct vs inherited/connected road identity;
- ramp/connector feature type and verified connectivity evidence;
- all candidate route/anchor alternatives and selection rationale;
- distance to each candidate corridor;
- named-place evidence and its source/type;
- model version, thresholds, run ID and input dataset versions;
- review status and reviewer decision, when available.

Do not overwrite source coordinates or original source records.

## 7. Safety and regression invariants

- Geographic enrichment must not change temporal candidate inclusion, temporal score, temporal status or `geographic_match_used`.
- No automatic match confirmation or rejection.
- Do not infer connectivity from proximity alone.
- Do not force a ramp to one road where topology supports more than one.
- Do not choose a route using the NVR point and then use distance to that route as independent evidence.
- Keep delayed-event candidates in their separate output and do not treat the NVR `Datum` field as a verified recovery/search timestamp.
- Incomplete or unavailable geodata must not remove temporal candidates.
- Keep all competing Police–NVR links for manual review.

## 8. Evidence needed before implementation

The current enrichment script reads road fields `ELEMENT_ID`, `Europavag`, `Huvudnummer`, `Lankroll` and crossing fields `ELEMENT_ID`, `Generaliseringstyp`, `Ingar_i_trafikplats`, `Namn`, `Trafikplatsnamn`. These fields support road identity and named crossing context, but the inspected code does not yet establish a verified topology relationship between a ramp and one or more major roads.

Before implementing inherited road identity, inspect the actual NVDB product schema and data for:
- stable link/node identifiers or explicit from/to connectivity;
- road-number assignment on ramps/connectors;
- link role and functional road classification;
- grade-separated crossings and junction representation;
- whether one ramp can legitimately connect multiple numbered roads.

Do not substitute endpoint snapping alone for authoritative connectivity where grade separation or parallel carriageways may be present.

## 9. NVDB topology model – verified public documentation

Trafikverket's public NVDB documentation describes the road network using network elements:
- **Reference link (referenslänk):** a directed road section starting at one node and ending at another; reference links have stable identities and are used to describe network topology.
- **Node (nod):** a network connection point, normally where a route choice is possible, and also used at road endpoints.
- **Port (port):** a connection point owned by a network element. Network connections are represented as port-to-port links; the connected ports point to one another.
- **Reference link parts (referenslänkdelar):** time-valid portions of a reference link.

Official references:
- [Trafikverket – Dataproduktspecifikationer, vägdata](https://bransch.trafikverket.se/tjanster/data-kartor-och-geodatatjanster/leverera-in-data/data-om-anlaggningen--vag/dataproduktspecifikationer-vag--och-vagtrafikdata/) – definitions of reference links, nodes, ports and identities.
- [Trafikverket – Introduktion till NVDB:s vägnät och företeelser (PDF)](https://bransch.trafikverket.se/contentassets/e0faf1739d244cb384aadf8c1f7a91dd/introduktion-till-nvdbs-vagnat-och-foreteelser.pdf) – describes how features are located on the network using reference-link object identity and relative positions.
- [NVDB – Hämta aktuella data](https://www.nvdb.se/sv/kund/hamta-aktuella-data/) – lists current open-API datasets including Vägnummer and Vägtrafiknät, and points to Lastkajen for historical data.
- [Trafikverket – Ruttning med NVDB](https://lastkajen.trafikverket.se/assets/Ruttning_med_NVDB.pdf) – explains why a single feature layer's geometries should not be treated as a complete routable network.

**Important implication:** the current enrichment's road-number and crossing feature layers are not, by themselves, proof of network connectivity. A road-number feature may be located along a reference link; a separate road-network product may be required to retrieve link/node/port topology. Endpoint proximity or shared geometry alone is not enough to assert a connection, especially at grade-separated junctions.

### Read-only schema inventory utility

The branch adds `scripts/inspect_nvdb_network_schema.py`. It inventories GeoPackage layer names, geometry types, feature counts, CRS and field names, highlighting possible topology fields. It does not export feature rows, infer connectivity or modify the source file.

Run locally against the exact NVDB GeoPackage intended for the pilot:
```bash
python scripts/inspect_nvdb_network_schema.py \\
  --gpkg /path/to/nvdb-network.gpkg \\
  --output /path/to/nvdb-network-schema-report.json
```
The field-name matches are discovery hints only. After inspection, compare the actual fields with the relevant official product specification and inspect relationship values before implementing graph traversal.

## 10. Evaluation plan

1. Build a manually labelled Luleå sample containing positive, negative and ambiguous pairs.
2. Include the current cases:
   - positive candidates: `506427:1 → 2026-348394`, `508827:2 → 2026-356616`, `509449:1 → 2026-358582`, `509449:2 → 2026-358465`;
   - negative controls: `506427:1 → 2026-348777`, `509449:1 → 2026-360471`;
   - ambiguous/competing links: `509449:1 → 2026-358465` and delayed candidates.
3. Keep the manual labels separate from model output to avoid training/evaluating on labels that were generated by the model.
4. Compare temporal-only and combined review rankings. Confirm that temporal outputs are byte-for-byte or semantically unchanged.
5. Inspect false positives and false negatives before tuning weights or distance bands.
6. Only after a sufficiently large, representative labelled sample exists, evaluate calibration (for example precision/recall and reliability of predicted probabilities). Until then, report ordinal review scores only.

## 11. Current implementation status

- Existing `scripts/enrich_police_nvr_geography.py` provides review-only nearest-road, named-crossing and named-segment evidence.
- Existing segment construction uses the stated road number and named anchors, and flags multiple anchor-pair candidates.
- Existing enrichment does not yet assign ramp/connector features an inherited major-road identity through verified network topology.
- The 36-row local named-place distance export is review evidence only; it does not establish the network schema or topology.
- The read-only schema inspector and its tests are added in a separate implementation branch; it has not yet been run against the user's local NVDB GeoPackage.
- No temporal matching logic, source data or production ingestion is changed.
