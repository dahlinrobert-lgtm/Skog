import hashlib
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from viltdata_azure_archive import validate_snapshot, upload_immutable, _safe_relative


def make_snapshot(root: pathlib.Path):
    (root / "raw" / "model").mkdir(parents=True)
    (root / "raw" / "statistics").mkdir(parents=True)
    contents = {
        "raw/model/statistics-model.json": b'{"species":[]}',
        "raw/model/counties.json": b'[]',
        "raw/statistics/national-batch-001.json": b'{"labels":["2025"],"dataSets":[{"data":[1]}]}',
    }
    requests = []
    for name, body in contents.items():
        path = root / name
        path.write_bytes(body)
        kind = "statistics_model" if "statistics-model" in name else "counties" if "counties" in name else "statistics"
        entry = {"kind": kind, "file": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        if kind == "statistics":
            entry.update({"status": "ok", "scope": "national", "batch": 1})
        requests.append(entry)
    manifest = {
        "schema_version": 2, "run_id": root.name, "status": "complete", "complete": True,
        "requests": requests, "statistics_requests_ok": 1,
        "statistics_requests_expected": 1, "errors": [],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return contents


class ViltdataAzureArchiveTests(unittest.TestCase):
    def test_accepts_complete_snapshot_and_checks_every_raw_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "20261118T204420Z"
            root.mkdir()
            contents = make_snapshot(root)
            manifest, raw, files = validate_snapshot(root)
            self.assertTrue(manifest["complete"])
            self.assertEqual(set(files), set(contents))
            self.assertTrue(raw.startswith(b"{"))

    def test_rejects_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "20261118T204420Z"
            root.mkdir()
            make_snapshot(root)
            path = root / "manifest.json"
            value = json.loads(path.read_text())
            value["complete"] = False
            value["status"] = "partial"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(RuntimeError, "not explicitly complete"):
                validate_snapshot(root)

    def test_rejects_missing_raw_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "20261118T204420Z"
            root.mkdir()
            make_snapshot(root)
            (root / "raw/statistics/national-batch-001.json").unlink()
            with self.assertRaisesRegex(RuntimeError, "missing"):
                validate_snapshot(root)

    def test_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "20261118T204420Z"
            root.mkdir()
            make_snapshot(root)
            (root / "raw/model/counties.json").write_bytes(b'[{"id":1}]')
            with self.assertRaisesRegex(RuntimeError, "integrity mismatch"):
                validate_snapshot(root)

    def test_rejects_unlisted_extra_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "20261118T204420Z"
            root.mkdir()
            make_snapshot(root)
            (root / "unexpected.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "inventory mismatch"):
                validate_snapshot(root)

    def test_rejects_path_traversal(self):
        for value in ("../secret.json", "/absolute.json", "raw/../../secret"):
            with self.assertRaises(ValueError):
                _safe_relative(value)

    def test_create_only_upload_and_matching_retry(self):
        blob = Mock()
        self.assertTrue(upload_immutable(blob, b"raw", {"sha256": "abc"}, "application/json"))
        self.assertFalse(blob.upload_blob.call_args.kwargs["overwrite"] is True)

    def test_rejects_conflicting_existing_object(self):
        from azure.core.exceptions import ResourceExistsError
        blob = Mock()
        blob.upload_blob.side_effect = ResourceExistsError("exists")
        blob.get_blob_properties.return_value.metadata = {"sha256": "wrong"}
        with self.assertRaises(RuntimeError):
            upload_immutable(blob, b"raw", {"sha256": "right"}, "application/json")


if __name__ == "__main__":
    unittest.main()
