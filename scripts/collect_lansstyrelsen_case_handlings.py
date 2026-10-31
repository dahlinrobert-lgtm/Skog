#!/usr/bin/env python3
"""Collect structured case and handling metadata from public Länsstyrelsen diary pages.

Only public metadata is persisted: case fields and handling rows. Page body text,
personal data outside the selected table fields, and document contents are omitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://diarium.lansstyrelsen.se/"


def case_url(href: str) -> str:
    if href.startswith(("http://", "https://")):
        return href
    path = href.lstrip("/")
    if not path.casefold().startswith("case/"):
        path = "Case/" + path
    return urljoin(BASE_URL, path)


def stable_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def rows_to_dict(rows: list[list[str]]) -> dict[str, str]:
    result = {}
    for row in rows:
        if len(row) >= 2 and row[0].strip():
            result[row[0].strip()] = row[1].strip()
    return result


def parse_case_page(target: dict, page_data: dict, observed_at: str) -> dict:
    tables = page_data.get("tables") or []
    case_fields = {}
    handlings = []
    for table in tables:
        rows = table.get("rows") or []
        if not rows:
            continue
        headers = [str(x).strip() for x in rows[0]]
        if headers and headers[0].casefold() == "handlingsnummer":
            for row in rows[1:]:
                values = dict(zip(headers, [str(x).strip() for x in row]))
                number = values.get("Handlingsnummer", "")
                if not number:
                    continue
                handlings.append({
                    "handling_number": number,
                    "title": values.get("Handlingsrubrik", ""),
                    "date": values.get("In/Upp-datum", ""),
                    "sender_recipient": values.get("Avsändare/mottagare", ""),
                })
        else:
            case_fields.update(rows_to_dict(rows))
    case_fields = {
        "diary": case_fields.get("Diarium", target.get("diary", "")),
        "diary_number": case_fields.get("Diarienummer", target.get("diary_number", "")),
        "registered_date": case_fields.get("In/Upp-datum", ""),
        "title": case_fields.get("Ärenderubrik", target.get("title", "")),
        "status": case_fields.get("Status", ""),
        "decision_date": case_fields.get("Beslutsdatum", ""),
        "sender_recipient": case_fields.get("Avsändare/mottagare", ""),
        "municipality": case_fields.get("Kommun", ""),
    }
    case_key = f"{case_fields['diary'].strip().casefold()}::{case_fields['diary_number'].strip()}"
    for handling in handlings:
        handling["handling_key"] = f"{case_key}::{handling['handling_number']}"
    content = {"case": case_fields, "handlings": handlings}
    return {
        "case_key": case_key,
        "source_url": page_data.get("final_url") or target["url"],
        "observed_at": observed_at,
        **content,
        "content_hash": stable_hash(content),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path("data/lansstyrelsen-diary/state.json"))
    parser.add_argument("--details", type=Path, default=Path("data/lansstyrelsen-diary/case-details.json"))
    parser.add_argument("--events", type=Path, default=Path("data/lansstyrelsen-diary/handling-events.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("case-handling-run.json"))
    parser.add_argument("--limit", type=int, default=50, help="0 means all eligible cases")
    parser.add_argument("--delay", type=float, default=0.8, help="Seconds between case requests")
    args = parser.parse_args()
    if args.limit < 0 or args.limit > 5000:
        parser.error("--limit must be between 0 and 5000")
    if args.delay < 0 or args.delay > 30:
        parser.error("--delay must be between 0 and 30 seconds")

    state = json.loads(args.state.read_text(encoding="utf-8"))
    existing = json.loads(args.details.read_text(encoding="utf-8")) if args.details.exists() else {"schema_version": 1, "cases": {}}
    cases = existing.setdefault("cases", {})
    records = list((state.get("records") or {}).values())
    targets, seen = [], set()
    for record in records:
        links = record.get("links") or (record.get("columns") or {}).get("links") or []
        for link in links:
            href = link.get("href") if isinstance(link, dict) else None
            if not href or "caseinfo.aspx" not in href.casefold():
                continue
            url = case_url(href)
            if url in seen:
                break
            seen.add(url)
            targets.append({
                "diary_number": record.get("diary_number") or "",
                "diary": record.get("diary") or "",
                "title": record.get("title") or "",
                "url": url,
            })
            break
    # Rotate through the complete national case set: least recently observed first.
    # New cases have no prior snapshot and are therefore prioritized automatically.
    targets.sort(key=lambda target: (
        (cases.get("{}::{}".format(target["diary"].strip().casefold(), target["diary_number"].strip())) or {}).get("last_seen_at", ""),
        target["diary"], target["diary_number"],
    ))
    if args.limit:
        targets = targets[:args.limit]

    observed_at = datetime.now(timezone.utc).isoformat()
    results, new_handlings, changed_handlings, failed = [], 0, 0, 0
    event_lines = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(locale="sv-SE")
        try:
            for index, target in enumerate(targets):
                item = {"diary_number": target["diary_number"], "url": target["url"], "ok": False}
                try:
                    response = page.goto(target["url"], wait_until="domcontentloaded", timeout=60000)
                    try:
                        page.locator("body").wait_for(state="visible", timeout=15000)
                    except PlaywrightTimeoutError:
                        pass
                    status = response.status if response else None
                    item["http_status"] = status
                    if not response or status >= 400:
                        raise RuntimeError(f"HTTP {status}")
                    page_data = {
                        "final_url": page.url,
                        "tables": page.locator("table").evaluate_all("""tables => tables.map(table => ({
                          rows: Array.from(table.querySelectorAll('tr')).map(row =>
                            Array.from(row.querySelectorAll('th,td')).map(cell => cell.innerText.trim())
                          ).filter(row => row.length)
                        }))"""),
                    }
                    parsed = parse_case_page(target, page_data, observed_at)
                    old = cases.get(parsed["case_key"])
                    old_handlings = {h.get("handling_key"): h for h in (old or {}).get("handlings", [])}
                    for handling in parsed["handlings"]:
                        previous = old_handlings.get(handling["handling_key"])
                        if previous is None:
                            new_handlings += 1
                            event_lines.append({
                                "event_type": "handling_first_seen",
                                "observed_at": observed_at,
                                "case_key": parsed["case_key"],
                                "diary_number": parsed["case"]["diary_number"],
                                "handling": handling,
                            })
                        elif previous != handling:
                            changed_handlings += 1
                            event_lines.append({
                                "event_type": "handling_changed",
                                "observed_at": observed_at,
                                "case_key": parsed["case_key"],
                                "diary_number": parsed["case"]["diary_number"],
                                "before": previous,
                                "after": handling,
                            })
                    parsed["first_seen_at"] = (old or {}).get("first_seen_at", observed_at)
                    parsed["last_seen_at"] = observed_at
                    parsed["observation_count"] = int((old or {}).get("observation_count", 0)) + 1
                    cases[parsed["case_key"]] = parsed
                    item.update({"ok": True, "handling_count": len(parsed["handlings"]), "case_key": parsed["case_key"]})
                except Exception as exc:
                    failed += 1
                    item["error"] = f"{type(exc).__name__}: {exc}"
                results.append(item)
                if args.delay and index + 1 < len(targets):
                    time.sleep(args.delay)
        finally:
            browser.close()

    details_doc = {"schema_version": 1, "updated_at": observed_at, "cases": cases}
    args.details.parent.mkdir(parents=True, exist_ok=True)
    args.details.write_text(json.dumps(details_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if event_lines:
        args.events.parent.mkdir(parents=True, exist_ok=True)
        with args.events.open("a", encoding="utf-8") as stream:
            for event in event_lines:
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "generated_at": observed_at,
        "eligible_case_count": len(seen),
        "requested_limit": args.limit,
        "target_count": len(targets),
        "success_count": sum(bool(x.get("ok")) for x in results),
        "failed_count": failed,
        "new_handling_count": new_handlings,
        "changed_handling_count": changed_handlings,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("eligible_case_count", "target_count", "success_count", "failed_count", "new_handling_count", "changed_handling_count")}, ensure_ascii=False))
    return 0 if results and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
