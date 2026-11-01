#!/usr/bin/env python3
"""Probe Länsstyrelsen diary month partitions with the production search parser."""
from __future__ import annotations
import calendar, json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

from search_lansstyrelsen_diary_browser import (
    URL, COUNTY_SELECT, TITLE_INPUT, SEARCH_BUTTON, RESULT_GRID,
    clean, parse_total,
)

COUNTY_LABEL = "Länsstyrelsen i Norrbottens län"

def query(page, start: str, end: str) -> dict:
    response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=30000)
    options = [
        {"label": clean(opt.inner_text()), "value": opt.get_attribute("value")}
        for opt in page.locator(f"{COUNTY_SELECT} option").all()
    ]
    county = next((x for x in options if x["label"] == COUNTY_LABEL), None)
    if county is None:
        raise RuntimeError(f"County option missing: {COUNTY_LABEL}")
    page.locator(COUNTY_SELECT).select_option(value=county["value"])
    page.locator(TITLE_INPUT).fill("vattenverksamhet")
    page.locator("#SearchPlaceHolder_CaseSearch_ddDatefrom").fill(start)
    page.locator("#SearchPlaceHolder_CaseSearch_ddDateto").fill(end)
    try:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=12000):
            page.locator(SEARCH_BUTTON).click(timeout=10000)
    except Exception:
        # ASP.NET may use an asynchronous postback rather than full navigation.
        pass
    grid = page.locator(RESULT_GRID)
    try:
        grid.wait_for(state="attached", timeout=20000)
    except Exception:
        pass
    body = clean(page.locator("body").inner_text(timeout=20000))
    total = parse_total(body)
    if grid.count() == 0:
        explicit_zero = total == 0
        return {"from":start,"to":end,"source_total":total,"visible_ids":0,
                "grid_present":False,"reconciled":explicit_zero,
                "error":None if explicit_zero else "Missing grid without explicit zero",
                "page_url":page.url,"body_excerpt":body[:1800]}
    grid_rows = grid.locator("tr")
    ids = []
    import re
    for i in range(grid_rows.count()):
        ids.extend(re.findall(r"\b\d{1,6}-\d{4}\b", clean(grid_rows.nth(i).inner_text())))
    unique = len(set(ids))
    return {"from":start,"to":end,"source_total":total,"visible_ids":unique,
            "grid_rows":grid_rows.count(),"grid_present":True,
            "reconciled": total is not None and unique == total,
            "error":None if total is not None else "Source total not parseable",
            "page_url":page.url,"body_excerpt":body[:1800]}

def main():
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale="sv-SE")
        try:
            for year in (2025, 2026):
                for month in range(1,13):
                    start=f"{year}-{month:02d}-01"
                    end=f"{year}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"
                    try:
                        item=query(page,start,end)
                    except Exception as exc:
                        item={"from":start,"to":end,"source_total":None,"visible_ids":0,
                              "grid_present":False,"reconciled":False,
                              "error":f"{type(exc).__name__}: {exc}"}
                    results.append(item)
                    print(json.dumps({k:v for k,v in item.items() if k!="body_excerpt"},ensure_ascii=False),flush=True)
        finally:
            browser.close()
    totals=[x["source_total"] for x in results if x["source_total"] is not None]
    payload={"captured_at_utc":datetime.now(timezone.utc).isoformat(),
             "county":COUNTY_LABEL,"search_term":"vattenverksamhet","monthly_results":results,
             "months_tested":len(results),"months_with_unknown_total":sum(x["source_total"] is None for x in results),
             "months_reconciled":sum(bool(x["reconciled"]) for x in results),
             "sum_monthly_totals":sum(totals)}
    Path("lansstyrelsen-monthly-partition-probe.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY "+json.dumps({k:v for k,v in payload.items() if k not in ("monthly_results","county","search_term")},ensure_ascii=False))

if __name__=="__main__":
    main()
