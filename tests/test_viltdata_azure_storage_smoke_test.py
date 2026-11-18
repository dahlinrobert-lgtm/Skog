import json
import pathlib
import sys
import unittest
from unittest.mock import Mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from viltdata_azure_storage_smoke_test import build_test_payload, sha256_bytes, upload_immutable


class ViltdataAzureSmokeTests(unittest.TestCase):
    def test_payload_is_deterministic_and_contains_no_source_data(self):
        first = build_test_payload("12345", "1")
        self.assertEqual(first, build_test_payload("12345", "1"))
        payload = json.loads(first)
        self.assertTrue(payload["synthetic"])
        self.assertFalse(payload["source_data_included"])
        self.assertEqual(payload["source_id"], "viltdata.kill_statistics")

    def test_sha256_is_a_stable_hex_digest(self):
        digest = sha256_bytes(b"synthetic")
        self.assertEqual(digest, sha256_bytes(b"synthetic"))
        self.assertEqual(len(digest), 64)
        self.assertTrue(all(char in "0123456789abcdef" for char in digest))

    def test_upload_uses_create_only_semantics(self):
        blob = Mock()
        created = upload_immutable(blob, b"payload", {"sha256": sha256_bytes(b"payload")}, "application/json")
        self.assertTrue(created)
        blob.upload_blob.assert_called_once()
        self.assertFalse(blob.upload_blob.call_args.kwargs["overwrite"])

    def test_existing_blob_must_match_metadata_and_bytes(self):
        from azure.core.exceptions import ResourceExistsError
        blob = Mock()
        blob.upload_blob.side_effect = ResourceExistsError("already exists")
        blob.get_blob_properties.return_value.metadata = {"sha256": sha256_bytes(b"payload")}
        blob.download_blob.return_value.readall.return_value = b"payload"
        self.assertFalse(upload_immutable(blob, b"payload", {"sha256": sha256_bytes(b"payload")}, "application/json"))

    def test_existing_blob_conflict_is_rejected(self):
        from azure.core.exceptions import ResourceExistsError
        blob = Mock()
        blob.upload_blob.side_effect = ResourceExistsError("already exists")
        blob.get_blob_properties.return_value.metadata = {"sha256": "different"}
        with self.assertRaises(RuntimeError):
            upload_immutable(blob, b"payload", {"sha256": sha256_bytes(b"payload")}, "application/json")


if __name__ == "__main__":
    unittest.main()
