from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-platform" / "scripts"))
from validate_event_bundle import SCHEMA, validate_bundle  # noqa: E402


class EventBundleValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.example = json.loads(
            (ROOT / "data-platform" / "examples" / "event-bundle.example.json").read_text(encoding="utf-8")
        )

    def test_example_bundle_is_valid(self):
        self.assertEqual(validate_bundle(self.example, self.schema), [])

    def test_unknown_run_reference_is_rejected(self):
        bundle = json.loads(json.dumps(self.example))
        bundle["observations"][0]["run_id"] = "missing-run"
        self.assertTrue(any("unknown run_id" in error for error in validate_bundle(bundle, self.schema)))

    def test_unknown_event_in_chain_is_rejected(self):
        bundle = json.loads(json.dumps(self.example))
        bundle["chains"][0]["event_ids"].append("missing-event")
        self.assertTrue(any("unknown event_ids" in error for error in validate_bundle(bundle, self.schema)))

    def test_self_relationship_is_rejected(self):
        bundle = json.loads(json.dumps(self.example))
        bundle["relationships"] = [{
            "relationship_id": "rel-self",
            "from_event_id": "event-planned-harvest-example",
            "to_event_id": "event-planned-harvest-example",
            "relationship_type": "same_area",
            "match_method": "test",
            "confidence_class": "uncertain",
            "rule_version": "test-v1",
            "review_status": "unreviewed"
        }]
        self.assertTrue(any("self-link" in error for error in validate_bundle(bundle, self.schema)))

    def test_failed_run_cannot_back_valid_observation(self):
        bundle = json.loads(json.dumps(self.example))
        bundle["source_runs"][0]["status"] = "failed"
        self.assertTrue(any("valid observation references failed run" in error for error in validate_bundle(bundle, self.schema)))


if __name__ == "__main__":
    unittest.main()
