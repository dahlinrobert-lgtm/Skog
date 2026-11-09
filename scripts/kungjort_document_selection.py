#!/usr/bin/env python3
"""Conservative, explainable scope classification for Kungjort planning notices.

This module is deliberately pure: it does not access Azure, call the Kungjort API,
or create links between documents. It classifies supplied metadata only.
"""
from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping

TEXT_FIELDS = frozenset({
    "title", "rubrik", "subject", "amne", "ämne", "summary",
    "sammanfattning", "description", "beskrivning", "doc_type",
    "document_type", "case_title", "arende", "ärende", "keywords",
    "tags", "planbeteckning", "plan_namn",
})

PRIMARY_PLAN_TERMS = (
    "detaljplan", "detaljplaner", "detaljplaneandring",
    "andring av detaljplan", "planandring", "omradesbestammelse",
    "oversiktsplan", "planprogram", "planbesked", "planlaggning",
    "planforslag", "plankarta", "planbeskrivning",
    "genomforandebeskrivning",
)

PROCESS_TERMS = (
    "samrad", "granskning", "antagande", "laga kraft",
    "overklagande", "utstallning", "planprocess",
)

ADJACENT_TERMS = (
    "vagplan", "jarnvagsplan", "vagombyggnad", "infrastrukturprojekt",
    "vindkraftspark", "vindkraftverk", "solcellspark", "kraftledning",
    "natkoncession", "vattenverksamhet", "miljotillstand", "bergtakt",
    "grustakt", "torvtakt",
)


def normalize(value: str) -> str:
    """Case- and accent-insensitive normalization for Swedish text."""
    value = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", value).casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.split())


def _collect_approved_text(value: object, chunks: list[str]) -> None:
    """Collect strings only from approved semantic fields, never IDs or URLs."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in TEXT_FIELDS:
                if isinstance(child, str):
                    chunks.append(child)
                elif isinstance(child, (list, tuple)):
                    chunks.extend(item for item in child if isinstance(item, str))
            if isinstance(child, (Mapping, list, tuple)):
                _collect_approved_text(child, chunks)
    elif isinstance(value, (list, tuple)):
        for child in value:
            if isinstance(child, (Mapping, list, tuple)):
                _collect_approved_text(child, chunks)


def searchable_text(record: Mapping) -> str:
    """Build search text from listing/detail metadata using a field allowlist."""
    chunks: list[str] = []
    _collect_approved_text(record, chunks)
    return normalize(" ".join(chunks))


def classify_plan_scope(record: Mapping) -> dict:
    """Return a conservative selection class with explicit, reproducible reasons."""
    text = searchable_text(record)
    primary = tuple(term for term in PRIMARY_PLAN_TERMS if normalize(term) in text)
    process = tuple(term for term in PROCESS_TERMS if normalize(term) in text)
    adjacent = tuple(term for term in ADJACENT_TERMS if normalize(term) in text)

    if primary:
        selection_class, include, priority = "core_plan", True, "P1"
        reasons = [f"explicit_plan_term:{term}" for term in primary]
    elif process:
        selection_class, include, priority = "process_candidate", False, "P2"
        reasons = [f"procedural_term_requires_plan_context:{term}" for term in process]
    elif adjacent:
        selection_class, include, priority = "adjacent_geography", False, "P3"
        reasons = [f"adjacent_sector_term:{term}" for term in adjacent]
    else:
        selection_class, include, priority = "other", False, "P4"
        reasons = ["no_supported_plan_scope_signal"]

    return {
        "selection_class": selection_class,
        "priority": priority,
        "include_in_core_plan_set": include,
        "reasons": reasons,
        "matched_terms": sorted(set(primary + process + adjacent)),
        "rule_version": "2026-11-09-v1",
    }


def classify_records(records: Iterable[Mapping]) -> list[dict]:
    """Classify records without changing or enriching the source objects."""
    return [classify_plan_scope(record) for record in records]
