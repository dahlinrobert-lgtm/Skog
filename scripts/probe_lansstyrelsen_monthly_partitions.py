#!/usr/bin/env python3
"""Probe monthly diary intervals using the production grid parser and pager."""
from __future__ import annotations
import calendar, json, re
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from search_lansstyrelsen_diary_browser import (
    URL, COUNTY_SELECT, TITLE_INPUT, SEARCH_BUTTON, RESULT_GRID,
    clean, parse_total, extract_grid, select_next_pager_action,
)

COUNTY_LABEL = "Länsstyrelsen i Norrbottens län"
DATE_FROM = "#SearchPlaceHolder_CaseSearch_ddDatefrom"
DATE_TO = "#SearchPlaceHolder_CaseSearch_ddDateto"

def query(page, start: str, end: str) -> dict:
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=30000)
    options = [{"label":clean(o.inner_text()),"value":o.get_attribute("value")}
               for o in page.locator(f"{COUNTY_SELECT} option").all()]
    county = next((o for o in options if o["label"] == COUNTY_LABEL), None)
    if not county:
        raise RuntimeError(f"County option not found: {COUNTY_LABEL}")
    page.locator(COUNTY_SELECT).select_option(value=county["value"])
    page.locator(TITLE_INPUT).fill("vattenverksamhet")
    page.locator(DATE_FROM).fill(start)
    page.locator(DATE_TO).fill(end)
    try:
        with page.expect_navigation(wait_until="domcontentloaded", timeout=12000):
            page.locator(SEARCH_BUTTON).click(timeout=10000)
    except PlaywrightTimeoutError:
        pass

    grid = page.locator(RESULT_GRID)
    try:
        grid.wait_for(state="attached", timeout=20000)
    except PlaywrightTimeoutError:
        pass
    body = clean(page.locator("body").inner_text(timeout=20000))
    total = parse_total(body)
    if grid.count() == 0:
        zero = re.search(r"\bSökresultat\s*:\s*0\b", body, re.I) is not None
        return {"from":start,"to":end,"source_total":0 if zero else total,
                "extracted_unique_ids":0,"pages_read":0,"grid_present":False,
                "pager_complete":zero,"reconciled":zero,"error":None if zero else "No grid and no explicit zero",
                "page_url":page.url,"body_excerpt":body[:1200]}

    seen=set()
    page_signatures=set()
    page_count=0
    pager_complete=False
    pager_trace=[]
    for page_no in range(1,101):
        grid.wait_for(state="visible",timeout=10000)
        ids=tuple(match for row in page.locator(f"{RESULT_GRID} tr").all()
                  for match in re.findall(r"\b\d{1,6}-\d{4}\b",clean(row.inner_text())))
        if ids in page_signatures:
            raise RuntimeError(f"Repeated page signature at page {page_no}: {ids[:4]}")
        page_signatures.add(ids)
        rows,diag=extract_grid(page,page_no,seen)
        page_count=page_no
        current_body=clean(page.locator("body").inner_text(timeout=15000))
        if total is None:
            total=parse_total(current_body)
        pager=page.locator(f"{RESULT_GRID} tr").last
        controls=pager.locator("a, input, button, [role='button']") if pager.count() else page.locator(f"{RESULT_GRID} a")
        candidates=[]
        for i in range(controls.count()):
            control=controls.nth(i)
            tag=control.evaluate("(e)=>e.tagName.toLowerCase()")
            label=clean(" ".join([
                control.inner_text() if tag not in {"input","button"} else "",
                control.get_attribute("value") or "",
                control.get_attribute("title") or "",
                control.get_attribute("aria-label") or "",
                control.get_attribute("alt") or "",
            ])).casefold()
            href=control.get_attribute("href") or ""
            onclick=control.get_attribute("onclick") or ""
            event=re.search(r"""__doPostBack\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\)"""," ".join((href,onclick)))
            if event:
                target,arg=event.groups()
                candidates.append({"label":label,"target":target,"argument":arg,"element":control})
        next_item=select_next_pager_action(candidates,page_no-1)
        pager_trace.append({"page":page_no,"visible_ids":len(ids),"new_ids":len(rows),
                            "pager":[{"label":c["label"],"argument":c["argument"]} for c in candidates]})
        if next_item is None:
            pager_complete=True
            break
        before=ids
        response_seen=False
        try:
            with page.expect_response(lambda resp:"diarium.lansstyrelsen.se" in resp.url
                                      and resp.request.method=="POST",timeout=25000):
                page.evaluate("([t,a])=>__doPostBack(t,a)",[next_item["target"],next_item["argument"]])
            response_seen=True
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_function("""({selector,previous})=>{
              const g=document.querySelector(selector); if(!g)return false;
              const ids=Array.from(g.querySelectorAll('tr')).flatMap(r=>
                Array.from((r.innerText||'').matchAll(/\b\d{1,6}-\d{4}\b/g),m=>m[0]));
              return ids.length>0 && ids.join('|')!==previous.join('|');
            }""",arg={"selector":RESULT_GRID,"previous":list(before)},timeout=25000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Pager postback failed page={page_no} arg={next_item['argument']} response_seen={response_seen}") from exc
    else:
        raise RuntimeError("Safety cap 100 page transitions reached")

    return {"from":start,"to":end,"source_total":total,
            "extracted_unique_ids":len(seen),"pages_read":page_count,
            "grid_present":True,"pager_complete":pager_complete,
            "reconciled": total is not None and len(seen)==total and pager_complete,
            "pager_trace":pager_trace,"error":None if total is not None else "Source total not parseable",
            "page_url":page.url}

def main():
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(locale="sv-SE")
        try:
            for year in (2025,2026):
                for month in range(1,13):
                    start=f"{year}-{month:02d}-01"
                    end=f"{year}-{month:02d}-{calendar.monthrange(year,month)[1]:02d}"
                    try:
                        result=query(page,start,end)
                    except Exception as exc:
                        result={"from":start,"to":end,"source_total":None,
                                "extracted_unique_ids":0,"pages_read":0,"grid_present":False,
                                "pager_complete":False,"reconciled":False,
                                "error":f"{type(exc).__name__}: {exc}"}
                    results.append(result)
                    print(json.dumps({k:v for k,v in result.items() if k!="pager_trace"},ensure_ascii=False),flush=True)
        finally:
            browser.close()
    payload={"captured_at_utc":datetime.now(timezone.utc).isoformat(),
             "county":COUNTY_LABEL,"search_term":"vattenverksamhet",
             "months_tested":len(results),
             "months_reconciled":sum(bool(x["reconciled"]) for x in results),
             "months_unknown_total":sum(x["source_total"] is None for x in results),
             "months_pager_incomplete":sum(not x["pager_complete"] for x in results),
             "sum_monthly_totals":sum(x["source_total"] or 0 for x in results),
             "monthly_results":results}
    Path("lansstyrelsen-monthly-partition-probe.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY "+json.dumps({k:v for k,v in payload.items() if k!="monthly_results"},ensure_ascii=False))

if __name__=="__main__":
    main()
