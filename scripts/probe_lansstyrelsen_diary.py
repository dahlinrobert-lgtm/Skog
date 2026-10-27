#!/usr/bin/env python3
"""Non-invasive probe of the public Länsstyrelserna diary search form.

This first step inspects form fields and checks whether the public search page can
be fetched. It does not submit searches, bypass controls, or collect case data.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://diarium.lansstyrelsen.se/"
SEARCH_URL = urljoin(BASE_URL, "default.aspx")
COUNTIES = {
    "Västra Götalands län": "Västra Götalands län",
    "Alla län": "Alla län",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", required=True, choices=COUNTIES)
    parser.add_argument("--search-term", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Skog-public-diary-source-probe/0.1 (+https://github.com/dahlinrobert-lgtm/Skog)"
    })
    result = {
        "source": BASE_URL,
        "search_url": SEARCH_URL,
        "requested_county": args.county,
        "search_term": args.search_term,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_ok": False,
        "http_status": None,
        "final_url": None,
        "page_title": None,
        "forms": [],
        "selects": [],
        "inputs": [],
        "notes": [
            "This diagnostic only inspects the public search page. It does not submit a search.",
            "The diary states that some cases may be absent and closed cases are displayed for six months."
        ],
    }

    try:
        response = session.get(SEARCH_URL, timeout=(15, 45))
        result["http_status"] = response.status_code
        result["final_url"] = response.url
        response.raise_for_status()
        result["request_ok"] = True
        soup = BeautifulSoup(response.text, "html.parser")
        result["page_title"] = soup.title.get_text(" ", strip=True) if soup.title else None

        for form in soup.find_all("form"):
            result["forms"].append({
                "id": form.get("id"),
                "method": (form.get("method") or "get").lower(),
                "action": urljoin(response.url, form.get("action") or response.url),
                "input_names": [
                    el.get("name") for el in form.find_all(["input", "select", "textarea"])
                    if el.get("name")
                ],
            })

        for select in soup.find_all("select"):
            options = []
            for option in select.find_all("option"):
                label = option.get_text(" ", strip=True)
                value = option.get("value", "")
                if label or value:
                    options.append({"label": label[:120], "value": value[:160]})
            result["selects"].append({
                "name": select.get("name"),
                "id": select.get("id"),
                "options_count": len(options),
                "options_sample": options[:80],
            })

        for field in soup.find_all("input"):
            result["inputs"].append({
                "type": field.get("type", "text"),
                "name": field.get("name"),
                "id": field.get("id"),
                "value_present": bool(field.get("value")),
                "value_length": len(field.get("value", "")),
            })

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "http_status": result["http_status"],
        "final_url": result["final_url"],
        "forms_found": len(result["forms"]),
        "selects_found": len(result["selects"]),
        "inputs_found": len(result["inputs"]),
        "error": result.get("error"),
    }, ensure_ascii=False))
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
