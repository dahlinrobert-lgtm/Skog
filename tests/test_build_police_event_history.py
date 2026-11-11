import unittest

from scripts.build_police_event_history import build_history, iter_records


class PoliceEventHistoryTests(unittest.TestCase):
    def test_iter_records_reads_literal_newline_separator(self):
        text = (
            '{"event_id":"1","retrieved_at":"2026-01-01T00:00:00Z","event":{"id":1}}'
            r'\n'
            '{"event_id":"2","retrieved_at":"2026-01-02T00:00:00Z","event":{"id":2}}'
        )
        self.assertEqual([row["event_id"] for row in iter_records(text)], ["1", "2"])

    def test_history_keeps_versions_and_reports_field_changes(self):
        records = [
            {"event_id":"a","retrieved_at":"2026-01-01T00:00:00Z","payload_sha256":"h1",
             "event":{"id":"a","headline":"Initial","lat":65.0}},
            {"event_id":"a","retrieved_at":"2026-01-02T00:00:00Z","payload_sha256":"h2",
             "event":{"id":"a","headline":"Updated","lat":65.0}},
            {"event_id":"b","retrieved_at":"2026-01-02T00:00:00Z","payload_sha256":"h3",
             "event":{"id":"b","headline":"Other"}},
        ]
        versions, changes, summary = build_history(records)
        self.assertEqual(len(versions), 3)
        self.assertEqual(summary["unique_event_id_count"], 2)
        self.assertEqual(summary["distinct_event_version_count"], 3)
        updated = next(row for row in changes if row["change_type"] == "updated")
        self.assertEqual(updated["changed_fields"], "headline")
        self.assertEqual(updated["from_retrieved_at"], "2026-01-01T00:00:00Z")

    def test_summary_counts_event_ids_not_version_buckets(self):
        records = [
            {"event_id":"a","retrieved_at":"2026-01-01T00:00:00Z","payload_sha256":"a1","event":{"id":"a","headline":"A"}},
            {"event_id":"a","retrieved_at":"2026-01-02T00:00:00Z","payload_sha256":"a2","event":{"id":"a","headline":"A2"}},
            {"event_id":"b","retrieved_at":"2026-01-01T00:00:00Z","payload_sha256":"b1","event":{"id":"b","headline":"B"}},
            {"event_id":"b","retrieved_at":"2026-01-02T00:00:00Z","payload_sha256":"b2","event":{"id":"b","headline":"B2"}},
            {"event_id":"c","retrieved_at":"2026-01-01T00:00:00Z","payload_sha256":"c1","event":{"id":"c","headline":"C"}},
        ]
        _versions, _changes, summary = build_history(records)
        self.assertEqual(summary["event_ids_with_multiple_versions"], 2)

    def test_identical_payload_versions_are_not_double_counted(self):
        records = [
            {"event_id":"a","retrieved_at":"2026-01-01T00:00:00Z","payload_sha256":"same",
             "event":{"id":"a","headline":"Initial"}},
            {"event_id":"a","retrieved_at":"2026-01-02T00:00:00Z","payload_sha256":"same",
             "event":{"id":"a","headline":"Initial"}},
        ]
        versions, changes, summary = build_history(records)
        self.assertEqual(len(versions), 1)
        self.assertEqual(summary["duplicate_payload_version_count"], 1)
        self.assertEqual(len(changes), 1)


if __name__ == "__main__":
    unittest.main()
