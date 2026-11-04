# Kungjort ingestion directly to Azure Blob Storage

The active collector writes the raw document archive and change history directly to the private Azure containers. It does not write document text, cursors or raw response data to the public Git repository.

## Storage layout

- `kungjort-raw/bootstrap-live/*.jsonl.gz`: page-level historical bootstrap batches.
- `kungjort-changes/changes-live/*.jsonl.gz`: page-level change and tombstone batches.
- `metadata/kungjort/state.json`: resumable cursor checkpoint.

The one-time migration retained the four earlier Git batches under `kungjort-raw/bootstrap/`. New live ingestion uses a separate prefix so it cannot overwrite those files.

## Consistency model

Each API page is archived before its continuation cursor is committed. Page names are deterministic hashes of the input cursor. Source-page hashes are stored as blob metadata; a retry reuses an already-archived page only when its source-page hash matches. A conflicting page fails closed. The checkpoint is stored after each successful page, limiting replay to the current page.

The original `changes_cursor` captured from the first historical export page is preserved. The change feed remains blocked until `bootstrap_complete=true`.

## Run

Use Actions → **Sync Kungjort archive to Azure Blob Storage**. Continue with mode `bootstrap` until the workflow reports `bootstrap_complete: true`. Daily scheduled runs then process changes.

Only GitHub OIDC is used for Azure authentication. The API key is read from `KUNGJORT_API_KEY`; it is never written to Azure or the Git repository.


## Large historical bootstrap runs

The manual workflow defaults to 300 pages (up to 30,000 listing rows at 100 rows/page) and allows up to 500 pages. The job timeout is 350 minutes. This is intended to complete the known pilot archive in one run where API latency and rate limits permit. The API returns a cursor and the collector persists the Azure checkpoint after every successfully archived page. If GitHub's job timeout or an API outage interrupts the run, start bootstrap again: it resumes from the last committed Azure cursor rather than restarting. Do not run changes mode before `bootstrap_complete=true`.


## Relevance-first collection

Every `/documents` listing page is indexed as compressed JSONL metadata under `metadata/kungjort/index/bootstrap-live/`. The collector classifies listing metadata before requesting document details. Full details are fetched only for `high` and `medium` matches. Low-priority documents remain searchable in the metadata index and can be reclassified later without repeating the listing export.

### High priority

- Forest and forestry: forest management, harvesting, thinning, clearcuts, forestry roads.
- Nature conservation and protection: nature conservation, reserves, habitat protection, key habitats, species protection, Natura 2000, shoreline protection.
- Land use and planning: land use, exploitation, detailed/comprehensive plans, property regulation, municipal land acquisition/sales, land allocation and leases.
- Environment and permits: environmental permits/supervision/review, contaminated land, remediation, water operations and environmental impact assessments.

### Medium priority

- Energy and infrastructure: wind/solar parks, power lines, grid concessions, road and railway plans/projects and infrastructure.
- Climate and water: climate adaptation, flooding, cloudbursts, stormwater, wetlands, peat and water management.
- Fire and risk: wildfires, forest fires, fire risk and prevention.

The classifier stores the priority, category, matched terms and rule version with each metadata row and relevant detail record. Matching is a deterministic keyword baseline, not semantic AI classification. Rules should be reviewed against a sample of the actual listing metadata before the complete historical export is launched. Unmatched documents are not deleted; only their full detail retrieval is skipped.


## Expanded Swedish relevance vocabulary

The relevance rules now include additional forestry terms (including regeneration, clearing, soil preparation, timber handling, forest damage and bark beetle), nature protection (habitat protection, species protection, reserve formation and consultation), land/property planning (property formation, easements, land leases and development agreements), and environmental permits/supervision (quarries, peat extraction, remediation, water operations and drainage).

Medium-priority vocabulary now also covers electricity grids and substations, energy storage, solar and wind installations, roads/railways, wetlands, water bodies, groundwater, flood risk and forest-fire preparedness.

Matching is case- and accent-insensitive, so accented Swedish terms and their ASCII spellings are treated alike. The generic standalone term `skog` is deliberately excluded because it could match incidental mentions and inflate the high-priority set. Terms are still matched against the metadata fields only; this change does not claim to classify the full document text. Review actual samples and measured precision/recall before increasing collection volume.
