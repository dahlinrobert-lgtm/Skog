# Police wildlife summary expansion

## Purpose

Police source events can be published as a single evening/night summary containing several separate wildlife incidents. The source event is therefore not necessarily the same unit as an individual collision statement.

The extraction pipeline creates child statement rows for review while preserving the original Police source event unchanged.

## Levels and identifiers

- **Source event:** original Police event, identified by `event_id` and retained in `events.csv`.
- **Expanded statement:** one extracted wildlife statement, identified locally by `parent_event_id` plus `occurrence_index`.
- **NVR match candidate:** a comparison between one expanded statement and one event-level NVR record.

`occurrence_index` is an extraction-order identifier within the parent event. It is not an official Police incident ID and does not imply that the statement is a confirmed collision.

## Expansion rules

1. Split the source text at each explicit clock-time marker. A segment is emitted only when it contains explicit wildlife-collision language.
2. Keep the segment text, parent event ID, publication date, source link, extracted time, municipality and species as separate fields.
3. For night summaries, times from 22:00 onward are assigned to the previous calendar date; times before 07:00 are assigned to the publication date. The date basis is retained.
4. Explicit counts such as “three wildlife collisions” may produce count-only review rows. These rows have no inferred time/date and are not passed into the individual Luleå match-candidate file.
5. Counts of animals, people, vehicles, reports or suspected offences do not multiply collision counts.
6. A summary with no separable timestamped statement or explicit collision count is not expanded by guessing. Source text remains available for later review.

## Extraction methods

- `wildlife_time_segment_v2`: timestamped wildlife statement extracted from a time-delimited source-text segment.
- `explicit_count_v1`: low-confidence count-only row from an explicit number of wildlife collisions.

The older `wildlife_text_line_v1` method remains accepted by the Luleå review builder for compatibility with previously generated files.

## Interpretation

Expanded rows are candidate statements, not verified collision records. Multiple rows may share one parent Police event. NVR matching must operate on expanded statements and event-level NVR rows, preserve all source identifiers and remain review-only. No automatic match confirmation is performed.
