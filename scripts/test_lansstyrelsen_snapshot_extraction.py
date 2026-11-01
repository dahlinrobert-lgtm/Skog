#!/usr/bin/env python3
"""Unit tests for Länsstyrelsen snapshot row extraction."""
from __future__ import annotations
import unittest
from search_lansstyrelsen_diary_browser import clean, parse_total, extract_grid

class _Cell:
    def __init__(self, value): self.value=value
    def inner_text(self): return self.value
    def get_attribute(self, name): return None

class _Cells:
    def __init__(self, values): self.values=values
    def all_inner_texts(self): return self.values

class _Row:
    def __init__(self, values, visible=True): self.values=values; self.visible=visible
    def is_visible(self): return self.visible
    def locator(self, selector):
        if selector == "th, td": return _Cells(self.values)
        if selector == "a": return _List([])
        raise AssertionError(selector)

class _List:
    def __init__(self, items): self.items=items
    def count(self): return len(self.items)
    def nth(self,index): return self.items[index]
    def all_inner_texts(self): return [x.inner_text() for x in self.items]
    @property
    def last(self): return self.items[-1]

class _Grid:
    def __init__(self, rows): self.rows=rows
    def locator(self, selector):
        if selector == "tr": return _List(self.rows)
        raise AssertionError(selector)

class _Page:
    def __init__(self, rows): self.grid=_Grid(rows)
    def locator(self, selector):
        if selector == "#SearchPlaceHolder_caseGridView": return self.grid
        raise AssertionError(selector)

class SnapshotGridExtractionTests(unittest.TestCase):
    def test_extracts_first_column_diary_id_not_text_regex_of_whole_row(self):
        page=_Page([
            _Row(["Diarienummer","Status","In/Upp-datum","Ärenderubrik"]),
            _Row(["1234-2026","Handläggning","2026-10-04","Text"]),
            _Row(["9876-2025","Avslutat","2025-05-03","Text"]),
            _Row(["not-a-case","", "", ""]),
        ])
        seen=set()
        records,diag=extract_grid(page,1,seen)
        self.assertEqual([r["diary_number"] for r in records],["1234-2026","9876-2025"])
        self.assertEqual(diag["result_rows_extracted"],2)

    def test_skips_duplicate_diary_id_across_pages(self):
        page=_Page([
            _Row(["Diarienummer","Status"]),
            _Row(["1234-2026","Handläggning"]),
        ])
        records,diag=extract_grid(page,2,{"1234-2026"})
        self.assertEqual(records,[])
        self.assertEqual(diag["result_rows_extracted"],0)

    def test_source_total_parser(self):
        self.assertEqual(parse_total("Sökresultat: 1–50 av 253"),253)
        self.assertEqual(parse_total("Sökresultat: 0 av 0"),0)

if __name__ == "__main__":
    unittest.main()
