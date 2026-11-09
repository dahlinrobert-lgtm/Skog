# Kungjort planning reference coverage audit

## Purpose

Measure whether the P1-P4 planning selection population has structured case and
decision references that could support conservative cross-document linkage.
This is a read-only audit, not entity resolution: shared values are counted but
no matter, process instance, event or spatial link is created.

## Inputs

The audit selects the latest immutable private selection index under
`metadata/kungjort/selection/v1/<run_id>/document-selection.jsonl.gz`.
It then reads detail records from current `kungjort-raw/bootstrap-live/`
before legacy `kungjort-raw/bootstrap/`. The first available detail record
for a document wins. A configurable per-prefix batch cap is reported, including
whether any source was truncated.

## Structured reference fields

Only known structured fields are examined:

- `detail.sections[].cases[].case_id`
- `detail.sections[].cases[].dnr`
- `detail.sections[].cases[].normalized_dnr`
- `detail.sections[].dnr[]`
- `detail.sections[].decision_id`
- `detail.sections[].diarieplan_kod`
- `detail.sections[].section_id`

No title, free text, municipality, date, URL or fuzzy similarity is used to
create a reference. Values are normalized conservatively (Unicode NFKC,
case-folding and whitespace normalization); punctuation is retained.

## Outputs and privacy

Per-document field-presence/count diagnostics are written only to a new
immutable private Azure prefix:
`metadata/kungjort/relationship-audit/v1/<run_id>/`.

The GitHub Actions artifact contains aggregate counts by priority and field,
plus counts of reference values shared by multiple documents. It contains no
document IDs, reference values, titles, municipality values, URLs, text or
examples.

## Interpretation and next step

A repeated identifier is a candidate linkage signal, not proof that two
documents belong to the same matter. In particular, case IDs, diarienummer,
decision IDs and section IDs are separate namespaces and must not be mixed.
Review coverage separately for P1, P2 and P4 context documents. Only after
field coverage and identifier semantics are verified should a subsequent
candidate-linkage stage be designed. Ambiguous or conflicting references must
remain review candidates.
