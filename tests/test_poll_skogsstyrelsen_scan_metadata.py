import unittest
from unittest.mock import Mock

from scripts.poll_skogsstyrelsen_scan_metadata import request_json


class PollSkogsstyrelsenScanMetadataTests(unittest.TestCase):
    def test_post_sends_large_query_parameters_as_form_data(self):
        session = Mock()
        response = Mock()
        response.json.return_value = {"features": []}
        session.post.return_value = response

        result = request_json(
            session,
            "https://example.test/MapServer/0/query",
            {"f": "json", "objectIds": ",".join(str(i) for i in range(500))},
            method="POST",
        )

        self.assertEqual(result, {"features": []})
        session.post.assert_called_once()
        kwargs = session.post.call_args.kwargs
        self.assertIn("data", kwargs)
        self.assertNotIn("params", kwargs)
        self.assertEqual(kwargs["timeout"], (30, 180))
        session.get.assert_not_called()

    def test_get_remains_default_for_metadata_and_id_queries(self):
        session = Mock()
        response = Mock()
        response.json.return_value = {"objectIds": [1, 2]}
        session.get.return_value = response

        result = request_json(session, "https://example.test/MapServer/0", {"f": "json"})

        self.assertEqual(result, {"objectIds": [1, 2]})
        session.get.assert_called_once()
        self.assertEqual(session.get.call_args.kwargs["params"], {"f": "json"})
        session.post.assert_not_called()

    def test_rejects_unsupported_http_method(self):
        with self.assertRaises(ValueError):
            request_json(Mock(), "https://example.test/query", {}, method="PUT")


if __name__ == "__main__":
    unittest.main()
