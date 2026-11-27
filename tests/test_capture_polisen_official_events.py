import unittest

from scripts.capture_polisen_official_events import build_snapshot, validate_payload


class PoliceOfficialApiSnapshotTests(unittest.TestCase):
    def test_build_snapshot_preserves_records_and_counts_norrbotten(self):
        records = [
            {
                "id": 101, "datetime": "2026-11-27 10:00:00 +01:00",
                "name": "Trafikolycka, Luleå", "type": "Trafikolycka",
                "location": {"name": "Norrbottens län", "gps": "66.83,20.40"},
            },
            {
                "id": 102, "datetime": "2026-11-27 10:01:00 +01:00",
                "name": "Brand, Umeå", "type": "Brand",
                "location": {"name": "Västerbottens län", "gps": "65.33,16.51"},
            },
        ]
        snapshot = build_snapshot(records, "2026-11-27T10:05:00+00:00", "https://polisen.se/api/events")
        self.assertEqual(snapshot["record_count"], 2)
        self.assertEqual(snapshot["norrbotten_record_count"], 1)
        self.assertEqual(snapshot["records"], records)

    def test_empty_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_payload([])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_payload([{"id": 1}, {"id": 1}])

    def test_missing_id_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_payload([{"name": "Missing id"}])

    def test_non_array_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_payload({"data": []})


if __name__ == "__main__":
    unittest.main()
