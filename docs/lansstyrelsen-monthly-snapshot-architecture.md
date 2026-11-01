# Länsstyrelsen diary monthly snapshot architecture

## Purpose

Preserve dated observations of public diary search results so that cases which later disappear from the portal's current search surface remain represented in Skog's own history.

This is an observation archive, not proof that an activity occurred, that a permit was required, or that a source record was legally complete.

## Collection model

1. Search each selected county diary separately.
2. Search each configured query phrase separately.
3. Apply registration-date intervals. The first interval size is one calendar month.
4. Do not assume a query is complete merely because a page rendered. Every interval must have:
   - a source-reported result total (or explicit zero-result marker);
   - pagination exhausted;
   - extracted unique diary IDs equal to the source total;
   - no unresolved request or parsing error.
5. If a month is above the portal's reliable extraction capacity, split it into smaller non-overlapping date intervals (day ranges, then smaller ranges if required). Persist only fully reconciled intervals. Keep failed intervals in diagnostics for retry.
6. Merge duplicate diary IDs across overlapping phrases only within the same county and snapshot run. Preserve every query phrase that found the case.
7. A snapshot run is complete only when all configured county/phrase/date intervals have either reconciled or have a deliberate, explicit zero result. A partial run must not be labelled as a complete national/monthly snapshot.

## Storage

- `data/lansstyrelsen-diary/state.json`: latest known source fields keyed by county + diary number. Existing purpose retained.
- `data/lansstyrelsen-diary/events.jsonl`: append-only first-seen, observed and source-change events. Existing purpose retained.
- `data/lansstyrelsen-diary/snapshots/YYYY/MM/<run-id>.jsonl`: immutable observation rows for one collection run, partitioned by observation month (not by case registration month).
- `data/lansstyrelsen-diary/snapshot-runs.jsonl`: one manifest per attempt, including run ID, UTC observation time, scope, query phrases, intervals, per-interval totals, extracted counts, pagination completion, reconciliation outcome and error summaries.

Snapshot rows should contain at minimum:
- run ID and observation timestamp;
- county diary label and diary number;
- search phrase(s) that matched;
- source registration date, title, status and public case link;
- source interval start/end;
- stable source-row content hash.

Do not overwrite old snapshot rows. A repeated identical row in a later monthly run is a new observation and should be represented in that later snapshot. Within the same run, deduplicate identical county + diary number rows while retaining all matching phrases.

## Schedule

- Monthly: full configured search coverage, retaining the complete result set and run manifest.
- Daily/weekly: optional narrow current-period check for urgent discovery, but never substitute it for the monthly full snapshot.
- Case handling history: keep the existing rotating metadata collector as a separate process; it records changes to a case's handling table and is not a substitute for search-result snapshots.

## Initial deployment

- Begin with Norrbotten and Västerbotten A/B query terms as currently configured.
- Run a validated pilot on a bounded month in each county.
- Compare each monthly interval total against extracted unique IDs.
- Only after the pilot passes, turn on the recurring monthly schedule.
- Do not interpret pre-deployment absences as removals. The baseline begins at the first successful snapshot.

## Quality gates

- Fail closed on unknown totals, missing grid without explicit zero, incomplete paging, duplicate IDs, or source count mismatch.
- Preserve failed-run diagnostics but do not merge failed/partial results into `state.json`.
- Retain run manifests for failed attempts so gaps are visible and retryable.
- Audit snapshot row counts, unique IDs, duplicate IDs within run, intervals with missing totals, and county/phrase completeness.
- Do not infer that an absent record was deleted from the source; it may have fallen outside the public search window or no longer matched the phrase.

## Operational caution

The date filter has been observed to affect search totals in one Norrbotten `vattenverksamhet` comparison (253 all-time vs 155 in 2026). The monthly coverage and reliable per-month paging have not yet been verified. Monthly partition diagnostics must pass before production snapshots are enabled.
