import unittest

from memory_hub_mcp.hub import HubError, MemoryHub


class MemoryHubUnitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.hub = MemoryHub()

    def test_acl_denies_org_write_for_developer(self):
        with self.assertRaises(HubError) as ctx:
            self.hub.memory_write("org/shared", "note", "ok", "src:1", "developer")
        self.assertEqual(ctx.exception.code, "ACL_DENY")

    def test_provenance_is_required(self):
        with self.assertRaises(HubError) as ctx:
            self.hub.memory_write("project/a", "note", "ok", "", "developer")
        self.assertEqual(ctx.exception.code, "PROVENANCE_REQUIRED")

    def test_sensitive_is_blocked_and_audited(self):
        with self.assertRaises(HubError) as ctx:
            self.hub.memory_write("project/a", "note", "api_key=ABCDEFGHIJKLMNOP", "src:2", "developer")
        self.assertEqual(ctx.exception.code, "SENSITIVE_BLOCKED")
        events = self.hub.memory_audit()
        self.assertEqual(events[0]["event_type"], "blocked_sensitive")


if __name__ == "__main__":
    unittest.main()
