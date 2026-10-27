#!/usr/bin/env python3
"""Inspect the public Länsstyrelsen diary search form and validate field mapping."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://diarium.lansstyrelsen.se/"
SEARCH_URL = urljoin(BASE_URL, "default.aspx")
PREFIX = "ctl00$SearchPlaceHolder$CaseSearch$"


def norm(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--county", required=True)
    p.add_argument("--search-term", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = {
        "source": BASE_URL,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_ok": False,
        "http_status": None,
        "page_title": None,
        "forms": [],
        "fields": [],
        "county_options": [],
        "button_candidates": [],
        "search_term": args.search_term,
        "requested_county": args.county,
    }
    try:
        response = requests.get(SEARCH_URL, headers={
            "User-Agent": "Skog-public-diary-form-inspector/0.2 (+https://github.com/dahlinrobert-lgtm/Skog)"
        }, timeout=(15, 45))
        result["http_status"] = response.status_code
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        result["request_ok"] = True
        result["page_title"] = soup.title.get_text(" ", strip=True) if soup.title else None
        for form in soup.find_all("form"):
            result["forms"].append({
                "id": form.get("id"),
                "method": form.get("method", "get"),
                "action": urljoin(response.url, form.get("action", "")),
                "fields": [x.get("name") for x in form.find_all(["input", "select", "textarea"]) if x.get("name")],
            })
        diary = soup.find("select", {"name": PREFIX + "ddDiaryID"})
        if diary:
            for opt in diary.find_all("option"):
                label = norm(opt)
                if label:
                    result["county_options"].append({"label": label, "value": opt.get("value", "")})
        form = soup.find("form", {"id": "form1"}) or soup.find("form")
        if form:
            for field in form.find_all(["input", "select", "textarea", "button"]):
                name = field.get("name", "")
                val = field.get("value", "")
                result["fields"].append({
                    "tag": field.name,
                    "type": field.get("type", ""),
                    "name": name,
                    "id": field.get("id", ""),
                    "value": val[:120] if name.lower().find("viewstate") < 0 and name.lower().find("eventvalidation") < 0 else "[redacted-hidden-state]",
                    "text": norm(field)[:120] if field.name in ("button",) else "",
                    "selected": bool(field.has_attr("selected")),
                    "disabled": field.has_attr("disabled"),
                })
                if field.name in ("button", "input") and (
                    field.get("type") in ("submit", "button", "image") or
                    re.search(r"sök|search", field.get("value", "") + " " + field.get("id", ""), re.I)
                ):
                    result["button_candidates"].append({
                        "tag": field.name, "type": field.get("type", ""),
                        "name": name, "id": field.get("id", ""), "value": field.get("value", "")
                    })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "http_status": result["http_status"],
        "forms": len(result["forms"]),
        "fields": len(result["fields"]),
        "county_options": len(result["county_options"]),
        "buttons": result["button_candidates"],
        "error": result.get("error"),
    }, ensure_ascii=False))
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
