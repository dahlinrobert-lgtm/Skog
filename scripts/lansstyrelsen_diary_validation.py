"""Dependency-free validation helpers for public Länsstyrelsen diary searches."""
from __future__ import annotations

import re


def has_explicit_zero_results(text: str) -> bool:
    """Return true only when the source explicitly says there are zero results."""
    normalized = text.replace("\u00a0", " ")
    return re.search(r"\bSökresultat\s*:\s*0\b", normalized, re.I) is not None
