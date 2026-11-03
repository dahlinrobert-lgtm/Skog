#!/usr/bin/env python3
"""Read-only connectivity and pilot-scope probe for Kungjort."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = "https://handlingar.kungjort.se/api/v1"
KEY = os.environ.get("KUNGJORT_API_KEY")
if not KEY:
    raise SystemExit("Missing KUNGJORT_API_KEY")

def get(path, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + KEY,
        "Accept": "application/json",
        "User-Agent": "Skog-Kungjort-Pilot-Probe/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response), response.headers.get("X-Request-ID")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"Kungjort API HTTP {exc.code}; request_id={exc.headers.get('X-Request-ID')}; body={body}") from exc

coverage, coverage_request_id = get("/coverage")
documents, documents_request_id = get("/documents", {"limit": 1})

rows = coverage.get("coverage", [])
by_municipality = {}
for row in rows:
    municipality = row.get("kommun") or "unknown"
    item = by_municipality.setdefault(municipality, {
        "documents_reported": 0,
        "coverage_rows": 0,
        "errors_reported": 0,
        "first_meeting_date": None,
        "last_meeting_date": None,
        "org_doc_types": [],
    })
    item["documents_reported"] += row.get("documents") or 0
    item["errors_reported"] += row.get("errors") or 0
    item["coverage_rows"] += 1
    item["org_doc_types"].append({
        "organ": row.get("organ"),
        "doc_type": row.get("doc_type"),
        "year": row.get("year"),
        "documents": row.get("documents"),
        "errors": row.get("errors"),
        "first_meeting_date": row.get("first_meeting_date"),
        "last_meeting_date": row.get("last_meeting_date"),
    })
    for key in ("first_meeting_date", "last_meeting_date"):
        value = row.get(key)
        if value and (item[key] is None or (key == "first_meeting_date" and value < item[key]) or (key == "last_meeting_date" and value > item[key])):
            item[key] = value

result = {
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "api": BASE,
    "coverage_generated_at": coverage.get("generated_at"),
    "complete_coverage": coverage.get("complete_coverage"),
    "coverage_rows": len(rows),
    "municipalities": by_municipality,
    "documents_endpoint": {
        "request_succeeded": True,
        "first_page_count": len(documents.get("documents", [])),
        "has_next_page": bool(documents.get("next_cursor")),
        "has_changes_cursor": bool(documents.get("changes_cursor")),
        "consistency": documents.get("consistency"),
        "sample_metadata": (
            {k: documents["documents"][0].get(k) for k in
             ("id", "kommun", "kommun_namn", "organ", "doc_type", "meeting_date",
              "revision", "parse_status", "pages", "scanned")}
            if documents.get("documents") else None
        ),
    },
    "request_ids": {
        "coverage": coverage_request_id,
        "documents": documents_request_id,
    },
}
with open("kungjort-api-probe.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
