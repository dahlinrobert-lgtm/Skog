#!/usr/bin/env python3
"""Regression tests for repeated rows while the portal's sliding pager advances."""
from __future__ import annotations
import unittest
from unittest.mock import Mock
from scripts.lansstyrelsen_pager import select_next_pager_action


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

    def test_no_continuation_is_terminal(self):
        self.assertIsNone(select_next_pager_action([], 5))


if __name__ == "__main__":
    unittest.main()
