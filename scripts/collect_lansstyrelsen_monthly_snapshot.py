#!/usr/bin/env python3
"""Collect one county/phrase over a calendar month with complete source reconciliation."""
from __future__ import annotations
import argparse, calendar, json, re, uuid
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from lansstyrelsen_pager import select_next_pager_action
from search_lansstyrelsen_diary_browser import (
 URL, COUNTY_SELECT, TITLE_INPUT, SEARCH_BUTTON, RESULT_GRID, clean, parse_total,
 extract_grid
)

DATE_FROM="#SearchPlaceHolder_CaseSearch_ddDatefrom"
DATE_TO="#SearchPlaceHolder_CaseSearch_ddDateto"

def collect_interval(page, county_label, phrase, start, end):
 page.goto(URL,wait_until="domcontentloaded",timeout=60000)
 page.locator(COUNTY_SELECT).wait_for(state="visible",timeout=30000)
 opts=[{"label":clean(o.inner_text()),"value":o.get_attribute("value")}
       for o in page.locator(f"{COUNTY_SELECT} option").all()]
 county=next((o for o in opts if o["label"]==county_label),None)
 if not county: raise RuntimeError(f"County option not found: {county_label}")
 page.locator(COUNTY_SELECT).select_option(value=county["value"])
 page.locator(TITLE_INPUT).fill(phrase)
 page.locator(DATE_FROM).fill(start); page.locator(DATE_TO).fill(end)
 try:
  with page.expect_navigation(wait_until="domcontentloaded",timeout=12000):
   page.locator(SEARCH_BUTTON).click(timeout=10000)
 except PlaywrightTimeoutError: pass
 grid=page.locator(RESULT_GRID)
 try: grid.wait_for(state="attached",timeout=20000)
 except PlaywrightTimeoutError: pass
 body=clean(page.locator("body").inner_text(timeout=20000))
 total=parse_total(body)
 if grid.count()==0:
  zero=re.search(r"\bSökresultat\s*:\s*0\b",body,re.I) is not None
  return {"from":start,"to":end,"source_total":0 if zero else total,
          "extracted_unique_ids":0,"pager_complete":zero,"reconciled":zero,
          "records":[],"pages_read":0,"error":None if zero else "No result grid and no explicit zero"}
 seen=set(); page_signatures=set(); records=[]; diagnostics=[]; pager_complete=False
 for page_no in range(1,101):
  grid.wait_for(state="visible",timeout=10000)
  ids=tuple(match for row in page.locator(f"{RESULT_GRID} tr").all()
            for match in re.findall(r"\b\d{1,6}-\d{4}\b",clean(row.inner_text())))
  if ids in page_signatures: raise RuntimeError(f"Repeated page signature at {page_no}")
  page_signatures.add(ids)
  extracted,diag=extract_grid(page,page_no,seen)
  records.extend(extracted); diagnostics.append(diag)
  body=clean(page.locator("body").inner_text(timeout=15000))
  if total is None: total=parse_total(body)
  pager=page.locator(f"{RESULT_GRID} tr").last
  controls=pager.locator("a, input, button, [role='button']") if pager.count() else page.locator(f"{RESULT_GRID} a")
  candidates=[]
  for i in range(controls.count()):
   c=controls.nth(i); tag=c.evaluate("(e)=>e.tagName.toLowerCase()")
   label=clean(" ".join([c.inner_text() if tag not in {"input","button"} else "",
    c.get_attribute("value") or "",c.get_attribute("title") or "",
    c.get_attribute("aria-label") or "",c.get_attribute("alt") or ""])).casefold()
   href=c.get_attribute("href") or ""; onclick=c.get_attribute("onclick") or ""
   event=re.search(r"""__doPostBack\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\)"""," ".join((href,onclick)))
   if event:
    target,arg=event.groups(); candidates.append({"label":label,"target":target,"argument":arg})
  next_item=select_next_pager_action(candidates,page_no-1)
  if next_item is None:
   pager_complete=True; break
  before=ids; response_seen=False
  try:
   with page.expect_response(lambda r:"diarium.lansstyrelsen.se" in r.url and r.request.method=="POST",timeout=25000):
    page.evaluate("([t,a])=>__doPostBack(t,a)",[next_item["target"],next_item["argument"]])
   response_seen=True
  except PlaywrightTimeoutError: pass
  try:
   page.wait_for_function("""({selector,previous})=>{
    const g=document.querySelector(selector);if(!g)return false;
    const ids=Array.from(g.querySelectorAll('tr')).flatMap(r=>
     Array.from((r.innerText||'').matchAll(/\\b\\d{1,6}-\\d{4}\\b/g),m=>m[0]));
    return ids.length>0 && ids.join('|')!==previous.join('|');
   }""",arg={"selector":RESULT_GRID,"previous":list(before)},timeout=25000)
  except PlaywrightTimeoutError as exc:
   raise RuntimeError(f"Pager postback failed at {page_no} response_seen={response_seen}") from exc
 else: raise RuntimeError("Safety cap: 100 page transitions")
 return {"from":start,"to":end,"source_total":total,"extracted_unique_ids":len(seen),
         "pager_complete":pager_complete,"reconciled":total is not None and len(seen)==total and pager_complete,
         "records":records,"pages_read":len(diagnostics),"table_diagnostics":diagnostics,"error":None}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--county",required=True)
 p.add_argument("--term",required=True)
 p.add_argument("--year",type=int,required=True)
 p.add_argument("--month",type=int,required=True)
 p.add_argument("--output",type=Path,default=Path("lansstyrelsen-month-run.json"))
 p.add_argument("--snapshots-root",type=Path,default=Path("data/lansstyrelsen-diary/snapshots"))
 p.add_argument("--manifest",type=Path,default=Path("data/lansstyrelsen-diary/snapshot-runs.jsonl"))
 a=p.parse_args()
 start=f"{a.year:04d}-{a.month:02d}-01"
 end=f"{a.year:04d}-{a.month:02d}-{calendar.monthrange(a.year,a.month)[1]:02d}"
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True); page=browser.new_page(locale="sv-SE")
  try:
   interval=collect_interval(page,a.county,a.term,start,end)
  finally: browser.close()
 observed=datetime.now(timezone.utc).isoformat()
 run={"run_id":f"diary-{a.year:04d}{a.month:02d}-{uuid.uuid4().hex[:12]}",
      "observed_at":observed,"source":URL,"county":a.county,"search_term":a.term,
      "intervals":[interval]}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(run,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 # Snapshot publication is orchestrated by the workflow after all configured
 # county/phrase runs succeed, preventing partial monthly publication.
 status={"run_complete":bool(interval.get("reconciled")),
         "source_total":interval.get("source_total"),
         "extracted_unique_ids":interval.get("extracted_unique_ids"),
         "pager_complete":interval.get("pager_complete")}
 print(json.dumps({"interval":{k:v for k,v in interval.items() if k!="records"},
                   "run":run,"status":status},ensure_ascii=False))
 if not status["run_complete"]: raise SystemExit(1)

if __name__=="__main__": main()
