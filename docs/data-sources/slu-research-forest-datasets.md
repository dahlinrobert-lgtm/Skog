# SLU research datasets – source screening for Skog

Screening date: 2026-11-03

## Purpose
Identify complementary forest datasets in the SLU research-data catalogue that can enrich Skog's event-based monitoring feed. The catalogue contains research datasets with different geographic coverage, temporal scope, access conditions and intended uses. It is not itself a single operational national data service.

## Priority screening

| Dataset/source | Content and temporal scope | Potential use in Skog | Screening priority / caveat |
|---|---|---|---|
| Sample tree data from the Swedish National Forest Inventory | Sample trees >=10 cm DBH. Includes measurements/coring from 1923–1929, 1953–1962, 1983–1992 and 2013–2022 surveys; species, diameter, age and expansion factors. | Long-term forest structure, species/age context, model validation and educational insights. | High research value, but sample-plot/tree data; do not present as wall-to-wall parcel information. Check coordinate precision, access and reuse terms. DOI 10.5878/k65t-qb32. |
| TFDI bark beetle damage inventory – Götaland and Svealand 2023 | Target-tailored forest damage inventory published 16 Apr 2026. | Specific forest-damage event layer, possible validation and historical context for bark-beetle damage. | High thematic value, geographically limited to Götaland/Svealand; inspect file geometry, observation date, attributes and licence before integration. DOI 10.5878/keeg-1938. |
| TFDI spruce bark beetle – Götaland and Svealand 2022 | Target-tailored inventory of spruce bark beetle damage. | Damage events and comparison with satellite/laser scan observations. | High thematic value, limited geography. DOI 10.5878/eref-hz37. |
| TFDI spruce bark beetle – Götaland and Svealand 2021 | Target-tailored inventory. | Historical damage series and detection-lag validation. | Regional coverage, check overlap with other years. DOI 10.5878/59bw-a884. |
| TFDI spruce bark beetle – Götaland and Svealand 2020 | Target-tailored inventory. | Historical damage series. | Regional coverage. DOI 10.5878/hzzy-qm08. |
| TFDI bark beetle – Västernorrland/eastern Jämtland 2014–2016 | Local/regional inventories linked to damage events. | Potentially useful for northern Sweden and long historical event context. | Especially relevant geography for a northern test, but old and event-specific. DOI 10.5878/036v-fm23 (2014); 2016 dataset also listed in catalogue. |
| TFDI bark beetle – Västernorrland 2011/2012 | Local/regional damage inventories. | Longer historical damage context. | Limited geography and dated surveys. DOI 10.5878/9cjq-b297 (2011); DOI 10.5878/yx8y-fj42 (2012). |
| TFDI resin top disease in young pine, 2012 | Inventory in coastal Norrbotten and southern Västerbotten. | Northern forest damage/health context, particularly valuable for Gräsmyr/Hörneå-region screening if geometries overlap. | High geographic relevance; narrow target disease and sample design. DOI 10.5878/hbrr-a912. |
| TFDI resin top disease in young pine, 2007 | Targeted inventory of young pine forest damage in northern Sweden. | Long-term damage context. | Very old, limited scope; check overlap and coordinate availability. DOI 10.5878/n1c5-vw84. |
| Riksskogstaxeringen – annual Skogsdata | Annual official statistics and thematic analyses. | National/regional context in feed insights and aggregated trend cards. | Useful, but primarily aggregated statistics rather than parcel-level event data. |
| Riksskogstaxeringen sample-plot validation data | Selected temporary sample plots, annual release; includes forest age, height, density, volume, site and vegetation variables. | Validate raster estimates and quantify uncertainty/bias. | The catalogue explicitly warns that boundary plots are excluded and the dataset should not be used to estimate area totals or means. Do not treat as a representative area sample. |

## Existing reference datasets to compare
- Skogliga grunddata: 10 m raster estimates for volume, basal area, mean height, mean diameter and biomass, combining Lantmäteriet laser data and NFI field plots. This remains a core observation/metrics source, not just a research-dataset discovery.
- SLU Skogskarta: satellite/field-data-derived forest products including tree-species maps. Potentially complements laser-derived metrics; assess product vintage and spatial resolution.
- Riksskogstaxeringen statistics and microdata: separate aggregate-statistics and controlled/research microdata pathways.
- SLU Forest Damage Centre dataset directory: curated references to forest-damage sources, potentially useful for discovering sources beyond the research catalogue.

## Recommended integration pattern
Do not bulk-ingest all research datasets. Maintain a source registry with:
- dataset title, DOI, publisher, licence/reuse terms and source URL;
- geographic footprint and CRS;
- observation period and publication/update date as separate fields;
- spatial support (wall-to-wall raster, polygon inventory, sample plots, aggregated statistics);
- variables, units and event/date semantics;
- access method, file format, size and update cadence;
- validation status and known sampling/design caveats.

For Skog's event model, keep research observations separate from operational events:
1. Observed forest condition / damage inventory;
2. operational or administrative event (planned/completed harvest, fire, nature conservation action);
3. sensor observation (laser scan, satellite acquisition);
4. derived interpretation / spatial-temporal relationship.

## First recommended pilots
1. Inspect the resin-top-disease dataset for Norrbotten/coastal Västerbotten (2012), because its geography is potentially relevant to northern monitoring and it offers a historical forest-health event layer.
2. Inspect the northern TFDI bark-beetle datasets for Västernorrland/eastern Jämtland (2014–2016) and test whether there is useful geometry and event-date information.
3. Inspect one Götaland/Svealand recent bark-beetle TFDI (2023) as a quality/format benchmark.
4. Review NFI sample tree and plot-validation datasets for appropriate validation use, not direct parcel-level mapping.
5. Evaluate SLU Skogskarta tree-species rasters as an additional forest attribute source, with careful treatment of vintage and model uncertainty.

## Product implications
Research-derived datasets can power carefully qualified "Did you know?" posts, for example that a disease inventory was conducted in a region or that historical samples indicate particular forest structures. Such posts must state survey year, geographic coverage, sample design and dataset source. A research inventory must not be phrased as a current or exhaustive national condition map.

## Source links
- SLU Research datasets: https://research.slu.se/en/datasets/
- SLU Department of Forest Resource Management datasets: https://research.slu.se/en/organisations/department-of-forest-resource-management/datasets/
- Sample tree data: https://research.slu.se/en/datasets/sample-tree-data-from-the-swedish-national-forest-inventory/
- SLU forest damage dataset directory: https://www.slu.se/om-slu/organisation/centrumbildningar/slu-skogsskadecentrum/verktyg-och-faktasidor/dataset-om-skog-och-skogsskador/
- Skogliga grunddata: https://www.slu.se/miljoanalys/statistik-och-miljodata/miljodatakatalogen/skogliga-grunddata/
- SLU Skogskarta and national forest estimates: https://www.slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/omraden/skoglig-fjarranalys/skogliga-kartproduktion/
- Riksskogstaxeringen data: https://www.slu.se/om-slu/organisation/institutioner/skoglig-resurshushallning/miljoanalys/riksskogstaxeringen/vara-data/
