# Skog data platform

Forest-specific data integration foundation. The architecture and initial contracts are documented in [docs/data-platform-architecture.md](../docs/data-platform-architecture.md).

## Current stage

This folder contains the source registry, initial logical contracts and a first machine-validated event-bundle contract. The event bundle is a synthetic contract example, not yet a production event pipeline. This folder does not itself run connectors, schedule jobs, or publish customer datasets.

The source registry now includes a first-pass commercial reuse assessment. Read [the open-data and commercial-use register](../docs/open-data-and-commercial-use.md) before adding a source or publishing data to customers. Registry status is a project risk classification, not a legal opinion or a substitute for product-specific terms.

## Principles

- Preserve raw source payloads and original raster assets.
- Make ingestion idempotent and auditable.
- Keep source-record identity separate from canonical forest-domain identity.
- Publish only complete, validated runs.
- Keep source-specific logic inside connectors.
- Preserve existing Skogskoll ingestion and alert-safety behavior.
- Treat commercial use, historical storage, derivatives, customer display and raw-data redistribution as separate rights checks.

## Files

- `config/sources.yml`: source, rights and operational registry (no credentials); optional `provenance` and `operations` blocks extend selected records without changing the canonical event model. Operational fields distinguish access, snapshots, history, commercial-use status and customer-display status.
- `scripts/validate_source_registry.py`: validates registry structure, unique source IDs, optional provenance metadata and controlled operational status fields.
- `schemas/event-bundle.schema.json`: JSON Schema contract for source runs, immutable observations, canonical events, evidence, relationships and event chains.
- `scripts/validate_event_bundle.py`: validates the event bundle schema and cross-record references; run with `python data-platform/scripts/validate_event_bundle.py`.
- `examples/event-bundle.example.json`: synthetic example showing one registered event and a one-event chain; it is not live source data.
- `scripts/collect_actions_in_water_sample.py`: read-only, limited sample snapshot collector for the Åtgärder i vatten ArcGIS REST service; default five features per geometry layer.
- `scripts/collect_samrad.py`: daily pilot collector for Skogsstyrelsen Samråd point, line and polygon layers; stores immutable gzip snapshots and refuses partial publication.
- `../scripts/build_harvest_event_bundle.py`: combines planned-harvest and Samråd observations into canonical events, evidence links, candidate relationships and per-notification event chains. Satellite-derived completed-harvest polygons are deliberately excluded.
- `../data/harvest_event_bundle.json`: latest schema-validated combined event bundle.
- `.github/workflows/collect-samrad.yml`: daily Samråd pilot collection and snapshot archive.
- `.github/workflows/validate-source-registry.yml`: runs the registry validator on relevant changes.
- `config/model-contract.yml`: initial logical record contract.
- `../docs/open-data-and-commercial-use.md`: policy, source assessments and pre-publication checklist.
