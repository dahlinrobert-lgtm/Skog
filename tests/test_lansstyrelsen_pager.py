from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lansstyrelsen_pager import advance_page_index, select_next_pager_action  # noqa: E402


def action(label: str, argument: str) -> dict:
    return {"label": label, "argument": argument}


class LansstyrelsenPagerTests(unittest.TestCase):
    def test_first_result_page_chooses_zero_based_page_one(self):
        candidates = [action("1", "Page$1"), action("2", "Page$2")]
        self.assertEqual(
            select_next_pager_action(candidates, current_page_index=0),
            candidates[0],
        )

    def test_second_result_page_chooses_page_two_not_page_one_again(self):
        candidates = [action("1", "Page$1"), action("2", "Page$2")]
        self.assertEqual(
            select_next_pager_action(candidates, current_page_index=1),
            candidates[1],
        )

    def test_numeric_page_link_is_preferred_to_sliding_window_ellipsis(self):
        candidates = [
            action("...", "Page$1"),
            action("3", "Page$2"),
            action("4", "Page$3"),
        ]
        self.assertEqual(
            select_next_pager_action(candidates, current_page_index=1),
            candidates[1],
        )

    def test_forward_ellipsis_page_argument_is_used_as_next_page(self):
        candidates = [action("...", "Page$6"), action(">>", "Page$Last")]
        self.assertEqual(
            select_next_pager_action(candidates, current_page_index=5),
            candidates[0],
        )

    def test_page_one_ellipsis_is_forward_window_action_when_no_numeric_forward_link(self):
        candidates = [action("...", "Page$1"), action(">>", "Page$Last")]
        self.assertEqual(
            select_next_pager_action(candidates, current_page_index=6),
            candidates[0],
        )

    def test_page_one_ellipsis_advances_logical_page_index(self):
        self.assertEqual(advance_page_index(6, "...", "Page$1"), 7)

    def test_numeric_page_argument_sets_zero_based_result_page_index(self):
        self.assertEqual(advance_page_index(1, "4", "Page$3"), 3)

    def test_next_action_advances_result_page_index(self):
        self.assertEqual(advance_page_index(4, "Nästa", "Next"), 5)

    def test_next_is_used_but_last_is_never_used_to_skip_pages(self):
        next_action = action("Nästa", "Next")
        candidates = [action("Sista", "Last"), next_action]
        self.assertEqual(
            select_next_pager_action(candidates, current_page_index=4),
            next_action,
        )
        self.assertIsNone(
            select_next_pager_action([action("Sista", "Last")], current_page_index=4)
        )


if __name__ == "__main__":
    unittest.main()
