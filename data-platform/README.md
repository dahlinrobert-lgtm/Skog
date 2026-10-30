# Skog data platform

Forest-specific data integration foundation. The architecture and initial contracts are documented in [docs/data-platform-architecture.md](../docs/data-platform-architecture.md).

## Current stage

This folder contains the initial source registry and logical data contract. It does not yet run connectors, schedule jobs, or publish datasets.

## Principles

- Preserve raw source payloads and original raster assets.
- Make ingestion idempotent and auditable.
- Keep source-record identity separate from canonical forest-domain identity.
- Publish only complete, validated runs.
- Keep source-specific logic inside connectors.
- Preserve existing Skogskoll ingestion and alert-safety behavior.

## Files

- `config/sources.yml`: source registry (no credentials).
- `config/model-contract.yml`: initial logical record contract.
