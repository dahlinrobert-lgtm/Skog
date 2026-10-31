#!/usr/bin/env python3
"""Check the Skogsstyrelsen raster account against Skogsdatalabbet services.

The catalogue explicitly says the Torvkarta and SIS REST/WMS services require
a user account. This script checks service metadata only using the account
issued for raster REST/WMS access. It never downloads raster pixels.

Never print credentials, credential-bearing URLs, response bodies, or tokens.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

SERVICES = {
    "torvkarta": (
        "https://geodata.skogsstyrelsen.se/arcgis/rest/services/"
        "Skogsdatalabbet/Torvkarta_1_0/ImageServer"
    ),
    "sis": (
        "https://geodata.skogsstyrelsen.se/arcgis/rest/services/"
        "Skogsdatalabbet/SIS_1_0/ImageServer"
    ),
}
OUT = Path("artifacts/skogsstyrelsen-geodata-account-probe.json")
TIMEOUT = (15, 45)


def probe_service(session: requests.Session, name: str, endpoint: str) -> dict:
    result = {
        "service_key": name,
        "result": "not_run",
        "http_status": None,
        "arcgis_error_code": None,
        "service_name": None,
        "pixel_type": None,
        "band_count": None,
    }
    try:
        response = session.get(
            endpoint,
            params={"f": "json"},
            timeout=TIMEOUT,
        )
        result["http_status"] = response.status_code
        if not response.ok:
            result["result"] = "http_denied_or_unavailable"
            return result
        try:
            payload = response.json()
        except ValueError:
            result["result"] = "non_json_response"
            return result

        error = payload.get("error") or {}
        if error:
            result["result"] = "arcgis_access_error"
            result["arcgis_error_code"] = error.get("code")
        elif payload.get("serviceDescription") is not None or payload.get("pixelType") is not None:
            result["result"] = "service_metadata_ok"
            result["service_name"] = payload.get("name")
            result["pixel_type"] = payload.get("pixelType")
            result["band_count"] = payload.get("bandCount")
        else:
            result["result"] = "unexpected_json_response"
    except requests.Timeout:
        result["result"] = "timeout"
    except requests.RequestException as exc:
        # Exception strings may contain request URLs; record only the class.
        result["result"] = "request_error"
        result["request_error_type"] = type(exc).__name__
    return result


def main() -> int:
    username = os.environ.get("SKOGSSTYRELSEN_GEODATA_USERNAME", "")
    password = os.environ.get("SKOGSSTYRELSEN_GEODATA_PASSWORD", "")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_scope": "Skogsdatalabbet raster REST account services",
        "authentication_method": "HTTP Basic authentication (requests auth)",
        "credentials_present": bool(username and password),
        "results": [],
        "notes": [
            "The Skogsdatalabbet catalogue lists Torvkarta and SIS REST/WMS services as requiring a user account.",
            "This probe uses the raster REST/WMS account supplied by Skogsstyrelsen, not FTP credentials and not OAuth client credentials.",
            "Only ImageServer metadata is requested; no raster pixels are exported.",
            "No credentials, request URLs, response bodies, or tokens are written to the report.",
            "A successful metadata response proves access to that service only; it does not imply access to restricted Geodatasamverkan products."
        ],
    }
    if not username or not password:
        report["result"] = "missing_github_secrets"
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    with requests.Session() as session:
        session.auth = (username, password)
        session.headers.update({"User-Agent": "Skog-geodata-account-probe/1.3"})
        report["results"] = [
            probe_service(session, name, endpoint)
            for name, endpoint in SERVICES.items()
        ]

    statuses = [x["result"] for x in report["results"]]
    if all(x == "service_metadata_ok" for x in statuses):
        report["result"] = "all_services_metadata_ok"
        exit_code = 0
    elif any(x == "service_metadata_ok" for x in statuses):
        report["result"] = "partial_service_access"
        exit_code = 0
    else:
        report["result"] = "no_service_metadata_access"
        exit_code = 1

    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


def write_report(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
