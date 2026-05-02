import unittest

from memory_hub_mcp.hub import MemoryHub


class MemoryHubBlackboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.hub = MemoryHub(ttl_days=30)

    def test_tool_flow_write_read_search_link_audit(self):
        one = self.hub.memory_write("project/demo", "decision", "use sqlite", "adr-1", "developer")
        two = self.hub.memory_write("project/demo", "note", "sync adapters", "issue-10", "developer")

        item = self.hub.memory_read(one["id"])
        self.assertEqual(item["namespace"], "project/demo")

        found = self.hub.memory_search("project/demo", "sqlite")
        self.assertEqual(len(found), 1)

        link = self.hub.memory_link(one["id"], two["id"], "depends_on", "developer")
        self.assertEqual(link["relation"], "depends_on")

        audit = self.hub.memory_audit(limit=10)
        self.assertGreaterEqual(len(audit), 3)


if __name__ == "__main__":
    unittest.main()
