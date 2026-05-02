import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class AgenticCodexMemoryHubBlackboxTest(unittest.TestCase):
    def test_agentic_install_and_memory_hub_methods(self):
        root = Path(__file__).resolve().parents[2]
        cli = root / "agentic"
        with tempfile.TemporaryDirectory(prefix="agentic-mhub-") as td:
            project = Path(td) / "project"
            home = Path(td) / "home"
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["CONTEXT7_API_KEY"] = "dummy"
            env["MEMORY_HUB_MCP_ENABLE"] = "1"

            subprocess.run([
                str(cli), "install",
                "--project-dir", str(project),
                "--agent-os", "codex",
                "--areas", "software",
                "--specializations", "software.backend",
            ], check=True, env=env)

            cfg = (project / ".codex" / "config.toml").read_text(encoding="utf-8")
            self.assertIn("mcp_servers.memory_hub", cfg)

            db_path = project / ".agentic" / "memory-hub.sqlite3"

            def call(tool, args):
                req = json.dumps({"tool": tool, "args": args})
                out = subprocess.check_output([
                    "python3", "-m", "memory_hub_mcp.server", "--db-path", str(db_path), "--once", req
                ], text=True)
                return json.loads(out)

            w1 = call("memory_write", {"namespace": "project/x", "record_type": "note", "content": "alpha", "source_ref": "SRC-1", "actor_role": "developer"})
            self.assertTrue(w1["ok"])
            mid = w1["result"]["id"]
            w2 = call("memory_write", {"namespace": "project/x", "record_type": "note", "content": "beta", "source_ref": "SRC-2", "actor_role": "developer"})
            self.assertTrue(w2["ok"])

            self.assertTrue(call("memory_read", {"memory_id": mid})["ok"])
            self.assertTrue(call("memory_search", {"namespace": "project/x", "query": "alp"})["ok"])
            self.assertTrue(call("memory_link", {"from_memory_id": mid, "to_memory_id": w2["result"]["id"], "relation": "related", "actor_role": "developer"})["ok"])
            self.assertTrue(call("memory_audit", {"limit": 5})["ok"])
            self.assertTrue(call("sweeper_mark_stale", {})["ok"])
            self.assertTrue(call("memory_revalidate", {"memory_id": mid, "actor_role": "team-lead", "ttl_days": 30})["ok"])


if __name__ == "__main__":
    unittest.main()
