#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from memory_hub_mcp.hub import MemoryHub, HubError

hub = MemoryHub(ttl_days=0)
ok = hub.memory_write("org/global", "policy", "approved", "doc:1", "product-owner")
assert ok["status"] == "active"

try:
    hub.memory_write("org/global", "policy", "denied", "doc:2", "developer")
    raise AssertionError("developer org write should fail")
except HubError as exc:
    assert exc.code == "ACL_DENY"

staled = hub.sweeper_mark_stale()
assert staled >= 1
re = hub.memory_revalidate(ok["id"], "team-lead", ttl_days=30)
assert re["status"] == "active"
PY

echo "[e2e] memory hub scenarios passed"
