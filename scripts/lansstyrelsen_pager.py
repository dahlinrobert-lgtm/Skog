"""Dependency-free pagination helpers for the Länsstyrelsen ASP.NET diary."""
from __future__ import annotations
import re


def select_next_pager_action(candidates: list[dict], current_page_index: int) -> dict | None:
    """Select the next action from a sliding ASP.NET GridView pager."""
    numeric = []
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if match and int(match.group(1)) > current_page_index + 1:
            numeric.append((int(match.group(1)), item))
    if numeric:
        return min(numeric, key=lambda pair: pair[0])[1]
    # In this portal, the ellipsis's Page$1 command advances the pager window.
    for item in candidates:
        if item["argument"].casefold() == "page$1" and item["label"] in {"...", "…"}:
            return item
    for item in candidates:
        if item["argument"].casefold() in {"last", "page$last"}:
            return item
    for item in candidates:
        if item["argument"].casefold() in {"next", "page$next"}:
            return item
    return None
