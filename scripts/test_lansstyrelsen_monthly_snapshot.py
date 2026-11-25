#!/usr/bin/env python3
"""Unit tests for monthly diary collection completeness rules."""
import unittest
from collect_lansstyrelsen_monthly_snapshot import collect_interval, select_county_and_wait

class MonthlySearchRuleTests(unittest.TestCase):
    def test_county_selection_waits_for_navigation_and_verifies_selection(self):
        from unittest.mock import Mock
        page = Mock()
        page.locator.return_value.inner_text.return_value = "Länsstyrelsen i Norrbottens län"
        select_county_and_wait(page, "Länsstyrelsen i Norrbottens län", "17")
        page.expect_navigation.assert_called_once_with(
            wait_until="domcontentloaded", timeout=15000
        )
        page.locator.return_value.select_option.assert_called_once_with(value="17")

    def test_county_selection_rejects_lost_selection(self):
        from unittest.mock import Mock
        page = Mock()
        page.locator.return_value.inner_text.return_value = "Alla län"
        with self.assertRaisesRegex(RuntimeError, "was not retained"):
            select_county_and_wait(page, "Länsstyrelsen i Norrbottens län", "17")

    def test_month_end_dates(self):
        import calendar
        self.assertEqual(calendar.monthrange(2025,2)[1],28)
        self.assertEqual(calendar.monthrange(2024,2)[1],29)

if __name__=="__main__": unittest.main()
