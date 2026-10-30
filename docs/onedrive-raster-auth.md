# OneDrive source for volume rasters in GitHub Actions

The analysis workflows download selected raster ZIP archives from the owner's personal OneDrive. The original OneDrive files are read-only from the workflow's perspective, and the large archives are not committed to Git history.

## Entra app configuration

Register an app that supports **personal Microsoft accounts** (the existing Skogskoll app supports all Entra tenants and personal Microsoft accounts).

Configure Microsoft Graph delegated permission:

- `Files.Read`

Keep `User.Read` if it was added by the app-registration wizard; it is not used by the raster downloader. Do not grant broader file permissions or admin consent for this personal-account workflow.

Under **Authentication → Settings**, enable **Allow public client flows**. The bootstrap script uses Microsoft's device code flow; it does not need a client secret or a SPA redirect URI.

## Create the refresh token locally

Use Python 3 and the `requests` package (already included in the repository requirements):

```powershell
python -m pip install requests
$env:ONEDRIVE_CLIENT_ID = "<your application client ID>"
python scripts/onedrive_device_login.py
```

Follow the Microsoft sign-in message printed in the terminal and sign in with the personal Microsoft account that owns the OneDrive files. Consent to the requested `Files.Read` access.

The script saves the refresh token to `%USERPROFILE%\.skogskoll-onedrive-auth.json` (or `~/.skogskoll-onedrive-auth.json` on other systems). The file is outside the repository and should be treated as a password. Do not commit it, upload it, or paste its contents into chat.

## GitHub Actions secrets required

In the repository, open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `ONEDRIVE_CLIENT_ID`: the app's Application (client) ID (not secret).
- `ONEDRIVE_REFRESH_TOKEN`: the `refresh_token` value from the local auth file.

There is no `ONEDRIVE_CLIENT_SECRET`. The app is a public client, and the downloader exchanges the delegated refresh token without a client secret.

If the refresh token is revoked or expires, rerun the local device-login script and replace the GitHub secret. Never put tokens, client secrets, downloaded archives, or auth response files in the repository.

## OneDrive source mapping

The downloader maps raster codes 12, 21 and 23 to the existing OneDrive item IDs. It downloads only a selected archive that is not already present in the workflow checkout. Codes 07, 10 and 13 remain available from the small archives currently tracked in the repository.

## Validation

After configuring secrets, run **Actions → Analyse real harvest polygons against volume rasters → Run workflow** and select raster code 23 with a small sample first (for example 25 polygons). Confirm the logs report a downloaded file size and SHA-256, and that the raster analysis report contains polygon statuses and valid-cell counts. Then test 12 and 21. Only then run a larger sample.

The workflow does not alter or delete the original OneDrive files. Treat the analysis report as diagnostic until results have been checked against known sample polygons and the official product documentation.
