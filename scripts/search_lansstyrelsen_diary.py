#!/usr/bin/env python3
"""Search the public Länsstyrelserna diary using its normal ASP.NET form.

This client submits an ordinary public search and stores only displayed public
case-result data. It does not access authenticated areas or bypass controls.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://diarium.lansstyrelsen.se/"
SEARCH_URL = urljoin(BASE_URL, "default.aspx")
FIELD_PREFIX = "ctl00$SearchPlaceHolder$CaseSearch$"


def normalized_text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def select_value(soup: BeautifulSoup, name: str, desired_label: str | None = None) -> str | None:
    el = soup.find("select", {"name": name})
    if not el:
        return None
    if desired_label is None:
        selected = el.find("option", selected=True)
        return selected.get("value") if selected else (el.find("option").get("value") if el.find("option") else None)
    for option in el.find_all("option"):
        label = normalized_text(option)
        if label == desired_label or desired_label in label:
            return option.get("value")
    return None


def parse_results(soup: BeautifulSoup) -> tuple[list[dict], str | None]:
    """Extract visible result rows conservatively; preserve row text if columns vary."""
    results: list[dict] = []
    seen: set[str] = set()
    pagination_text = None

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [normalized_text(c) for c in rows[0].find_all(["th", "td"])]
        # Ignore form/layout tables; result tables tend to have case-related headings.
        if not any(re.search(r"ärende|diarie|rubrik|datum|status|handling", h, re.I) for h in headers):
            continue
        for row in rows[1:]:
            cells = [normalized_text(c) for c in row.find_all(["td", "th"])]
            if not cells or not any(cells):
                continue
            links = [
                {"text": normalized_text(a), "href": urljoin(SEARCH_URL, a.get("href", ""))}
                for a in row.find_all("a", href=True)
                if normalized_text(a) or a.get("href")
            ]
            record = {
                "columns": {headers[i] if i < len(headers) and headers[i] else f"column_{i+1}": cell
                            for i, cell in enumerate(cells)},
                "row_text": " | ".join(cells),
                "links": links,
            }
            key = record["row_text"]
            if key not in seen:
                seen.add(key)
                results.append(record)

    # Record pagination controls/text so the next iteration can be implemented reliably.
    candidates = []
    for el in soup.find_all(["a", "span", "div"]):
        text = normalized_text(el)
        if text and re.search(r"\b(sida|page|nästa|next|föregående|previous)\b", text, re.I):
            if len(text) <= 160:
                candidates.append(text)
    if candidates:
        pagination_text = " | ".join(dict.fromkeys(candidates))[:1000]
    return results, pagination_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", required=True, help="Exact public diary label, e.g. Länsstyrelsen i Västra Götalands län")
    parser.add_argument("--search-term", required=True, help="Search phrase to put in the case-title field")
    parser.add_argument("--max-pages", type=int, default=1, help="Reserved for future pagination support; currently capped at one submitted search")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Skog-public-diary-search/0.1 (+https://github.com/dahlinrobert-lgtm/Skog)",
        "Referer": SEARCH_URL,
    })
    result = {
        "source": BASE_URL,
        "search_url": SEARCH_URL,
        "requested_county": args.county,
        "search_term": args.search_term,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_ok": False,
        "search_submitted": False,
        "http_status": None,
        "final_url": None,
        "page_title": None,
        "result_count": 0,
        "results": [],
        "pagination_diagnostics": None,
        "notes": [
            "Search uses the public form and only stores displayed text and links.",
            "The diary may omit some cases and displays closed cases only for a limited period.",
            "The first implementation submits one search and does not claim completeness or follow pagination."
        ],
    }

    try:
        initial = session.get(SEARCH_URL, timeout=(15, 45))
        initial.raise_for_status()
        soup = BeautifulSoup(initial.text, "html.parser")
        form = soup.find("form", {"id": "form1"}) or soup.find("form")
        if form is None:
            raise RuntimeError("No search form was found.")

        diary_select = FIELD_PREFIX + "ddDiaryID"
        county_value = None
        for option in soup.find_all("option"):
            label = normalized_text(option)
            if args.county in label and "Länsstyrelsen i " in label:
                county_value = option.get("value")
                break
        if county_value is None:
            # Permit passing the literal all-county option if the source has one.
            county_value = select_value(soup, diary_select, args.county)
        if county_value is None:
            available = [normalized_text(o) for o in soup.find("select", {"name": diary_select}).find_all("option")] if soup.find("select", {"name": diary_select}) else []
            raise RuntimeError(f"Could not map county label {args.county!r} to a select value. Available sample: {available[:25]}")

        payload = {}
        for field in form.find_all(["input", "select", "textarea"]):
            name = field.get("name")
            if not name or field.get("disabled"):
                continue
            tag = field.name
            typ = (field.get("type") or "").lower()
            if tag == "input" and typ in {"submit", "button", "image", "reset", "file"}:
                continue
            if tag == "input" and typ in {"checkbox", "radio"} and not field.has_attr("checked"):
                continue
            if tag == "select":
                selected = field.find("option", selected=True)
                payload[name] = selected.get("value", "") if selected else (field.find("option").get("value", "") if field.find("option") else "")
            else:
                payload[name] = field.get("value", "")

        payload[diary_select] = county_value
        payload[FIELD_PREFIX + "title"] = args.search_term
        payload[FIELD_PREFIX + "btnSearch"] = "Sök"

        action = urljoin(initial.url, form.get("action") or initial.url)
        response = session.post(action, data=payload, timeout=(15, 60))
        result["search_submitted"] = True
        result["http_status"] = response.status_code
        result["final_url"] = response.url
        response.raise_for_status()
        result["request_ok"] = True
        soup = BeautifulSoup(response.text, "html.parser")
        result["page_title"] = soup.title.get_text(" ", strip=True) if soup.title else None
        rows, pagination = parse_results(soup)
        result["results"] = rows
        result["result_count"] = len(rows)
        result["pagination_diagnostics"] = pagination
        result["response_excerpt"] = normalized_text(soup.body)[:1600] if soup.body else ""

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "search_submitted": result["search_submitted"],
        "http_status": result["http_status"],
        "county": result["requested_county"],
        "search_term": result["search_term"],
        "result_count": result["result_count"],
        "final_url": result["final_url"],
        "error": result.get("error"),
    }, ensure_ascii=False))
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
