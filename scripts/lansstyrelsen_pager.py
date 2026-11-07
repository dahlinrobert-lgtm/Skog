"""Dependency-free pagination helpers for the Länsstyrelsen ASP.NET diary."""
from __future__ import annotations

import re


def select_next_pager_action(
    candidates: list[dict], current_page_index: int
) -> dict | None:
    """Select the next safe forward action from an ASP.NET GridView pager.

    GridView Page$N arguments are zero-based page indexes. The visible label is
    not necessarily the same as the argument (and can be an ellipsis), so use
    the postback argument for numeric links and the label only to distinguish
    the sliding-window ellipsis.
    """
    forward = []
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if not match:
            continue
        target_index = int(match.group(1))
        # Trust the zero-based WebForms target, not the visible label. An
        # ellipsis can represent the next page (for example Page$6 on page 5).
        # A backward ellipsis (for example Page$1) must never restart paging.
        if target_index > current_page_index:
            forward.append((target_index, item))

    if forward:
        return min(forward, key=lambda pair: pair[0])[1]

    # Prefer a genuine Next action. Do not jump to Last: doing so can silently
    # skip result pages and make a national collection appear incomplete.
    for item in candidates:
        if item["argument"].casefold() in {"next", "page$next"}:
            return item

    return None


def advance_page_index(current_page_index: int, label: str, argument: str) -> int:
    """Track the result-page index without counting pager-window shifts as pages.

    ASP.NET GridView numeric Page$N arguments identify zero-based result pages.
    The ellipsis Page$1 postback advances the visible pager window and must not
    increment the result-page index. A genuine Next action advances one page.
    """
    normalized_label = (label or "").strip()
    normalized_argument = (argument or "").casefold()
    if normalized_label in {"...", "…"}:
        return current_page_index
    match = re.fullmatch(r"page\$(\d+)", normalized_argument, re.I)
    if match:
        return int(match.group(1))
    if normalized_argument in {"next", "page$next"}:
        return current_page_index + 1
    return current_page_index
