#!/usr/bin/env python3
"""Probe monthly diary date filters robustly and retain per-month diagnostics."""
from __future__ import annotations
import calendar, json, re
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

def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def parse_total(body: str) -> int | None:
    match = re.search(r"Sökresultat\s*:?\s*[\d\s–-]+\s+av\s+(\d+)", body, re.I)
    if match:
        return int(match.group(1))
    if re.search(r"Sökresultat\s*:?\s*0\b", body, re.I):
        return 0
    return None

def run_query(page, start: str, end: str) -> dict:
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.locator(COUNTY).wait_for(state="visible", timeout=30000)
    page.locator(COUNTY).select_option(value="21")
    page.locator(TITLE).fill("vattenverksamhet")
    page.locator(DATE_FROM).fill(start)
    page.locator(DATE_TO).fill(end)
    try:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=12000):
            page.locator(SEARCH).click(timeout=10000)
    except PlaywrightTimeoutError:
        pass
    grid = page.locator(GRID)
    try:
        grid.wait_for(state="attached", timeout=20000)
    except PlaywrightTimeoutError:
        pass
    body = clean(page.locator("body").inner_text(timeout=20000))
    total = parse_total(body)
    if grid.count() == 0:
        return {"from":start,"to":end,"reported_total":total,"visible_unique_ids":0,
                "grid_rows":0,"grid_present":False,"result_text_excerpt":body[:1400],
                "page_url":page.url,"error":None if total == 0 else "No result grid and no explicit source total"}
    rows = grid.locator("tr")
    ids=[]
    for i in range(rows.count()):
        ids.extend(re.findall(r"\b\d{1,6}-\d{4}\b", clean(rows.nth(i).inner_text())))
    unique=len(set(ids))
    return {"from":start,"to":end,"reported_total":total,"visible_unique_ids":unique,
            "grid_rows":rows.count(),"grid_present":True,
            "result_text_excerpt":body[:1400],"page_url":page.url,
            "error":None if total is not None else "Could not parse source total"}

def main():
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale="sv-SE")
        try:
            for year in (2025, 2026):
                for month in range(1,13):
                    last=calendar.monthrange(year,month)[1]
                    start=f"{year}-{month:02d}-01"
                    end=f"{year}-{month:02d}-{last:02d}"
                    try:
                        item=run_query(page,start,end)
                    except Exception as exc:
                        item={"from":start,"to":end,"reported_total":None,
                              "visible_unique_ids":0,"grid_rows":0,"grid_present":False,
                              "error":f"{type(exc).__name__}: {exc}"}
                    results.append(item)
                    print(json.dumps(item,ensure_ascii=False),flush=True)
        finally:
            browser.close()
    payload={"captured_at_utc":datetime.now(timezone.utc).isoformat(),
             "county":"Norrbotten","county_value":"21","term":"vattenverksamhet",
             "monthly_results":results,
             "sum_monthly_totals":sum(x["reported_total"] or 0 for x in results)}
    Path("lansstyrelsen-monthly-partition-probe.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY "+json.dumps({"sum_monthly_totals":payload["sum_monthly_totals"],
        "months_tested":len(results),
        "months_with_results":sum(1 for x in results if (x["reported_total"] or 0)>0),
        "months_missing_count":sum(1 for x in results if x["reported_total"] is None),
        "months_with_errors":sum(1 for x in results if x.get("error"))},ensure_ascii=False))

if __name__=="__main__":
    main()
