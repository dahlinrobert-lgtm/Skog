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
    """Inspect entry bundles and fetch webpack's named lazy chunks for archive widgets."""
    reports = []
    seen = set()
    patterns = re.compile(r"county|pagination|pageSize|pageNumber|loadMore|news|nyhet|search|filter|api/|graphql|axios|fetch\\(", re.I)
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
                start, end = max(0, match.start()-250), min(len(body), match.end()+500)
                excerpt = re.sub(r"\\s+", " ", body[start:end])
                if excerpt not in matches:
                    matches.append(excerpt)
                if len(matches) >= 20:
                    break
            reports.append({"url": url, "final_url": final_url, "status": "ok",
                            "bytes": len(body.encode("utf-8")), "relevant_code_excerpts": matches})
        except Exception as exc:
            reports.append({"url": url, "status": "error", "error": str(exc)[:1000]})

    # The runtime bundle maps chunk IDs to names and content hashes. Resolve
    # only the two archive-related chunks identified in the main bundle.
    runtime = next((body for url, body in bodies.items() if "runtime~main" in url), "")
    if runtime:
        name_match = re.search(r"c\\.u=e=>\\(\\(\\{(.*?)\\}\\[e\\]\\|\\|e\\)", runtime)
        hash_match = re.search(r'\\+"\\."\\+\\{(.*?)\\}\\[e\\]', runtime)
        if name_match and hash_match:
            names = {k: v for k, v in re.findall(r'(\\d+):"([A-Za-z0-9_-]+)"', name_match.group(1))}
            hashes = {k: v for k, v in re.findall(r'(\\d+):"([a-f0-9]{8,})"', hash_match.group(1))}
            for chunk_id, chunk_name in names.items():
                if chunk_name not in {"countycontent", "filter-news", "pagelist"}:
                    continue
                digest = hashes.get(chunk_id)
                if not digest:
                    continue
                chunk_url = f"{BASE}/Static/dist/{chunk_name}.{digest}.js"
                try:
                    chunk_body, final_url = fetch(chunk_url)
                    excerpts = []
                    for match in patterns.finditer(chunk_body):
                        a, b = max(0, match.start()-350), min(len(chunk_body), match.end()+700)
                        excerpt = re.sub(r"\\s+", " ", chunk_body[a:b])
                        if excerpt not in excerpts:
                            excerpts.append(excerpt)
                        if len(excerpts) >= 50:
                            break
                    reports.append({"url": chunk_url, "final_url": final_url, "status": "ok",
                                    "chunk_id": chunk_id, "chunk_name": chunk_name,
                                    "bytes": len(chunk_body.encode("utf-8")),
                                    "relevant_code_excerpts": excerpts})
                except Exception as exc:
                    reports.append({"url": chunk_url, "status": "error", "chunk_id": chunk_id,
                                    "chunk_name": chunk_name, "error": str(exc)[:1000]})
    return reports

def main() -> None:
    html, final_url = fetch(ARCHIVE_URL)
    archive = parse_archive(html)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Trafikverket public news archive",
        "county": "Västerbotten",
        "county_query_parameter": "county=18",
        "archive_url": ARCHIVE_URL,
        "final_url": final_url,
        "html_bytes": len(html.encode("utf-8")),
        "archive": archive,
        "sitemaps": inspect_sitemaps(),
        "frontend_scripts": inspect_frontend_scripts(archive["scripts"]),
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
