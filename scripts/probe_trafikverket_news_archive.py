#!/usr/bin/env python3
"""Low-impact discovery probe for Trafikverket's Västerbotten news archive."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://www.trafikverket.se"
ARCHIVE_URL = BASE + "/om-oss/nyheter/?county=18"
OUT = Path("artifacts/trafikverket-news-archive-probe.json")
UA = "Skog-Trafikverket-news-archive-probe/1.0"


def fetch(url: str, timeout: int = 45) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml,text/xml,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), response.geturl()


class ArchiveParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self.forms: list[dict] = []
        self.scripts: list[object] = []
        self._anchor: dict | None = None
        self._form: dict | None = None
        self._script = False
        self._script_text = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self._anchor = {"href": a["href"], "text": ""}
        elif tag == "form":
            self._form = {"action": a.get("action"), "method": a.get("method", "get").lower(), "inputs": []}
        elif tag in {"input", "select", "button"} and self._form is not None:
            self._form["inputs"].append({k: a.get(k) for k in ("name", "type", "value", "id") if a.get(k) is not None})
        elif tag == "script":
            self._script = True
            self._script_text = ""
            if a.get("src"):
                self.scripts.append(a["src"])

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor["text"] += data
        if self._script:
            self._script_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor is not None:
            self._anchor["text"] = re.sub(r"\s+", " ", self._anchor["text"]).strip()
            self.links.append(self._anchor)
            self._anchor = None
        elif tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None
        elif tag == "script" and self._script:
            text = self._script_text
            if re.search(r"pagination|load.?more|county|nyhet|search|api|ajax", text, re.I):
                self.scripts.append({"inline_excerpt": text[:4000]})
            self._script = False
            self._script_text = ""


def parse_archive(html: str) -> dict:
    parser = ArchiveParser()
    parser.feed(html)
    news_links = []
    pagination_links = []
    for link in parser.links:
        href = urllib.parse.urljoin(BASE, link["href"])
        if "/om-oss/nyheter/" in href or "/vara-projekt/" in href:
            news_links.append({"url": href, "text": link["text"]})
        if re.search(r"page|offset|start|skip|more|next|p=|sida", link["href"], re.I):
            pagination_links.append({"url": href, "text": link["text"]})
    count_match = re.search(r"Visar\s+1\s*[-–]\s*\d+\s+av\s+(\d+)\s+nyheter", html, re.I)
    return {
        "archive_count": int(count_match.group(1)) if count_match else None,
        "news_links": news_links,
        "pagination_links": pagination_links,
        "forms": parser.forms,
        "scripts": parser.scripts,
    }


def inspect_sitemaps() -> list[dict]:
    candidates = [BASE + "/robots.txt", BASE + "/sitemap.xml", BASE + "/sitemap_index.xml"]
    reports = []
    visited: set[str] = set()
    queue = candidates[:]
    while queue and len(visited) < 35:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            body, final_url = fetch(url)
            item = {"url": url, "final_url": final_url, "status": "ok", "bytes": len(body)}
            if url.endswith("robots.txt"):
                sitemap_urls = re.findall(r"(?im)^sitemap:\s*(https?://\S+)", body)
                item["sitemap_declarations"] = sitemap_urls
                queue.extend(sitemap_urls[:10])
            elif "<" in body[:100]:
                try:
                    root = ET.fromstring(body)
                    locs = [node.text.strip() for node in root.iter() if node.tag.endswith("}loc") and node.text]
                    item["loc_count"] = len(locs)
                    item["vasterbotten_news_urls"] = [
                        loc for loc in locs
                        if "/om-oss/nyheter/" in loc and "/vasterbotten/" in loc
                    ][:500]
                    if root.tag.endswith("sitemapindex"):
                        queue.extend(locs[:25])
                except ET.ParseError:
                    item["note"] = "Response was not parseable XML."
            reports.append(item)
        except Exception as exc:
            reports.append({"url": url, "status": "error", "error": str(exc)[:1000]})
    return reports



def inspect_frontend_scripts(script_paths: list[object]) -> list[dict]:
    """Inspect entry bundles and resolve archive-related webpack lazy chunks."""
    reports = []
    seen = set()
    patterns = re.compile(r"county|pagination|pageSize|pageNumber|loadMore|news|nyhet|search|filter|api/|graphql|axios|fetch\(", re.I)
    bodies: dict[str, str] = {}
    for item in script_paths:
        if not isinstance(item, str) or not item.startswith("/"):
            continue
        url = urllib.parse.urljoin(BASE, item)
        if url in seen:
            continue
        seen.add(url)
        try:
            body, final_url = fetch(url)
            bodies[url] = body
            matches = []
            for match in patterns.finditer(body):
                a, b = max(0, match.start()-250), min(len(body), match.end()+500)
                excerpt = re.sub(r"\s+", " ", body[a:b])
                if excerpt not in matches:
                    matches.append(excerpt)
                if len(matches) >= 20:
                    break
            reports.append({"url": url, "final_url": final_url, "status": "ok",
                            "bytes": len(body.encode("utf-8")), "relevant_code_excerpts": matches})
        except Exception as exc:
            reports.append({"url": url, "status": "error", "error": str(exc)[:1000]})

    runtime = next((body for url, body in bodies.items() if "runtime" in url.lower()), "")
    if not runtime:
        runtime = next((body for body in bodies.values() if re.search(r"\\.u\\s*=|chunkName|chunkFilename", body, re.I)), "")
    # Webpack runtime syntax varies by build; capture the literal map expressions
    # instead of assuming a single minifier-specific function signature.
    name_match = re.search(r"\.u\s*=\s*[^;]{0,300}?\(\s*\{([^{}]{20,})\}\s*\[", runtime)
    hash_match = re.search(r'\+"\."\+\{([^{}]{20,})\}\[', runtime)
    if not name_match:
        name_match = re.search(r"chunkName|chunkFilename", runtime, re.I)
    if not hash_match:
        hash_match = re.search(r"contenthash|chunkHash", runtime, re.I)
    names = {}
    hashes = {}
    if name_match and name_match.lastindex:
        names = {k: v for k, v in re.findall(r'(\d+)\s*:\s*"([A-Za-z0-9_-]+)"', name_match.group(1))}
    if hash_match and hash_match.lastindex:
        hashes = {k: v for k, v in re.findall(r'(\d+)\s*:\s*"([a-f0-9]{8,})"', hash_match.group(1))}
    reports.append({"runtime_chunk_map_diagnostic": {
        "runtime_found": bool(runtime), "name_map_found": bool(name_match),
        "hash_map_found": bool(hash_match), "name_entries": len(names),
        "hash_entries": len(hashes),
        "target_names": {k:v for k,v in names.items() if v in {"countycontent","filter-news","pagelist"}}
    }})
    # Do not synthesize URLs unless both maps resolve the same chunk ID.
    for chunk_id, chunk_name in names.items():
        if chunk_name not in {"countycontent", "filter-news", "pagelist"}:
            continue
        digest = hashes.get(chunk_id)
        if not digest:
            reports.append({"chunk_name": chunk_name, "chunk_id": chunk_id,
                            "status": "unresolved_hash"})
            continue
        chunk_url = f"{BASE}/Static/dist/{chunk_name}.{digest}.js"
        try:
            chunk_body, final_url = fetch(chunk_url)
            excerpts = []
            # Capture request/data-flow clues across the complete minified bundle,
            # rather than stopping at the first generic filter-related matches.
            clue_pattern = re.compile(
                r"fetch\s*\(|XMLHttpRequest|axios|\$fetch|\.get\(|\.post\(|"
                r"URLSearchParams|application/json|content-type|api/|/api|"
                r"FilterCounty|FilterType|pageSize|pageNumber|currentPage|"
                r"totalItems|totalPages|loadMore|newsItems|newsList|News",
                re.I,
            )
            seen_excerpts = set()
            for match in clue_pattern.finditer(chunk_body):
                a, b = max(0, match.start()-650), min(len(chunk_body), match.end()+1100)
                excerpt = re.sub(r"\s+", " ", chunk_body[a:b])
                if excerpt not in seen_excerpts:
                    seen_excerpts.add(excerpt)
                    excerpts.append({"offset": match.start(), "clue": match.group(0), "excerpt": excerpt})
                if len(excerpts) >= 120:
                    break
            reports.append({"url": chunk_url, "final_url": final_url, "status": "ok",
                            "chunk_id": chunk_id, "chunk_name": chunk_name,
                            "bytes": len(chunk_body.encode("utf-8")),
                            "relevant_code_excerpts": excerpts})
        except Exception as exc:
            reports.append({"url": chunk_url, "status": "error", "chunk_id": chunk_id,
                            "chunk_name": chunk_name, "error": str(exc)[:1000]})
    return reports


def inspect_county_content_api() -> list[dict]:
    """Probe the source-confirmed county content endpoint with bounded page sizes."""
    reports = []
    for page_size in (10, 25, 50):
        query = urllib.parse.urlencode({"countyid": 18, "pageSize": page_size})
        url = f"{BASE}/api/PageListApi/GetCurrentCountyContent?{query}"
        try:
            body, final_url = fetch(url)
            payload = json.loads(body)
            pages = payload.get("pages", []) if isinstance(payload, dict) else []
            samples = []
            for page in pages[:5] if isinstance(pages, list) else []:
                if isinstance(page, dict):
                    samples.append({
                        key: page.get(key) for key in
                        ("title", "name", "url", "link", "publishDate", "date")
                        if page.get(key) is not None
                    })
                else:
                    samples.append({"value_type": type(page).__name__})
            reports.append({
                "url": url, "final_url": final_url, "status": "ok",
                "http_payload_type": type(payload).__name__,
                "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
                "pages_count": len(pages) if isinstance(pages, list) else None,
                "sample_page_metadata": samples,
                "response_bytes": len(body.encode("utf-8")),
            })
        except Exception as exc:
            reports.append({"url": url, "status": "error", "error": str(exc)[:1000]})
    return reports



def inspect_news_archive_api() -> list[dict]:
    """Probe the source-confirmed full news-list API with county and paging filters."""
    reports = []
    for county_id in (18,):
        for page in (1, 2):
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page, "counties": county_id,
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                items = payload.get("Items", []) if isinstance(payload, dict) else []
                sample = []
                for item in items[:5] if isinstance(items, list) else []:
                    if isinstance(item, dict):
                        sample.append({
                            key: item.get(key) for key in
                            ("Name", "Link", "Date", "Changed", "Label", "Preamble")
                            if item.get(key) is not None
                        })
                reports.append({
                    "url": url, "final_url": final_url, "status": "ok",
                    "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
                    "total_hits": payload.get("TotalHits") if isinstance(payload, dict) else None,
                    "items_count": len(items) if isinstance(items, list) else None,
                    "sample_items": sample,
                    "response_bytes": len(body.encode("utf-8")),
                })
            except Exception as exc:
                reports.append({"url": url, "status": "error", "error": str(exc)[:1000]})
    return reports




def inspect_news_archive_date_filters() -> list[dict]:
    """Test bounded historical date windows using the frontend-discovered parameters."""
    windows = [
        ("pre_oldest_wide", "2020-01-01", "2024-12-31"),
        ("around_oldest", "2024-11-01", "2024-12-01"),
        ("oldest_day_exact", "2024-11-14", "2024-11-15"),
        ("year_2025_control", "2025-01-01", "2025-12-31"),
        ("year_2026_control", "2026-01-01", "2026-12-31"),
    ]
    reports = []
    for label, from_date, to_date in windows:
        query = urllib.parse.urlencode({
            "pageSize": 10, "currentPage": 1, "counties": 18,
            "fromDate": from_date, "toDate": to_date,
        })
        url = f"{BASE}/api/news?{query}"
        try:
            body, final_url = fetch(url)
            payload = json.loads(body)
            items = payload.get("Items", []) if isinstance(payload, dict) else []
            reports.append({
                "window": label, "from_date": from_date, "to_date": to_date,
                "url": url, "final_url": final_url, "status": "ok",
                "total_hits": payload.get("TotalHits") if isinstance(payload, dict) else None,
                "items_count": len(items) if isinstance(items, list) else None,
                "sample_items": [
                    {key: item.get(key) for key in ("Name", "Link", "Date", "Changed")}
                    for item in items[:3] if isinstance(item, dict)
                ],
            })
        except Exception as exc:
            reports.append({
                "window": label, "from_date": from_date, "to_date": to_date,
                "url": url, "status": "error", "error": str(exc)[:1000],
            })
    return reports



def collect_historical_date_windows() -> list[dict]:
    """Fully paginate bounded pre-2025 date windows for Västerbotten."""
    windows = [
        ("2000_2009", "2000-01-01", "2009-12-31"),
        ("2010_2019", "2010-01-01", "2019-12-31"),
        ("2020_2020", "2020-01-01", "2020-12-31"),
        ("2021_2021", "2021-01-01", "2021-12-31"),
        ("2022_2022", "2022-01-01", "2022-12-31"),
        ("2023_2023", "2023-01-01", "2023-12-31"),
        ("2024_2024", "2024-01-01", "2024-12-31"),
    ]
    reports = []
    for label, from_date, to_date in windows:
        all_items = []
        page_reports = []
        total_hits = None
        error = None
        for page_number in range(1, 101):
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page_number, "counties": 18,
                "fromDate": from_date, "toDate": to_date,
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                    raise ValueError("Unexpected API response shape")
                reported_total = payload.get("TotalHits")
                if not isinstance(reported_total, int):
                    raise ValueError("Missing TotalHits")
                if total_hits is None:
                    total_hits = reported_total
                elif total_hits != reported_total:
                    raise ValueError("TotalHits changed during date-window pagination")
                items = payload["Items"]
                page_reports.append({"page": page_number, "returned": len(items), "url": url})
                all_items.extend(item for item in items if isinstance(item, dict))
                if len(all_items) >= total_hits or not items:
                    break
            except Exception as exc:
                error = f"page {page_number}: {exc}"
                break
        else:
            error = "Reached 100 pages before collecting TotalHits"
        by_link = {}
        for item in all_items:
            link = item.get("Link")
            if isinstance(link, str) and link:
                by_link.setdefault(link, item)
        records = [{
            "title": item.get("Name"),
            "url": urllib.parse.urljoin(BASE, link),
            "published_date": item.get("Date"),
            "changed_at": item.get("Changed"),
            "category": item.get("Label"),
        } for link, item in by_link.items()]
        reports.append({
            "window": label, "from_date": from_date, "to_date": to_date,
            "status": "error" if error else "ok", "error": error,
            "reported_total_hits": total_hits, "pages_fetched": page_reports,
            "raw_items_count": len(all_items), "unique_article_count": len(records),
            "records": records,
            "complete_against_reported_total": error is None and total_hits is not None and len(all_items) >= total_hits,
        })
    return reports


def collect_county_news_inventory(page_size: int = 10, max_pages: int = 100) -> dict:
    """Inventory all pages from the source-confirmed county-filtered news API."""
    if page_size < 1 or page_size > 10 or max_pages < 1:
        raise ValueError("page_size must be 1..10 and max_pages must be positive; the public API has only been verified with pageSize=10")
    all_items = []
    page_reports = []
    total_hits = None
    for page_number in range(1, max_pages + 1):
        query = urllib.parse.urlencode({
            "pageSize": page_size, "currentPage": page_number, "counties": 18,
        })
        url = f"{BASE}/api/news?{query}"
        try:
            body, final_url = fetch(url)
        except Exception as exc:
            raise RuntimeError(f"County news API request failed on page {page_number} ({url}): {exc}") from exc
        payload = json.loads(body)
        if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
            raise ValueError(f"Unexpected API response on page {page_number}")
        reported_total = payload.get("TotalHits")
        if not isinstance(reported_total, int):
            raise ValueError(f"Missing TotalHits on page {page_number}")
        if total_hits is None:
            total_hits = reported_total
        elif total_hits != reported_total:
            raise ValueError("TotalHits changed during pagination; inventory is not a stable snapshot")
        items = payload["Items"]
        page_reports.append({
            "page": page_number, "returned": len(items),
            "response_bytes": len(body.encode("utf-8")), "url": url,
        })
        all_items.extend(item for item in items if isinstance(item, dict))
        if len(all_items) >= total_hits or not items:
            break
    else:
        raise ValueError("Reached max_pages before collecting TotalHits")
    by_link = {}
    for item in all_items:
        link = item.get("Link")
        if isinstance(link, str) and link:
            by_link.setdefault(link, item)
    records = []
    for link, item in by_link.items():
        records.append({
            "title": item.get("Name"), "url": urllib.parse.urljoin(BASE, link),
            "published_date": item.get("Date"), "changed_at": item.get("Changed"),
            "category": item.get("Label"), "preamble": item.get("Preamble"),
        })
    dates = [r["published_date"] for r in records if r["published_date"]]
    return {
        "county_id": 18, "page_size": page_size, "reported_total_hits": total_hits,
        "pages_fetched": page_reports, "raw_items_count": len(all_items),
        "unique_article_count": len(records),
        "duplicate_count": len(all_items) - len(records),
        "date_values": dates,
        "records": records,
        "complete_against_reported_total": len(all_items) >= total_hits,
    }




def diagnose_national_pagination(years: tuple[int, ...] = (2024, 2025, 2026), pages_to_probe: int = 4) -> list[dict]:
    """Capture per-page TotalHits and article identities without assuming stable totals."""
    reports = []
    for year in years:
        page_reports = []
        for page_number in range(1, pages_to_probe + 1):
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page_number,
                "fromDate": f"{year}-01-01", "toDate": f"{year}-12-31",
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                    raise ValueError("Unexpected API response shape")
                items = [item for item in payload["Items"] if isinstance(item, dict)]
                page_reports.append({
                    "page": page_number,
                    "reported_total_hits": payload.get("TotalHits"),
                    "returned": len(items),
                    "links": [item.get("Link") for item in items if item.get("Link")],
                    "dates": [item.get("Date") for item in items if item.get("Date")],
                    "final_url": final_url,
                    "status": "ok",
                })
                if not items:
                    break
            except Exception as exc:
                page_reports.append({"page": page_number, "url": url, "status": "error", "error": str(exc)[:1000]})
                break
        totals = [p.get("reported_total_hits") for p in page_reports if p.get("status") == "ok"]
        reports.append({
            "year": year, "pages_probed": page_reports,
            "reported_total_hits_by_page": totals,
            "totals_stable": len(set(totals)) <= 1,
            "unique_links_in_probe": len({link for p in page_reports for link in p.get("links", [])}),
        })
    return reports



def diagnose_national_pagination_boundaries(page_map: dict[int, tuple[int, ...]] | None = None) -> list[dict]:
    """Probe pages around the previously observed national pagination failure points."""
    if page_map is None:
        page_map = {2024: (1, 2, 3, 9, 10, 11, 12, 13), 2025: (12, 13, 14), 2026: (47, 48, 49, 50)}
    reports = []
    for year, page_numbers in page_map.items():
        pages = []
        for page_number in page_numbers:
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page_number,
                "fromDate": f"{year}-01-01", "toDate": f"{year}-12-31",
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                    raise ValueError("Unexpected API response shape")
                items = [item for item in payload["Items"] if isinstance(item, dict)]
                pages.append({
                    "page": page_number, "reported_total_hits": payload.get("TotalHits"),
                    "returned": len(items),
                    "links": [item.get("Link") for item in items if item.get("Link")],
                    "dates": [item.get("Date") for item in items if item.get("Date")],
                    "final_url": final_url, "status": "ok",
                })
            except Exception as exc:
                pages.append({"page": page_number, "url": url, "status": "error", "error": str(exc)[:1000]})
        all_links = [link for page in pages for link in page.get('links', [])]
        reports.append({
            "year": year, "requested_pages": list(page_numbers), "pages": pages,
            "reported_total_hits_by_page": [p.get("reported_total_hits") for p in pages if p.get("status") == "ok"],
            "unique_links": len(set(all_links)), "returned_items": len(all_links),
            "duplicate_links": len(all_links) - len(set(all_links)),
        })
    return reports

def diagnose_2024_monthly_windows() -> list[dict]:
    """Test whether month-sized date filters avoid the 2024 annual pagination gap."""
    reports = []
    for month in range(1, 13):
        from_date = f"2024-{month:02d}-01"
        if month == 12:
            to_date = "2024-12-31"
        else:
            to_date = f"2024-{month + 1:02d}-01"
        pages = []
        for page_number in range(1, 21):
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page_number,
                "fromDate": from_date, "toDate": to_date,
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                    raise ValueError("Unexpected API response shape")
                items = [item for item in payload["Items"] if isinstance(item, dict)]
                pages.append({
                    "page": page_number, "reported_total_hits": payload.get("TotalHits"),
                    "returned": len(items),
                    "links": [item.get("Link") for item in items if item.get("Link")],
                    "dates": [item.get("Date") for item in items if item.get("Date")],
                    "final_url": final_url, "status": "ok",
                })
                if not items:
                    break
            except Exception as exc:
                pages.append({"page": page_number, "url": url, "status": "error", "error": str(exc)[:1000]})
                break
        links = [link for page in pages for link in page.get('links', [])]
        reports.append({
            "month": f"2024-{month:02d}", "from_date": from_date, "to_date": to_date,
            "pages": pages, "reported_total_hits_by_page": [p.get("reported_total_hits") for p in pages if p.get("status") == "ok"],
            "returned_items": len(links), "unique_links": len(set(links)),
            "duplicate_links": len(links) - len(set(links)),
        })
    return reports

def diagnose_2024_monthly_repeatability(repeats: int = 3) -> list[dict]:
    """Repeat identical first-page requests to detect changing API results."""
    if repeats < 2 or repeats > 5:
        raise ValueError("repeats must be between 2 and 5")
    reports = []
    for month, from_date, to_date in (("2024-11", "2024-11-01", "2024-12-01"), ("2024-12", "2024-12-01", "2024-12-31")):
        runs = []
        for attempt in range(1, repeats + 1):
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": 1, "fromDate": from_date, "toDate": to_date,
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                    raise ValueError("Unexpected API response shape")
                items = [item for item in payload["Items"] if isinstance(item, dict)]
                runs.append({
                    "attempt": attempt, "reported_total_hits": payload.get("TotalHits"),
                    "returned": len(items),
                    "links": [item.get("Link") for item in items if item.get("Link")],
                    "dates": [item.get("Date") for item in items if item.get("Date")],
                    "final_url": final_url, "status": "ok",
                })
            except Exception as exc:
                runs.append({"attempt": attempt, "url": url, "status": "error", "error": str(exc)[:1000]})
        link_sets = [tuple(run.get('links', [])) for run in runs if run.get('status') == 'ok']
        totals = [run.get('reported_total_hits') for run in runs if run.get('status') == 'ok']
        reports.append({
            "month": month, "runs": runs,
            "totals_stable": len(set(totals)) <= 1,
            "first_page_links_stable": len(set(link_sets)) <= 1,
        })
    return reports

def diagnose_monthly_pagination_repeatability(repeats: int = 2) -> list[dict]:
    """Repeat each page request for the November and December 2024 windows."""
    if repeats < 2 or repeats > 3:
        raise ValueError("repeats must be 2 or 3")
    reports = []
    windows = (("2024-11", "2024-11-01", "2024-12-01", 5), ("2024-12", "2024-12-01", "2024-12-31", 6))
    for month, from_date, to_date, max_pages in windows:
        page_reports = []
        for page_number in range(1, max_pages + 1):
            attempts = []
            for attempt in range(1, repeats + 1):
                query = urllib.parse.urlencode({
                    "pageSize": 10, "currentPage": page_number,
                    "fromDate": from_date, "toDate": to_date,
                })
                url = f"{BASE}/api/news?{query}"
                try:
                    body, final_url = fetch(url)
                    payload = json.loads(body)
                    if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                        raise ValueError("Unexpected API response shape")
                    items = [item for item in payload["Items"] if isinstance(item, dict)]
                    attempts.append({
                        "attempt": attempt, "reported_total_hits": payload.get("TotalHits"),
                        "returned": len(items),
                        "links": [item.get("Link") for item in items if item.get("Link")],
                        "dates": [item.get("Date") for item in items if item.get("Date")],
                        "final_url": final_url, "status": "ok",
                    })
                except Exception as exc:
                    attempts.append({"attempt": attempt, "url": url, "status": "error", "error": str(exc)[:1000]})
            link_sets = [tuple(a.get('links', [])) for a in attempts if a.get('status') == 'ok']
            totals = [a.get('reported_total_hits') for a in attempts if a.get('status') == 'ok']
            page_reports.append({
                "page": page_number, "attempts": attempts,
                "totals_stable": len(set(totals)) <= 1,
                "links_stable": len(set(link_sets)) <= 1,
            })
        reports.append({
            "month": month, "from_date": from_date, "to_date": to_date,
            "pages": page_reports,
        })
    return reports

def diagnose_monthly_pages_after_empty() -> list[dict]:
    """Probe pages after the first empty page to detect gaps in API pagination."""
    windows = (("2024-11", "2024-11-01", "2024-12-01", (4, 5, 6, 7, 8)), ("2024-12", "2024-12-01", "2024-12-31", (5, 6, 7, 8, 9)))
    reports = []
    for month, from_date, to_date, page_numbers in windows:
        pages = []
        for page_number in page_numbers:
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page_number,
                "fromDate": from_date, "toDate": to_date,
            })
            url = f"{BASE}/api/news?{query}"
            attempts = []
            for attempt in (1, 2):
                try:
                    body, final_url = fetch(url)
                    payload = json.loads(body)
                    if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                        raise ValueError("Unexpected API response shape")
                    items = [item for item in payload["Items"] if isinstance(item, dict)]
                    attempts.append({
                        "attempt": attempt, "reported_total_hits": payload.get("TotalHits"),
                        "returned": len(items), "links": [item.get("Link") for item in items if item.get("Link")],
                        "dates": [item.get("Date") for item in items if item.get("Date")],
                        "final_url": final_url, "status": "ok",
                    })
                except Exception as exc:
                    attempts.append({"attempt": attempt, "url": url, "status": "error", "error": str(exc)[:1000]})
            links = [tuple(a.get('links', [])) for a in attempts if a.get('status') == 'ok']
            totals = [a.get('reported_total_hits') for a in attempts if a.get('status') == 'ok']
            pages.append({
                "page": page_number, "attempts": attempts,
                "totals_stable": len(set(totals)) <= 1, "links_stable": len(set(links)) <= 1,
            })
        reports.append({
            "month": month, "pages_after_and_around_end": pages,
        })
    return reports

def collect_national_news_inventory(start_year: int = 2024, max_pages_per_year: int = 1000) -> dict:
    """Fully paginate national news results from start_year through the current year.

    Omitting the counties parameter is intentional: it requests the national feed.
    Each calendar year is fetched separately to keep pagination bounded and auditable.
    """
    current_year = datetime.now(timezone.utc).year
    if start_year < 2000 or start_year > current_year or max_pages_per_year < 1:
        raise ValueError("Invalid start_year or max_pages_per_year")
    yearly_reports = []
    all_items = []
    for year in range(start_year, current_year + 1):
        from_date, to_date = f"{year}-01-01", f"{year}-12-31"
        total_hits = None
        year_items = []
        pages = []
        error = None
        for page_number in range(1, max_pages_per_year + 1):
            query = urllib.parse.urlencode({
                "pageSize": 10, "currentPage": page_number,
                "fromDate": from_date, "toDate": to_date,
            })
            url = f"{BASE}/api/news?{query}"
            try:
                body, final_url = fetch(url)
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                    raise ValueError("Unexpected API response shape")
                reported_total = payload.get("TotalHits")
                if not isinstance(reported_total, int):
                    raise ValueError("Missing TotalHits")
                if total_hits is None:
                    total_hits = reported_total
                elif total_hits != reported_total:
                    raise ValueError("TotalHits changed during annual pagination")
                items = payload["Items"]
                pages.append({"page": page_number, "returned": len(items), "url": url})
                year_items.extend(item for item in items if isinstance(item, dict))
                if len(year_items) >= total_hits or not items:
                    break
            except Exception as exc:
                error = f"page {page_number}: {exc}"
                break
        else:
            error = f"Reached {max_pages_per_year} pages before collecting TotalHits"
        all_items.extend(year_items)
        yearly_reports.append({
            "year": year, "from_date": from_date, "to_date": to_date,
            "status": "error" if error else "ok", "error": error,
            "reported_total_hits": total_hits, "pages_fetched": pages,
            "raw_items_count": len(year_items),
            "complete_against_reported_total": error is None and total_hits is not None and len(year_items) >= total_hits,
        })
    by_link = {}
    for item in all_items:
        link = item.get("Link")
        if isinstance(link, str) and link:
            by_link.setdefault(link, item)
    records = [{
        "title": item.get("Name"),
        "url": urllib.parse.urljoin(BASE, link),
        "published_date": item.get("Date"),
        "changed_at": item.get("Changed"),
        "category": item.get("Label"),
        "preamble": item.get("Preamble"),
    } for link, item in by_link.items()]
    return {
        "scope": "national", "start_year": start_year, "end_year": current_year,
        "county_filter": None, "page_size": 10, "yearly_reports": yearly_reports,
        "raw_items_count": len(all_items), "unique_article_count": len(records),
        "duplicate_count": len(all_items) - len(records), "records": records,
        "complete": all(report["complete_against_reported_total"] for report in yearly_reports),
    }


def collect_national_news_inventory_monthly(start_year: int = 2024, max_pages_per_month: int = 100) -> dict:
    """Collect national news in month-sized windows, stopping only after two empty pages."""
    current_year = datetime.now(timezone.utc).year
    if start_year < 2000 or start_year > current_year or max_pages_per_month < 2:
        raise ValueError("Invalid start_year or max_pages_per_month; at least two pages are required")
    import calendar
    monthly_reports = []
    all_items = []
    for year in range(start_year, current_year + 1):
        last_month = 12 if year < current_year else datetime.now(timezone.utc).month
        for month in range(1, last_month + 1):
            from_date = f"{year}-{month:02d}-01"
            to_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
            month_items = []
            pages = []
            consecutive_empty_pages = 0
            error = None
            for page_number in range(1, max_pages_per_month + 1):
                query = urllib.parse.urlencode({
                    "pageSize": 10, "currentPage": page_number,
                    "fromDate": from_date, "toDate": to_date,
                })
                url = f"{BASE}/api/news?{query}"
                try:
                    body, final_url = fetch(url)
                    payload = json.loads(body)
                    if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                        raise ValueError("Unexpected API response shape")
                    items = [item for item in payload["Items"] if isinstance(item, dict)]
                    pages.append({
                        "page": page_number, "returned": len(items),
                        "reported_total_hits": payload.get("TotalHits"), "url": url,
                        "final_url": final_url,
                    })
                    if items:
                        month_items.extend(items)
                        consecutive_empty_pages = 0
                    else:
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 2:
                            break
                except Exception as exc:
                    error = f"page {page_number}: {exc}"
                    break
            else:
                error = f"Reached {max_pages_per_month} pages without two consecutive empty pages"
            all_items.extend(month_items)
            by_link = {}
            for item in month_items:
                link = item.get("Link")
                if isinstance(link, str) and link:
                    by_link.setdefault(link, item)
            monthly_reports.append({
                "month": f"{year}-{month:02d}", "from_date": from_date, "to_date": to_date,
                "status": "error" if error else "ok", "error": error, "pages_fetched": pages,
                "raw_items_count": len(month_items), "unique_article_count": len(by_link),
                "duplicate_count": len(month_items) - len(by_link),
                "terminated_by_two_empty_pages": error is None and consecutive_empty_pages >= 2,
            })
    by_link = {}
    for item in all_items:
        link = item.get("Link")
        if isinstance(link, str) and link:
            by_link.setdefault(link, item)
    records = [{
        "title": item.get("Name"), "url": urllib.parse.urljoin(BASE, link),
        "published_date": item.get("Date"), "changed_at": item.get("Changed"),
        "category": item.get("Label"), "preamble": item.get("Preamble"),
    } for link, item in by_link.items()]
    return {
        "scope": "national", "start_year": start_year, "end_year": current_year,
        "window": "calendar_month", "county_filter": None, "page_size": 10,
        "monthly_reports": monthly_reports, "raw_items_count": len(all_items),
        "unique_article_count": len(records), "duplicate_count": len(all_items) - len(records),
        "records": records, "complete": all(report["status"] == "ok" and report["terminated_by_two_empty_pages"] for report in monthly_reports),
    }

def build_gis_linkage_inventory(records: list[dict]) -> dict:
    """Classify news as candidates for linkage to Trafikverket geodata; never claim a spatial match."""
    import re
    rules = {
        "road_network_nvdb": r"(?:E[ ]?[0-9]{1,2}|väg[ ]?[0-9]{1,4}|riksväg[ ]?[0-9]{1,3}|länsväg[ ]?[0-9]{1,4})|vägnät|vägsträck|bro|tunnel|trafikplats|cirkulationsplats|vägräcke|beläggning",
        "rail_network_njdb": r"järnväg|järnvägs|järnvägsnät|spår|bangård|plankorsning|järnvägsövergång|station|Norrbotniabanan|Ostlänken|Västlänken|Mälarbanan",
        "traffic_information_api": r"trafikläge|trafikstörning|köbildning|köer|framkomlighet|trafikpåverkan|avstäng|omledning|olyck|vägarbete|banarbete",
        "road_traffic_data": r"trafikflöde|trafikmängd|fordonsflöde|hastighet|restid|kapacitet|trafikprognos",
        "environment_surrounding_geodata": r"buller|viltpassage|faunapassage|naturvärde|vattenverksamhet|dagvatten|grundvatten|miljökonsekvens",
        "project_planning_candidate": r"samråd|vägplan|järnvägsplan|lokalisering|tillstånd|byggstart|byggnation|projekt|utbyggnad|nybyggnad",
    }
    results = []
    totals = {key: 0 for key in rules}
    for record in records:
        fields = [record.get(key) or '' for key in ('title', 'preamble', 'category', 'url')]
        text = ' '.join(str(value) for value in fields)
        matches = [key for key, pattern in rules.items() if re.search(pattern, text, flags=re.IGNORECASE)]
        for key in matches:
            totals[key] += 1
        route_refs = sorted(set(match.group(0).replace(' ', '').upper() for match in re.finditer(r'(?:E[ ]?[0-9]{1,2}|väg[ ]?[0-9]{1,4}|riksväg[ ]?[0-9]{1,3}|länsväg[ ]?[0-9]{1,4})', text, flags=re.IGNORECASE)))
        results.append({
            'title': record.get('title'), 'url': record.get('url'),
            'published_date': record.get('published_date'), 'category': record.get('category'),
            'candidate_gis_layers': matches, 'route_references': route_refs,
            'linkage_status': 'thematic_candidate_only' if matches else 'unclassified',
        })
    return {
        'method': 'keyword_rules_title_preamble_category_url',
        'warning': 'Thematic candidates only. No coordinates, geometry intersection or verified feature match is inferred from news text.',
        'candidate_counts_overlapping': totals, 'records': results,
        'records_with_any_candidate': sum(bool(row['candidate_gis_layers']) for row in results),
    }

def main() -> None:
    monthly_inventory = collect_national_news_inventory_monthly(start_year=2024)
    gis_linkage_inventory = build_gis_linkage_inventory(monthly_inventory["records"])
    html, final_url = fetch(ARCHIVE_URL)
    archive = parse_archive(html)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Trafikverket public news archive",
        "scope": "Västerbotten probe plus national inventory",
        "county": "Västerbotten",
        "county_query_parameter": "county=18",
        "archive_url": ARCHIVE_URL,
        "final_url": final_url,
        "html_bytes": len(html.encode("utf-8")),
        "archive": archive,
        "sitemaps": inspect_sitemaps(),
        "frontend_scripts": inspect_frontend_scripts(archive["scripts"]),
        "county_content_api_probes": inspect_county_content_api(),
        "news_archive_api_probes": inspect_news_archive_api(),
        "news_archive_date_filter_probes": inspect_news_archive_date_filters(),
        "historical_date_window_inventories": collect_historical_date_windows(),
        "full_county_news_inventory": collect_county_news_inventory(),
        "national_pagination_diagnostics": diagnose_national_pagination(),
        "national_pagination_boundary_diagnostics": diagnose_national_pagination_boundaries(),
        "national_2024_monthly_window_diagnostics": diagnose_2024_monthly_windows(),
        "national_2024_monthly_repeatability_diagnostics": diagnose_2024_monthly_repeatability(),
        "national_monthly_pagination_repeatability": diagnose_monthly_pagination_repeatability(),
        "national_monthly_pages_after_empty": diagnose_monthly_pages_after_empty(),
        "national_news_inventory_from_2024": collect_national_news_inventory(start_year=2024),
        "national_monthly_news_inventory_from_2024": monthly_inventory,
        "national_news_gis_linkage_inventory": gis_linkage_inventory,
        "limitations": [
            "This probe does not assume an undocumented pagination parameter.",
            "It does not download article bodies; the next implementation step depends on the discovered public links and paging mechanism.",
            "Frontend script excerpts are diagnostic clues only; no undocumented endpoint is called by this probe.",
            "A county-filtered result can include project news whose article URL is not under the Västerbotten path."
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Archive count shown by source: {archive['archive_count']}")
    print(f"Candidate news/project links on first page: {len(archive['news_links'])}")
    print(f"Pagination-like links: {len(archive['pagination_links'])}")
    print(f"Sitemap endpoints inspected: {len(report['sitemaps'])}")
    print(f"Report: {OUT}")


if __name__ == "__main__":
    main()
