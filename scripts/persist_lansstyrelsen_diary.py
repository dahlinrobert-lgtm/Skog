#!/usr/bin/env python3
"""Persist public Länsstyrelsen diary search results and append auditable events.

The input is a successful diary-search JSON file. Results are keyed by diary
number plus diary/county label, never by title text. This script only writes
local output files; it does not publish or change GitHub data by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(record: dict[str, Any]) -> str:
    tracked = {
        key: value for key, value in record.items()
        if key not in {"first_observed_at", "last_observed_at", "observation_count", "content_hash", "event_type"}
    }
    return hashlib.sha256(canonical_json(tracked).encode("utf-8")).hexdigest()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="diary-search.json")
    parser.add_argument("--state", type=Path, required=True, help="Persistent state JSON")
    parser.add_argument("--events", type=Path, required=True, help="Append-only events JSONL")
    parser.add_argument("--summary", type=Path, required=True, help="Run summary JSON")
    args = parser.parse_args()

    run = read_json(args.input, {})
    if not run.get("request_ok"):
        raise SystemExit("Refusing to persist a failed diary search")
    if run.get("error"):
        raise SystemExit(f"Refusing to persist a search with error: {run['error']}")
    total = run.get("reported_total_results")
    queries = run.get("queries")
    if not run.get("total_reconciled"):
        raise SystemExit("Refusing to persist results until all source queries are reconciled")
    if total is None:
        raise SystemExit("Refusing to persist results until a validated source total is present")
    if run.get("pagination", {}).get("has_next_page") is not False:
        raise SystemExit("Refusing to persist results until pagination is confirmed complete")
    if not isinstance(run.get("results"), list):
        raise SystemExit("Input results must be a list")

    if isinstance(queries, list) and queries:
        for query in queries:
            query_total = query.get("reported_total_results")
            if (
                not query.get("request_ok")
                or query.get("error")
                or query_total is None
                or query.get("result_count") != query_total
                or not query.get("total_reconciled")
                or query.get("pagination", {}).get("has_next_page") is not False
            ):
                raise SystemExit(
                    f"Refusing to persist: query failed validation: "
                    f"{query.get('requested_county', '')} / {query.get('search_term', '')}"
                )
        unique_keys = {
            f"{str(record.get('diary') or run.get('requested_county') or '').casefold()}::"
            f"{str(record.get('diary_number') or '').strip()}"
            for record in run["results"] if isinstance(record, dict)
            and str(record.get("diary_number") or "").strip()
        }
        if len(unique_keys) != len(run["results"]) or len(unique_keys) != run.get("result_count"):
            raise SystemExit("Refusing to persist: result count must match unique county/diary-number pairs")
        if len(queries) != len(run.get("per_query_counts", queries)):
            raise SystemExit("Refusing to persist: per-query validation metadata is incomplete")
    elif run.get("result_count") != total:
        raise SystemExit("Refusing to persist results until the extracted count matches a reported source total")

    county = str(run.get("requested_county") or "").strip()
    search_term = str(run.get("search_term") or "").strip()
    observed_at = str(run.get("tested_at_utc") or datetime.now(timezone.utc).isoformat())
    if not county or not search_term:
        raise SystemExit("Search county and phrase are required")
    if not isinstance(run.get("results"), list):
        raise SystemExit("Input results must be a list")

    state = read_json(args.state, {"schema_version": 1, "records": {}})
    records: dict[str, dict[str, Any]] = state.setdefault("records", {})
    previous_counts = len(records)
    events: list[dict[str, Any]] = []
    seen_this_run: set[str] = set()
    invalid_count = 0

    for raw in run["results"]:
        if not isinstance(raw, dict):
            invalid_count += 1
            continue
        diary_number = str(raw.get("diary_number") or "").strip()
        if not diary_number or "-" not in diary_number:
            invalid_count += 1
            continue
        record_county = str(raw.get("diary") or county).strip()
        key = f"{record_county.casefold()}::{diary_number}"
        if key in seen_this_run:
            invalid_count += 1
            continue
        seen_this_run.add(key)
        query_terms = raw.get("query_terms")
        if not isinstance(query_terms, list) or not query_terms:
            query_terms = [search_term]
        query_terms = sorted({str(term).strip() for term in query_terms if str(term).strip()})
        record_query_label = query_terms[0] if query_terms else search_term

        candidate = {
            "record_key": key,
            "diary_number": diary_number,
            "diary": record_county,
            "query_term": record_query_label,
            "queries_seen": query_terms or [search_term],
            "source_url": run.get("source"),
            "title": raw.get("title") or raw.get("Ärenderubrik"),
            "status": raw.get("status") or raw.get("Status"),
            "source_date": raw.get("date") or raw.get("In/Upp-datum"),
            "columns": raw,
            "links": raw.get("links", []),
            "last_query_total": total,
            "last_query_page": raw.get("page_number"),
        }
        candidate_hash = content_hash(candidate)
        previous = records.get(key)

        if previous is None:
            record = {
                **candidate, "first_observed_at": observed_at, "last_observed_at": observed_at,
                "observation_count": 1, "queries_seen": sorted(set(query_terms or [search_term])),
                "content_hash": candidate_hash,
            }
            records[key] = record
            events.append({
                "event_id": hashlib.sha256(f"{key}|first_seen|{observed_at}".encode()).hexdigest(),
                "event_type": "first_seen", "record_key": key, "diary_number": diary_number,
                "diary": record_county, "observed_at": observed_at, "source_date": candidate["source_date"],
                "title": candidate["title"], "content_hash": candidate_hash, "baseline_only": True,
                "note": "First observation by this tool; not proof that the case was newly registered.",
            })
        else:
            def source_projection(record: dict[str, Any]) -> dict[str, Any]:
                columns = record.get("columns", {})
                return {
                    "source_url": record.get("source_url"), "diary_number": record.get("diary_number"),
                    "diary": record.get("diary"), "title": record.get("title") or columns.get("Ärenderubrik"),
                    "status": record.get("status") or columns.get("Status"),
                    "source_date": record.get("source_date") or columns.get("In/Upp-datum"),
                    "sender_recipient": columns.get("Avsändare/mottagare"),
                    "postal_place": columns.get("Postort"), "municipality": columns.get("Kommun"),
                    "decision_date": columns.get("Beslutsdatum"),
                }
            previous_source = source_projection(previous)
            candidate_source = source_projection(candidate)
            previous_queries = set(previous.get("queries_seen", []))
            if previous.get("query_term"):
                previous_queries.add(previous["query_term"])
            previous_queries.update(query_terms or [search_term])
            updated = {
                **previous, "last_observed_at": observed_at,
                "observation_count": int(previous.get("observation_count", 0)) + 1,
                "queries_seen": sorted(previous_queries), "query_term": record_query_label,
                "last_query_total": total, "last_query_page": raw.get("page_number"),
            }
            if previous_source != candidate_source:
                updated.update(candidate)
                updated["columns"] = {**previous.get("columns", {}), **candidate.get("columns", {})}
                updated.update({
                    "first_observed_at": previous.get("first_observed_at", observed_at),
                    "last_observed_at": observed_at,
                    "observation_count": int(previous.get("observation_count", 0)) + 1,
                    "queries_seen": sorted(previous_queries),
                    "content_hash": content_hash(source_projection(updated)),
                })
                records[key] = updated
                events.append({
                    "event_id": hashlib.sha256(f"{key}|record_changed|{observed_at}|{updated['content_hash']}".encode()).hexdigest(),
                    "event_type": "record_changed", "record_key": key, "diary_number": diary_number,
                    "diary": record_county, "observed_at": observed_at, "previous_hash": previous.get("content_hash"),
                    "content_hash": updated["content_hash"],
                    "before": {k: previous.get(k) for k in ("title", "status", "source_date")},
                    "after": {k: updated.get(k) for k in ("title", "status", "source_date")},
                    "note": "A source-row change was detected. Query metadata alone is not a change.",
                })
            else:
                updated["content_hash"] = content_hash(candidate_source)
                records[key] = updated

    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.events.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.events.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "observed_at": observed_at,
        "diary": county,
        "counties": run.get("counties") or [county],
        "county_summaries": run.get("county_summaries") or [],
        "query_count": len(run.get("queries") or []),
        "search_term": search_term,
        "search_terms": run.get("search_terms") or [search_term],
        "request_ok": True,
        "extracted_count": len(run["results"]),
        "reported_total_results": total,
        "total_reconciled": run.get("total_reconciled"),
        "pagination": run.get("pagination"),
        "state_record_count_before": previous_counts,
        "state_record_count_after": len(records),
        "first_seen_events": sum(e["event_type"] == "first_seen" for e in events),
        "changed_events": sum(e["event_type"] == "record_changed" for e in events),
        "invalid_or_duplicate_records": invalid_count,
        "absent_ids_interpreted_as_removed": False,
        "note": "Records absent from a search are not marked removed: they may not match the current search phrase or may be outside the source's current result window.",
    }
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
