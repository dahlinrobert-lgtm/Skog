# Kungjort: document selection and prioritisation

## Purpose

The archive contains a wider range of notices than the population needed for a
historical planning register. Do not run full entity resolution across every
notice as the first step. First identify the core planning population, retain
procedural candidates, and keep adjacent land-use matters in a separate track.
Then expand the selected population with documents that are demonstrably related
to its cases.

This selection is a working analytical view. It must never delete, rewrite, or
replace archived source notices or the existing relevance classification.

## Recommended sequence

1. Classify all available listing metadata using a dedicated planning-scope
   classifier. Do not reuse the existing high/medium/low relevance priority as
   if it were a planning classification: that classifier also targets forestry,
   nature protection, permits, energy and other themes.
2. Create a prioritised core set and separate candidate queues.
3. Expand the core set with context documents through explicit case/reference
   relations. This expansion happens before the final set is frozen.
4. Run the deeper relationship inventory on the expanded set.
5. Validate event chains and process rounds manually before spatial matching.

## Selection classes

| Class | Priority | Default action | Meaning |
|---|---|---|---|
| `core_plan` | P1 | Include | Explicit detailed-plan instrument or other named spatial-planning instrument |
| `process_candidate` | P2 | Review | Procedural milestone such as consultation, review, adoption or legal force, but no explicit plan context |
| `adjacent_geography` | P3 | Separate track | Infrastructure, energy or environmental matters with spatial relevance but not automatically part of the core plan register |
| `other` | P4 | Exclude from core analysis | No supported planning/geography signal |

P2 is deliberately not automatically included. A consultation or adoption notice
may concern a permit, procurement, a committee matter or another unrelated
process. It needs corroborating plan context or a strong relationship to a P1
case. P3 is retained for later analysis and must not be silently mixed with
detailed development plans.

## Classification signals

The first implementation uses an explicit allowlist of semantic text fields:
title/rubrik, subject/ämne, summary/sammanfattning, description/beskrivning,
document type, case title, keywords/tags, plan designation and plan name.
Nested section headings and summaries are considered. Opaque IDs, URLs, dates,
authority names and arbitrary unlabelled strings are not classification text.

P1 terms are specific plan instruments and plan-process concepts, including
`detaljplan`, `planändring`, `områdesbestämmelse`, `översiktsplan`,
`planprogram`, `planbesked`, `plankarta` and `planbeskrivning`.

P2 terms include `samråd`, `granskning`, `antagande`, `laga kraft` and
`överklagande`. These terms alone are insufficient to include a notice in the
core set.

P3 includes selected adjacent sector terms such as `vägplan`, `järnvägsplan`,
wind/solar projects, grid infrastructure and environmental permits. The list is
a separate analysis track, not a judgement that these matters are unimportant.

The classifier uses case- and accent-insensitive substring matching. The
generic word `plan` is intentionally not a trigger. Rules are versioned and
return explicit reasons and matched terms for auditability.

## What the first source-schema sample confirms

The value-free schema audit reviewed 69 archive batches. This is a bounded
sample, not a census of every archived record. It confirms that:

- Listing metadata consistently exposes document type, municipality,
  municipality name, meeting/publication meeting dates and revision fields in
  the reviewed records.
- Detail records expose nested section-level case references:
  `detail.sections[].cases[].case_id`, `dnr`, `normalized_dnr` and
  `relation`.
- The same detail structure also contains section-level `dnr[]`,
  `decision_id`, `diarieplan_kod`, `rubrik`, `sammanfattning` and
  `section_id`.
- Change records expose `operation`, `revision` and `changed_at`, which
  can help preserve source-change history but must not be confused with a
  planning event date.

The case-reference arrays are not populated in every reviewed detail record.
For that reason, the context expansion cannot rely on one identifier alone.
The next inventory must measure coverage by document class and distinguish
missing values from missing fields. The schema sample proves field availability,
not that any given reference is unique, stable or semantically equivalent.

## Context expansion: do not lose the rest of a process

The initial P1/P2/P3 classification is not the final document population.
After P1 matters have been identified, search for additional notices connected
to those matters. Context documents may be included even when their own
classification is P4 or their title does not contain planning terminology.

Use evidence in this order:

1. Exact normalized case reference / diarienummer, within a compatible
   authority and jurisdiction.
2. Exact source `case_id` or explicit relation between case records.
3. Exact plan designation or explicit reference to an earlier/later decision.
4. Decision identifier and explicit predecessor/successor reference.
5. Supporting evidence: same municipality/authority, compatible chronology,
   plan-name alias or property reference.

A same municipality, generic lifecycle word, shared keyword, similar title or
geographic proximity is not enough to add a document to a matter. Each context
addition must record the matched reference, relation type, evidence source and
confidence. Ambiguous records remain candidates for review.

The expansion must be iterative: a newly added context document may contain a
further explicit reference to another notice. Stop only when no new supported
links are found. Preserve all original selection classes alongside the
context-inclusion reason.

## Keep the levels separate

- **Selection class** answers whether a notice belongs in the core planning
  analysis or a separate review queue.
- **Matter linkage** answers which continuing administrative matter a notice
  belongs to.
- **Process-instance linkage** answers which proposal version or procedural
  round it describes.
- **Event extraction** answers which dated milestone the notice evidences.
- **Spatial linkage** answers which versioned geometry the process instance
  describes.

Do not infer a new process instance merely because a notice is a second
consultation or review. Preserve round number where supported; otherwise leave
it unknown. Do not infer `laga kraft` from an adoption notice.

## Output and privacy

The derived document-level selection index belongs in private Azure storage,
not in GitHub artifacts. It may contain source document identifiers,
classification reasons, source references and linkage candidates. Public or
GitHub Actions artifacts should contain aggregate counts, rule versions,
coverage and quality metrics only—never notice IDs, titles, URLs, text or
examples.

The first operational report should count records by source, selection class,
priority, document type and municipality coverage, and show field coverage for
the identifiers needed for context expansion. Avoid exporting individual
municipality counts if they could expose sensitive or small-cell information;
the report is for internal technical review.

## Validation requirements before broad use

- Test the classifier on a manually reviewed sample from each class.
- Measure precision separately for P1, P2 and P3; do not optimise only for
  volume or recall.
- Review false positives caused by quoted, historical or unrelated references.
- Check whether P1 documents have retrievable detail records; identify P1
  documents missing details.
- Confirm how case references, case IDs and relations are populated in actual
  source records before enabling context expansion.
- Retain an `unclassified`/review path for records with sparse metadata.
- Never discard low-priority records from the source archive.

## Implementation boundary

This change introduces the selection policy and deterministic pure classifier.
It does not yet scan Azure, fetch missing document details, create matter links,
or change the existing ingestion/relevance rules. The next operational step is
a read-only Azure selection inventory with private document-level output and an
aggregate-only downloadable report. That inventory will establish real
coverage and produce the sample for manual precision review before linkage is
implemented.
