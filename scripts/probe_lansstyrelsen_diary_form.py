#!/usr/bin/env python3
"""Inspect public Länsstyrelsen diary form controls without submitting a search.

This probe is read-only. It records control identifiers, labels, option values,
form metadata, and hidden-field names/lengths (never hidden-field values).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

URL = "https://diarium.lansstyrelsen.se/default.aspx"


def main() -> int:
    output = Path("lansstyrelsen-form-probe.json")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="sv-SE")
        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            try:
                page.locator("form").first.wait_for(state="attached", timeout=30000)
            except PlaywrightTimeoutError:
                pass
            payload = page.evaluate("""() => {
              const text = e => (e?.innerText || e?.textContent || '').trim().replace(/\\s+/g, ' ');
              const controls = Array.from(document.querySelectorAll('input,select,textarea,button'))
                .map(e => {
                  const id = e.id || '';
                  const name = e.name || '';
                  const labels = Array.from(e.labels || []).map(text).filter(Boolean);
                  const parentText = text(e.parentElement).slice(0, 180);
                  const options = e.tagName === 'SELECT'
                    ? Array.from(e.options).map(o => ({text: text(o), value: o.value, selected: o.selected}))
                    : [];
                  const type = (e.getAttribute('type') || e.tagName).toLowerCase();
                  const result = {
                    tag: e.tagName.toLowerCase(), type, id, name,
                    placeholder: e.getAttribute('placeholder') || '',
                    ariaLabel: e.getAttribute('aria-label') || '',
                    labels, parentText,
                    valueLength: (e.value || '').length,
                    disabled: !!e.disabled,
                    options: options.length ? options : undefined
                  };
                  if (type === 'hidden' && !/VIEWSTATE|EVENTVALIDATION/i.test(name)) {
                    result.value = (e.value || '').slice(0, 200);
                  }
                  return result;
                });
              const forms = Array.from(document.forms).map(f => ({
                id: f.id || '', name: f.name || '', method: f.method || '',
                action: f.action || '', enctype: f.enctype || ''
              }));
              const scripts = Array.from(document.scripts).map(s => s.src).filter(Boolean);
              const grid = document.querySelector('#SearchPlaceHolder_caseGridView');
              return {
                url: location.href, readyState: document.readyState,
                title: document.title, forms, controls, scriptUrls: scripts,
                gridPresent: !!grid,
                aspNet: {
                  hasDoPostBack: typeof window.__doPostBack === 'function',
                  viewStateFields: Array.from(document.querySelectorAll('input[type=hidden]'))
                    .filter(e => /VIEWSTATE|EVENTVALIDATION|EVENTTARGET|EVENTARGUMENT/i.test(e.name || e.id))
                    .map(e => ({id:e.id, name:e.name, valueLength:(e.value||'').length}))
                }
              };
            }""")
            payload["httpStatus"] = response.status if response else None
            payload["capturedAtUtc"] = datetime.now(timezone.utc).isoformat()
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({
                "httpStatus": payload["httpStatus"],
                "forms": payload["forms"],
                "controlCount": len(payload["controls"]),
                "controls": [
                    {k:v for k,v in c.items() if k not in {"options"}}
                    for c in payload["controls"]
                ],
                "viewStateFields": payload["aspNet"]["viewStateFields"],
                "scriptUrls": payload["scriptUrls"],
            }, ensure_ascii=False))
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
