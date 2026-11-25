#!/usr/bin/env python3
"""Unit tests for monthly diary collection completeness rules."""
import unittest
from unittest.mock import Mock

from collect_lansstyrelsen_monthly_snapshot import (
    collect_interval,
    select_county_and_wait,
    build_repeated_page_diagnostic,
)


class MonthlySearchRuleTests(unittest.TestCase):
    def _page(self, selected_county):
        page = Mock()
        navigation = Mock()
        navigation.__enter__ = Mock(return_value=None)
        navigation.__exit__ = Mock(return_value=False)
        page.expect_navigation.return_value = navigation

        county_locator = Mock()
        county_locator.inner_text.return_value = selected_county
        title_locator = Mock()
        page.locator.side_effect = lambda selector: (
            county_locator if selector.startswith("#SearchPlaceHolder_CaseSearch_ddDiaryID")
            else title_locator
        )
        return page, navigation, county_locator

    def test_county_selection_waits_for_navigation_and_verifies_selection(self):
        page, navigation, county_locator = self._page(
            "Länsstyrelsen i Norrbottens län"
        )

        select_county_and_wait(
            page, "Länsstyrelsen i Norrbottens län", "17"
        )

        page.expect_navigation.assert_called_once_with(
            wait_until="domcontentloaded", timeout=15000
        )
        navigation.__enter__.assert_called_once()
        navigation.__exit__.assert_called_once()
        county_locator.select_option.assert_called_once_with(value="17")

    def test_county_selection_rejects_lost_selection(self):
        page, _, county_locator = self._page("Alla län")

        with self.assertRaisesRegex(RuntimeError, "was not retained"):
            select_county_and_wait(
                page, "Länsstyrelsen i Norrbottens län", "17"
            )


    def test_repeated_page_diagnostic_preserves_pager_and_truncation_metadata(self):
        diagnostic = build_repeated_page_diagnostic(
            7, ("123-2026", "456-2026"),
            ["123-2026 Första ärendet", "456-2026 Andra ärendet"],
            "1 2 3 ...", "<tr>" + ("x" * 12010) + "</tr>",
            "body excerpt",
        )
        self.assertEqual(diagnostic["page_number"], 7)
        self.assertEqual(diagnostic["diary_numbers"], ["123-2026", "456-2026"])
        self.assertEqual(len(diagnostic["pager_html"]), 12000)
        self.assertTrue(diagnostic["pager_html_truncated"])
        self.assertEqual(diagnostic["pager_html_original_length"], 12019)
        self.assertEqual(diagnostic["body_text_excerpt"], "body excerpt")

    def test_month_end_dates(self):
        import calendar

        self.assertEqual(calendar.monthrange(2025, 2)[1], 28)
        self.assertEqual(calendar.monthrange(2024, 2)[1], 29)


if __name__ == "__main__":
    unittest.main()
