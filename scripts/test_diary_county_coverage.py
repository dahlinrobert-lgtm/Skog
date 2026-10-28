#!/usr/bin/env python3
"""Regression tests for validating all-county diary search coverage."""
from __future__ import annotations

import unittest


def summarize_county_coverage(counties, queries, is_all_counties=True):
    """Small pure helper mirroring the batch workflow's coverage contract."""
    labels = list(counties)
    expected = 21 if is_all_counties else len(labels)
    summaries = []
    for county in labels:
        matching = [q for q in queries if q.get("requested_county") == county]
        summaries.append({
            "county": county,
            "query_count": len(matching),
            "successful_queries": sum(bool(q.get("request_ok") and q.get("total_reconciled")) for q in matching),
            "failed_queries": sum(not (q.get("request_ok") and q.get("total_reconciled")) for q in matching),
        })
    completed = sum(
        row["query_count"] > 0 and row["failed_queries"] == 0
        for row in summaries
    )
    failed = [row["county"] for row in summaries if row["query_count"] == 0 or row["failed_queries"] > 0]
    coverage_ok = (
        (len(labels) == expected and len(set(labels)) == expected)
        and completed == expected
        and not failed
        and all(q.get("request_ok") and q.get("total_reconciled") for q in queries)
    )
    return {"expected": expected, "completed": completed, "failed": failed, "ok": coverage_ok}


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
        result = summarize_county_coverage(counties, self.queries(counties))
        self.assertTrue(result["ok"])
        self.assertEqual(result["completed"], 21)
        self.assertEqual(result["failed"], [])

    def test_missing_county_query_fails(self):
        counties = self.counties()
        result = summarize_county_coverage(counties, self.queries(counties[:-1]))
        self.assertFalse(result["ok"])
        self.assertEqual(result["completed"], 20)
        self.assertEqual(result["failed"], [counties[-1]])

    def test_unreconciled_county_query_fails(self):
        counties = self.counties()
        queries = self.queries(counties)
        queries[8]["total_reconciled"] = False
        result = summarize_county_coverage(counties, queries)
        self.assertFalse(result["ok"])
        self.assertIn(counties[8], result["failed"])

    def test_duplicate_county_label_fails(self):
        counties = self.counties()
        counties[-1] = counties[0]
        result = summarize_county_coverage(counties, self.queries(counties))
        self.assertFalse(result["ok"])

    def test_single_county_mode_does_not_require_21_counties(self):
        counties = ["County X"]
        result = summarize_county_coverage(counties, self.queries(counties), is_all_counties=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["expected"], 1)


if __name__ == "__main__":
    unittest.main()
