# Kungjort work ID extraction audit

## Purpose

Extract municipal work IDs and protocol decision references from the private Kungjort archive using the reference hierarchy in \`kungjort-work-id-and-decision-references.md\`.

## Extraction rules

- Detect work-ID-shaped strings with a municipal alphabetic prefix, four-digit year and slash serial, e.g. \`KLF2023/1308\`.
- Normalize only case and whitespace. Keep the prefix, year, slash and serial; never match on the serial alone.
- Extract protocol references as separate date and paragraph fields, e.g. \`2023-10-23 (§ 21)\`.
- Search only allowlisted semantic text fields in the private selection index and archived detail records.
- Namespace candidate groups by the municipality/authority supplied by the selection record. Identical-looking work IDs in different authorities are not grouped.
- A repeated work ID creates a candidate group of notices, not a finalized matter or process-instance assignment.

## Storage and privacy

The private document-level extraction and candidate groups are written as a new immutable blob under:

\`metadata/kungjort/work-id-audit/v1/<audit_run_id>/work-id-extraction.jsonl.gz\`

The GitHub artifact contains aggregate counts only. It does not expose work IDs, protocol values, document IDs, titles, municipality values, URLs, text or candidate pairs.

The audit is read-only with respect to all source blobs and existing selection/reference indexes. It does not modify ingestion, create final matter links, infer event types from protocol citations, or merge process instances.

## Interpretation

The work ID is the primary practical cross-notice matter reference. Protocol date/paragraph is event-level supporting evidence. The audit detects these references but does not decide whether a notice is a consultation, review, adoption or another event; that requires contextual extraction and, where needed, protocol source review.

## Known limitations

- The work-ID pattern is intentionally conservative and may miss municipalities using other identifier formats.
- The authority key is only as reliable as the municipality value in the selection index; missing authority values are grouped only with other missing-authority records and should be reviewed separately.
- A repeated work ID can cover sub-matters or multiple procedural rounds. Candidate groups must be reviewed before matter/process links are finalized.
- Protocol references may be present without a work ID and are not globally unique by date and paragraph alone.
