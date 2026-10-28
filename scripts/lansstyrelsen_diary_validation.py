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
