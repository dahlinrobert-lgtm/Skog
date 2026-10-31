#!/usr/bin/env python3
"""Probe public Länsstyrelsen diary case pages and discover document links.

The search collector stores result-grid metadata only. This probe follows CaseInfo
links for a bounded sample and writes page text plus attachment/link metadata to
a workflow artifact; it does not publish case contents into the repository.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://diarium.lansstyrelsen.se/"


def build_case_url(href: str) -> str:
    """Resolve result-grid CaseInfo links under the portal's /Case/ route."""
    if href.startswith(("http://", "https://")):
        return href
    path = href.lstrip("/")
    if not path.casefold().startswith("case/"):
        path = "Case/" + path
    return urljoin(BASE_URL, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path("data/lansstyrelsen-diary/state.json"))
    parser.add_argument("--output", type=Path, default=Path("case-detail-probe.json"))
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 50:
        parser.error("--limit must be between 1 and 50")

    state = json.loads(args.state.read_text(encoding="utf-8"))
    records = list((state.get("records") or {}).values())
    targets = []
    seen = set()
    for record in records:
        for link in record.get("links") or (record.get("columns") or {}).get("links") or []:
            href = link.get("href") if isinstance(link, dict) else None
            if not href or "caseinfo.aspx" not in href.casefold():
                continue
            url = build_case_url(href)
            if url in seen:
                continue
            seen.add(url)
            targets.append({
                "diary_number": record.get("diary_number") or "",
                "diary": record.get("diary") or "",
                "title": record.get("title") or "",
                "url": url,
            })
            break
        if len(targets) >= args.limit:
            break

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="sv-SE")
        try:
            for target in targets:
                item = {**target, "ok": False}
                try:
                    response = page.goto(target["url"], wait_until="domcontentloaded", timeout=60000)
                    try:
                        page.locator("body").wait_for(state="visible", timeout=15000)
                    except PlaywrightTimeoutError:
                        pass
                    item.update({
                        "http_status": response.status if response else None,
                        "final_url": page.url,
                        "page_title": page.title(),
                        "body_text": page.locator("body").inner_text(timeout=20000),
                        "tables": page.locator("table").evaluate_all("""tables => tables.map(table => ({
                            caption: table.querySelector('caption')?.innerText || '',
                            rows: Array.from(table.querySelectorAll('tr')).map(row =>
                                Array.from(row.querySelectorAll('th,td')).map(cell => cell.innerText.trim())
                            ).filter(row => row.length)
                        }))"""),
                        "links": page.locator("a[href]").evaluate_all("""links => links.map(a => ({
                            text: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                            href: a.href
                        }))"""),
                        "frames": [frame.url for frame in page.frames if frame.url and frame.url != page.url],
                        "ok": bool(response and response.status < 400),
                    })
                except Exception as exc:
                    item["error"] = f"{type(exc).__name__}: {exc}"
                results.append(item)
        finally:
            browser.close()

    output = {
        "source": BASE_URL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_limit": args.limit,
        "target_count": len(targets),
        "success_count": sum(bool(item.get("ok")) for item in results),
        "results": results,
        "note": "Diagnostic artifact only. Page text and links are not committed to the repository.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("requested_limit", "target_count", "success_count")}, ensure_ascii=False))
    return 0 if results and output["success_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
