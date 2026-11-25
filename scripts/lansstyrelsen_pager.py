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

    # Page$1 is not enough to determine ellipsis direction. In the live
    # portal DOM, a forward window ellipsis follows the visible numeric links
    # (for example: 1 2 3 4 5 ... >>). A backward ellipsis is preceded by the
    # previous-window control and followed by numeric links (for example:
    # << ... 2 3 4 5 6). Only accept Page$1 when it is at the right edge of
    # the pager action sequence and no backward control precedes it.
    for index, item in enumerate(candidates):
        if (
            item.get("label", "").strip() not in {"...", "…"}
            or item["argument"].casefold() != "page$1"
        ):
            continue
        preceding = candidates[:index]
        following = candidates[index + 1:]
        has_backward_control = any(
            candidate.get("label", "").strip() in {"<<", "‹", "«"}
            or candidate.get("argument", "").casefold() in {"page$first", "first"}
            for candidate in preceding
        )
        has_numeric_after = any(
            re.fullmatch(r"Page\$(\d+)", candidate.get("argument", ""), re.I)
            and candidate.get("label", "").strip() not in {"...", "…"}
            for candidate in following
        )
        if not has_backward_control and not has_numeric_after:
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


def build_pager_action_diagnostic(
    page_from: int, action: dict, response_seen: bool, page_changed: bool
) -> dict:
    """Return explicit evidence for one completed pager transition."""
    return {
        "page_from": page_from,
        "label": action.get("label", ""),
        "target": action.get("target", ""),
        "argument": action.get("argument", ""),
        "response_seen": bool(response_seen),
        "page_changed": bool(page_changed),
    }


def build_pager_state_diagnostic(
    page_from: int, row_text: str, candidates: list[dict], pager_html: str,
    html_limit: int = 12000,
) -> dict:
    """Capture bounded, read-only evidence of the visible pager before a transition."""
    html = pager_html or ""
    return {
        "page_from": page_from,
        "row_text": row_text or "",
        "candidate_actions": [dict(item) for item in candidates],
        "pager_html": html[:html_limit],
        "pager_html_truncated": len(html) > html_limit,
        "pager_html_original_length": len(html),
    }
