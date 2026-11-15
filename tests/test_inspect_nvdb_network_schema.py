import unittest

from scripts.inspect_nvdb_network_schema import field_inventory


class NvdbNetworkSchemaInspectionTests(unittest.TestCase):
    def test_identifies_reference_link_node_and_port_fields(self):
        result = field_inventory([
            "ELEMENT_ID",
            "ReferenslanksID",
            "Startnod",
            "Slutnod",
            "PortID",
            "Huvudnummer",
        ])
        self.assertEqual(result["field_count"], 6)
        self.assertEqual(
            result["topology_candidate_fields"],
            ["ReferenslanksID", "Startnod", "Slutnod", "PortID"],
        )

    def test_keeps_unknown_schema_fields_without_claiming_topology(self):
        result = field_inventory(["ELEMENT_ID", "Huvudnummer", "Lankroll"])
        self.assertEqual(result["fields"], ["ELEMENT_ID", "Huvudnummer", "Lankroll"])
        self.assertEqual(result["topology_candidate_fields"], [])


if __name__ == "__main__":
    unittest.main()
