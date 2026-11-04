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
