"""Dependency-free pagination helpers for the Länsstyrelsen ASP.NET diary."""
from __future__ import annotations

import re


def select_next_pager_action(
    candidates: list[dict], current_page_index: int
) -> dict | None:
    """Select the next safe forward action from an ASP.NET GridView pager.

    Numeric Page$N postbacks are zero-based result-page indexes. When the
    visible numeric window is exhausted, this portal exposes an ellipsis
    postback whose Page$N argument can be lower than the logical page index.
    In that position the ellipsis advances the pager window; it is distinct
    from a numeric page link. Never use Page$Last because it can skip pages.
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

    # The portal renders both forward and backward ellipses with the
    # same visible label. Their Page$N argument is the direction signal:
    # only an argument beyond the current logical page can advance safely.
    # Treating every ellipsis as forward can send a late page (e.g. index 10)
    # back to an earlier page (e.g. Page$5), creating a 5-page loop.
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
            # The portal's ellipsis shifts its pager window and fetches the next
            # result page, even when its Page$N argument points behind our index.
            return current_page_index + 1
        if target_index > current_page_index:
            return target_index
        return current_page_index
    if normalized_argument in {"next", "page$next"}:
        return current_page_index + 1
    return current_page_index
