import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from viltdata_kill_statistics_snapshot import (
    build_statistics_url,
    get_start_year,
    validate_statistics,
)


class ViltdataKillSnapshotTests(unittest.TestCase):
    def test_builds_multi_species_kill_query_and_county_filter(self):
        url = build_statistics_url(
            [{"id": 48, "name": "Rådjur"}, {"id": 37, "name": "Kronhjort"}],
            1960, 2025, {"id": 1, "name": "Stockholms län"},
        )
        self.assertIn("StatisticsReportType=kill", url)
        self.assertIn("Species%5B0%5D%5BID%5D=48", url)
        self.assertIn("Species%5B1%5D%5BID%5D=37", url)
        self.assertIn("Counties%5B0%5D%5Bid%5D=1", url)
        self.assertIn("R%C3%A5djur", url)

    def test_start_year_uses_model_value(self):
        self.assertEqual(get_start_year({"avskjutning": {"Nationellt": 1939}}, ["Nationellt"], 1900), 1939)
        self.assertEqual(get_start_year({"avskjutning": {"Län": 1960}}, ["Län"], 1900), 1960)
        self.assertEqual(get_start_year({}, ["Län"], 1960), 1960)

    def test_validates_labels_and_dataset_alignment(self):
        self.assertEqual(
            validate_statistics({"labels": ["2024", "2025"], "dataSets": [{"label": "Rådjur", "data": [1, None]}]}),
            {"labels": 2, "datasets": 1},
        )
        with self.assertRaises(ValueError):
            validate_statistics({"labels": ["2024", "2025"], "dataSets": [{"data": [1]}]})

    def test_rejects_empty_statistics_response(self):
        with self.assertRaises(ValueError):
            validate_statistics({"labels": [], "dataSets": []})


if __name__ == "__main__":
    unittest.main()
