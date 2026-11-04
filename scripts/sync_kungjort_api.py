#!/usr/bin/env python3
"""Resumable metadata/full-text archive and change sync for the Kungjort pilot."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://handlingar.kungjort.se/api/v1"
ROOT = Path("data/kungjort")
STATE_PATH = ROOT / "state.json"
PAGE_SIZE = 100
USER_AGENT = "Skog-Kungjort-Archive/1.0"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Api:
    def __init__(self, key, opener=None, sleep=time.sleep):
        if not key:
            raise RuntimeError("Missing KUNGJORT_API_KEY")
        self.key = key
        self.opener = opener or urllib.request.urlopen
        self.sleep = sleep

    def get(self, path, params=None):
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        for attempt in range(7):
            req = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + self.key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            })
            try:
                with self.opener(req, timeout=90) as response:
                    payload = json.load(response)
                    return payload, response.headers.get("X-Request-ID")
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 503) or attempt == 6:
                    body = exc.read().decode("utf-8", "replace")[:500]
                    raise RuntimeError(
                        f"Kungjort API HTTP {exc.code}; "
                        f"request_id={exc.headers.get('X-Request-ID')}; body={body}"
                    ) from exc
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = max(1, min(300, int(retry_after))) if retry_after else min(120, 2 ** attempt + random.random())
                except ValueError:
                    delay = min(120, 2 ** attempt + random.random())
                self.sleep(delay)
        raise RuntimeError("API retry loop exhausted")


def load_state():
    if not STATE_PATH.exists():
        return {
            "schema_version": 1,
            "bootstrap_complete": False,
            "bootstrap_cursor": None,
            "changes_cursor": None,
            "last_sync_at": None,
        }
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if state.get("schema_version") != 1:
        raise RuntimeError("Unsupported Kungjort state schema")
    return state


def save_state(state):
    ROOT.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)


def append_records(mode, records):
    if not records:
        return None
    ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = ROOT / mode
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}-{os.getpid()}.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return str(path)


def document_id(row):
    return row.get("id") or row.get("document_id")


def fetch_detail(api, row):
    doc_id = document_id(row)
    if not doc_id:
        raise RuntimeError("Document list item has no id/document_id")
    encoded = urllib.parse.quote(str(doc_id), safe="")
    detail, request_id = api.get(f"/documents/{encoded}")
    # Keep list metadata alongside the full detail response for traceability.
    return {
        "record_type": "document",
        "document_id": str(doc_id),
        "captured_at": utc_now(),
        "list_record": row,
        "detail": detail,
        "request_id": request_id,
    }


def bootstrap(api, state, max_pages):
    if state.get("bootstrap_complete"):
        print("Historical bootstrap already complete.")
        return state
    cursor = state.get("bootstrap_cursor")
    if cursor and not state.get("changes_cursor"):
        raise RuntimeError("Bootstrap checkpoint exists without the original changes_cursor; refusing unsafe resume")
    records = []
    pages = 0
    while pages < max_pages:
        params = {"limit": PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        page, request_id = api.get("/documents", params)
        if pages == 0 and not state.get("changes_cursor"):
            initial_changes_cursor = page.get("changes_cursor")
            if not initial_changes_cursor:
                raise RuntimeError("First /documents page did not provide changes_cursor; refusing unsafe bootstrap")
            state["changes_cursor"] = initial_changes_cursor
        rows = page.get("documents")
        if not isinstance(rows, list):
            raise RuntimeError("/documents response has no documents array")
        for row in rows:
            records.append(fetch_detail(api, row))
        cursor = page.get("next_cursor")
        state["bootstrap_cursor"] = cursor
        pages += 1
        print(f"Bootstrap page {pages}: {len(rows)} list rows; {len(records)} detail records collected.")
        if not cursor:
            state["bootstrap_complete"] = True
            break
    archive = append_records("bootstrap", records)
    state["last_sync_at"] = utc_now()
    save_state(state)
    print(json.dumps({
        "mode": "bootstrap",
        "pages_this_run": pages,
        "documents_this_run": len(records),
        "archive": archive,
        "bootstrap_complete": state["bootstrap_complete"],
        "next_cursor_present": bool(state.get("bootstrap_cursor")),
        "changes_cursor_saved": bool(state.get("changes_cursor")),
    }, ensure_ascii=False))
    return state


def extract_change_cursor(payload):
    # API revisions may expose the continuation under either cursor field.
    return payload.get("next_cursor") or payload.get("changes_cursor")


def sync_changes(api, state, max_pages):
    if not state.get("bootstrap_complete"):
        raise RuntimeError("Changes sync is blocked until historical bootstrap is complete")
    cursor = state.get("changes_cursor")
    if not cursor:
        raise RuntimeError("No saved changes_cursor; refusing to start an unsafe changes sync")
    records = []
    pages = 0
    while pages < max_pages:
        payload, _ = api.get("/changes", {"cursor": cursor, "limit": PAGE_SIZE})
        changes = payload.get("changes")
        if not isinstance(changes, list):
            raise RuntimeError("/changes response has no changes array")
        for change in changes:
            action = str(change.get("operation") or change.get("action") or change.get("type") or "").lower()
            doc_id = change.get("document_id") or change.get("id")
            if action in ("delete", "deleted", "tombstone"):
                records.append({
                    "record_type": "tombstone",
                    "document_id": str(doc_id) if doc_id is not None else None,
                    "captured_at": utc_now(),
                    "change": change,
                })
            elif action in ("upsert", "insert", "update", "updated", "created"):
                row = change.get("document") if isinstance(change.get("document"), dict) else change
                records.append(fetch_detail(api, row))
            else:
                raise RuntimeError(f"Unknown change operation {action!r}; refusing to advance cursor")
        new_cursor = extract_change_cursor(payload)
        if not new_cursor:
            # Empty changes may legitimately signal that the supplied cursor is current.
            if changes:
                raise RuntimeError("Non-empty /changes page did not provide a continuation cursor")
            break
        if new_cursor == cursor:
            raise RuntimeError("/changes cursor did not advance")
        cursor = new_cursor
        state["changes_cursor"] = cursor
        pages += 1
        print(f"Changes page {pages}: {len(changes)} changes.")
        if not payload.get("next_cursor"):
            break
    archive = append_records("changes", records)
    state["last_sync_at"] = utc_now()
    save_state(state)
    print(json.dumps({
        "mode": "changes",
        "pages_this_run": pages,
        "records_this_run": len(records),
        "archive": archive,
        "changes_cursor_saved": bool(state.get("changes_cursor")),
    }, ensure_ascii=False))
    return state


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("bootstrap", "changes"), required=True)
    parser.add_argument("--max-pages", type=int, default=5)
    args = parser.parse_args(argv)
    if args.max_pages < 1 or args.max_pages > 100:
        parser.error("--max-pages must be between 1 and 100")
    api = Api(os.environ.get("KUNGJORT_API_KEY"))
    state = load_state()
    if args.mode == "bootstrap":
        bootstrap(api, state, args.max_pages)
    else:
        sync_changes(api, state, args.max_pages)


if __name__ == "__main__":
    main()
