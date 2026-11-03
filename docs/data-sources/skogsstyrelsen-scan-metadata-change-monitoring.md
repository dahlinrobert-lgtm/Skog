# Skogsstyrelsen laser-scan metadata change monitoring

## Why this is a poller, not a weekly snapshot job

Skogsstyrelsen's metadata service is manually published. The scan-index
features can therefore remain unchanged across many checks and then change
when a new publication is made. The daily check is only a low-frequency
availability/content check; it does not imply that the source publishes daily
or weekly.

## Behaviour

- Query the national layer, not only the three pilot raster extents.
- Retrieve all object IDs, then fetch every feature in bounded batches.
- Validate that every requested feature was returned. An incomplete response
  fails the workflow and is never recorded as a publication.
- Fingerprint attributes AND geometry, so additions, removals, edits and
  geometry corrections are detected.
- If the fingerprint is unchanged, do not create a snapshot or commit.
- If it changes, store a compressed full snapshot and update `latest.json`.
- Keep source scan date, source service metadata and detection timestamp
  separate. Detection time is not publication time.

## Important limitations

The service's layer metadata may expose a service-level publication timestamp,
but that timestamp is not assumed to be a reliable per-feature update time.
The first successful run establishes a baseline; it cannot reconstruct
publications that happened before monitoring began. Omdrev 3 remains ongoing:
a new metadata publication is evidence of added/changed source records, not
proof that the round is complete.

## Source

Skogsstyrelsen, `GeodataportalVisaSkogligaGrunddataMetadata/MapServer/0`,
ArcGIS REST query service. Metadata features represent 2.5 km index areas,
not exact aircraft flight paths.
