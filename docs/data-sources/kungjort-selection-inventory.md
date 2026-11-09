# Kungjort planning selection inventory

## Purpose

This is the operational, read-only-derived inventory following the planning
scope policy. It reads the existing private archive and writes a versioned
selection index to the private Azure metadata container. It never changes or
deletes source blobs, source checkpoints, the existing relevance labels, or
the daily changes feed.

## Inputs and precedence

The inventory reads JSONL.GZ batches from these prefixes:

1. `metadata/kungjort/index/reclassified-v2/` (preferred listing metadata)
2. `metadata/kungjort/index/bootstrap-live/` (original listing metadata)
3. `kungjort-raw/bootstrap-live/` (current detailed records)
4. `kungjort-raw/bootstrap/` (legacy detailed records)

A document is keyed by its source document identifier. Duplicate appearances
are consolidated into one derived selection record. Metadata precedence is
reclassified index, original listing index, then available detail-list metadata.
The first available detail record enriches the classifier input. No source record
is overwritten.

## Classification and outputs

The selection classifier receives allowlisted semantic text from both listing
metadata and available detail content. The derived private index contains one
row per unique document, with its ID, P1-P4 classification and reasons, matched
terms, source-prefix provenance, whether a detail record exists, whether a
case reference appears in the known detail structure, and limited metadata
(title, municipality and document type) for internal review.

The private index is written under
`metadata/kungjort/selection/v1/<run_id>/document-selection.jsonl.gz`.
Each run has a new immutable path; an existing path is never overwritten.

The GitHub Actions artifact contains aggregate counts only: source batches and
records reviewed, unique documents, duplicate source records, missing-ID
counts, class/priority counts, detail coverage and case-reference coverage.
It contains no document IDs, titles, municipality values, URLs, text, examples
or source records.

## Coverage and interpretation

The workflow caps processing at a configurable number of batches per source
prefix (default 500, maximum 2,000). The report states how many batches and
records were actually reviewed. If a source prefix contains more batches than
the cap, the report is a partial inventory and must not be described as a full
census. Increase the cap and rerun to cover the remaining archive.

The inventory deduplicates by document ID, not by matter, plan or process
instance. It does not establish case relationships, event chains, process
rounds or spatial footprints. A document with a case reference is only counted
as having a reference; no matching or inference is performed.

## Next validation step

Review aggregate class proportions and detail/reference coverage. Then draw a
manually reviewed sample from P1, P2, P3 and P4 using the private index, and
measure precision separately. Do not enable automatic context expansion until
the actual source reference fields and their coverage have been checked and the
manual sample supports the rules.
