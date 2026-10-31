#!/usr/bin/env python3
"""Safely verify the Skogsstyrelsen protected DTW WMS account.

The official DTW technical specification documents USER/PASS parameters on
its WMS GetCapabilities endpoint. This probe therefore tests that exact
interface rather than the ArcGIS ImageServer REST metadata endpoint.
Never print request URLs, credentials, response bodies, or tokens.
"""
from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

WMS = (
    "https://geodata.skogsstyrelsen.se/arcgis/services/"
    "Samverkan/Markfuktighet_DTW_1_1/ImageServer/WMSServer"
)
OUT = Path("artifacts/skogsstyrelsen-geodata-account-probe.json")
TIMEOUT = (15, 45)


def main() -> int:
    username = os.environ.get("SKOGSSTYRELSEN_GEODATA_USERNAME", "")
    password = os.environ.get("SKOGSSTYRELSEN_GEODATA_PASSWORD", "")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "service": "Skogsstyrelsen DTW WMS GetCapabilities",
        "authentication_method": "documented WMS USER/PASS parameters",
        "result": "not_run",
        "http_status": None,
        "wms_version": None,
        "service_title": None,
        "credentials_present": bool(username and password),
        "notes": [
            "No credentials, request URLs, response bodies, or tokens are written to the report.",
            "DTW access is restricted to eligible Geodatasamverkan participants; account validity and entitlement are separate.",
            "This metadata-only check does not request map images or raster pixels."
        ],
    }
    if not username or not password:
        report["result"] = "missing_github_secrets"
        write_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    try:
        response = requests.get(
            WMS,
            params={
                "SERVICE": "WMS",
                "REQUEST": "GetCapabilities",
                "VERSION": "1.3.0",
                "USER": username,
                "PASS": password,
            },
            headers={"User-Agent": "Skog-geodata-account-probe/1.1"},
            timeout=TIMEOUT,
        )
        report["http_status"] = response.status_code
        if not response.ok:
            report["result"] = "http_denied_or_unavailable"
        else:
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                report["result"] = "non_xml_response"
            else:
                root_name = root.tag.rsplit("}", 1)[-1]
                if root_name in {"ServiceExceptionReport", "ExceptionReport"}:
                    report["result"] = "wms_service_exception"
                elif root_name == "WMS_Capabilities":
                    report["result"] = "authenticated_service_metadata_ok"
                    report["wms_version"] = root.attrib.get("version")
                    service = next(
                        (node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Service"),
                        None,
                    )
                    if service is not None:
                        title = next(
                            (node for node in service if node.tag.rsplit("}", 1)[-1] == "Title"),
                            None,
                        )
                        report["service_title"] = title.text if title is not None else None
                else:
                    report["result"] = "unexpected_xml_response"
    except requests.Timeout:
        report["result"] = "timeout"
    except requests.RequestException as exc:
        # Exception strings can include request URLs; record only the class.
        report["result"] = "request_error"
        report["request_error_type"] = type(exc).__name__

    write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "authenticated_service_metadata_ok" else 1


def write_report(report: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
