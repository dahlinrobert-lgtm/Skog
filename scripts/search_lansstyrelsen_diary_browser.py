#!/usr/bin/env python3
"""Use a real browser to submit one search on the public Länsstyrelsen diary."""
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
    return re.sub(r"\s+", " ", text).strip()


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
            page = browser.new_page(locale="sv-SE")
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            result["initial_http_status"] = response.status if response else None
            page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=30000)
            county_options = page.locator(f"{COUNTY_SELECT} option").all_text_contents()
            if args.county not in [clean(x) for x in county_options]:
                raise RuntimeError(f"County option not found. Available option sample: {[clean(x) for x in county_options[:25]]}")
            page.locator(COUNTY_SELECT).select_option(label=args.county)
            page.locator(TITLE_INPUT).fill(args.search_term)

            # Click the actual visible button. Its page JavaScript updates hidden
            # fields and clicks the hidden submit control as an ordinary browser would.
            with page.expect_navigation(wait_until="domcontentloaded", timeout=45000):
                page.locator(SEARCH_BUTTON).click()
            page.wait_for_timeout(800)
            result["final_url"] = page.url
            result["http_status"] = page.locator("body").evaluate("el => el ? 200 : 0")
            body_text = clean(page.locator("body").inner_text(timeout=20000))
            result["page_text_length"] = len(body_text)
            result["page_text_excerpt"] = body_text[:4000]
            result["page_text_tail_excerpt"] = body_text[-4000:]
            result["query_occurrences"] = body_text.casefold().count(args.search_term.casefold())
            result["criterion_validation_message"] = "Minst ett sökkriterium förutom diarium måste vara angivet" in body_text
            tables = page.locator("table")
            for i in range(min(tables.count(), 40)):
                table = tables.nth(i)
                rows = table.locator("tr")
                row_count = rows.count()
                row_texts = [clean(rows.nth(k).inner_text()) for k in range(min(row_count, 4))]
                result["table_diagnostics"].append({
                    "id": table.get_attribute("id"),
                    "class": table.get_attribute("class"),
                    "row_count": row_count,
                    "sample_rows": row_texts,
                })
            # Extract visible table rows with a case-like identifier or title.
            seen = set()
            for table in range(tables.count()):
                rows = page.locator("table").nth(table).locator("tr")
                for row_index in range(rows.count()):
                    row = rows.nth(row_index)
                    if not row.is_visible():
                        continue
                    text = clean(row.inner_text())
                    if len(text) < 8 or text in seen:
                        continue
                    if re.search(r"\b\d{4}/\d+\b|ärende|diarie|beslut|handling", text, re.I):
                        seen.add(text)
                        links = row.locator("a")
                        result["results"].append({
                            "row_text": text[:1200],
                            "links": [
                                {"text": clean(links.nth(j).inner_text()), "href": links.nth(j).get_attribute("href")}
                                for j in range(links.count())
                            ],
                        })
            result["result_count"] = len(result["results"])
            result["request_ok"] = result["initial_http_status"] == 200
            browser.close()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "initial_http_status": result.get("initial_http_status"),
        "http_status": result.get("http_status"),
        "county": result["requested_county"],
        "search_term": result["search_term"],
        "result_count": result["result_count"],
        "criterion_validation_message": result.get("criterion_validation_message"),
        "error": result.get("error"),
    }, ensure_ascii=False))
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
