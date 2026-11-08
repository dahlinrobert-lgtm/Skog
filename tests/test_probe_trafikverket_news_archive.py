import unittest

from scripts.probe_trafikverket_news_archive import inspect_frontend_scripts, parse_archive


class TrafikverketArchiveParserTests(unittest.TestCase):
    def test_frontend_inspector_ignores_inline_excerpt_objects(self):
        self.assertEqual(inspect_frontend_scripts([{"inline_excerpt": "county news"}]), [])

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
