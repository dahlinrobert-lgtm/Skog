# Luleå Police wildlife candidate review

The script `scripts/build_lulea_police_review.py` creates a conservative review subset from the existing `data/police_events/wildlife_incidents.csv`.

Run: `python scripts/build_lulea_police_review.py`

Optional paths: `--input`, `--output`, and `--report`.

Selection:
- Only rows whose extracted municipality is exactly Luleå.
- Only `wildlife_text_line_v1` rows are exported as individual text candidates.
- Rows without occurrence date/time remain visible and are flagged for review.
- `explicit_count_v1` count-only rows are excluded from the candidate CSV and counted separately.
- A coarse geographic-evidence label helps manual review; it is not a parsed address, road-number match, or geocoded result.

The output is not a verified collision register. It does not use summary-level Police coordinates, create coordinates, match NVR records, or apply distance thresholds. Generate locally or as a short-lived artifact; do not commit location-rich candidate text without a clear storage/access rationale.
