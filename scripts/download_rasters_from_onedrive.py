#!/usr/bin/env python3
"""Download selected Skogsstyrelsen volume ZIP archives from a personal OneDrive using delegated OAuth."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "skogliga-grunddata"
DRIVE_ID = "FDA5CD345A37C354"
ITEMS = {
    "12": "FDA5CD345A37C354!s54aeac4e38e74c73a2dc743948312fe9",
    "21": "FDA5CD345A37C354!s526b9a7e2484409ba34e90af3aacd216",
    "23": "FDA5CD345A37C354!sef562c75df7f4ba2b19bb045b5e11620",
}


def main() -> int:
    codes = [x.strip() for x in os.environ.get("RASTER_CODES", "12,21,23").split(",") if x.strip()]
    unknown = [code for code in codes if code not in ITEMS]
    if unknown:
        raise SystemExit(f"No OneDrive item mapping configured for raster code(s): {','.join(unknown)}.")

    missing = [code for code in codes if not (DATA_DIR / f"sks_Volym_omdrev3_{code}.zip").exists()]
    if not missing:
        print("All selected raster archives already exist; no OneDrive download needed.")
        return 0

    client_id = os.environ.get("ONEDRIVE_CLIENT_ID", "")
    refresh_token = os.environ.get("ONEDRIVE_REFRESH_TOKEN", "")
    if not (client_id and refresh_token):
        raise SystemExit(
            "Missing GitHub Actions secrets. Configure ONEDRIVE_CLIENT_ID and "
            "ONEDRIVE_REFRESH_TOKEN to download missing archives from personal "
            f"OneDrive. Missing raster codes: {','.join(missing)}"
        )

    response = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data={
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "https://graph.microsoft.com/Files.Read offline_access",
        },
        timeout=60,
    )
    if not response.ok:
        error = response.json().get("error", "unknown_error")
        raise SystemExit(
            f"OneDrive OAuth refresh failed (HTTP {response.status_code}, {error}). "
            "Re-authenticate with scripts/onedrive_device_login.py and replace "
            "the ONEDRIVE_REFRESH_TOKEN GitHub secret."
        )
    token = response.json().get("access_token")
    if not token:
        raise SystemExit("OAuth response did not contain an access token.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "User-Agent": "Skogskoll-volume-analysis/1.0"})
    # Resolve item metadata first. The stored source identifiers include a
    # drive prefix and a custom "s" marker; the Graph item ID must be the
    # complete driveItem ID returned by Graph, not a guessed suffix.
    for code in missing:
        stored_id = ITEMS[code]
        metadata_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{stored_id}"
        metadata = session.get(metadata_url, timeout=60)
        if not metadata.ok:
            body = metadata.text[:1200].replace("\\n", " ")
            raise SystemExit(
                f"Graph could not resolve the configured OneDrive item for raster {code} "
                f"(HTTP {metadata.status_code}): {body}"
            )
        item = metadata.json()
        item_id = item.get("id")
        if not item_id or "file" not in item:
            raise SystemExit(
                f"Configured OneDrive item for raster {code} is not a file; "
                f"Graph returned item name={item.get('name', '<unknown>')!r}."
            )
        print(
            f"Resolved raster {code} OneDrive item: name={item.get('name')!r}, "
            f"size={item.get('size')}, item_id={item_id}",
            flush=True,
        )
        target = DATA_DIR / f"sks_Volym_omdrev3_{code}.zip"
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item_id}/content"
        temp = target.with_suffix(target.suffix + ".part")
        with session.get(url, stream=True, allow_redirects=True, timeout=(60, 300)) as download:
            if not download.ok:
                body = download.text[:1200].replace("\\n", " ")
                raise SystemExit(
                    f"OneDrive content download for raster {code} failed "
                    f"(HTTP {download.status_code}): {body}"
                )
            digest = hashlib.sha256()
            size = 0
            with temp.open("wb") as stream:
                for chunk in download.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        stream.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
        if size < 1024:
            temp.unlink(missing_ok=True)
            raise SystemExit(f"Downloaded raster {code} is unexpectedly small ({size} bytes).")
        temp.replace(target)
        print(f"Downloaded raster {code}: bytes={size}, sha256={digest.hexdigest()}, file={target.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
