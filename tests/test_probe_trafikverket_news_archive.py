import json
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from scripts.probe_trafikverket_news_archive import collect_county_news_inventory, collect_historical_date_windows, collect_national_news_inventory, diagnose_2024_monthly_repeatability, diagnose_2024_monthly_windows, diagnose_national_pagination, diagnose_national_pagination_boundaries, inspect_county_content_api, inspect_frontend_scripts, inspect_news_archive_api, inspect_news_archive_date_filters, parse_archive


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
    def test_national_inventory_uses_all_counties_and_year_windows(self, mocked_fetch):
        current_year = datetime.now(timezone.utc).year
        responses = []
        for year in range(2024, current_year + 1):
            items = [{"Name": "National story", "Link": f"/story-{year}/", "Date": f"1 jan. {year}"}] if year == 2024 else []
            responses.append((json.dumps({"Items": items, "TotalHits": len(items)}), "https://www.trafikverket.se/api/news"))
        mocked_fetch.side_effect = responses
        result = collect_national_news_inventory(start_year=2024)
        self.assertEqual(result["scope"], "national")
        self.assertIsNone(result["county_filter"])
        self.assertEqual(result["unique_article_count"], 1)
        self.assertTrue(result["complete"])
        self.assertIn("fromDate=2024-01-01", mocked_fetch.call_args_list[0].args[0])
        self.assertNotIn("counties=", mocked_fetch.call_args_list[0].args[0])
        self.assertEqual(mocked_fetch.call_count, current_year - 2024 + 1)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_national_pagination_diagnostic_records_page_specific_totals(self, mocked_fetch):
        mocked_fetch.side_effect = [
            (json.dumps({"Items": [{"Name": "A", "Link": "/a/", "Date": "1 jan. 2025"}], "TotalHits": 721}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [{"Name": "B", "Link": "/b/", "Date": "2 jan. 2025"}], "TotalHits": 120}), "https://www.trafikverket.se/api/news"),
        ]
        result = diagnose_national_pagination(years=(2025,), pages_to_probe=2)
        self.assertEqual(result[0]["reported_total_hits_by_page"], [721, 120])
        self.assertFalse(result[0]["totals_stable"])
        self.assertEqual(result[0]["unique_links_in_probe"], 2)
        self.assertNotIn("counties=", mocked_fetch.call_args_list[0].args[0])

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_2024_monthly_diagnostic_uses_month_date_filters(self, mocked_fetch):
        item_response = (
            json.dumps({"Items": [{"Link": "/example/", "Date": "1 jan. 2024"}], "TotalHits": 1}),
            "https://www.trafikverket.se/api/news",
        )
        empty_response = (
            json.dumps({"Items": [], "TotalHits": 1}),
            "https://www.trafikverket.se/api/news",
        )
        mocked_fetch.side_effect = [response for _ in range(12) for response in (item_response, empty_response)]
        result = diagnose_2024_monthly_windows()
        self.assertEqual(len(result), 12)
        self.assertEqual(result[0]["month"], "2024-01")
        self.assertEqual(result[0]["returned_items"], 1)
        self.assertIn("fromDate=2024-01-01", mocked_fetch.call_args_list[0].args[0])
        self.assertIn("toDate=2024-02-01", mocked_fetch.call_args_list[0].args[0])
        self.assertIn("fromDate=2024-02-01", mocked_fetch.call_args_list[2].args[0])
        self.assertIn("toDate=2024-03-01", mocked_fetch.call_args_list[2].args[0])
        self.assertEqual(mocked_fetch.call_count, 24)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_2024_monthly_repeatability_detects_stable_first_page(self, mocked_fetch):
        response = (json.dumps({"Items": [{"Link": "/same/", "Date": "21 nov. 2024"}], "TotalHits": 39}), "https://www.trafikverket.se/api/news")
        mocked_fetch.return_value = response
        result = diagnose_2024_monthly_repeatability(repeats=2)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["totals_stable"])
        self.assertTrue(result[0]["first_page_links_stable"])
        self.assertEqual(mocked_fetch.call_count, 4)

    @patch("scripts.probe_trafikverket_news_archive.fetch")
    def test_national_boundary_diagnostic_probes_requested_pages(self, mocked_fetch):
        mocked_fetch.side_effect = [
            (json.dumps({"Items": [{"Link": "/a/", "Date": "1 jan. 2025"}], "TotalHits": 721}), "https://www.trafikverket.se/api/news"),
            (json.dumps({"Items": [{"Link": "/a/", "Date": "1 jan. 2025"}], "TotalHits": 120}), "https://www.trafikverket.se/api/news"),
        ]
        result = diagnose_national_pagination_boundaries(page_map={2025: (12, 13)})
        self.assertEqual(result[0]["requested_pages"], [12, 13])
        self.assertEqual(result[0]["reported_total_hits_by_page"], [721, 120])
        self.assertEqual(result[0]["duplicate_links"], 1)
        self.assertIn("currentPage=12", mocked_fetch.call_args_list[0].args[0])
        self.assertNotIn("counties=", mocked_fetch.call_args_list[0].args[0])

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
