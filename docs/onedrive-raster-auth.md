# OneDrive source for volume rasters in GitHub Actions

The analysis workflows can download raster ZIPs from the user's personal OneDrive without committing the large archives to Git history. The original files in OneDrive are read-only from the workflow's perspective.

## GitHub Actions secrets required

In the repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `ONEDRIVE_CLIENT_ID`: Application (client) ID for an OAuth app that supports personal Microsoft accounts.
- `ONEDRIVE_CLIENT_SECRET`: Secret value for that app (not the secret's ID).
- `ONEDRIVE_REFRESH_TOKEN`: Delegated OAuth refresh token issued after the owner signs in and consents to Microsoft Graph `Files.Read`.

The app must support **personal Microsoft accounts**. Use the Microsoft identity platform's authorization-code flow with delegated `Files.Read` and `offline_access` permissions. Do not use an app-only/client-credentials token: a personal OneDrive account requires delegated user access.

Never commit tokens, client secrets, downloaded archives, or auth response files to GitHub. If a refresh token is rotated/revoked, update the GitHub secret. Grant only read access; the workflow only downloads files.

## OneDrive source mapping

The downloader currently maps raster codes 12, 21 and 23 to the existing OneDrive item IDs. It downloads only a selected archive that is not already present in the workflow checkout. Codes 07, 10 and 13 remain available from the small archives currently tracked in the repository.

## Validation

After configuring secrets, run **Actions → Analyse real harvest polygons against volume rasters → Run workflow** and select raster code 23 with a small sample first (for example 25 polygons). Confirm the logs report a downloaded file size and SHA-256, and that the raster analysis report contains polygon statuses and valid-cell counts. Then test 12 and 21. Only then run a larger sample.

The workflow does not alter or delete the original OneDrive files. The analysis report should be treated as diagnostic until its results have been checked against known sample polygons and the official product documentation.
