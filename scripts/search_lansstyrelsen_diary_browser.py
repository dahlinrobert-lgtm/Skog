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
    parser.add_argument("--extra-search-terms", default="", help="Additional comma- or newline-separated title phrases")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    terms = [args.search_term.strip()]
    for extra in re.split(r"[,;\n\r]+", args.extra_search_terms or ""):
        extra = extra.strip()
        if extra and extra.casefold() not in {t.casefold() for t in terms}:
            terms.append(extra)

    batch = {
        "source": URL,
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_county": args.county,
        "search_term": terms[0],
        "search_terms": terms,
        "browser_submission": True,
        "request_ok": False,
        "result_count": 0,
        "reported_total_results": None,
        "results": [],
        "pagination": {"pages_read": 0, "has_next_page": False},
        "table_diagnostics": [],
        "error": None,
        "queries": [],
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                merged_by_id: dict[str, dict] = {}
                for term in terms:
                    query_result = {
                        "search_term": term,
                        "request_ok": False,
                        "result_count": 0,
                        "reported_total_results": None,
                        "results": [],
                        "pagination": {"pages_read": 0, "has_next_page": None},
                        "table_diagnostics": [],
                        "error": None,
                    }
                    page = browser.new_page(locale="sv-SE")
                    try:
                        response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                        query_result["initial_http_status"] = response.status if response else None
                        page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=30000)
                        options = [clean(x) for x in page.locator(f"{COUNTY_SELECT} option").all_text_contents()]
                        if args.county not in options:
                            raise RuntimeError(f"County option not found: {args.county}")
                        page.locator(COUNTY_SELECT).select_option(label=args.county)
                        page.locator(TITLE_INPUT).fill(term)

                        try:
                            with page.expect_navigation(wait_until="domcontentloaded", timeout=20000):
                                page.locator(SEARCH_BUTTON).click()
                        except PlaywrightTimeoutError:
                            if page.locator(SEARCH_BUTTON).is_visible():
                                page.locator(SEARCH_BUTTON).click(timeout=3000)
                            page.wait_for_timeout(1800)

                        try:
                            page.locator(RESULT_GRID).wait_for(state="attached", timeout=12000)
                            grid_present = True
                        except PlaywrightTimeoutError:
                            grid_present = page.locator(RESULT_GRID).count() > 0
                        body_text = clean(page.locator("body").inner_text(timeout=20000))
                        query_result["http_status"] = 200 if page.locator("body").count() else 0
                        query_result["reported_total_results"] = parse_total(body_text)
                        query_result["criterion_validation_message"] = (
                            "Minst ett sökkriterium förutom diarium måste vara angivet" in body_text
                        )
                        if query_result["criterion_validation_message"]:
                            raise RuntimeError("Diary form rejected the query because a search criterion was missing")
                        if query_result["reported_total_results"] == 0:
                            query_result["request_ok"] = True
                            query_result["pagination"]["has_next_page"] = False
                        elif not grid_present:
                            raise RuntimeError("No result grid found although the page did not report zero results")
                        else:
                            local_seen: set[str] = set()
                            query_result["request_ok"] = True
                            for page_number in range(1, 101):
                                page.locator(RESULT_GRID).wait_for(state="visible", timeout=10000)
                                current_body = clean(page.locator("body").inner_text(timeout=20000))
                                if query_result["reported_total_results"] is None:
                                    query_result["reported_total_results"] = parse_total(current_body)
                                records, diag = extract_grid(page, page_number, local_seen)
                                query_result["results"].extend(records)
                                query_result["table_diagnostics"].append(diag)
                                query_result["pagination"]["pages_read"] = page_number

                                controls = page.locator(
                                    "#SearchPlaceHolder_caseGridView a, "
                                    "#SearchPlaceHolder_caseGridView input[type='submit'], "
                                    "#SearchPlaceHolder_caseGridView input[type='button']"
                                )
                                next_control = None
                                for i in range(controls.count()):
                                    control = controls.nth(i)
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
                                    query_result["pagination"]["has_next_page"] = False
                                    break

                                old_count = len(local_seen)
                                old_first = query_result["results"][0]["diary_number"] if query_result["results"] else None
                                href = next_control.get_attribute("href") or ""
                                postback_match = re.search(r"__doPostBack\(['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]*)['\"]\)", href)
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
                                if len(local_seen) == old_count:
                                    new_body = clean(page.locator("body").inner_text(timeout=20000))
                                    new_grid = page.locator(RESULT_GRID)
                                    new_first = clean(new_grid.locator("tr").nth(1).locator("td, th").nth(0).inner_text()) if new_grid.count() and new_grid.locator("tr").count() > 1 else None
                                    if new_body == current_body or new_first == old_first:
                                        raise RuntimeError(f"Pagination did not advance after page {page_number}")
                            else:
                                raise RuntimeError("Safety cap reached after 100 result pages")

                        query_result["result_count"] = len(query_result["results"])
                        query_result["total_reconciled"] = (
                            query_result["reported_total_results"] is not None
                            and query_result["reported_total_results"] == query_result["result_count"]
                            and query_result["pagination"]["has_next_page"] is False
                        )
                        if not query_result["total_reconciled"]:
                            raise RuntimeError(
                                f"Query '{term}' extracted {query_result['result_count']} records but source reported "
                                f"{query_result['reported_total_results']}"
                            )
                        query_result["validation_warning"] = None
                        batch["queries"].append(query_result)
                        for record in query_result["results"]:
                            number = record["diary_number"]
                            if number not in merged_by_id:
                                record["query_terms"] = [term]
                                merged_by_id[number] = record
                            elif term not in merged_by_id[number]["query_terms"]:
                                merged_by_id[number]["query_terms"].append(term)
                    finally:
                        page.close()

                batch["results"] = list(merged_by_id.values())
                batch["request_ok"] = True
                batch["result_count"] = len(batch["results"])
                batch["reported_total_results"] = sum(q["reported_total_results"] for q in batch["queries"])
                batch["pagination"]["pages_read"] = sum(q["pagination"]["pages_read"] or 0 for q in batch["queries"])
                batch["pagination"]["has_next_page"] = False
                batch["total_reconciled"] = all(q.get("total_reconciled") for q in batch["queries"])
                batch["per_query_counts"] = [
                    {"search_term": q["search_term"], "extracted_count": q["result_count"],
                     "reported_total_results": q["reported_total_results"], "total_reconciled": q["total_reconciled"]}
                    for q in batch["queries"]
                ]
            finally:
                browser.close()
    except Exception as exc:
        batch["error"] = f"{type(exc).__name__}: {exc}"
        batch["request_ok"] = False

    batch["validation_warning"] = None
    if not batch["request_ok"] and not batch.get("error"):
        batch["error"] = "Search batch was not validated"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": batch["request_ok"],
        "county": batch["requested_county"],
        "search_term": batch["search_term"],
        "search_terms": batch.get("search_terms"),
        "result_count": batch["result_count"],
        "reported_total_results": batch["reported_total_results"],
        "total_reconciled": batch.get("total_reconciled"),
        "per_query_counts": batch.get("per_query_counts"),
        "pagination": batch["pagination"],
        "error": batch.get("error"),
        "validation_warning": batch.get("validation_warning"),
    }, ensure_ascii=False))
    if not batch["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
