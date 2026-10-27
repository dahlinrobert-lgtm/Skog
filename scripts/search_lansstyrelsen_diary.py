#!/usr/bin/env python3
"""Search the public Länsstyrelserna diary through its normal ASP.NET form.

Submits one public search, retains visible result rows, and writes diagnostics.
This does not access authenticated areas or bypass any controls.
"""
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
DIARY_FIELD = PREFIX + "ddDiaryID"
TITLE_FIELD = PREFIX + "title"
SEARCH_BUTTON = PREFIX + "btnSearch"


def norm(node) -> str:
    return re.sub(r"\\s+", " ", node.get_text(" ", strip=True)).strip()


def parse_results(soup: BeautifulSoup) -> tuple[list[dict], str | None]:
    results: list[dict] = []
    seen: set[str] = set()
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        # ASP.NET layouts often put the real header in a thead; also inspect first row.
        header_row = table.find("tr")
        headers = [norm(c) for c in header_row.find_all(["th", "td"])] if header_row else []
        joined = " ".join(headers)
        if not re.search(r"ärende|diarie|rubrik|datum|status|handling", joined, re.I):
            continue
        for row in rows[1:]:
            cells = [norm(c) for c in row.find_all(["td", "th"])]
            if not cells or not any(cells):
                continue
            row_text = " | ".join(cells)
            if row_text in seen:
                continue
            seen.add(row_text)
            results.append({
                "columns": {headers[i] if i < len(headers) and headers[i] else f"column_{i+1}": val
                            for i, val in enumerate(cells)},
                "row_text": row_text,
                "links": [
                    {"text": norm(a), "href": urljoin(SEARCH_URL, a.get("href", ""))}
                    for a in row.find_all("a", href=True)
                ],
            })
    indicators = []
    body_text = norm(soup.body) if soup.body else ""
    for line in body_text.split(" | "):
        if re.search(r"träff|resultat|sida|nästa|föregående|ingen.*ärend|hittade", line, re.I):
            indicators.append(line[:180])
    return results, " | ".join(dict.fromkeys(indicators))[:1200] or None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", required=True, help="Exact public diary label, e.g. Länsstyrelsen i Västra Götalands län")
    parser.add_argument("--search-term", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Skog-public-diary-search/0.2 (+https://github.com/dahlinrobert-lgtm/Skog)",
        "Referer": SEARCH_URL,
    })
    result = {
        "source": BASE_URL, "search_url": SEARCH_URL,
        "requested_county": args.county, "search_term": args.search_term,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_ok": False, "search_submitted": False,
        "http_status": None, "final_url": None, "page_title": None,
        "result_count": 0, "results": [], "pagination_diagnostics": None,
        "notes": [
            "One ordinary public form submission; pagination is not yet followed.",
            "The diary may omit some cases; closed cases are displayed only for six months."
        ],
    }

    try:
        initial = session.get(SEARCH_URL, timeout=(15, 45))
        initial.raise_for_status()
        soup = BeautifulSoup(initial.text, "html.parser")
        form = soup.find("form", {"id": "form1"}) or soup.find("form")
        if form is None:
            raise RuntimeError("No search form was found.")

        diary_select = soup.find("select", {"name": DIARY_FIELD})
        if diary_select is None:
            raise RuntimeError(f"Diary selector {DIARY_FIELD!r} was not found.")
        county_value = None
        for option in diary_select.find_all("option"):
            if norm(option) == args.county or (args.county == "Alla län" and norm(option) == "Alla län"):
                county_value = option.get("value")
                break
        if county_value is None:
            # Match a label written as a county name without the "Länsstyrelsen i" prefix.
            for option in diary_select.find_all("option"):
                if args.county in norm(option):
                    county_value = option.get("value")
                    break
        if county_value is None:
            raise RuntimeError(f"County label {args.county!r} not present in the diary selector.")

        payload: dict[str, str] = {}
        for field in form.find_all(["input", "select", "textarea"]):
            name = field.get("name")
            if not name or field.has_attr("disabled"):
                continue
            tag = field.name
            typ = (field.get("type") or "").lower()
            if tag == "input":
                if typ in {"submit", "button", "image", "reset", "file"}:
                    continue
                if typ in {"checkbox", "radio"} and not field.has_attr("checked"):
                    continue
                payload[name] = field.get("value", "")
            elif tag == "select":
                selected = field.find("option", selected=True)
                payload[name] = selected.get("value", "") if selected else (
                    field.find("option").get("value", "") if field.find("option") else ""
                )
            else:
                payload[name] = field.get_text()

        # ASP.NET Web Forms requires its hidden state fields and the actual event target.
        payload[DIARY_FIELD] = county_value
        payload[TITLE_FIELD] = args.search_term
        # The visible "Sök" control is type=button and is wired through JavaScript.
        # Its hidden submit companion is the actual ASP.NET postback target.
        payload[PREFIX + "txtHiddenDiaryID"] = county_value
        payload["__EVENTTARGET"] = PREFIX + "btnHiddenSearch"
        payload["__EVENTARGUMENT"] = ""
        payload[PREFIX + "btnHiddenSearch"] = ""

        action = urljoin(initial.url, form.get("action") or initial.url)
        response = session.post(action, data=payload, timeout=(15, 60))
        result["search_submitted"] = True
        result["http_status"] = response.status_code
        result["final_url"] = response.url
        response.raise_for_status()
        result["request_ok"] = True
        output_soup = BeautifulSoup(response.text, "html.parser")
        result["page_title"] = output_soup.title.get_text(" ", strip=True) if output_soup.title else None
        results, diagnostics = parse_results(output_soup)
        result["results"] = results
        result["result_count"] = len(results)
        result["pagination_diagnostics"] = diagnostics
        result["response_excerpt"] = norm(output_soup.body)[:2200] if output_soup.body else ""
        result["submitted_field_names"] = sorted(payload.keys())
        result["response_title_contains_query"] = args.search_term.casefold() in norm(output_soup.body).casefold() if output_soup.body else False
        result["response_contains_no_results_marker"] = bool(
            output_soup.body and re.search(r"inga (träffar|ärenden)|hittade inga|0 träff", norm(output_soup.body), re.I)
        )

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "search_submitted": result["search_submitted"],
        "http_status": result["http_status"],
        "county": result["requested_county"],
        "search_term": result["search_term"],
        "result_count": result["result_count"],
        "final_url": result["final_url"],
        "pagination_diagnostics": result["pagination_diagnostics"],
        "error": result.get("error"),
    }, ensure_ascii=False))
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
