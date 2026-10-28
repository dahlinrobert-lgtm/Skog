#!/usr/bin/env python3
"""Regression tests for Länsstyrelsen diary response validation."""

from __future__ import annotations

import unittest

from scripts.lansstyrelsen_diary_validation import has_explicit_zero_results


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


if __name__ == "__main__":
    unittest.main()
