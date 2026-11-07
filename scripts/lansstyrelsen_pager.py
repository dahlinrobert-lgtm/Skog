"""Dependency-free pagination helpers for the Länsstyrelsen ASP.NET diary."""
from __future__ import annotations

import re


def select_next_pager_action(
    candidates: list[dict], current_page_index: int
) -> dict | None:
    """Select the next safe forward action from an ASP.NET GridView pager.

    Numeric Page$N postbacks are zero-based result-page indexes. This portal
    also uses an ellipsis with Page$1 as a forward pager-window control after
    the numeric window is exhausted. Only consider that special control when
    no ordinary forward numeric link exists; never use Page$Last because it
    can skip uncollected result pages.
    """
    forward = []
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if not match:
            continue
        target_index = int(match.group(1))
        if target_index > current_page_index:
            forward.append((target_index, item))

    if forward:
        return min(forward, key=lambda pair: pair[0])[1]

    # Observed portal behavior: after reaching the end of the visible numeric
    # window, the ellipsis posts Page$1 and advances to another 50-row page.
    # It is not the same as clicking the visible page-1 numeric link.
    for item in candidates:
        if (
            item["argument"].casefold() == "page$1"
            and item.get("label", "").strip() in {"...", "…"}
        ):
            return item

    for item in candidates:
        if item["argument"].casefold() in {"next", "page$next"}:
            return item

    return None


def advance_page_index(current_page_index: int, label: str, argument: str) -> int:
    """Advance the logical result-page index for numeric, ellipsis and Next actions.

    Numeric Page$N arguments identify zero-based result pages. The portal's
    special ellipsis Page$1 is a forward window action when selected as an
    ellipsis (not the numeric page-one link), and the observed postback changes
    the result rows; count it as one result-page transition.
    """
    normalized_label = (label or "").strip()
    normalized_argument = (argument or "").casefold()
    match = re.fullmatch(r"page\$(\d+)", normalized_argument, re.I)
    if match:
        target_index = int(match.group(1))
        if target_index > current_page_index:
            return target_index
        if target_index == 1 and normalized_label in {"...", "…"}:
            return current_page_index + 1
        return current_page_index
    if normalized_argument in {"next", "page$next"}:
        return current_page_index + 1
    return current_page_index
