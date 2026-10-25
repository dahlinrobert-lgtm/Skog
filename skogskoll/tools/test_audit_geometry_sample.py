"""Tests for the diagnostic real-sample geometry auditor."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("audit-geometry-sample.py")


class AuditGeometrySampleTests(unittest.TestCase):
    def test_report_keeps_crs_and_authority_unverified(self):
        sample = {
            "objektidentitet": "sample",
            "typ": "fastighet",
            "enhetsutbredning": [{
                "objektidentitet": "area-1",
                "omradesnummer": 1,
                "yta": [{
                    "type": "Polygon",
                    "coordinates": [[[732000, 7078000], [732010, 7078000],
                                     [732010, 7078010], [732000, 7078000]]]
                }]
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            output = Path(tmp) / "report.json"
            source.write_text(json.dumps(sample), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SCRIPT), str(source), str(output),
                "--hypothesis-crs", "EPSG:3006",
                "--reference-lon", "19.7", "--reference-lat", "63.75"
            ], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(report["source_crs_verified"])
            self.assertFalse(report["authoritative_boundary_verified"])
            self.assertEqual(report["overall_status"], "diagnostic_only_crs_unverified")
            self.assertEqual(report["feature_count"], 1)
            self.assertTrue(report["features"][0]["outer_ring_closed"])
            self.assertTrue(report["features"][0]["valid_in_hypothesis_crs"])


if __name__ == "__main__":
    unittest.main()
