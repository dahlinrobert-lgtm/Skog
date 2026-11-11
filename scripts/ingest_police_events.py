from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://brottsplatskartan.se/api/events"
APP_ID = "skogskoll-polishandelser"
AREA = "Norrbottens län"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "police_events"
EVENTS = DATA / "events.csv"
WILDLIFE = DATA / "wildlife_candidates.csv"

FIELDS = [
    "event_id", "published_datetime", "date", "year", "month", "type_original",
    "headline", "description", "content", "title_location", "location_string",
    "administrative_area_level_1", "administrative_area_level_2",
    "latitude", "longitude", "external_source_link", "permalink",
    "is_summary", "retrieved_at", "payload_sha256",
]
WILDLIFE_RE = re.compile(
    r"viltolyck|renolyck|älgolyck|rådjursolyck|hjortolyck|"
    r"kollision.{0,40}(älg|ren|rådjur|hjort)|"
    r"(älg|ren|rådjur|hjort).{0,40}(påkörd|påkö|kollision)",
    re.IGNORECASE,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_page(page: int, limit: int) -> dict:
    response = requests.get(
        API, params={"area": AREA, "limit": limit, "page": page, "app": APP_ID},
        headers={"User-Agent": f"{APP_ID}/1.0 (+GitHub Actions)"}, timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected API response: expected a JSON object")
    return payload


def read_events() -> dict[str, dict]:
    if not EVENTS.exists():
        return {}
    with EVENTS.open(encoding="utf-8", newline="") as f:
        return {str(row["event_id"]): row for row in csv.DictReader(f) if row.get("event_id")}


def normalize(event: dict, retrieved_at: str) -> dict:
    published = event.get("pubdate_iso8601") or event.get("published_at") or event.get("date") or ""
    try:
        dt = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
        date, year, month = dt.date().isoformat(), dt.year, dt.month
        published = dt.isoformat()
    except (ValueError, TypeError):
        date, year, month = "", "", ""
    payload = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "event_id": str(event.get("id") or ""),
        "published_datetime": published, "date": date, "year": year, "month": month,
        "type_original": event.get("title_type") or event.get("type") or "",
        "headline": event.get("headline") or "",
        "description": event.get("description") or event.get("content_teaser") or "",
        "content": event.get("content") or "",
        "title_location": event.get("title_location") or "",
        "location_string": event.get("location_string") or event.get("locations") or "",
        "administrative_area_level_1": event.get("administrative_area_level_1") or "",
        "administrative_area_level_2": event.get("administrative_area_level_2") or "",
        "latitude": event.get("lat") if event.get("lat") is not None else "",
        "longitude": event.get("lng") if event.get("lng") is not None else "",
        "external_source_link": event.get("external_source_link") or "",
        "permalink": event.get("permalink") or "",
        "is_summary": str((event.get("title_type") or event.get("type") or "").casefold().startswith("sammanfattning")).lower(),
        "retrieved_at": retrieved_at,
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def collect(full: bool, max_pages: int, limit: int, sleep_seconds: float, raw_path: Path) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.touch(exist_ok=True)
    current = read_events()
    retrieved_at = now()
    new_versions = 0
    requested_limit = limit
    min_limit = 10
    while True:
        seen: set[str] = set()
        page = 1
        restart_with_smaller_limit = False
        while page <= max_pages:
            try:
                payload = get_page(page, requested_limit)
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if full and status == 400 and page > 1 and requested_limit > min_limit:
                    next_limit = max(min_limit, requested_limit // 2)
                    print(
                        f"pagination_retry=smaller_limit old_limit={requested_limit} "
                        f"new_limit={next_limit} failed_page={page}; restarting at page 1"
                    )
                    requested_limit = next_limit
                    restart_with_smaller_limit = True
                    break
                if full and status == 400 and page > 1:
                    print(
                        f"pagination_stopped_at_page={page} status=400 limit={requested_limit}; "
                        f"preserving successfully retrieved records"
                    )
                    break
                raise
            items = payload.get("data") or []
            links = payload.get("links") or {}
            if not items:
                break
            with raw_path.open("a", encoding="utf-8") as raw:
                for event in items:
                    event_id = str(event.get("id") or "")
                    if not event_id or event_id in seen:
                        continue
                    seen.add(event_id)
                    row = normalize(event, retrieved_at)
                    previous = current.get(event_id)
                    if previous and previous.get("payload_sha256") == row["payload_sha256"]:
                        continue
                    raw.write(json.dumps({
                        "retrieved_at": retrieved_at,
                        "event_id": event_id,
                        "payload_sha256": row["payload_sha256"],
                        "event": event,
                    }, ensure_ascii=False) + "\n")
                    current[event_id] = row
                    new_versions += 1
            last_page = links.get("last_page")
            print(f"page={page} rows={len(items)} limit={requested_limit} last_page={last_page}")
            if (full and last_page and page >= int(last_page)) or (not full and page >= max_pages):
                break
            page += 1
            time.sleep(sleep_seconds)
        if not restart_with_smaller_limit:
            break

    ordered = sorted(current.values(), key=lambda r: (r["published_datetime"], r["event_id"]))
    write_csv(EVENTS, FIELDS, ordered)
    candidates = []
    for row in ordered:
        searchable = " ".join(str(row.get(k, "")) for k in ("type_original", "headline", "description", "content"))
        if WILDLIFE_RE.search(searchable):
            candidates.append(row)
    write_csv(WILDLIFE, FIELDS, candidates)
    print(f"archive_events={len(ordered)} wildlife_candidates={len(candidates)} changed_or_new_versions={new_versions}")


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Paginate the complete area history")
    parser.add_argument("--max-pages", type=int, default=10000)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--sleep", type=float, default=0.35)
    parser.add_argument("--raw-output", type=Path, required=True, help="Required isolated JSONL segment path; upload it to durable object storage")
    args = parser.parse_args()
    collect(args.full, args.max_pages, args.limit, args.sleep, args.raw_output)


if __name__ == "__main__":
    main()
