#!/usr/bin/env python3
"""Search the public Länsstyrelsen diary and extract result-grid rows."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

URL = "https://diarium.lansstyrelsen.se/default.aspx"
COUNTY_SELECT = "#SearchPlaceHolder_CaseSearch_ddDiaryID"
TITLE_INPUT = "#SearchPlaceHolder_CaseSearch_title"
SEARCH_BUTTON = "#SearchPlaceHolder_CaseSearch_btnSearch"
RESULT_GRID = "#SearchPlaceHolder_caseGridView"


def clean(text: str) -> str:
    return re.sub(r"\\s+", " ", text).strip()


def parse_total(text: str) -> int | None:
    patterns = (
        r"Sökresultat\s*:?\s*[\d\s–-]+\s+av\s+(\d+)",
        r"\b(?:träffar|ärenden)\s*:?\s*(\d+)\b",
        r"\bantal\s+(?:träffar|ärenden)\s*:?\s*(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


def extract_grid(page, page_number: int, seen: set[str]) -> tuple[list[dict], dict]:
    grid = page.locator(RESULT_GRID)
    rows = grid.locator("tr")
    headers = [clean(x) for x in rows.nth(0).locator("th, td").all_inner_texts()] if rows.count() else []
    records = []
    for row_index in range(1, rows.count()):
        row = rows.nth(row_index)
        if not row.is_visible():
            continue
        values = [clean(x) for x in row.locator("th, td").all_inner_texts()]
        if not values or not any(values):
            continue
        diary_number = values[0]
        if not re.fullmatch(r"\d{1,6}-\d{4}", diary_number):
            continue
        if diary_number in seen:
            continue
        seen.add(diary_number)
        record = {
            headers[i] if i < len(headers) and headers[i] else f"column_{i+1}": value
            for i, value in enumerate(values)
        }
        links = row.locator("a")
        record.update({
            "diary_number": diary_number,
            "status": record.get("Status"),
            "date": record.get("In/Upp-datum"),
            "title": record.get("Ärenderubrik"),
            "links": [
                {"text": clean(links.nth(i).inner_text()), "href": links.nth(i).get_attribute("href")}
                for i in range(links.count())
            ],
            "page_number": page_number,
        })
        records.append(record)
    diag = {
        "page_number": page_number,
        "headers": headers,
        "row_count_including_header": rows.count(),
        "result_rows_extracted": len(records),
    }
    return records, diag


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
                options = [clean(x) for x in page.locator(f"{COUNTY_SELECT} option").all_text_contents()]
                if args.county not in options:
                    raise RuntimeError(f"County option not found: {args.county}")
                page.locator(COUNTY_SELECT).select_option(label=args.county)
                page.locator(TITLE_INPUT).fill(args.search_term)

                # Wait for either a full postback or an async postback to settle.
                try:
                    with page.expect_navigation(wait_until="domcontentloaded", timeout=20000):
                        page.locator(SEARCH_BUTTON).click()
                except PlaywrightTimeoutError:
                    # This public ASP.NET form can use an asynchronous postback.
                    page.locator(SEARCH_BUTTON).click(timeout=3000) if page.locator(SEARCH_BUTTON).is_visible() else None
                    page.wait_for_timeout(1800)

                # The query may return zero rows, in which case the grid is absent.
                try:
                    page.locator(RESULT_GRID).wait_for(state="attached", timeout=12000)
                    grid_present = True
                except PlaywrightTimeoutError:
                    grid_present = page.locator(RESULT_GRID).count() > 0

                body_text = clean(page.locator("body").inner_text(timeout=20000))
                result["http_status"] = 200 if page.locator("body").count() else 0
                result["page_text_excerpt"] = body_text[:5000]
                result["page_text_tail_excerpt"] = body_text[-2500:]
                result["criterion_validation_message"] = (
                    "Minst ett sökkriterium förutom diarium måste vara angivet" in body_text
                )
                result["reported_total_results"] = parse_total(body_text)

                if result["criterion_validation_message"]:
                    raise RuntimeError("Diary form rejected the query because a search criterion was missing")
                if result["reported_total_results"] == 0:
                    result["request_ok"] = True
                    result["pagination"]["has_next_page"] = False
                elif not grid_present:
                    raise RuntimeError("No result grid found although the page did not report zero results")
                else:
                    seen: set[str] = set()
                    max_pages = 100
                    result["request_ok"] = True
                    for page_number in range(1, max_pages + 1):
                        try:
                            page.locator(RESULT_GRID).wait_for(state="visible", timeout=10000)
                        except PlaywrightTimeoutError:
                            raise RuntimeError(f"Result grid not visible on page {page_number}")
                        body_text = clean(page.locator("body").inner_text(timeout=20000))
                        if result["reported_total_results"] is None:
                            result["reported_total_results"] = parse_total(body_text)
                        records, diag = extract_grid(page, page_number, seen)
                        result["results"].extend(records)
                        result["table_diagnostics"].append(diag)
                        result["pagination"]["pages_read"] = page_number

                        next_candidates = page.locator(
                            "#SearchPlaceHolder_caseGridView a, "
                            "#SearchPlaceHolder_caseGridView input[type='submit'], "
                            "#SearchPlaceHolder_caseGridView input[type='button']"
                        )
                        next_control = None
                        for i in range(next_candidates.count()):
                            control = next_candidates.nth(i)
                            label = clean(" ".join([
                                control.inner_text() if control.evaluate("(e) => e.tagName.toLowerCase() !== 'input'") else "",
                                control.get_attribute("value") or "",
                                control.get_attribute("title") or "",
                                control.get_attribute("aria-label") or "",
                            ]))
                            if label.casefold() in {"next", "nästa", ">", "»", "›"} or "nästa" in label.casefold() or "next" in label.casefold():
                                next_control = control
                                break

                        if next_control is None:
                            result["pagination"]["has_next_page"] = False
                            break

                        old_first_id = result["results"][0]["diary_number"] if result["results"] else None
                        old_page_count = len(seen)
                        href = next_control.get_attribute("href") or ""
                        postback_match = re.search(r"__doPostBack\(['\"]([^'\"]+)['\"],['\"]([^'\"]*)['\"]\)", href)
                        if postback_match:
                            target, argument = postback_match.groups()
                            with page.expect_response(lambda resp: "diarium.lansstyrelsen.se" in resp.url and resp.request.method == "POST", timeout=15000):
                                page.evaluate("([t,a]) => __doPostBack(t,a)", [target, argument])
                        else:
                            try:
                                with page.expect_navigation(wait_until="domcontentloaded", timeout=12000):
                                    next_control.click()
                            except PlaywrightTimeoutError:
                                next_control.click(timeout=3000)
                                page.wait_for_timeout(1200)
                        page.wait_for_timeout(300)
                        if len(seen) == old_page_count:
                            new_body = clean(page.locator("body").inner_text(timeout=20000))
                            new_grid = page.locator(RESULT_GRID)
                            new_first_id = None
                            if new_grid.count() and new_grid.locator("tr").count() > 1:
                                new_first_id = clean(new_grid.locator("tr").nth(1).locator("td, th").nth(0).inner_text())
                            if new_body == body_text or new_first_id == old_first_id:
                                raise RuntimeError(f"Pagination did not advance after page {page_number}")
                    else:
                        raise RuntimeError(f"Safety cap reached after {max_pages} result pages")

                result["result_count"] = len(result["results"])
                result["visible_case_count_hint"] = result["result_count"]
                result["total_reconciled"] = (
                    result["reported_total_results"] is not None
                    and result["reported_total_results"] == result["result_count"]
                    and result["pagination"]["has_next_page"] is False
                )
                if result["request_ok"] and result["reported_total_results"] is not None and not result["total_reconciled"]:
                    result["validation_warning"] = "Extracted results do not match reported total"
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
    if not result["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
