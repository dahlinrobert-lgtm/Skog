"""Dependency-free pagination helpers for the Länsstyrelsen ASP.NET diary."""
from __future__ import annotations

import re


def select_next_pager_action(
    candidates: list[dict], current_page_index: int
) -> dict | None:
    """Select the next safe forward action from an ASP.NET GridView pager.

    Numeric Page$N postbacks are zero-based result-page indexes. When the
    visible numeric window is exhausted, this portal exposes a special
    forward-window ellipsis using Page$1, even when the logical result-page
    index is later. Other ellipses are accepted only when their Page$N
    argument is ahead of the current index, which avoids following a
    backward-window ellipsis. Never use Page$Last because it can skip pages.
    """
    forward = []
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if not match or item.get("label", "").strip() in {"...", "…"}:
            continue
        target_index = int(match.group(1))
        if target_index > current_page_index:
            forward.append((target_index, item))

    if forward:
        return min(forward, key=lambda pair: pair[0])[1]

    # The portal's forward sliding-window ellipsis is specifically Page$1.
    # It advances the visible pager window, not the underlying result-page
    # index, so it remains valid after the first few result pages. Do not
    # generalize this to every lower Page$N argument: those can be backward
    # ellipses and would restart an earlier window.
    for item in candidates:
        if (
            item.get("label", "").strip() in {"...", "…"}
            and item["argument"].casefold() == "page$1"
        ):
            return item

    # Other forward ellipses have a Page$N argument beyond the current
    # logical page. A lower/equal argument (except the portal's special
    # Page$1 forward-window command above) is a backward window.
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if (
            match
            and item.get("label", "").strip() in {"...", "…"}
            and int(match.group(1)) > current_page_index
        ):
            return item

    for item in candidates:
        if item["argument"].casefold() in {"next", "page$next"}:
            return item

    return None


def advance_page_index(current_page_index: int, label: str, argument: str) -> int:
    """Advance the logical result-page index for numeric, ellipsis and Next actions."""
    normalized_label = (label or "").strip()
    normalized_argument = (argument or "").casefold()
    match = re.fullmatch(r"page\$(\d+)", normalized_argument, re.I)
    if match:
        target_index = int(match.group(1))
        if normalized_label in {"...", "…"}:
            # Page$1 is a pager-window transition, not a result-page index.
            # Keep the logical index stable while the visible window advances.
            if target_index == 1:
                return current_page_index
            return target_index if target_index > current_page_index else current_page_index
        if target_index > current_page_index:
            return target_index
        return current_page_index
    if normalized_argument in {"next", "page$next"}:
        return current_page_index + 1
    return current_page_index
