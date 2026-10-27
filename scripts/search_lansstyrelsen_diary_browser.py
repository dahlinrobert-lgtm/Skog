#!/usr/bin/env python3
"""Use a real browser to search the public Länsstyrelsen diary and extract cases."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://diarium.lansstyrelsen.se/default.aspx"
COUNTY_SELECT = "#SearchPlaceHolder_CaseSearch_ddDiaryID"
TITLE_INPUT = "#SearchPlaceHolder_CaseSearch_title"
SEARCH_BUTTON = "#SearchPlaceHolder_CaseSearch_btnSearch"


def clean(text: str) -> str:
    return re.sub(r"\\s+", " ", text).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", required=True, help="Exact diary option label")
    parser.add_argument("--search-term", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = {
        "source": URL,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_county": args.county,
        "search_term": args.search_term,
        "browser_submission": True,
        "request_ok": False,
        "result_count": 0,
        "results": [],
        "table_diagnostics": [],
        "page_text_excerpt": "",
        "error": None,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(locale="sv-SE")
                response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                result["initial_http_status"] = response.status if response else None
                page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=30000)
                county_options = page.locator(f"{COUNTY_SELECT} option").all_text_contents()
                if args.county not in [clean(x) for x in county_options]:
                    raise RuntimeError(
                        f"County option not found. Available option sample: {[clean(x) for x in county_options[:25]]}"
                    )
                page.locator(COUNTY_SELECT).select_option(label=args.county)
                page.locator(TITLE_INPUT).fill(args.search_term)

                # Submit through the actual page JavaScript, like a normal user.
                with page.expect_navigation(wait_until="domcontentloaded", timeout=45000):
                    page.locator(SEARCH_BUTTON).click()
                page.wait_for_timeout(900)
                result["final_url"] = page.url
                result["http_status"] = 200 if page.locator("body").count() else 0
                body_text = clean(page.locator("body").inner_text(timeout=20000))
                result["page_text_length"] = len(body_text)
                result["page_text_excerpt"] = body_text[:4000]
                result["page_text_tail_excerpt"] = body_text[-4000:]
                result["query_occurrences"] = body_text.casefold().count(args.search_term.casefold())
                result["criterion_validation_message"] = (
                    "Minst ett sökkriterium förutom diarium måste vara angivet" in body_text
                )

                tables = page.locator("table")
                result_rows = []
                seen_rows: set[str] = set()
                for table_index in range(min(tables.count(), 80)):
                    table = tables.nth(table_index)
                    if not table.is_visible():
                        continue
                    rows = table.locator("tr")
                    row_count = rows.count()
                    row_samples = []
                    for row_index in range(row_count):
                        row = rows.nth(row_index)
                        if not row.is_visible():
                            continue
                        cells = row.locator("th, td")
                        cell_values = [clean(cells.nth(i).inner_text()) for i in range(cells.count())]
                        row_text = " | ".join(value for value in cell_values if value)
                        if row_text and len(row_samples) < 5:
                            row_samples.append(row_text[:700])
                        if not row_text or row_text in seen_rows:
                            continue
                        seen_rows.add(row_text)
                        diary_match = re.search(r"\\b(\\d{1,6}-\\d{4})\\b", row_text)
                        if not diary_match:
                            continue
                        links = row.locator("a")
                        result_rows.append({
                            "diary_number": diary_match.group(1),
                            "row_text": row_text[:1800],
                            "cells": cell_values,
                            "links": [
                                {"text": clean(links.nth(i).inner_text()), "href": links.nth(i).get_attribute("href")}
                                for i in range(links.count())
                            ],
                            "table_index": table_index,
                            "row_index": row_index,
                        })
                    result["table_diagnostics"].append({
                        "index": table_index,
                        "id": table.get_attribute("id"),
                        "class": table.get_attribute("class"),
                        "row_count": row_count,
                        "sample_rows": row_samples,
                    })

                # If tables are nested/layout-only, fall back to unique case numbers
                # in visible body text. Do not mistake headings for individual cases.
                if not result_rows:
                    for match in re.finditer(r"(?<!\\d)(\\d{1,6}-\\d{4})(?!\\d)", body_text):
                        number = match.group(1)
                        start = max(0, match.start() - 220)
                        end = min(len(body_text), match.end() + 900)
                        # Prefer the nearest separator-delimited snippet around one
                        # diary number; this is best-effort until detail-page parsing
                        # and pagination have been independently validated.
                        result_rows.append({
                            "diary_number": number,
                            "row_text": body_text[start:end],
                            "cells": [],
                            "links": [],
                            "table_index": None,
                            "row_index": None,
                        })
                    deduped = {}
                    for item in result_rows:
                        deduped.setdefault(item["diary_number"], item)
                    result_rows = list(deduped.values())

                result["results"] = result_rows
                result["result_count"] = len(result_rows)
                result["visible_case_count_hint"] = len(
                    re.findall(r"\\b\\d{1,6}-\\d{4}\\b", body_text)
                )
                result["request_ok"] = (
                    result["initial_http_status"] == 200
                    and result.get("http_status") == 200
                    and not result["criterion_validation_message"]
                )
            finally:
                browser.close()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "initial_http_status": result.get("initial_http_status"),
        "http_status": result.get("http_status"),
        "county": result["requested_county"],
        "search_term": result["search_term"],
        "result_count": result["result_count"],
        "visible_case_count_hint": result.get("visible_case_count_hint"),
        "criterion_validation_message": result.get("criterion_validation_message"),
        "error": result.get("error"),
    }, ensure_ascii=False))
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
