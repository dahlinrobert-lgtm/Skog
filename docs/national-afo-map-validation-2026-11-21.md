# National ÄFO map data validation — 2026-11-21

## Result

The national ÄFO collection from `alg-grasmyr` workflow run #10 completed successfully on `main` at commit `d89c6867c798010d11a6a911b98e71e28b5e354d`.

- Workflow: https://github.com/dahlinrobert-lgtm/alg-grasmyr/actions/runs/44917302093
- Artifact: `national-afo-snapshot-batch` (artifact ID `14711579587`)
- Artifact SHA-256: `6c11f24f23056be0507ef6618a15c46b8534573cecd85b51959f4338f331ddf6`
- Snapshot date: `2026-11-21`
- Hunting season: `2026/2027`

## Independent artifact checks

The downloaded workflow artifact was inspected independently, rather than relying only on the green workflow status.

| Check | Result |
|---|---:|
| Individual immutable AFO snapshot files | 129 |
| Unique AFO IDs | 129 |
| Dashboard area rows | 129 |
| Snapshot/dashboard ID sets | Exact match |
| Snapshot/dashboard field mismatches | 0 |
| Snapshot dates | 129 × 2026-11-21 |
| Hunting seasons | 129 × 2026/2027 |
| Data status | 129 × `area_rows_available` |
| Underlying ÄJO source rows | 3,237 |
| Sum of `fallda_totalt` | 56,715 |
| Sum of `avskjutningsmal_totalt` | 79,704 |

For every AFO, the snapshot and dashboard values matched for `fallda_totalt`, `avskjutningsmal_totalt`, `hunting_season`, `data_status` and `source_row_count`.

## Regional spot-checks

| County | AFOs | Harvested | Targets |
|---|---:|---:|---:|
| Västerbottens län | 5 | 10,171 | 13,793 |
| Norrbottens län | 6 | 9,371 | 15,551 |

The previously failing AFO `25-004` (ÄFO 4, Norrbottens län) is present in the successful batch with 1,927 harvested and 3,267 assigned target.

## Map integration and deployment

Skog PR #465 was merged to `main` at `82070febd7c04f507ed871170a77b5c3a77f80d1`.

- PR: https://github.com/dahlinrobert-lgtm/Skog/pull/465
- The updated `docs/bevakning.html` fetches `data/national_afo_dashboard.json` from the alg-grasmyr `main` branch.
- The frontend checks for duplicate IDs and exact equality between the geometry and statistics AFO ID sets before rendering the layer.
- GitHub Pages build and deployment for the merged commit completed successfully: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44917175783

**Verification boundary:** the national dashboard JSON and the deployed Pages build are verified. The external Länsstyrelsen ArcGIS geometry service and the rendered map in a live browser were not independently queried in this validation. The map's own runtime check is designed to fail visibly if the geometry and statistics IDs do not match exactly. A final visual browser check remains appropriate.

## Operational follow-up

Two other workflows on the same Skog main commit attempted to push generated files directly to protected `main` and were rejected by repository rules requiring changes through pull requests:

- Source registry refresh: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44917176510
- Gräsmyr monitoring snapshot: https://github.com/dahlinrobert-lgtm/Skog/actions/runs/44917176484

These failures do not invalidate the national ÄFO snapshot or Pages deployment. They do mean those workflows need a PR-based publication path (or an explicitly authorized exception) before their generated updates can be committed.
