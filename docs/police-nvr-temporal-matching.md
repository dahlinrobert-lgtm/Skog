# Police–NVR temporal candidate matching

## Purpose
Generate explainable candidate links between individual Police wildlife statements and event-level NVR collisions. This is a separate derived crosswalk: Police and NVR source rows are never modified, and no candidate is automatically confirmed.

## Why time is a first-class dimension
NVR animal exports contain `Datum` as `YYYY-MM-DD HH:MM`. Police text may contain an explicit clock time, while extracted `occurrence_date` can have a documented basis such as `night_summary_after_midnight`. The matcher uses the Police occurrence date and time fields from the individual text row. It does not silently substitute the publication date when occurrence date is absent.

Same municipality + same date creates a candidate pair, not a confirmed match. A close time match and matching species strengthen it. Explicit road/place text can add evidence after NVR location enrichment is available. Absence of a geographic match is not a rejection.

## Event grain and identifiers
- Police side: individual `wildlife_text_line_v1` statement rows, retaining parent event ID and exact text.
- NVR side: one row per year-qualified `accident_key` from `build_nvr_accident_points.py`; never join on raw `OlycksID` alone and never match animal-level `DjurID` rows independently.
- NVR `event_datetime_values` can contain multiple values from animal rows; compare all valid values but preserve the full source value string.
- Keep municipality and species as separate evidence fields.

## Current matching rule (candidate generation only)
1. Require a valid Police `occurrence_date`; missing dates remain unmatched and visible in the Police review file.
2. Require Luleå on both sides for this Luleå pilot.
3. Generate all pairs on the same calendar date.
4. If Police time is available, compare it with each NVR event time on that date and retain the minimum absolute difference.
5. Record time bands: within 15 minutes, within 1 hour, within configured window (default 180 minutes), same-date time conflict, or time unavailable. Missing Police time is always classified as unavailable; it is not treated as a conflict with a known NVR time. A pair without Police time remains a date-only weak candidate even if species matches; species is supporting evidence, not a substitute for temporal evidence.
6. Add species and text-term evidence. Road/place fields on NVR are optional and will be empty until the separately versioned NVR location-enrichment output is joined.
7. Keep all same-date pairs, including time conflicts, for audit; do not discard a pair solely because its time differs.
8. Do not resolve one-to-many or many-to-one relationships automatically. Multiple Police statements can share a parent event, and multiple NVR events can occur on the same date.

The score is an ordinal candidate-priority aid, not a probability. It must not be interpreted as match confidence until calibrated against manually reviewed positive and negative pairs.

## Run
First build the Luleå Police subset:
```bash
python scripts/build_lulea_police_review.py
```
Then build NVR event-level rows from the validated annual exports using the existing `build_nvr_accident_points.py` in the bear-data repository. Copy the resulting derived CSV into a restricted local working folder; do not commit it.
Run:
```bash
python scripts/match_police_nvr_temporal.py --police data/police_events/lulea_review_candidates.csv --nvr /path/to/nvr-accidents.csv --output /path/to/lulea-police-nvr-temporal-candidates.csv --report /path/to/lulea-police-nvr-temporal-audit.json
```
The CSV contains candidate pairs and evidence fields. The optional JSON report counts Police statements and NVR events with zero, one, or multiple candidate links, including Police statements with no valid occurrence date. It is a local derived file and must not be committed with row-level data. Each Police statement is identified by `police_candidate_id` (parent event ID plus occurrence index), so two statements under the same Police event remain distinct.

## Known limitations and validation
- NVR reports can lag by up to two months; absence of a same-date NVR event is not evidence that the Police event did not occur.
- NVR's public contractor dataset does not cover every Police-reported collision.
- Police date basis must be inspected. A date inferred from a night summary can be less certain than a clearly stated occurrence date; retain `occurrence_date_basis`.
- Clock times may be rounded, delayed, or reflect a report time rather than exact collision time. The 15/60/180-minute bands are provisional review categories, not validated thresholds.
- A single date may contain several collisions in Luleå. Date alone is not enough to choose one.
- Text token overlap is weak evidence and not a geocoder. No geography is used by this first version.
- The current Police extractor may have false positive text candidates; manual review is required before matching.

## Validation gates
1. Run unit tests on synthetic fixtures.
2. Run on the actual local Luleå subset and NVR event-level export; inspect all candidate pairs manually.
3. Measure how many Police statements have 0, 1, or multiple NVR candidates, and vice versa.
4. Review date/time offsets and false-positive patterns before tuning any thresholds.
5. Add versioned geographic enrichment and a manually labelled evaluation sample before any automatic event resolution.
