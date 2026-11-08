import json
import unittest
from unittest.mock import patch

from scripts.probe_trafikverket_news_archive import inspect_county_content_api, inspect_frontend_scripts, parse_archive


class TrafikverketArchiveParserTests(unittest.TestCase):
    def test_frontend_inspector_ignores_inline_excerpt_objects(self):
        result = inspect_frontend_scripts([{"inline_excerpt": "county news"}])
        self.assertEqual(len(result), 1)
        self.assertIn("runtime_chunk_map_diagnostic", result[0])
        self.assertFalse(result[0]["runtime_chunk_map_diagnostic"]["runtime_found"])

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
