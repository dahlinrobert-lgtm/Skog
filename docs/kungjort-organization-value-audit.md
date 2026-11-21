# Kungjort organization-value audit

## Purpose

Inventory source values from the `organ`, `publication_organ` and `organ_name` fields represented in the current selection index. This is an evidence inventory, not an identity resolver and not a hierarchy update.

## Privacy boundary

- Raw source values, normalized values, SHA-256 hashes and document IDs are written only to a versioned blob under the existing private Azure metadata container.
- The GitHub Actions artifact contains aggregate counts only: category counts, unique group counts, detail coverage, source batch coverage and a private blob path.
- Never include raw names, hashes, titles, document IDs, document links, excerpts or source values in workflow logs or GitHub artifacts.
- The workflow uses the existing Azure OIDC identity and private metadata container. No new credential or permission is introduced by this feature.
- The report is manual opt-in only. It is not part of the scheduled daily synchronization mode.

## Classification

Normalization is case- and accent-insensitive. Categories are conservative candidates:
- `administration_candidate`
- `committee_or_board_candidate`
- `municipal_assembly_candidate`
- `municipality_level_publisher`
- `other_public_authority`
- `unclassified_organ`
- `empty` (ignored by the audit when normalization produces no usable text)

A generic issuing organ is not promoted to a committee, administration or municipality identity. A candidate label is not a verified entity identity.

## Coverage and limitations

The inventory uses the current selection inventory source precedence and reports source batches reviewed and whether any source prefix was truncated by `--max-batches`. The result must not be described as complete when `source_scan_truncated` contains `true`.

The audit uses only evidence sources `organ`, `publication_organ` and `organ_name` from the existing `issuing_organ.evidence` structure. Other evidence fields are ignored. Document detail coverage is reported separately; absence of a detail record does not imply absence of organizational metadata in listing metadata.

## Activation

Run manually via the existing `Sync Kungjort archive to Azure Blob Storage` workflow using mode `organization-report`. The mode is excluded from the direct synchronization step and only runs the dedicated audit and aggregate artifact export. It does not change scheduled `changes` runs.

The PR workflow only compiles and runs unit tests. It does not sign in to Azure, read source archives or write blobs.
