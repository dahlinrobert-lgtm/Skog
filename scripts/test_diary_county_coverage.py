#!/usr/bin/env python3
"""Regression tests for the production all-county coverage validation helper."""
from __future__ import annotations

import unittest

from scripts.lansstyrelsen_diary_validation import summarize_county_coverage


class AllCountyCoverageTests(unittest.TestCase):
    def counties(self):
        return [f"County {i}" for i in range(21)]

    def queries(self, counties):
        return [
            {"requested_county": county, "request_ok": True, "total_reconciled": True}
            for county in counties
        ]

    def test_all_21_counties_with_validated_queries_pass(self):
        counties = self.counties()
        result = summarize_county_coverage(counties, self.queries(counties), is_all_counties=True)
        self.assertTrue(result["county_coverage_ok"])
        self.assertEqual(result["completed_counties"], 21)
        self.assertEqual(result["failed_counties"], [])

    def test_missing_county_query_fails(self):
        counties = self.counties()
        result = summarize_county_coverage(counties, self.queries(counties[:-1]), is_all_counties=True)
        self.assertFalse(result["county_coverage_ok"])
        self.assertEqual(result["completed_counties"], 20)
        self.assertEqual(result["failed_counties"], [counties[-1]])

    def test_unreconciled_county_query_fails(self):
        counties = self.counties()
        queries = self.queries(counties)
        queries[8]["total_reconciled"] = False
        result = summarize_county_coverage(counties, queries, is_all_counties=True)
        self.assertFalse(result["county_coverage_ok"])
        self.assertIn(counties[8], result["failed_counties"])

    def test_duplicate_county_label_fails(self):
        counties = self.counties()
        counties[-1] = counties[0]
        result = summarize_county_coverage(counties, self.queries(counties), is_all_counties=True)
        self.assertFalse(result["county_coverage_ok"])

    def test_single_county_mode_does_not_require_21_counties(self):
        counties = ["County X"]
        result = summarize_county_coverage(counties, self.queries(counties), is_all_counties=False)
        self.assertTrue(result["county_coverage_ok"])
        self.assertEqual(result["expected_county_count"], 1)


if __name__ == "__main__":
    unittest.main()
