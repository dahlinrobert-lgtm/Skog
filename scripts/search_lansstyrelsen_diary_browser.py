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

from lansstyrelsen_diary_validation import (
    has_explicit_zero_results,
    resolve_county_labels,
    summarize_county_coverage,
)

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


def select_next_pager_action(candidates: list[dict], current_page_index: int) -> dict | None:
    """Select the next action from a sliding ASP.NET GridView pager."""
    numeric = []
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if match and int(match.group(1)) > current_page_index + 1:
            numeric.append((int(match.group(1)), item))
    if numeric:
        return min(numeric, key=lambda pair: pair[0])[1]
    # In this portal, the ellipsis's Page$1 command advances the pager window.
    for item in candidates:
        if item["argument"].casefold() == "page$1" and item["label"] in {"...", "…"}:
            return item
    for item in candidates:
        if item["argument"].casefold() in {"last", "page$last"}:
            return item
    for item in candidates:
        if item["argument"].casefold() in {"next", "page$next"}:
            return item
    return None


def parse_search_terms(primary: str, extras: str = "") -> list[str]:
    """Normalize a primary phrase and optional comma/semicolon/newline-separated phrases."""
    terms: list[str] = []
    for candidate in [primary, *re.split(r"[,;\n\r]+", extras or "")]:
        term = candidate.strip()
        if term and term.casefold() not in {existing.casefold() for existing in terms}:
            terms.append(term)
    if not terms:
        raise ValueError("At least one non-empty search term is required")
    if any(len(term) < 2 for term in terms):
        raise ValueError("Search terms must contain at least two characters")
    if len(terms) > 10:
        raise ValueError("A maximum of 10 search terms can be searched in one batch")
    return terms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--county", required=True, help="Exact public diary option label or 'Alla län'")
    parser.add_argument("--search-term", required=True)
    parser.add_argument("--extra-search-terms", default="", help="Additional comma- or newline-separated title phrases")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        terms = parse_search_terms(args.search_term, args.extra_search_terms)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    def wait_for_diary_form(page, *, attempts: int = 3) -> None:
        """Wait for the diary form, retrying transient slow/partial portal loads."""
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=45000)
                page.locator(TITLE_INPUT).wait_for(state="visible", timeout=15000)
                page.locator(SEARCH_BUTTON).wait_for(state="visible", timeout=15000)
                return
            except PlaywrightTimeoutError as exc:
                last_error = exc
                if attempt == attempts:
                    break
                # A fresh navigation is more reliable than waiting indefinitely on
                # a partially initialized ASP.NET page.
                try:
                    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                except PlaywrightTimeoutError:
                    pass
                page.wait_for_timeout(1500 * attempt)
        raise RuntimeError(
            f"Diary search form did not become ready after {attempts} attempts: {last_error}"
        ) from last_error

    def get_options(browser) -> list[dict]:
        page = browser.new_page(locale="sv-SE")
        try:
            for attempt in range(1, 4):
                try:
                    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                except PlaywrightTimeoutError:
                    pass
                try:
                    wait_for_diary_form(page, attempts=2)
                    options = [
                        {"label": clean(opt.inner_text()), "value": opt.get_attribute("value")}
                        for opt in page.locator(f"{COUNTY_SELECT} option").all()
                    ]
                    if options:
                        return options
                except Exception:
                    if attempt == 3:
                        raise
                    page.wait_for_timeout(1500 * attempt)
            raise RuntimeError("Diary county list remained empty after retries")
        finally:
            page.close()

    def run_query(term: str, browser, county_label: str) -> dict:
        result = {
            "search_term": term, "requested_county": county_label, "request_ok": False,
            "result_count": 0, "reported_total_results": None, "results": [],
            "pagination": {"pages_read": 0, "has_next_page": None},
            "table_diagnostics": [], "error": None,
        }
        page = browser.new_page(locale="sv-SE")
        seen: set[str] = set()
        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            result["initial_http_status"] = response.status if response else None
            page.locator(COUNTY_SELECT).wait_for(state="visible", timeout=30000)
            options = [
                {"label": clean(opt.inner_text()), "value": opt.get_attribute("value")}
                for opt in page.locator(f"{COUNTY_SELECT} option").all()
            ]
            selected = next((o for o in options if o["label"] == county_label), None)
            if selected is None:
                raise RuntimeError(f"County option not found: {county_label}")
            page.locator(COUNTY_SELECT).select_option(value=selected["value"])
            page.locator(TITLE_INPUT).fill(term)
            # The portal may submit through a full navigation or an ASP.NET
            # asynchronous postback. Do not treat a timed-out navigation wait as
            # proof that the submit failed; wait for either results or validation.
            try:
                with page.expect_navigation(wait_until="domcontentloaded", timeout=12000):
                    page.locator(SEARCH_BUTTON).click(timeout=10000)
            except PlaywrightTimeoutError:
                pass

            try:
                page.locator(RESULT_GRID).wait_for(state="attached", timeout=20000)
                grid_present = True
            except PlaywrightTimeoutError:
                grid_present = page.locator(RESULT_GRID).count() > 0

            body_text = clean(page.locator("body").inner_text(timeout=20000))
            result["submit_button_present"] = page.locator(SEARCH_BUTTON).count() > 0
            result["submit_button_text"] = (
                clean(page.locator(SEARCH_BUTTON).inner_text())
                if page.locator(SEARCH_BUTTON).count() else None
            )
            result["document_ready_state"] = page.evaluate("document.readyState")
            result["form_action"] = page.locator(SEARCH_BUTTON).evaluate(
                "(e) => ({tag: e.tagName, type: e.getAttribute('type'), name: e.getAttribute('name'), value: e.getAttribute('value'), disabled: e.disabled, formAction: e.form ? e.form.action : null})"
            ) if page.locator(SEARCH_BUTTON).count() else None
            result["http_status"] = 200 if page.locator("body").count() else 0
            result["reported_total_results"] = parse_total(body_text)
            # Search results can legitimately contain zero matches. The result page
            # may not render the original ASP.NET grid in that case, but it displays
            # "Sökresultat: 0". Accept only an explicit zero count, never an unknown one.
            if not grid_present and has_explicit_zero_results(body_text):
                result["reported_total_results"] = 0
                result["request_ok"] = True
                result["pagination"]["has_next_page"] = False
                result["result_count"] = 0
                result["total_reconciled"] = True
                result["validation_warning"] = None
                result["zero_results_confirmed_by_source"] = True
                return result
            # Preserve enough source diagnostics to explain portal/layout changes
            # without accepting an unvalidated response as a successful search.
            result["body_text_excerpt"] = body_text[:2500]
            result["result_grid_present"] = grid_present
            result["result_grid_selector"] = RESULT_GRID
            result["current_url"] = page.url
            result["title_input_value"] = page.locator(TITLE_INPUT).input_value() if page.locator(TITLE_INPUT).count() else None
            result["criterion_validation_message"] = (
                "Minst ett sökkriterium förutom diarium måste vara angivet" in body_text
            )
            if result["criterion_validation_message"]:
                raise RuntimeError("Diary form rejected the query because a search criterion was missing")

            if result["reported_total_results"] == 0:
                result["request_ok"] = True
                result["pagination"]["has_next_page"] = False
            elif not grid_present:
                # Include diagnostics from the actual submitted page in the error.
                # A fresh-page probe only shows the initial form and cannot tell
                # whether the submit was rejected, intercepted, or postback failed.
                result["diagnostic_after_submit"] = {
                    "body_text_excerpt": body_text[:2500],
                    "current_url": page.url,
                    "result_grid_present": grid_present,
                    "title_input_value": result.get("title_input_value"),
                    "county_selected_value": page.locator(COUNTY_SELECT).input_value()
                        if page.locator(COUNTY_SELECT).count() else None,
                    "county_selected_label": page.locator(
                        f"{COUNTY_SELECT} option:checked"
                    ).inner_text() if page.locator(f"{COUNTY_SELECT} option:checked").count() else None,
                    "submit_button": result.get("form_action"),
                    "document_ready_state": result.get("document_ready_state"),
                }
                raise RuntimeError(
                    "No result grid found although source did not report zero results; "
                    f"submitted-page diagnostics: {json.dumps(result['diagnostic_after_submit'], ensure_ascii=False)}"
                )
            else:
                result["request_ok"] = True
                visited_page_signatures: set[tuple[str, ...]] = set()
                current_page_index = 0
                for iteration in range(1, 501):
                    page.locator(RESULT_GRID).wait_for(state="visible", timeout=10000)
                    visible_ids = tuple(
                        match
                        for row in page.locator(f"{RESULT_GRID} tr").all()
                        for match in re.findall(r"\b\d{1,6}-\d{4}\b", clean(row.inner_text()))
                    )
                    if visible_ids in visited_page_signatures:
                        # The diary uses an ASP.NET sliding pager. Its Page$1
                        # ellipsis command advances the visible page-number window,
                        # not always the underlying result page. A window transition
                        # can briefly leave the same 50 result rows visible. Detect
                        # a loop only after the pager itself offers no new action.
                        current_pager_row = page.locator(f"{RESULT_GRID} tr").last
                        current_controls = (
                            current_pager_row.locator("a, input, button, [role='button']")
                            if current_pager_row.count()
                            else page.locator(f"{RESULT_GRID} a, {RESULT_GRID} input, {RESULT_GRID} button")
                        )
                        current_actions = []
                        for control_index in range(current_controls.count()):
                            control = current_controls.nth(control_index)
                            tag_name = control.evaluate("(e) => e.tagName.toLowerCase()")
                            control_label = clean(" ".join([
                                control.inner_text() if tag_name not in {"input", "button"} else "",
                                control.get_attribute("value") or "",
                                control.get_attribute("title") or "",
                                control.get_attribute("aria-label") or "",
                                control.get_attribute("alt") or "",
                            ])).casefold()
                            href_value = control.get_attribute("href") or ""
                            onclick_value = control.get_attribute("onclick") or ""
                            postback = re.search(
                                r"""__doPostBack\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\)""",
                                " ".join((href_value, onclick_value)),
                            )
                            if postback:
                                action_target, action_argument = postback.groups()
                                current_actions.append({
                                    "label": control_label,
                                    "target": action_target,
                                    "argument": action_argument,
                                })
                        continuation = select_next_pager_action(current_actions, current_page_index)
                        if continuation is None:
                            raise RuntimeError(
                                f"Pagination loop detected at iteration {iteration}: "
                                f"repeated result page with {len(visible_ids)} diary IDs "
                                "and no valid pager continuation"
                            )
                    visited_page_signatures.add(visible_ids)

                    current_body = clean(page.locator("body").inner_text(timeout=20000))
                    if result["reported_total_results"] is None:
                        result["reported_total_results"] = parse_total(current_body)

                    rows, diag = extract_grid(page, iteration, seen)
                    result["results"].extend(rows)
                    result["table_diagnostics"].append(diag)
                    result["pagination"]["pages_read"] = iteration
                    result["pagination"]["current_page_index"] = current_page_index

                    # The portal uses a sliding GridView page window. Its ellipsis
                    # postback argument "Page$1" advances the *window*, not the
                    # result-page index. The first/last links use Page$First/Last.
                    pager_rows = page.locator(f"{RESULT_GRID} tr")
                    pager = pager_rows.last
                    pager_text = clean(pager.inner_text()) if pager.count() else ""
                    controls = pager.locator("a, input, button, [role='button']") if pager.count() else page.locator(
                        f"{RESULT_GRID} a, {RESULT_GRID} input, {RESULT_GRID} button"
                    )

                    candidates = []
                    for i in range(controls.count()):
                        control = controls.nth(i)
                        tag = control.evaluate("(e) => e.tagName.toLowerCase()")
                        label = clean(" ".join([
                            control.inner_text() if tag not in {"input", "button"} else "",
                            control.get_attribute("value") or "",
                            control.get_attribute("title") or "",
                            control.get_attribute("aria-label") or "",
                            control.get_attribute("alt") or "",
                        ])).casefold()
                        href = control.get_attribute("href") or ""
                        onclick = control.get_attribute("onclick") or ""
                        event = re.search(
                            r"""__doPostBack\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\)""",
                            " ".join((href, onclick)),
                        )
                        if event:
                            target, argument = event.groups()
                            candidates.append({
                                "label": label, "target": target, "argument": argument,
                                "element": control,
                            })

                    next_item = select_next_pager_action(candidates, current_page_index)

                    if next_item is None:
                        for item in candidates:
                            if item["argument"].casefold() == "page$1" and item["label"] in {"...", "…"}:
                                next_item = item
                                break

                    if next_item is None:
                        # A GridView may expose a direct Next or Last control.
                        for item in candidates:
                            if item["argument"].casefold() in {"next", "page$next", "last", "page$last"}:
                                next_item = item
                                break

                    if next_item is None:
                        reported_now = parse_total(current_body)
                        if reported_now is not None and len(seen) < reported_now:
                            raise RuntimeError(
                                "Portal pager exposes no continuation although source total is larger: "
                                f"iteration={iteration}, extracted={len(seen)}, reported={reported_now}, "
                                f"pager_text={pager_text!r}, candidates="
                                f"{[(x['label'], x['argument']) for x in candidates]!r}"
                            )
                        result["pagination"]["has_next_page"] = False
                        break

                    target = next_item["target"]
                    argument = next_item["argument"]
                    before_signature = visible_ids
                    response_seen = False
                    try:
                        with page.expect_response(
                            lambda resp: "diarium.lansstyrelsen.se" in resp.url
                            and resp.request.method == "POST",
                            timeout=25000,
                        ):
                            page.evaluate("([t,a]) => __doPostBack(t,a)", [target, argument])
                        response_seen = True
                    except PlaywrightTimeoutError:
                        pass

                    try:
                        page.wait_for_function(
                            """({selector, previous}) => {
                                const grid = document.querySelector(selector);
                                if (!grid) return false;
                                const ids = Array.from(grid.querySelectorAll('tr'))
                                  .flatMap(row => Array.from((row.innerText || '').matchAll(/\\b\\d{1,6}-\\d{4}\\b/g), m => m[0]));
                                return ids.length > 0 && ids.join('|') !== previous.join('|');
                            }""",
                            arg={"selector": RESULT_GRID, "previous": list(before_signature)},
                            timeout=25000,
                        )
                    except PlaywrightTimeoutError as exc:
                        raise RuntimeError(
                            "WebForms page-window postback did not change the visible result page: "
                            f"iteration={iteration}, argument={argument!r}, response_seen={response_seen}, "
                            f"current_ids={before_signature[:4]!r}"
                        ) from exc

                    page_after = tuple(
                        match
                        for row in page.locator(f"{RESULT_GRID} tr").all()
                        for match in re.findall(r"\\b\\d{1,6}-\\d{4}\\b", clean(row.inner_text()))
                    )
                    current_page_index += 1
                    result["pagination"]["last_page_signature"] = list(page_after[:5])
                else:
                    raise RuntimeError("Safety cap reached after 500 result-page transitions")

            result["result_count"] = len(result["results"])
            result["total_reconciled"] = (
                result["reported_total_results"] is not None
                and result["reported_total_results"] == result["result_count"]
                and result["pagination"]["has_next_page"] is False
            )
            if not result["total_reconciled"]:
                raise RuntimeError(
                    f"Query '{term}' / '{county_label}' extracted {result['result_count']} records "
                    f"but source reported {result['reported_total_results']}"
                )
            result["validation_warning"] = None
            return result
        finally:
            page.close()

    batch = {
        "source": URL, "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_county": args.county, "search_term": terms[0], "search_terms": terms,
        "browser_submission": True, "request_ok": False, "result_count": 0,
        "reported_total_results": None, "results": [],
        "pagination": {"pages_read": 0, "has_next_page": False},
        "table_diagnostics": [], "error": None, "queries": [], "counties": [],
    }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                options = get_options(browser)
                if args.county == "Alla län":
                    # Search each county separately. The public result grid does not
                    # reliably include the county label on each row, so using a portal
                    # wide "Alla län" option would make us misattribute every record
                    # to the aggregate label in persistent history.
                    try:
                        counties = resolve_county_labels(options)
                    except ValueError as exc:
                        raise RuntimeError(
                            "The portal's county diary list is incomplete or ambiguous; "
                            "refusing to report an all-county search as successful. "
                            f"{exc}"
                        ) from exc
                    selection_mode = "individual_counties"
                else:
                    counties = [args.county]
                    selection_mode = "single_county"
                batch["counties"] = counties
                batch["selection_mode"] = selection_mode
                batch["expected_county_count"] = len(counties)
                batch["county_coverage_ok"] = (
                    len(counties) == 21
                    and len(set(counties)) == 21
                    if args.county == "Alla län"
                    else True
                )
                merged: dict[str, dict] = {}
                for county in counties:
                    for term in terms:
                        try:
                            query = run_query(term, browser, county)
                        except Exception as query_exc:
                            # Keep diagnostics from the failing county/term. Without
                            # this wrapper, the batch-level error loses the page text
                            # and URL needed to troubleshoot a portal response.
                            query = {
                                "search_term": term,
                                "requested_county": county,
                                "request_ok": False,
                                "result_count": 0,
                                "reported_total_results": None,
                                "results": [],
                                "pagination": {"pages_read": 0, "has_next_page": None},
                                "table_diagnostics": [],
                                "error": f"{type(query_exc).__name__}: {query_exc}",
                            }
                            try:
                                diag_page = browser.new_page(locale="sv-SE")
                                try:
                                    diag_page.goto(URL, wait_until="domcontentloaded", timeout=30000)
                                    query["diagnostic_url"] = diag_page.url
                                    query["diagnostic_http_status"] = 200
                                    query["diagnostic_body_text_excerpt"] = clean(
                                        diag_page.locator("body").inner_text(timeout=10000)
                                    )[:2500]
                                    query["diagnostic_result_grid_present"] = (
                                        diag_page.locator(RESULT_GRID).count() > 0
                                    )
                                    query["diagnostic_county_select_present"] = (
                                        diag_page.locator(COUNTY_SELECT).count() > 0
                                    )
                                finally:
                                    diag_page.close()
                            except Exception as diag_exc:
                                query["diagnostic_capture_error"] = (
                                    f"{type(diag_exc).__name__}: {diag_exc}"
                                )
                            batch["queries"].append(query)
                            raise RuntimeError(
                                f"Search failed for '{term}' in '{county}': {query['error']}; "
                                f"diagnostics: {json.dumps({k: query.get(k) for k in ('diagnostic_url', 'diagnostic_http_status', 'diagnostic_body_text_excerpt', 'diagnostic_result_grid_present', 'diagnostic_county_select_present', 'diagnostic_capture_error')}, ensure_ascii=False)}"
                            ) from query_exc
                        batch["queries"].append(query)
                        for record in query["results"]:
                            diary_number = record["diary_number"]
                            key = f"{county.casefold()}::{diary_number}"
                            if key not in merged:
                                record["diary"] = county
                                record["query_terms"] = [term]
                                merged[key] = record
                            elif term not in merged[key]["query_terms"]:
                                merged[key]["query_terms"].append(term)
                batch["results"] = list(merged.values())
                batch["request_ok"] = bool(batch["queries"]) and all(q["request_ok"] for q in batch["queries"])
                batch["result_count"] = len(batch["results"])
                batch["reported_total_results"] = sum(q["reported_total_results"] for q in batch["queries"] if q["reported_total_results"] is not None)
                batch["pagination"]["pages_read"] = sum(q["pagination"]["pages_read"] or 0 for q in batch["queries"])
                batch["pagination"]["has_next_page"] = False if all(q["pagination"]["has_next_page"] is False for q in batch["queries"]) else None
                batch["total_reconciled"] = batch["request_ok"] and all(q.get("total_reconciled") for q in batch["queries"])
                batch["per_query_counts"] = [
                    {"county": q["requested_county"], "search_term": q["search_term"],
                     "extracted_count": q["result_count"], "reported_total_results": q["reported_total_results"],
                     "total_reconciled": q["total_reconciled"]}
                    for q in batch["queries"]
                ]
                coverage = summarize_county_coverage(
                    counties, batch["queries"], is_all_counties=args.county == "Alla län"
                )
                batch.update(coverage)
                for row in batch["county_summaries"]:
                    row["unique_records"] = sum(
                        1 for rec in batch["results"] if rec.get("diary") == row["county"]
                    )
                # National search must verify not just the portal dropdown but that
                # every county/term query returned a validated, reconciled response.
                if args.county == "Alla län" and not batch["county_coverage_ok"]:
                    raise RuntimeError(
                        "All-county coverage validation failed: "
                        f"{batch['completed_counties']}/{batch['expected_county_count']} counties complete; "
                        f"failed counties: {batch['failed_counties']!r}"
                    )
                # The persistence layer validates aggregate queries per-query. Its top-level
                # total is set to unique IDs to handle overlap between county/query sets.
                batch["reported_total_results"] = batch["result_count"]
            finally:
                browser.close()
    except Exception as exc:
        batch["error"] = f"{type(exc).__name__}: {exc}"
        batch["request_ok"] = False
        batch["total_reconciled"] = False
    batch["validation_warning"] = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "request_ok": batch["request_ok"], "county": batch["requested_county"],
        "counties_searched": len(batch.get("counties", [])), "selection_mode": batch.get("selection_mode"),
        "expected_county_count": batch.get("expected_county_count"),
        "completed_counties": batch.get("completed_counties"),
        "failed_counties": batch.get("failed_counties"),
        "county_coverage_ok": batch.get("county_coverage_ok"),
        "search_terms": batch.get("search_terms"), "result_count": batch["result_count"],
        "reported_total_results": batch["reported_total_results"],
        "total_reconciled": batch.get("total_reconciled"), "per_query_counts": batch.get("per_query_counts"),
        "error": batch.get("error"),
    }, ensure_ascii=False))
    if not batch["request_ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
