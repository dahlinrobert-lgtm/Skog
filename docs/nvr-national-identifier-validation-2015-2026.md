# NVR national identifier and event-key validation, 2015–2026

## Purpose and scope

This document records structural checks performed on the local annual NVR animal-level CSV exports for 2015–2026. The source files remain outside this repository; no row-level Police or NVR records are committed.

The checks support a provisional data model with an event-level key and optional animal-level source identifier. They do not establish a formal guarantee from NVR about identifier semantics.

## National inventory

The first audit covered all twelve annual files and reported:

| Measure | Result |
|---|---:|
| Annual files found | 12 (2015–2026) |
| Animal-level rows | 777,482 |
| Non-empty `DjurID` values | 383,953 |
| Rows with missing `DjurID` | 393,529 |
| Repeated non-empty `DjurID` values in inspected files | 0 |
| Repeated `DjurID` values across different years | 0 |
| Distinct year-qualified `OlycksID` keys | 765,449 |
| Year-qualified event keys with multiple animal rows | 9,331 |

No non-empty `DjurID` value was repeated in the inspected 2015–2026 files. However, 393,529 rows have no `DjurID`; therefore `DjurID` cannot serve as a mandatory identifier for the complete historical animal-level dataset. Treat it as an optional source identifier. The observed uniqueness is an empirical property of these files, not a contractual guarantee from the data provider.

## Event-key validation

The second audit reported:

- No missing `OlycksID` values.
- No missing `Datum` values.
- No rows where the first four numeric characters of `Datum` disagreed with the annual file's year.
- 187,660 raw `OlycksID` values appeared in more than one year.

The reused raw IDs demonstrate that `OlycksID` alone is not a safe nationwide historical key. The provisional event key is therefore:

```text
event_key = year(Datum) + "-" + OlycksID
```

The year must be derived from the validated event date, with the annual source file year retained as an independent validation field. Do not silently substitute the file year when the date is missing or malformed.

The audit's year check compared the file year with the first four characters of `Datum` when those characters were numeric. Malformed date strings were not separately classified by this check and require a dedicated date-parse validation before production ingestion.

## DjurID availability by year

Missing `DjurID` rows varied substantially over time:

| Year | Animal rows | Missing DjurID |
|---:|---:|---:|
| 2015 | 45,353 | 45,344 |
| 2016 | 56,480 | 56,466 |
| 2017 | 58,800 | 58,799 |
| 2018 | 63,540 | 63,539 |
| 2019 | 64,534 | 64,532 |
| 2020 | 62,146 | 61,920 |
| 2021 | 68,508 | 42,929 |
| 2022 | 67,791 | 0 |
| 2023 | 71,317 | 0 |
| 2024 | 77,571 | 0 |
| 2025 | 77,034 | 0 |
| 2026 | 64,408 | 0 |

This is a material change in identifier availability across the historical series. Do not infer or generate missing `DjurID` values from row order, `OlycksID`, or other fields. A locally generated immutable row key may be used for storage and lineage, but must be clearly distinguished from a source-issued identifier.

## Recommended data model

- **Event table:** one row per `event_key` (year-qualified `OlycksID`), retaining the original `OlycksID`, event date, source year and documented event-level attributes.
- **Animal table:** one row per source animal record, linked to `event_key`. Retain `DjurID` as nullable, along with species, sex, age-class, outcome and the original source values.
- **Source-row lineage:** retain source filename, source row position or another stable ingestion lineage key, retrieval time and source-file checksum. A generated lineage key is not a replacement for `DjurID`.
- **Candidate matching:** Police–NVR candidate generation operates at event grain. Animal-level rows enrich review and preserve multi-animal outcomes; they must not create duplicate event matches.

## Limitations and next checks

1. These results describe the local 2015–2026 annual files inspected. Re-run the audit against a fresh source snapshot before production baselining.
2. The checks establish observed uniqueness and completeness patterns, not a provider-backed identifier contract.
3. Add strict parsing tests for every `Datum` value, including malformed values, before deriving event year.
4. Validate that each `event_key` has consistent event-level attributes and coordinates, while preserving legitimate animal-level differences such as species and outcome.
5. Keep source data immutable and retain audit outputs, file hashes, retrieval timestamps and code version for reproducibility.

## Decision

For the current historical NVR dataset, use year-qualified `OlycksID` as the **provisional event key**. Treat `DjurID` as an optional source identifier, not as the primary key for all animal rows. This decision is supported by the observed 2015–2026 export checks above and remains subject to source-contract confirmation and strict date validation.
