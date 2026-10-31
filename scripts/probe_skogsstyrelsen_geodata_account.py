#!/usr/bin/env python3
"""Verify the Skogsstyrelsen raster geodata account against open forest data.

This is the raster REST/WMS account (username/password), NOT the separate
Skogliga grunddata calculation API, which uses OAuth client credentials.
The probe reads ImageServer service metadata only; it never exports pixels.
Never print request URLs, credentials, response bodies, or tokens.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

SERVICE = (
    "https://geodata.skogsstyrelsen.se/arcgis/rest/services/"
    "Publikt/SkogligaGrunddata_3_1/ImageServer"
)
OUT = Path("artifacts/skogsstyrelsen-geodata-account-probe.json")
TIMEOUT = (15, 45)


def main() -> int:
    username = os.environ.get("SKOGSSTYRELSEN_GEODATA_USERNAME", "")
    password = os.environ.get("SKOGSSTYRELSEN_GEODATA_PASSWORD", "")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "service": "Skogliga grunddata ImageServer (open raster data)",
        "authentication_method": "raster REST USER/PASS parameters",
        "result": "not_run",
        "http_status": None,
        "arcgis_error_code": None,
        "service_name": None,
        "service_description": None,
        "pixel_type": None,
        "band_count": None,
        "credentials_present": bool(username and password),
        "notes": [
            "This tests the raster REST/WMS account supplied by Skogsstyrelsen.",
            "It is not the separate Skogliga grunddata calculation API, which requires OAuth client_id/client_secret.",
            "No credentials, request URLs, response bodies, or tokens are written to the report.",
            "Only ImageServer metadata is requested; no raster pixels are exported.",
            "Success on this open-data service does not imply entitlement to restricted DTW or first-laser-scan products."
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
            headers={"User-Agent": "Skog-geodata-account-probe/1.2"},
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
                elif payload.get("serviceDescription") is not None or payload.get("pixelType") is not None:
                    report["result"] = "raster_service_metadata_ok"
                    report["service_name"] = payload.get("name")
                    report["service_description"] = payload.get("serviceDescription")
                    report["pixel_type"] = payload.get("pixelType")
                    report["band_count"] = payload.get("bandCount")
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
    return 0 if report["result"] == "raster_service_metadata_ok" else 1


def write_report(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
