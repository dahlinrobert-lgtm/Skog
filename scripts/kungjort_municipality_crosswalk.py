"""SCB municipality-code crosswalk for Kungjort provenance validation.

The initial curated set covers the five municipality names observed in the
2026-11-10 Kungjort selection inventory. Unknown names fail closed and are
reported for review; this is deliberately not presented as the full national
290-municipality register.
"""
from __future__ import annotations

import re
import unicodedata

SCB_REFERENCE_YEAR = 2026
SCB_SOURCE_URL = (
    "https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/"
    "regionala-indelningar/lan-och-kommuner/lan-och-kommuner-i-kodnummerordning/"
)

# Codes and canonical names checked against SCB's 2026 municipality register.
# Key is the accent-insensitive normalized municipality name.
SCB_OBSERVED_MUNICIPALITIES = {
    "ornskoldsvik": {"municipality_code": "2284", "municipality_name": "Örnsköldsvik"},
    "umea": {"municipality_code": "2480", "municipality_name": "Umeå"},
    "skelleftea": {"municipality_code": "2482", "municipality_name": "Skellefteå"},
    "lulea": {"municipality_code": "2580", "municipality_name": "Luleå"},
    "sundsvall": {"municipality_code": "2281", "municipality_name": "Sundsvall"},
}


def normalize_municipality_name(value: str) -> str:
    """Normalize Swedish municipality labels without guessing abbreviations."""
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    text = re.sub(r"\\bkommun\\b$", "", text).strip()
    decomposed = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def resolve_scb_municipality(value: str) -> dict:
    """Return an exact normalized SCB match, or an explicit unmatched result."""
    key = normalize_municipality_name(value)
    match = SCB_OBSERVED_MUNICIPALITIES.get(key)
    if not match:
        return {
            "status": "unmatched",
            "municipality_code": None,
            "municipality_name": None,
            "normalized_name": key,
        }
    return {
        "status": "matched",
        **match,
        "normalized_name": key,
    }
