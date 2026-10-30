#!/usr/bin/env python3
"""Sign in to a personal Microsoft account and save a OneDrive refresh token locally.

The token is written outside the repository (by default to the user's home
folder). Never commit or share that file.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests

AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPES = "https://graph.microsoft.com/Files.Read offline_access"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-id",
        default=os.environ.get("ONEDRIVE_CLIENT_ID", ""),
        help="Entra application (client) ID; may also be set as ONEDRIVE_CLIENT_ID.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / ".skogskoll-onedrive-auth.json",
        help="Private local output file (default: ~/.skogskoll-onedrive-auth.json).",
    )
    args = parser.parse_args()

    if not args.client_id:
        parser.error("Supply --client-id or set ONEDRIVE_CLIENT_ID.")

    device_response = requests.post(
        f"{AUTHORITY}/oauth2/v2.0/devicecode",
        data={"client_id": args.client_id, "scope": SCOPES},
        timeout=30,
    )
    if not device_response.ok:
        raise SystemExit(
            f"Could not start Microsoft sign-in (HTTP {device_response.status_code}). "
            "Check the client ID and that public client flows are enabled."
        )

    device = device_response.json()
    print(device.get("message", "Open the Microsoft device-login page and enter the displayed code."))
    device_code = device["device_code"]
    interval = int(device.get("interval", 5))
    deadline = time.monotonic() + int(device.get("expires_in", 900))

    while time.monotonic() < deadline:
        time.sleep(interval)
        token_response = requests.post(
            f"{AUTHORITY}/oauth2/v2.0/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": args.client_id,
                "device_code": device_code,
            },
            timeout=30,
        )
        payload = token_response.json()
        if token_response.ok and payload.get("refresh_token"):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temp_path = args.output.with_suffix(args.output.suffix + ".tmp")
            temp_path.write_text(
                json.dumps(
                    {
                        "client_id": args.client_id,
                        "refresh_token": payload["refresh_token"],
                        "scope": payload.get("scope", SCOPES),
                        "created_at": int(time.time()),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            temp_path.replace(args.output)
            try:
                os.chmod(args.output, 0o600)
            except OSError:
                pass
            print(f"Sign-in successful. Refresh token saved locally to: {args.output}")
            print("Do not upload this file or paste its contents into chat.")
            print("Next, add its refresh_token value to the GitHub Actions secret ONEDRIVE_REFRESH_TOKEN.")
            return 0

        error = payload.get("error", "")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "authorization_declined":
            raise SystemExit("Microsoft sign-in was declined.")
        if error == "expired_token":
            raise SystemExit("The device code expired. Run this script again.")
        description = payload.get("error_description", "Unknown Microsoft identity error.")
        raise SystemExit(f"Microsoft sign-in failed ({error or token_response.status_code}): {description}")

    raise SystemExit("The device code expired before sign-in completed. Run this script again.")


if __name__ == "__main__":
    raise SystemExit(main())
