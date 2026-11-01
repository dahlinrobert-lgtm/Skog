"""Unit tests for diary pagination parsing and safety checks."""
import re
import unittest


def parse_total(text):
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


def is_forward_page_argument(argument, current_page, label=""):
    page_match = re.fullmatch(r"Page\$(\d+)", argument, re.I)
    if page_match:
        return int(page_match.group(1)) > current_page
    return argument.isdigit() and int(argument) > current_page




def select_next_pager_action(candidates, current_page_index):
    """Select the next action from a sliding ASP.NET GridView pager."""
    numeric = []
    for item in candidates:
        match = re.fullmatch(r"Page\$(\d+)", item["argument"], re.I)
        if match and int(match.group(1)) > current_page_index + 1:
            numeric.append((int(match.group(1)), item))
    if numeric:
        return min(numeric, key=lambda pair: pair[0])[1]
    # In this portal, the ellipsis's Page$1 command advances the pager window.
    for item in candidates:
        if item["argument"].casefold() == "page$1" and item["label"] in {"...", "…"}:
            return item
    for item in candidates:
        if item["argument"].casefold() in {"last", "page$last"}:
            return item
    for item in candidates:
        if item["argument"].casefold() in {"next", "page$next"}:
            return item
    return None


def parse_search_terms(primary, extras=""):
    terms = []
    for candidate in [primary, *re.split(r"[,;\n\r]+", extras or "")]:
        term = candidate.strip()
        if term and term.casefold() not in {v.casefold() for v in terms}:
            terms.append(term)
    if not terms:
        raise ValueError("At least one non-empty search term is required")
    if any(len(term) < 2 for term in terms) or len(terms) > 10:
        raise ValueError("Invalid search-term count or length")
    return terms


class DiaryPaginationSafetyTests(unittest.TestCase):
    def test_parse_total_extracts_source_reported_total(self):
        self.assertEqual(parse_total("Sökresultat: 1–50 av 253"), 253)

    def test_parse_total_zero(self):
        self.assertEqual(parse_total("Sökresultat: 0 av 0"), 0)

    def test_parse_total_unknown(self):
        self.assertIsNone(parse_total("Sökresultat visas nedan"))

    def test_water_query_has_six_terms(self):
        terms = parse_search_terms(
            "vattenverksamhet",
            "markavvattning\ndikesrensning\ntrumma\nvåtmarksanläggning\nomgrävning av vattendrag",
        )
        self.assertEqual(len(terms), 6)

    def test_forward_pager_ellipsis_is_recognized(self):
        self.assertTrue(is_forward_page_argument("Page$7", 6, "..."))

    def test_numeric_current_page_is_not_forward(self):
        self.assertFalse(is_forward_page_argument("6", 6, "6"))

    def test_numeric_later_page_is_forward(self):
        self.assertTrue(is_forward_page_argument("7", 6, "7"))

    def test_current_page_argument_is_not_forward(self):
        self.assertFalse(is_forward_page_argument("Page$6", 6, "6"))

    def test_later_webforms_page_argument_is_forward(self):
        self.assertTrue(is_forward_page_argument("Page$7", 6, "7"))

    def test_non_numeric_page_argument_is_not_forward(self):
        self.assertFalse(is_forward_page_argument("Page$Next", 6, "next"))


    def test_sliding_window_ellipsis_page_one_is_continuation(self):
        candidates = [
            {"label": "<<", "argument": "Page$First"},
            {"label": "...", "argument": "Page$1"},
            {"label": "2", "argument": "Page$2"},
            {"label": "3", "argument": "Page$3"},
            {"label": "6", "argument": "Page$6"},
        ]
        selected = select_next_pager_action(candidates, 6)
        self.assertEqual(selected["label"], "...")

    def test_next_numeric_page_in_window_is_selected(self):
        candidates = [
            {"label": "4", "argument": "Page$4"},
            {"label": "5", "argument": "Page$5"},
            {"label": "6", "argument": "Page$6"},
        ]
        selected = select_next_pager_action(candidates, 2)
        self.assertEqual(selected["argument"], "Page$4")

    def test_first_page_link_is_not_selected_as_forward(self):
        candidates = [{"label": "<<", "argument": "Page$First"}]
        self.assertIsNone(select_next_pager_action(candidates, 6))

    def test_no_continuation_when_only_current_and_previous_pages(self):
        candidates = [
            {"label": "1", "argument": "Page$1"},
            {"label": "2", "argument": "Page$2"},
            {"label": "3", "argument": "Page$3"},
        ]
        self.assertIsNone(select_next_pager_action(candidates, 3))

    def test_webforms_javascript_postback_href_is_parsed(self):
        href = "javascript:__doPostBack('ctl00$SearchPlaceHolder$caseGridView','Page$2')"
        match = re.search(
            r"""__doPostBack\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\)""",
            href,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.groups(), (
            "ctl00$SearchPlaceHolder$caseGridView",
            "Page$2",
        ))

    def test_webforms_page_three_postback_is_parsed(self):
        href = "javascript:__doPostBack('ctl00$SearchPlaceHolder$caseGridView','Page$3')"
        match = re.search(
            r"""__doPostBack\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\)""",
            href,
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.group(2), "Page$3")


if __name__ == "__main__":
    unittest.main()
