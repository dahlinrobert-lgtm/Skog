import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from scripts import ingest_police_events


class AdaptivePolicePaginationTests(unittest.TestCase):
    def test_full_fetch_restarts_with_smaller_limit_after_http_400(self):
        calls = []

        def page(page_number, limit):
            calls.append((page_number, limit))
            if limit == 100 and page_number == 2:
                response = requests.Response()
                response.status_code = 400
                raise requests.HTTPError("400 Client Error", response=response)
            event_id = f"{limit}-{page_number}"
            return {
                "data": [{"id": event_id, "pubdate_iso8601": "2026-01-01T12:00:00Z"}],
                "links": {"last_page": 2},
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch.object(ingest_police_events, "DATA", root),
                patch.object(ingest_police_events, "EVENTS", root / "events.csv"),
                patch.object(ingest_police_events, "WILDLIFE", root / "wildlife.csv"),
                patch.object(ingest_police_events, "get_page", side_effect=page),
                patch.object(ingest_police_events.time, "sleep"),
            ):
                ingest_police_events.collect(
                    full=True, max_pages=100, limit=100, sleep_seconds=0,
                    raw_path=root / "raw.jsonl",
                )

            with (root / "events.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            raw_lines = (root / "raw.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertEqual(calls, [(1, 100), (2, 100), (1, 50), (2, 50)])
        # The first 100-limit attempt is retained as an observed version. The
        # second attempt contributes two different IDs, while the repeated
        # 100-1 payload hash is not appended again.
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            {row["event_id"] for row in rows}, {"100-1", "50-1", "50-2"}
        )
        self.assertEqual(len(raw_lines), 3)


if __name__ == "__main__":
    unittest.main()
