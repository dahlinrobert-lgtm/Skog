import json
import unittest
from unittest.mock import patch

from scripts.probe_trafikverket_news_archive import collect_county_news_inventory, collect_historical_date_windows, inspect_county_content_api, inspect_frontend_scripts, inspect_news_archive_api, inspect_news_archive_date_filters, parse_archive


class TrafikverketArchiveParserTests(unittest.TestCase):
    def test_frontend_inspector_ignores_inline_excerpt_objects(self):
        result = inspect_frontend_scripts([{"inline_excerpt": "county news"}])
        self.assertEqual(len(result), 1)
        self.assertIn("runtime_chunk_map_diagnostic", result[0])
        self.assertFalse(result[0]["runtime_chunk_map_diagnostic"]["runtime_found"])


    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_historical_windows_paginate_to_reported_total(self, mocked_fetch):
        mocked_fetch.side_effect = [
            (json.dumps({"Items": [], "TotalHits": 0}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [], "TotalHits": 0}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [], "TotalHits": 0}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [], "TotalHits": 0}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [], "TotalHits": 0}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [], "TotalHits": 0}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [{"Name": "Recent", "Link": "/recent/", "Date": "14 nov. 2024"}], "TotalHits": 1}), "https://www.trafikverket.se/api/news"),
        ]
        result = collect_historical_date_windows()
        self.assertEqual(len(result), 7)
        self.assertTrue(all(item["complete_against_reported_total"] for item in result))
        self.assertIn("fromDate=2000-01-01", result[0]["pages_fetched"][0]["url"])
        self.assertIn("toDate=2009-12-31", result[0]["pages_fetched"][0]["url"])
        self.assertEqual(mocked_fetch.call_count, 7)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_full_inventory_paginates_and_deduplicates(self, mocked_fetch):
        responses = [
            (json.dumps({"Items": [
                {"Name": "A", "Link": "/a/", "Date": "1 jan. 2024"},
                {"Name": "B", "Link": "/b/", "Date": "2 jan. 2024"},
            ], "TotalHits": 3}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [
                {"Name": "B duplicate", "Link": "/b/", "Date": "2 jan. 2024"},
            ], "TotalHits": 3}), "https://www.trafikverket.se/api/news"),
        ]
        mocked_fetch.side_effect = responses
        result = collect_county_news_inventory(page_size=2)
        self.assertEqual(result["reported_total_hits"], 3)
        self.assertEqual(result["raw_items_count"], 3)
        self.assertEqual(result["unique_article_count"], 2)
        self.assertEqual(result["duplicate_count"], 1)
        self.assertTrue(result["complete_against_reported_total"])
        self.assertEqual(mocked_fetch.call_count, 2)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_news_archive_api_uses_county_and_page_parameters(self, mocked_fetch):
        mocked_fetch.return_value = (
            json.dumps({"Items": [{"Name": "Test", "Link": "/test/"}], "TotalHits": 67}),
            "https://www.trafikverket.se/api/news",
        )
        result = inspect_news_archive_api()
        self.assertEqual(len(result), 2)
        self.assertEqual([item["total_hits"] for item in result], [67, 67])
        self.assertIn("counties=18", result[0]["url"])
        self.assertIn("currentPage=1", result[0]["url"])
        self.assertIn("currentPage=2", result[1]["url"])
        self.assertEqual(mocked_fetch.call_count, 2)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_date_filter_probe_tests_historical_and_control_windows(self, mocked_fetch):
        mocked_fetch.return_value = (
            json.dumps({"Items": [{"Name": "Test", "Link": "/test/", "Date": "14 nov. 2024"}], "TotalHits": 1}),
            "https://www.trafikverket.se/api/news",
        )
        result = inspect_news_archive_date_filters()
        self.assertEqual(len(result), 5)
        self.assertTrue(all(item["status"] == "ok" for item in result))
        self.assertIn("fromDate=2020-01-01", result[0]["url"])
        self.assertIn("toDate=2024-12-31", result[0]["url"])
        self.assertIn("counties=18", result[0]["url"])
        self.assertEqual(mocked_fetch.call_count, 5)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_county_content_api_uses_bounded_sizes(self, mocked_fetch):
        mocked_fetch.return_value = (
            json.dumps({"pages": [{"title": "Test", "url": "/test/"}]}),
            "https://www.trafikverket.se/api/PageListApi/GetCurrentCountyContent",
        )
        result = inspect_county_content_api()
        self.assertEqual(len(result), 3)
        self.assertEqual([item["pages_count"] for item in result], [1, 1, 1])
        self.assertIn("countyid=18", result[0]["url"])
        self.assertIn("pageSize=10", result[0]["url"])
        self.assertEqual(mocked_fetch.call_count, 3)

    def test_extracts_count_links_and_paging(self):
        html = """
        <html><body>
          <p>Visar 1 - 10 av 67 nyheter</p>
          <a href="/om-oss/nyheter/lansnyheter/vasterbotten/2024/exempel/">Exempel</a>
          <a href="?county=18&page=2">Nästa sida</a>
          <form action="/om-oss/nyheter/"><input name="county" value="18"></form>
        </body></html>
        """
        result = parse_archive(html)
        self.assertEqual(result["archive_count"], 67)
        self.assertEqual(len(result["news_links"]), 1)
        self.assertEqual(len(result["pagination_links"]), 1)
        self.assertEqual(result["forms"][0]["inputs"][0]["name"], "county")


if __name__ == "__main__":
    unittest.main()
