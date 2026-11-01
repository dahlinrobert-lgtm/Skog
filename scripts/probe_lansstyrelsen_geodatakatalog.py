#!/usr/bin/env python3
"""Discover relevant public Länsstyrelsen geodata catalogue records.

This is a metadata inventory probe, not a data collector. It does not download
or archive feature data and does not infer that a catalogue record represents
a completed management action.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CATALOG_API = "https://ext-geodatakatalog.lansstyrelsen.se/GeodataKatalogen/srv/api"
SEARCH_URL = CATALOG_API + "/search/records/_search"
USER_AGENT = "Skog-Lansstyrelsen-Catalog-Probe/1.0"
SEARCH_TERMS = (
    "naturvårdsbränning",
    "naturvårdande skötsel",
    "naturvårdsåtgärder",
    "slåtter",
    "bete",
    "hamling",
    "död ved",
    "veteranisering",
    "restaurering skog",
    "invasiva arter",
    "ängs- och betesmark",
    "Natura 2000 skötsel",
    "genomförda åtgärder",
    "utförda åtgärder",
    "restaureringsåtgärder",
    "skötselåtgärder",
    "naturvårdsinsatser",
    "åtgärdade träd",
    "frihuggning",
    "naturvårdande åtgärder",
)


def build_query(term: str, offset: int = 0, size: int = 100) -> dict:
    if not term.strip():
        raise ValueError("Search term must not be empty")
    if offset < 0 or not 1 <= size <= 200:
        raise ValueError("Invalid pagination values")
    return {
        "from": offset,
        "size": size,
        "track_total_hits": True,
        "query": {
            "bool": {
                "must": [{"query_string": {"query": f'+anytext:"{term}"'}}],
                "filter": [{"term": {"isTemplate": {"value": "n"}}}],
            }
        },
    }


def request_json(url: str, body: dict, retries: int = 3) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                method="POST",
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Content-Type": "application/json;charset=UTF-8",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("error"):
                raise RuntimeError(f"Invalid catalogue response: {payload!r}")
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Catalogue request failed after {retries} attempts: {last_error}")


def response_hits(payload: dict) -> tuple[int, list[dict]]:
    hits_container = payload.get("hits") or {}
    total_value = hits_container.get("total", 0)
    if isinstance(total_value, dict):
        total = int(total_value.get("value", 0))
    else:
        total = int(total_value or 0)
    hits = hits_container.get("hits") or []
    if not isinstance(hits, list):
        raise RuntimeError("Unexpected catalogue hits format")
    return total, hits


def hit_title(source: dict) -> str | None:
    for key in ("resourceTitleObject", "resourceTitle", "title"):
        value = source.get(key)
        if isinstance(value, dict):
            value = value.get("default") or next(iter(value.values()), None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def run_probe(*, size: int = 100, max_records_per_term: int = 200, delay: float = 0.15) -> dict:
    if not 1 <= size <= 200:
        raise ValueError("size must be 1..200")
    if not size <= max_records_per_term <= 1000:
        raise ValueError("max_records_per_term must be size..1000")
    merged: dict[str, dict] = {}
    term_reports = []

    for term in SEARCH_TERMS:
        offset = 0
        total = 0
        fetched = 0
        pages = 0
        while offset < max_records_per_term:
            page_size = min(size, max_records_per_term - offset)
            payload = request_json(SEARCH_URL + "?bucket=metadata", build_query(term, offset, page_size))
            total, hits = response_hits(payload)
            pages += 1
            if not hits:
                break
            for hit in hits:
                record_id = hit.get("_id")
                source = hit.get("_source") or {}
                if not record_id:
                    continue
                item = merged.setdefault(str(record_id), {
                    "metadata_uuid": str(record_id),
                    "title": hit_title(source),
                    "source": source,
                    "matched_terms": [],
                })
                if term not in item["matched_terms"]:
                    item["matched_terms"].append(term)
                fetched += 1
            offset += len(hits)
            if len(hits) < page_size or offset >= total:
                break
            if delay:
                time.sleep(delay)
        term_reports.append({
            "term": term,
            "catalogue_total": total,
            "records_examined": fetched,
            "pages": pages,
            "truncated_at_cap": total > fetched and fetched >= max_records_per_term,
        })
        if delay:
            time.sleep(delay)

    records = sorted(merged.values(), key=lambda item: ((item.get("title") or "").casefold(), item["metadata_uuid"]))
    title_counts = Counter("title available" if item["title"] else "title missing" for item in records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalogue": CATALOG_API,
        "search_endpoint": SEARCH_URL,
        "search_terms": list(SEARCH_TERMS),
        "unique_metadata_records": len(records),
        "title_quality": dict(title_counts),
        "term_results": term_reports,
        "records": records,
        "interpretation": (
            "Metadata discovery only. A matching record is a candidate source, not proof of "
            "a machine-readable layer or completed physical management action. Verify links, "
            "geometry, update frequency, license, stable identifiers and status semantics."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("catalogue-probe"))
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--max-records-per-term", type=int, default=200)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()
    if not 0 <= args.delay <= 10:
        parser.error("--delay must be between 0 and 10")
    result = run_probe(size=args.size, max_records_per_term=args.max_records_per_term, delay=args.delay)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "catalogue-inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {key: value for key, value in result.items() if key != "records"}
    (args.output_dir / "catalogue-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
