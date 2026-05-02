from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .hub import HubError, MemoryHub


TOOLS = {
    "memory_write",
    "memory_read",
    "memory_search",
    "memory_link",
    "memory_audit",
    "memory_revalidate",
    "sweeper_mark_stale",
}


def handle_request(hub: MemoryHub, req: dict) -> dict:
    tool = req.get("tool")
    args = req.get("args", {})
    if tool not in TOOLS:
        return {"ok": False, "error": "UNKNOWN_TOOL", "message": f"unsupported tool: {tool}"}
    try:
        result = getattr(hub, tool)(**args)
        return {"ok": True, "result": result}
    except HubError as exc:
        return {"ok": False, **exc.as_dict()}


def run_stdio(hub: MemoryHub) -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        resp = handle_request(hub, req)
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="memory_hub.sqlite3")
    parser.add_argument("--once", help="single JSON request")
    args = parser.parse_args()

    Path(args.db_path).parent.mkdir(parents=True, exist_ok=True)
    hub = MemoryHub(db_path=args.db_path)
    if args.once:
        req = json.loads(args.once)
        print(json.dumps(handle_request(hub, req), ensure_ascii=False))
        return 0
    return run_stdio(hub)


if __name__ == "__main__":
    raise SystemExit(main())
