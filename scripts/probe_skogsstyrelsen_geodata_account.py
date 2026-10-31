#!/usr/bin/env python3
"""Safely verify the Skogsstyrelsen protected raster REST account.

Credentials are sent as request parameters because the official DTW technical
specification documents USER/PASS authentication for this protected service.
Never print request URLs, credentials, response bodies, or tokens.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SERVICE = (
    "https://geodata.skogsstyrelsen.se/arcgis/rest/services/"
    "Samverkan/Markfuktighet_DTW_1_1/ImageServer"
)
OUT = Path("artifacts/skogsstyrelsen-geodata-account-probe.json")
TIMEOUT = (15, 45)


def main() -> int:
    username = os.environ.get("SKOGSSTYRELSEN_GEODATA_USERNAME", "")
    password = os.environ.get("SKOGSSTYRELSEN_GEODATA_PASSWORD", "")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "service": SERVICE,
        "authentication_method": "ArcGIS REST USER/PASS parameters",
        "result": "not_run",
        "http_status": None,
        "arcgis_error_code": None,
        "service_name": None,
        "service_description": None,
        "capabilities": None,
        "credentials_present": bool(username and password),
        "notes": [
            "No credentials, request URLs, tokens, or response bodies are written to the report.",
            "The tested DTW service is documented as restricted to Geodatasamverkan participants; a valid account alone may not grant entitlement.",
            "This is a metadata-only access check; it does not download raster pixels."
        ],
    }
    if not username or not password:
        report["result"] = "missing_github_secrets"
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    try:
        response = requests.get(
            SERVICE,
            params={"f": "json", "USER": username, "PASS": password},
            headers={"User-Agent": "Skog-geodata-account-probe/1.0"},
            timeout=TIMEOUT,
        )
        report["http_status"] = response.status_code
        if not response.ok:
            report["result"] = "http_denied_or_unavailable"
        else:
            try:
                payload = response.json()
            except ValueError:
                report["result"] = "non_json_response"
            else:
                error = payload.get("error") or {}
                if error:
                    report["result"] = "arcgis_access_error"
                    report["arcgis_error_code"] = error.get("code")
                elif payload.get("name") or payload.get("serviceDescription") or payload.get("pixelType"):
                    report["result"] = "authenticated_service_metadata_ok"
                    report["service_name"] = payload.get("name")
                    report["service_description"] = payload.get("serviceDescription")
                    report["capabilities"] = payload.get("capabilities")
                else:
                    report["result"] = "unexpected_json_response"
    except requests.Timeout:
        report["result"] = "timeout"
    except requests.RequestException as exc:
        # Exception strings can contain request URLs; record only the class.
        report["result"] = "request_error"
        report["request_error_type"] = type(exc).__name__

    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "authenticated_service_metadata_ok" else 1


def write_report(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
