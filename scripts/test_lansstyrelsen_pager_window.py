#!/usr/bin/env python3
"""Regression tests for repeated rows while the portal's sliding pager advances."""
from __future__ import annotations
import unittest
from unittest.mock import Mock
from scripts.lansstyrelsen_pager import (\n    build_pager_state_diagnostic, select_next_pager_action,\n)


class SlidingPagerWindowTests(unittest.TestCase):
    def test_page_window_ellipsis_remains_a_valid_continuation(self):
        actions = [
            {"label": "1", "target": "grid", "argument": "Page$1"},
            {"label": "2", "target": "grid", "argument": "Page$2"},
            {"label": "...", "target": "grid", "argument": "Page$1"},
        ]
        next_action = select_next_pager_action(actions, 5)
        self.assertIsNotNone(next_action)
        self.assertEqual(next_action["label"], "...")

    def test_direct_next_action_is_selected_after_numeric_window(self):
        actions = [{"label": "Nästa", "target": "grid", "argument": "Next"}]
        self.assertEqual(select_next_pager_action(actions, 5)["argument"], "Next")


    def test_last_action_is_terminal_candidate(self):
        actions = [{"label": "sista", "target": "grid", "argument": "Page$Last"}]
        self.assertEqual(select_next_pager_action(actions, 5)["argument"], "Page$Last")

    def test_numeric_pages_take_precedence_over_last(self):
        actions = [
            {"label": "Sista", "target": "grid", "argument": "Page$Last"},
            {"label": "6", "target": "grid", "argument": "Page$6"},
        ]
        self.assertEqual(select_next_pager_action(actions, 4)["argument"], "Page$6")

    def test_pager_state_captures_candidates_and_row_text(self):
        state = build_pager_state_diagnostic(
            7, "1 2 ... 8", [{"label": "...", "target": "grid", "argument": "Page$1"}],
            "<tr>pager</tr>",
        )
        self.assertEqual(state["page_from"], 7)
        self.assertEqual(state["row_text"], "1 2 ... 8")
        self.assertEqual(state["candidate_actions"][0]["argument"], "Page$1")
        self.assertEqual(state["pager_html"], "<tr>pager</tr>")
        self.assertFalse(state["pager_html_truncated"])

    def test_pager_html_is_capped_and_reports_truncation(self):
        state = build_pager_state_diagnostic(1, "row", [], "x" * 12001)
        self.assertEqual(len(state["pager_html"]), 12000)
        self.assertTrue(state["pager_html_truncated"])
        self.assertEqual(state["pager_html_original_length"], 12001)

    def test_no_continuation_is_terminal(self):
        self.assertIsNone(select_next_pager_action([], 5))


if __name__ == "__main__":
    unittest.main()
