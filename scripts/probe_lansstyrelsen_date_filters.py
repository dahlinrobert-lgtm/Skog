#!/usr/bin/env python3
"""Validate Länsstyrelsen diary registration-date filters on one controlled query."""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

URL = "https://diarium.lansstyrelsen.se/default.aspx"
COUNTY = "#SearchPlaceHolder_CaseSearch_ddDiaryID"
TITLE = "#SearchPlaceHolder_CaseSearch_title"
DATE_FROM = "#SearchPlaceHolder_CaseSearch_ddDatefrom"
DATE_TO = "#SearchPlaceHolder_CaseSearch_ddDateto"
SEARCH = "#SearchPlaceHolder_CaseSearch_btnSearch"
GRID = "#SearchPlaceHolder_caseGridView"

def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def inspect_query(page, county_value, term, start, end):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.locator(COUNTY).wait_for(state="visible", timeout=30000)
    page.locator(COUNTY).select_option(value=county_value)
    page.locator(TITLE).fill(term)
    page.locator(DATE_FROM).fill(start)
    page.locator(DATE_TO).fill(end)
    try:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=12000):
            page.locator(SEARCH).click(timeout=10000)
    except PlaywrightTimeoutError:
        pass
    try:
        page.locator(GRID).wait_for(state="attached", timeout=20000)
    except PlaywrightTimeoutError:
        pass
    body = clean(page.locator("body").inner_text(timeout=20000))
    match = re.search(r"Sökresultat\s*:?\s*[\d\s–-]+\s+av\s+(\d+)", body, re.I)
    grid = page.locator(GRID)
    rows = grid.locator("tr")
    ids=[]
    for i in range(rows.count()):
        ids.extend(re.findall(r"\b\d{1,6}-\d{4}\b", clean(rows.nth(i).inner_text())))
    return {
        "county_value":county_value,"term":term,"date_from":start,"date_to":end,
        "reported_total":int(match.group(1)) if match else None,
        "visible_unique_ids":sorted(set(ids)),
        "grid_rows":rows.count(),
        "body_excerpt":body[-1800:],
        "page_url":page.url
    }

def main():
    page_results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale="sv-SE")
        try:
            # Compare all-time count with a single-year slice to establish whether
            # the public registration-date filters are applied to title searches.
            page_results.append(inspect_query(page,"21","vattenverksamhet","1900-01-01","2026-12-31"))
            page_results.append(inspect_query(page,"21","vattenverksamhet","2026-01-01","2026-12-31"))
        finally:
            browser.close()
    payload={"captured_at_utc":datetime.now(timezone.utc).isoformat(),"queries":page_results}
    Path("lansstyrelsen-date-filter-probe.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{k:v for k,v in q.items() if k!="body_excerpt"} for q in page_results],ensure_ascii=False))

if __name__=="__main__":
    main()
