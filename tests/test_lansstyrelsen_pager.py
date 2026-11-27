from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lansstyrelsen_pager import (  # noqa: E402
    advance_page_index, build_pager_action_diagnostic, select_next_pager_action,
    source_total_reconciled,
)


def action(label: str, argument: str) -> dict:
    return {"label": label, "argument": argument}


class LansstyrelsenPagerTests(unittest.TestCase):
    def test_source_total_reconciles_raw_rows_even_when_unique_records_are_deduplicated(self):
        # Observed Blekinge query: 143 source rows across pages, 8 repeated case IDs.
        raw_result_rows_seen = 50 + 50 + 43
        unique_records_extracted = 135
        self.assertEqual(raw_result_rows_seen, 143)
        self.assertEqual(unique_records_extracted, 135)
        self.assertTrue(source_total_reconciled(143, raw_result_rows_seen))

    def test_source_total_does_not_reconcile_when_any_result_rows_are_unread(self):
        self.assertFalse(source_total_reconciled(143, 142))

    def test_source_total_unknown_never_reconciles(self):
        self.assertFalse(source_total_reconciled(None, 143))

    def test_pager_action_diagnostic_records_exact_postback_and_transition(self):
        selected = {"label": "...", "target": "ctl00$Main$GridView", "argument": "Page$1"}
        self.assertEqual(
            build_pager_action_diagnostic(6, selected, True, True),
            {"page_from": 6, "label": "...", "target": "ctl00$Main$GridView",
             "argument": "Page$1", "response_seen": True, "page_changed": True},
        )

    def test_pager_action_diagnostic_keeps_response_and_page_change_distinct(self):
        diagnostic = build_pager_action_diagnostic(6, action("...", "Page$1"), False, True)
        self.assertFalse(diagnostic["response_seen"])
        self.assertTrue(diagnostic["page_changed"])

    def test_first_result_page_chooses_zero_based_page_one(self):
        candidates = [action("1", "Page$1"), action("2", "Page$2")]
        self.assertEqual(select_next_pager_action(candidates, 0), candidates[0])

    def test_second_result_page_chooses_page_two_not_page_one_again(self):
        candidates = [action("1", "Page$1"), action("2", "Page$2")]
        self.assertEqual(select_next_pager_action(candidates, 1), candidates[1])

    def test_numeric_page_link_is_preferred_to_sliding_window_ellipsis(self):
        candidates = [
            action("...", "Page$1"),
            action("3", "Page$2"),
            action("4", "Page$3"),
        ]
        self.assertEqual(select_next_pager_action(candidates, 1), candidates[1])

    def test_forward_ellipsis_page_argument_is_used_as_next_page(self):
        candidates = [action("...", "Page$6"), action(">>", "Page$Last")]
        self.assertEqual(select_next_pager_action(candidates, 5), candidates[0])

    def test_forward_page_one_ellipsis_advances_late_sliding_window(self):
        candidates = [
            action("1", "Page$1"),
            action("2", "Page$2"),
            action("...", "Page$1"),
        ]
        self.assertEqual(select_next_pager_action(candidates, 5), candidates[2])
        self.assertEqual(advance_page_index(5, "...", "Page$1"), 5)

    def test_page_one_ellipsis_after_previous_control_is_backward(self):
        # Captured from Blekinge run #18: << ... 2 3 4 5 6.
        candidates = [
            {"label": "<<", "argument": "Page$First"},
            {"label": "...", "argument": "Page$1"},
            action("2", "Page$2"),
            action("3", "Page$3"),
            action("4", "Page$4"),
            action("5", "Page$5"),
        ]
        self.assertIsNone(select_next_pager_action(candidates, 5))

    def test_page_one_ellipsis_after_numeric_links_is_forward(self):
        # Forward window: 1 2 3 4 5 ... >>
        candidates = [
            action("1", "Page$1"),
            action("2", "Page$2"),
            action("3", "Page$3"),
            action("4", "Page$4"),
            action("5", "Page$5"),
            action("...", "Page$1"),
            action(">>", "Page$Last"),
        ]
        self.assertEqual(select_next_pager_action(candidates, 5), candidates[5])

    def test_backward_shifted_ellipsis_is_not_selected_after_later_pages(self):
        candidates = [
            action("2", "Page$2"), action("3", "Page$3"),
            action("4", "Page$4"), action("5", "Page$5"),
            action("...", "Page$6"), action(">>", "Page$Last"),
        ]
        self.assertIsNone(select_next_pager_action(candidates, 7))

    def test_backward_ellipsis_is_not_selected_as_forward(self):
        candidates = [
            action("1", "Page$1"),
            action("2", "Page$2"),
            action("3", "Page$3"),
            action("4", "Page$4"),
            action("5", "Page$5"),
            action("...", "Page$5"),
            action(">>", "Page$Last"),
        ]
        self.assertIsNone(select_next_pager_action(candidates, 10))

    def test_forward_ellipsis_is_selected_when_argument_is_ahead(self):
        candidates = [action("...", "Page$6"), action(">>", "Page$Last")]
        self.assertEqual(select_next_pager_action(candidates, 5), candidates[0])

    def test_forward_ellipsis_advances_but_backward_ellipsis_does_not(self):
        self.assertEqual(advance_page_index(5, "...", "Page$6"), 6)
        self.assertEqual(advance_page_index(7, "...", "Page$6"), 7)

    def test_numeric_page_argument_sets_zero_based_result_page_index(self):
        self.assertEqual(advance_page_index(1, "4", "Page$3"), 3)

    def test_next_action_advances_result_page_index(self):
        self.assertEqual(advance_page_index(4, "Nästa", "Next"), 5)

    def test_next_is_used_but_last_is_never_used_to_skip_pages(self):
        next_action = action("Nästa", "Next")
        candidates = [action("Sista", "Last"), next_action]
        self.assertEqual(select_next_pager_action(candidates, 4), next_action)
        self.assertIsNone(select_next_pager_action([action("Sista", "Last")], 4))


if __name__ == "__main__":
    unittest.main()
