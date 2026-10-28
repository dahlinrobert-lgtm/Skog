"""Dependency-free validation helpers for public Länsstyrelsen diary searches."""
from __future__ import annotations

import re


def has_explicit_zero_results(text: str) -> bool:
    """Return true only when the source explicitly says there are zero results."""
    normalized = text.replace("\u00a0", " ")
    return re.search(r"\bSökresultat\s*:\s*0\b", normalized, re.I) is not None



EXPECTED_SWEDISH_COUNTIES = 21


def resolve_county_labels(options: list[dict]) -> list[str]:
    """Return all individual county diary labels, failing closed on incomplete lists."""
    labels = [
        str(option.get("label") or "").strip()
        for option in options
        if str(option.get("label") or "").strip()
        and option.get("value") not in (None, "", "0", "-1")
        and "välj" not in str(option.get("label") or "").casefold()
        and "alla län" not in str(option.get("label") or "").casefold()
    ]
    if len(set(labels)) != len(labels):
        raise ValueError(f"Duplicate county diary options found: {labels!r}")
    if len(labels) != EXPECTED_SWEDISH_COUNTIES:
        raise ValueError(
            f"Expected {EXPECTED_SWEDISH_COUNTIES} individual county diary options, "
            f"found {len(labels)}: {labels!r}"
        )
    return labels


def summarize_county_coverage(
    counties: list[str],
    queries: list[dict],
    *,
    is_all_counties: bool,
) -> dict:
    """Summarize and validate whether all requested county searches completed."""
    labels = [str(label).strip() for label in counties]
    expected = EXPECTED_SWEDISH_COUNTIES if is_all_counties else len(labels)
    summaries = []
    for county in labels:
        matching = [q for q in queries if q.get("requested_county") == county]
        successful = sum(
            bool(q.get("request_ok") and q.get("total_reconciled"))
            for q in matching
        )
        summaries.append({
            "county": county,
            "query_count": len(matching),
            "successful_queries": successful,
            "failed_queries": len(matching) - successful,
        })
    completed = sum(
        row["query_count"] > 0 and row["failed_queries"] == 0
        for row in summaries
    )
    failed = [
        row["county"] for row in summaries
        if row["query_count"] == 0 or row["failed_queries"] > 0
    ]
    valid = (
        len(labels) == expected
        and len(set(labels)) == expected
        and completed == expected
        and not failed
        and all(q.get("request_ok") and q.get("total_reconciled") for q in queries)
    )
    return {
        "expected_county_count": expected,
        "completed_counties": completed,
        "failed_counties": failed,
        "county_summaries": summaries,
        "county_coverage_ok": valid,
    }
