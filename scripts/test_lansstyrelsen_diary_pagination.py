"""Unit tests for the diary result pager helpers without browser dependencies."""
import unittest


def parse_total(text):
    import re
    patterns = (
        r"Sökresultat\s*:?\s*[\d\s–-]+\s+av\s+(\d+)",
        r"\b(?:träffar|ärenden)\s*:?\s*(\d+)\b",
        r"\bantal\s+(?:träffar|ärenden)\s*:?\s*(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


def parse_search_terms(primary, extras=""):
    import re
    terms = []
    for candidate in [primary, *re.split(r"[,;\n\r]+", extras or "")]:
        term = candidate.strip()
        if term and term.casefold() not in {existing.casefold() for existing in terms}:
            terms.append(term)
    if not terms:
        raise ValueError("At least one non-empty search term is required")
    if any(len(term) < 2 for term in terms):
        raise ValueError("Search terms must contain at least two characters")
    if len(terms) > 10:
        raise ValueError("A maximum of 10 search terms can be searched in one batch")
    return terms


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
