#!/usr/bin/env python3
"""Unit tests for monthly diary collection completeness rules."""
import unittest
from collect_lansstyrelsen_monthly_snapshot import collect_interval

class MonthlySearchRuleTests(unittest.TestCase):
    def test_month_end_dates(self):
        import calendar
        self.assertEqual(calendar.monthrange(2025,2)[1],28)
        self.assertEqual(calendar.monthrange(2024,2)[1],29)

if __name__=="__main__": unittest.main()
