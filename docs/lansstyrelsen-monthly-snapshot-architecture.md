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

## Verified pilot status (2026-11-17)

- Two successful manual pilot runs are published for Norrbotten, category B: registration month October 2026 (workflow run #16) and September 2026 (workflow run #17).
- Each run reconciled all six configured phrases. The two runs produced twelve immutable snapshot files and twelve manifest entries, including explicit zero-result snapshots.
- These runs demonstrate repeatability for one county/category and two months only. They do not establish national coverage, completeness outside the configured phrases, or permission for unattended collection or customer display.

## Controlled national discovery

The separate workflow `.github/workflows/lansstyrelsen-national-diary-discovery.yml` is intended for manually controlled coverage discovery:

- Seven fixed groups of three counties cover the 21 county diaries.
- One category (A or B) is selected per run; each category has six phrases. A run therefore has at most 18 county/phrase intervals.
- For a focused pagination probe, an optional single custom search phrase can override the category phrases. In this mode the selected three-county group produces exactly three diagnostic intervals; the phrase is validated to 2–80 characters. This remains manual diagnostics-only and does not persist snapshots.
- An optional `single_county=blekinge` selector isolates the Blekinge diary while retaining the same collector, validation tests, custom phrase/date filters and diagnostics artifact. It overrides the selected county group and reduces a custom-phrase probe to one interval. The default `all` preserves the existing three-county group behaviour.
- Run one group at a time and evaluate response times, failures, and source behaviour before proceeding to another group.
- The workflow uploads diagnostics as a 30-day artifact only. It does not call `persist_lansstyrelsen_snapshots.py`, alter the append-only archive or manifest, or push to `main`.
- It is a discovery/test facility, not an automated national archive. A successful group does not imply nationwide coverage.
- Do not use the existing publishing workflow for national discovery: that workflow persists reconciled snapshots and proposes them through a pull request; it does not publish directly to `main`.

No recurring schedule is enabled or approved. Do not start a full national sequence until the source's technical limitations and applicable access conditions have been clarified. Do not interpret pre-deployment absences as removals.

## Quality gates

- Fail closed on unknown totals, missing grid without explicit zero, incomplete paging, duplicate IDs, or source count mismatch.
- Preserve failed-run diagnostics but do not merge failed/partial results into `state.json`.
- Retain run manifests for failed attempts so gaps are visible and retryable.
- Audit snapshot row counts, unique IDs, duplicate IDs within run, intervals with missing totals, and county/phrase completeness.
- Do not infer that an absent record was deleted from the source; it may have fallen outside the public search window or no longer matched the phrase.

## Operational caution

The date filter has been observed to affect search totals in one Norrbotten `vattenverksamhet` comparison (253 all-time vs 155 in 2026). Per-month paging has passed the six configured intervals in each of two Norrbotten pilot months. This does not validate all counties, all phrases, or nationwide reliability. National discovery remains manual and diagnostics-only until portal behaviour and technical limitations are assessed.


## PR-baserad arkivering (2026-11-27)

Både `.github/workflows/lansstyrelsen-monthly-snapshots.yml` och `.github/workflows/lansstyrelsen-diary-search.yml` publicerar nu via `peter-evans/create-pull-request@v7`. Direktpush till skyddad `main` är inte tillåten (GH013).

Flödena delar concurrency group `lansstyrelsen-diary-archive` och branch `automation/lansstyrelsen-diary-history` eftersom de skriver till samma append-only-arkiv. Den dagliga sökningen hämtar senaste `main`, applicerar de validerade sökresultaten på nytt, auditerar state/events och skapar/uppdaterar PR. Månadskörningen lägger till immutable snapshotfiler och manifestrader i samma PR. PR-validering kör regressionstester men hoppar över browserinsamling och persistence.

Efter merge av PR #709 startade daglig run [#148](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073390751) automatiskt. Dess slutresultat och eventuell data-PR måste granskas innan PR-publiceringen betraktas som liveverifierad. En data-PR kräver normal granskning/merge; workflow-success i sig innebär inte att data har publicerats på `main`.


## Högvolymstest av paginering – diagnostics-only (2026-11-27)

- [Run #24](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073035588) avstämde `vattenverksamhet` för oktober 2026 i Skåne, Halland och Västra Götaland: 14, 11 och 46 poster, en sida per län.
- [Run #25](https://github.com/dahlinrobert-lgtm/Skog/actions/runs/46073391186) använde den breda tekniska testfrasen `an` för oktober 2026 i Norrbotten, Västerbotten och Jämtland. 848/874/820 unika diarienummer hämtades på 17/18/17 sidor. Pagerfönstret flyttade sig via `Page$6`, `Page$11` och `Page$16`; alla 16/17/16 sidbyten bekräftades och inga dubbletter av diarienummer eller case-ID:n hittades.

Båda körningarna var diagnostics-only och persisterade inga resultat. De utökar inte de 36 arkiverade manifestintervallen eller arkivets två län. Testfrasen `an` är endast en teknisk pagination-probe. Paginering över 17–18 sidor har nu observerats i dessa tre län, men det verifierar inte samtliga 21 län, andra fraser, provider rate limits eller återkommande stabilitet.

Projektledarens [PM-PR #106](https://github.com/dahlinrobert-lgtm/skogskoll-project-manager-history/pull/106) har registrerat resultatet; `risk_assessed=false` kvarstår.
