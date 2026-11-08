import unittest
from unittest.mock import patch

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scripts.collect_lansstyrelsen_case_handlings import build_coverage_summary, goto_with_retries


class Response:
    def __init__(self, status):
        self.status = status


class FakePage:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def goto(self, *args, **kwargs):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return Response(outcome)


class RetryTests(unittest.TestCase):
    def test_coverage_summary_reports_national_and_county_progress(self):
        targets = [
            {"diary": "Länsstyrelsen i Norrbottens län", "diary_number": "1-2026"},
            {"diary": "Länsstyrelsen i Norrbottens län", "diary_number": "2-2026"},
            {"diary": "Länsstyrelsen i Västerbottens län", "diary_number": "3-2026"},
        ]
        cases = {
            "länsstyrelsen i norrbottens län::1-2026": {},
            "länsstyrelsen i västerbottens län::3-2026": {},
        }
        coverage = build_coverage_summary(targets, cases)
        self.assertEqual(coverage["eligible_case_count"], 3)
        self.assertEqual(coverage["observed_case_count"], 2)
        self.assertEqual(coverage["unobserved_case_count"], 1)
        self.assertEqual(coverage["coverage_percent"], 66.67)
        norrbotten = next(x for x in coverage["by_county"] if x["county"].endswith("Norrbottens län"))
        self.assertEqual(norrbotten["observed_case_count"], 1)
        self.assertEqual(norrbotten["unobserved_case_count"], 1)

    @patch("scripts.collect_lansstyrelsen_case_handlings.time.sleep")
    def test_retries_server_error_then_succeeds(self, sleep):
        page = FakePage([500, 503, 200])
        response, attempts = goto_with_retries(page, "https://example.test/case")
        self.assertEqual(response.status, 200)
        self.assertEqual(attempts, 3)
        self.assertEqual(page.calls, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("scripts.collect_lansstyrelsen_case_handlings.time.sleep")
    def test_does_not_retry_permanent_client_error(self, sleep):
        page = FakePage([404, 200])
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            goto_with_retries(page, "https://example.test/case")
        self.assertEqual(page.calls, 1)
        sleep.assert_not_called()

    @patch("scripts.collect_lansstyrelsen_case_handlings.time.sleep")
    def test_timeout_is_retried(self, sleep):
        page = FakePage([PlaywrightTimeoutError("timeout"), 200])
        response, attempts = goto_with_retries(page, "https://example.test/case")
        self.assertEqual(response.status, 200)
        self.assertEqual(attempts, 2)


if __name__ == "__main__":
    unittest.main()
