"""Unit tests for the diary result pager helpers."""
import unittest

from scripts.search_lansstyrelsen_diary_browser import parse_search_terms, parse_total


class DiaryPaginationSafetyTests(unittest.TestCase):
    def test_parse_total_extracts_source_reported_total(self):
        self.assertEqual(parse_total("Sökresultat: 1–50 av 253"), 253)

    def test_parse_total_zero(self):
        self.assertEqual(parse_total("Sökresultat: 0 av 0"), 0)

    def test_parse_search_terms_retains_six_water_phrases(self):
        terms = parse_search_terms(
            "vattenverksamhet",
            "markavvattning\ndikesrensning\ntrumma\nvåtmarksanläggning\nomgrävning av vattendrag",
        )
        self.assertEqual(len(terms), 6)
        self.assertEqual(terms[-1], "omgrävning av vattendrag")

    def test_parse_total_does_not_invent_unknown_total(self):
        self.assertIsNone(parse_total("Sökresultat visas nedan"))


if __name__ == "__main__":
    unittest.main()
