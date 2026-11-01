import importlib.util
import unittest

spec = importlib.util.spec_from_file_location(
    "protected_tree_probe", "scripts/probe_lansstyrelsen_protected_tree_actions.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProtectedTreeProbeTests(unittest.TestCase):
    def test_summary_reports_count_and_fields_without_feature_rows(self):
        metadata = {
            "name": "Protected trees - completed actions",
            "type": "Feature Layer",
            "geometryType": "esriGeometryPoint",
            "objectIdField": "OBJECTID",
            "globalIdField": "GlobalID",
            "capabilities": "Query",
            "maxRecordCount": 2000,
            "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID"}],
            "extent": {"spatialReference": {"wkid": 3006}},
        }
        result = module.summarize_metadata(metadata, {"count": 42})
        self.assertEqual(result["feature_count"], 42)
        self.assertEqual(result["object_id_field"], "OBJECTID")
        self.assertEqual(result["field_names"], ["OBJECTID"])
        self.assertFalse(result["feature_rows_requested"])
        self.assertFalse(result["geometry_rows_requested"])
        self.assertFalse(result["catalogue_access_warning"]["is_open_data"])
        self.assertEqual(result["catalogue_access_warning"]["confidentiality"], "K2")

    def test_count_only_response_requires_integer(self):
        metadata = {"fields": []}
        with self.assertRaisesRegex(RuntimeError, "integer count-only"):
            module.summarize_metadata(metadata, {"features": []})


if __name__ == "__main__":
    unittest.main()
