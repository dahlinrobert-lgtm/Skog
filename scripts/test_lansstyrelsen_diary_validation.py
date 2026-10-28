#!/usr/bin/env python3
"""Regression tests for Länsstyrelsen diary response validation."""

from __future__ import annotations

import unittest

from scripts.lansstyrelsen_diary_validation import has_explicit_zero_results, resolve_county_labels


class ExplicitZeroResultTests(unittest.TestCase):
    def test_accepts_standard_zero_result_message(self):
        self.assertTrue(has_explicit_zero_results("Diarium för länet\nSökresultat: 0"))

    def test_accepts_nonbreaking_space_from_portal(self):
        self.assertTrue(has_explicit_zero_results("Diarium för länet\nSökresultat:\u00a00"))

    def test_does_not_confuse_nonzero_results_with_zero(self):
        self.assertFalse(has_explicit_zero_results("Sökresultat: 10"))

    def test_requires_explicit_result_count(self):
        self.assertFalse(has_explicit_zero_results("Sökningen avslutades utan resultatgrid"))
        self.assertFalse(has_explicit_zero_results("Antal ärenden: 0"))


class CountyOptionValidationTests(unittest.TestCase):
    def make_options(self, count=21):
        return [
            {"label": f"Länsstyrelsen i testlän {i} län", "value": str(i + 1)}
            for i in range(count)
        ]

    def test_accepts_exactly_21_individual_county_options(self):
        labels = resolve_county_labels(self.make_options())
        self.assertEqual(len(labels), 21)

    def test_rejects_incomplete_county_list(self):
        with self.assertRaisesRegex(ValueError, "Expected 21"):
            resolve_county_labels(self.make_options(20))

    def test_ignores_aggregate_and_placeholder_options(self):
        options = self.make_options()
        options.extend([
            {"label": "Alla län", "value": "0"},
            {"label": "Välj diarium", "value": "-1"},
        ])
        self.assertEqual(len(resolve_county_labels(options)), 21)

    def test_rejects_duplicate_county_labels(self):
        options = self.make_options()
        options[-1] = dict(options[0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            resolve_county_labels(options)


if __name__ == "__main__":
    unittest.main()
