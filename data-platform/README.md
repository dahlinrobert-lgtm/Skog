# Skog data platform

Forest-specific data integration foundation. The architecture and initial contracts are documented in [docs/data-platform-architecture.md](../docs/data-platform-architecture.md).

## Current stage

This folder contains the initial source registry and logical data contract. It does not yet run connectors, schedule jobs, or publish datasets.

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

- `config/sources.yml`: source and rights registry (no credentials).
- `config/model-contract.yml`: initial logical record contract.
- `../docs/open-data-and-commercial-use.md`: policy, source assessments and pre-publication checklist.
