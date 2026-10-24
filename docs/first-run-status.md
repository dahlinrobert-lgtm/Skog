## Status after first scheduled run (2026-10-24)

The scheduled monitor run completed successfully:
https://github.com/dahlinrobert-lgtm/Skog/actions/runs/40082300173

Confirmed source results from the run log:
- Skogsstyrelsen: 253 cutting-notification features intersected the 10 km rectangular search bbox.
- Copernicus Sentinel-1: 100 scenes returned; latest acquisition was 2026-10-24T04:56:56Z.
- Copernicus Sentinel-2 L2A: 100 scenes returned; latest acquisition was 2026-10-22T10:30:31Z.
- The catalogue calls returned 100 items each due to the configured query limit. The first-run count of 200 is an initial catalogue sample, not 200 newly acquired scenes since a previous check.
- The cutting-notification result set includes old cases and multiple municipalities; it is not yet a Gräsmyr-village or parcel-level selection.
- The date of image acquisition and the catalogue publication/creation time are distinct fields and should continue to be recorded separately.

## Work applied after this first run
- Added a run findings section to README.
- Added initial configuration for recency and catalogue page size.
- Updated the monitor script to follow STAC next links, deduplicate scene IDs, and keep first-run items out of the 'new since previous run' alert arrays.

The updated script has been committed but not yet verified in a subsequent Actions run. Next priorities: execute and inspect that version, verify pagination behavior, then geospatially clip/compare cutting notifications against a verified Gräsmyr polygon and pursue Lantmäteriet imagery outcome metadata.
