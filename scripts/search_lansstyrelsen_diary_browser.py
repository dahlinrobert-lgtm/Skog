#!/usr/bin/env python3
"""Search the public Länsstyrelsen diary and extract result-grid rows."""
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
RESULT_GRID = "#SearchPlaceHolder_caseGridView"


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
        "reported_total_results": None,
        "results": [],
        "pagination": {"pages_read": 0, "has_next_page": None},
        "table_diagnostics": [],
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
                with page.expect_navigation(wait_until="domcontentloaded", timeout=45000):
                    page.locator(SEARCH_BUTTON).click()

                result["request_ok"] = True
                seen = set()
                max_pages = 100
                for page_number in range(1, max_pages + 1):
                    page.wait_for_timeout(300)
                    body_text = clean(page.locator("body").inner_text(timeout=20000))
                    grid = page.locator(RESULT_GRID)
                    if grid.count() == 0 or not grid.is_visible():
                        result["request_ok"] = False
                        result["error"] = "Search completed but the expected result grid was not found"
                        break

                    grid_rows = grid.locator("tr")
                    rows_this_page = 0
                    header_cells = grid_rows.nth(0).locator("th, td")
                    headers = [clean(header_cells.nth(i).inner_text()) for i in range(header_cells.count())]
                    for row_index in range(1, grid_rows.count()):
                        row = grid_rows.nth(row_index)
                        if not row.is_visible():
                            continue
                        cells = row.locator("th, td")
                        values = [clean(cells.nth(i).inner_text()) for i in range(cells.count())]
                        if not any(values):
                            continue

                        # Column headers are source-defined. Preserve the complete row
                        # and map key fields by header, not positional guesses.
                        record = {headers[i] if i < len(headers) and headers[i] else f"column_{i+1}": v
                                  for i, v in enumerate(values)}
                        diary_number = values[0] if values else ""
                        if not re.fullmatch(r"\d{1,6}-\d{4}", diary_number):
                            continue
                        if diary_number in seen:
                            continue
                        seen.add(diary_number)
                        links = row.locator("a")
                        record.update({
                            "diary_number": diary_number,
                            "status": record.get("Status"),
                            "date": record.get("In/Upp-datum"),
                            "title": record.get("Ärenderubrik"),
                            "links": [
                                {"text": clean(links.nth(i).inner_text()),
                                 "href": links.nth(i).get_attribute("href")}
                                for i in range(links.count())
                            ],
                            "page_number": page_number,
                        })
                        result["results"].append(record)
                        rows_this_page += 1

                    result["pagination"]["pages_read"] = page_number
                    result["table_diagnostics"].append({
                        "page_number": page_number,
                        "headers": headers,
                        "row_count_including_header": grid_rows.count(),
                        "result_rows_extracted": rows_this_page,
                    })

                    # Read total hits displayed by the source separately from
                    # the rows captured. This must reconcile before data is trusted.
                    total_match = re.search(r"Sökresultat\s*:?\s*[\d\s–-]+\s+av\s+(\d+)", body_text, re.I)
                    if total_match:
                        result["reported_total_results"] = int(total_match.group(1))

                    next_button = page.locator(
                        "#SearchPlaceHolder_caseGridView a[title*='Next'], "
                        "#SearchPlaceHolder_caseGridView a[aria-label*='Next'], "
                        "#SearchPlaceHolder_caseGridView a[title*='Nästa'], "
                        "#SearchPlaceHolder_caseGridView a[aria-label*='Nästa']"
                    )
                    if next_button.count() == 0:
                        # Fall back to visible grid pager links. Use DOM postback target
                        # through the user's normal public UI, not a guessed endpoint.
                        pager_links = grid.locator("a")
                        candidates = []
                        for i in range(pager_links.count()):
                            link = pager_links.nth(i)
                            label = clean(link.inner_text())
                            title = clean(link.get_attribute("title") or "")
                            aria = clean(link.get_attribute("aria-label") or "")
                            if label in {"Next", "Nästa", ">", "»"} or "next" in title.lower() or "nästa" in title.lower() or "next" in aria.lower():
                                candidates.append(link)
                        next_button = candidates[0] if candidates else None
                    if not next_button or (hasattr(next_button, "count") and next_button.count() == 0):
                        result["pagination"]["has_next_page"] = False
                        break
                    result["pagination"]["has_next_page"] = True
                    before = len(seen)
                    try:
                        with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                            next_button.click()
                    except Exception:
                        # Some ASP.NET GridView paging uses an asynchronous postback.
                        try:
                            next_button.click(timeout=3000)
                            page.wait_for_timeout(1000)
                        except Exception:
                            result["request_ok"] = False
                            result["error"] = f"Could not advance to result page {page_number + 1}"
                            break
                    if len(seen) == before:
                        new_body = clean(page.locator("body").inner_text(timeout=20000))
                        if new_body == body_text:
                            result["request_ok"] = False
                            result["error"] = f"Pagination did not change the page after page {page_number}"
                            break
                else:
                    result["request_ok"] = False
                    result["error"] = f"Safety cap reached after {max_pages} result pages"

                result["result_count"] = len(result["results"])
                result["visible_case_count_hint"] = len(seen)
                result["total_reconciled"] = (
                    result["reported_total_results"] is not None
                    and result["reported_total_results"] == result["result_count"]
                    and result["pagination"]["has_next_page"] is False
                )
                result["page_text_excerpt"] = clean(page.locator("body").inner_text(timeout=20000))[:3000]
                if result["request_ok"] and not result["total_reconciled"]:
                    result["validation_warning"] = "Captured row count has not been reconciled to the source's total hit count"
            finally:
                browser.close()
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["request_ok"] = False

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": result["request_ok"],
        "county": result["requested_county"],
        "search_term": result["search_term"],
        "result_count": result["result_count"],
        "reported_total_results": result["reported_total_results"],
        "total_reconciled": result.get("total_reconciled"),
        "pagination": result["pagination"],
        "error": result.get("error"),
        "validation_warning": result.get("validation_warning"),
    }, ensure_ascii=False))
    # Return nonzero when we failed to obtain the grid or pagination stopped
    # unexpectedly. A total reconciliation warning remains visible but doesn't
    # hide a technically successful first-page capture.
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
