from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collect_samrad import PAGE_SIZE, query_envelope, query_params, fetch_layer, filter_to_radius  # noqa: E402


class FakeResponse:
    def __init__(self, payload, url="https://example.test/query"):
        self.payload = payload
        self.url = url
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []
    def get(self, url, params, timeout, headers):
        self.calls.append(params)
        return FakeResponse(self.payloads.pop(0), url)


def feature(oid, lon=19.66455, lat=63.74646):
    return {
        "type": "Feature", "id": oid,
        "properties": {"ObjectId": oid, "Beteckn": f"S {oid}-2026", "UUID": f"uuid-{oid}"},
        "geometry": {"type": "Point", "coordinates": [lon, lat]}
    }


class SamradCollectorTests(unittest.TestCase):
    def test_query_envelope_contains_area_center(self):
        env = query_envelope(63.74646, 19.66455, 10000)
        self.assertLess(env["xmin"], 19.66455)
        self.assertGreater(env["xmax"], 19.66455)
        self.assertLess(env["ymin"], 63.74646)
        self.assertGreater(env["ymax"], 63.74646)

    def test_query_params_are_ordered_and_paged(self):
        params = query_params({"xmin": 1, "ymin": 2, "xmax": 3, "ymax": 4}, 600)
        self.assertEqual(params["resultOffset"], "600")
        self.assertEqual(params["resultRecordCount"], str(PAGE_SIZE))
        self.assertEqual(params["orderByFields"], "ObjectId")

    def test_fetch_layer_reads_multiple_pages_and_deduplicates(self):
        first = [feature(i) for i in range(PAGE_SIZE)]
        second = [feature(PAGE_SIZE), feature(PAGE_SIZE + 1)]
        session = FakeSession([{"features": first, "exceededTransferLimit": True},
                               {"features": second, "exceededTransferLimit": False}])
        result = fetch_layer(session, "points", "https://example.test/query", {"xmin": 19, "ymin": 63, "xmax": 20, "ymax": 64})
        self.assertEqual(result["records_fetched"], PAGE_SIZE + 2)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[1]["resultOffset"], str(PAGE_SIZE))

    def test_fetch_layer_rejects_page_without_stable_id(self):
        session = FakeSession([{"features": [{"type": "Feature", "properties": {}, "geometry": None}]}])
        with self.assertRaises(RuntimeError):
            fetch_layer(session, "points", "https://example.test/query", {"xmin": 19, "ymin": 63, "xmax": 20, "ymax": 64})

    def test_filter_to_radius_keeps_only_intersecting_features(self):
        collection = {"features": [feature(1), feature(2, lon=20.5, lat=64.5)]}
        result = filter_to_radius(collection, 63.74646, 19.66455, 10000)
        self.assertEqual([f["id"] for f in result["features"]], [1])
        self.assertEqual(result["records_in_scope"], 1)


if __name__ == "__main__":
    unittest.main()
