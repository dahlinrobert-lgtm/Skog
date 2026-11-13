# Viltdata harvest statistics snapshot diff

The diff tool compares two complete immutable snapshots produced by
`scripts/viltdata_kill_statistics_snapshot.py`.

## Run

From the repository root:

```powershell
python -m unittest tests.test_viltdata_kill_statistics_diff -v

python scripts/viltdata_kill_statistics_diff.py `
  data/viltdata/kill-statistics/20261113T170433Z `
  data/viltdata/kill-statistics/<CURRENT_RUN_ID>
```

By default, outputs are written to:

```text
data/viltdata/kill-statistics/diffs/<BASELINE>_to_<CURRENT>/
  summary.json
  changes.json
```

An existing output directory is never overwritten. Supply `--output` to choose
another new directory.

## Safety and comparison rules

- Both manifests must declare `status: complete` and `complete: true`.
- Every expected statistics request must be successful and its raw file must
  exist.
- Each requested species must occur exactly once in each scope, and every
  dataset must align with its year labels.
- Observations are keyed by geography scope, species ID and year. Species
  labels are descriptive, not identifiers.
- Null and zero remain distinct. Blank strings are normalized to null.
- The tool refuses to compare snapshots with different observation coverage.
  This prevents missing files, missing datasets or changed year coverage from
  being misreported as value deletions.
- Raw snapshots are read-only; the tool writes separate diff artifacts.

## Change types

- `new_value`: null to a non-zero reported value
- `new_zero`: null to an explicit numeric zero
- `value_changed`: one reported value to another
- `became_missing`: a reported value to null
- `unchanged`: identical values, including null-to-null

A complete snapshot means all planned requests succeeded and passed the
snapshot script's structural validation. It does not mean every year or
species has been fully reported by Viltdata.
