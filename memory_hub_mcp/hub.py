from __future__ import annotations

import hashlib
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

UTC = timezone.utc


@dataclass(frozen=True)
class HubError(Exception):
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"error": self.code, "message": self.message}


class MemoryHub:
    def __init__(self, db_path: str = ":memory:", ttl_days: int = 30) -> None:
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS namespaces (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL,
                record_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                created_by_role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active','stale','blocked')),
                sensitivity_flag INTEGER NOT NULL DEFAULT 0,
                hash TEXT NOT NULL,
                FOREIGN KEY(namespace) REFERENCES namespaces(name)
            );
            CREATE TABLE IF NOT EXISTS memory_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_memory_id INTEGER NOT NULL,
                to_memory_id INTEGER NOT NULL,
                relation TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(from_memory_id) REFERENCES memories(id),
                FOREIGN KEY(to_memory_id) REFERENCES memories(id)
            );
            CREATE TABLE IF NOT EXISTS memory_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER,
                event_type TEXT NOT NULL,
                namespace TEXT,
                actor_role TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                payload_hash TEXT,
                FOREIGN KEY(memory_id) REFERENCES memories(id)
            );
            CREATE INDEX IF NOT EXISTS idx_mem_ns ON memories(namespace);
            CREATE INDEX IF NOT EXISTS idx_mem_rt ON memories(record_type);
            CREATE INDEX IF NOT EXISTS idx_mem_status ON memories(status);
            CREATE INDEX IF NOT EXISTS idx_mem_expires ON memories(expires_at);
            """
        )
        self.conn.commit()

    def _now(self) -> datetime:
        return datetime.now(tz=UTC)

    def _iso(self, dt: datetime) -> str:
        return dt.isoformat()

    def _ensure_namespace(self, namespace: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO namespaces(name, created_at) VALUES(?,?)",
            (namespace, self._iso(self._now())),
        )

    def _audit(self, event_type: str, actor_role: str, namespace: str | None = None, memory_id: int | None = None, reason: str | None = None, payload_hash: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO memory_events(memory_id,event_type,namespace,actor_role,reason,created_at,payload_hash) VALUES(?,?,?,?,?,?,?)",
            (memory_id, event_type, namespace, actor_role, reason, self._iso(self._now()), payload_hash),
        )

    def _enforce_acl(self, namespace: str, actor_role: str) -> None:
        if namespace.startswith("org/") and actor_role not in {"product-owner", "team-lead"}:
            raise HubError("ACL_DENY", f"role '{actor_role}' cannot write to {namespace}")

    def _validate_provenance(self, source_ref: str) -> None:
        if not source_ref.strip():
            raise HubError("PROVENANCE_REQUIRED", "source_ref is required")

    def _entropy(self, text: str) -> float:
        if not text:
            return 0.0
        probs = [text.count(c) / len(text) for c in set(text)]
        return -sum(p * math.log2(p) for p in probs)

    def _contains_sensitive(self, content: str) -> tuple[bool, str | None]:
        patterns = [
            r"AKIA[0-9A-Z]{16}",
            r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----",
            r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}",
            r"\b\d{3}-\d{2}-\d{4}\b",
        ]
        for pattern in patterns:
            if re.search(pattern, content):
                return True, f"pattern:{pattern}"
        compact = re.sub(r"\s+", "", content)
        if len(compact) >= 24 and self._entropy(compact) > 4.2:
            return True, "entropy"
        return False, None

    def memory_write(self, namespace: str, record_type: str, content: str, source_ref: str, actor_role: str) -> dict[str, Any]:
        payload_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        try:
            self._enforce_acl(namespace, actor_role)
            self._validate_provenance(source_ref)
            blocked, reason = self._contains_sensitive(content)
            if blocked:
                self._audit("blocked_sensitive", actor_role, namespace=namespace, reason=reason, payload_hash=payload_hash)
                self.conn.commit()
                raise HubError("SENSITIVE_BLOCKED", "sensitive payload blocked")

            now = self._now()
            expires_at = now + timedelta(days=self.ttl_days)
            self._ensure_namespace(namespace)
            cur = self.conn.execute(
                """INSERT INTO memories(namespace,record_type,content,source_ref,created_by_role,created_at,expires_at,status,sensitivity_flag,hash)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (namespace, record_type, content, source_ref, actor_role, self._iso(now), self._iso(expires_at), "active", 0, payload_hash),
            )
            memory_id = int(cur.lastrowid)
            self._audit("write_accepted", actor_role, namespace=namespace, memory_id=memory_id, payload_hash=payload_hash)
            self.conn.commit()
            return {"id": memory_id, "status": "active", "expires_at": self._iso(expires_at)}
        except HubError as exc:
            if exc.code == "ACL_DENY":
                self._audit("write_denied", actor_role, namespace=namespace, reason=exc.message, payload_hash=payload_hash)
                self.conn.commit()
            raise

    def memory_read(self, memory_id: int, include_stale: bool = False) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise HubError("NOT_FOUND", f"memory {memory_id} not found")
        if row["status"] == "stale" and not include_stale:
            raise HubError("STALE_EXCLUDED", "record is stale")
        return dict(row)

    def memory_search(self, namespace: str, query: str, include_stale: bool = False) -> list[dict[str, Any]]:
        status_clause = "" if include_stale else "AND status='active'"
        rows = self.conn.execute(
            f"SELECT * FROM memories WHERE namespace=? {status_clause} AND content LIKE ? ORDER BY id DESC",
            (namespace, f"%{query}%"),
        ).fetchall()
        return [dict(r) for r in rows]

    def memory_link(self, from_memory_id: int, to_memory_id: int, relation: str, actor_role: str) -> dict[str, Any]:
        now = self._iso(self._now())
        cur = self.conn.execute(
            "INSERT INTO memory_links(from_memory_id,to_memory_id,relation,created_at) VALUES(?,?,?,?)",
            (from_memory_id, to_memory_id, relation, now),
        )
        self._audit("link_created", actor_role, memory_id=from_memory_id, reason=relation)
        self.conn.commit()
        return {"id": int(cur.lastrowid), "relation": relation}

    def memory_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM memory_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def sweeper_mark_stale(self) -> int:
        now = self._iso(self._now())
        cur = self.conn.execute("UPDATE memories SET status='stale' WHERE status='active' AND expires_at < ?", (now,))
        self.conn.commit()
        return cur.rowcount

    def memory_revalidate(self, memory_id: int, actor_role: str, ttl_days: int | None = None) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise HubError("NOT_FOUND", f"memory {memory_id} not found")
        ttl = ttl_days if ttl_days is not None else self.ttl_days
        expires = self._now() + timedelta(days=ttl)
        self.conn.execute("UPDATE memories SET status='active', expires_at=? WHERE id=?", (self._iso(expires), memory_id))
        self._audit("revalidated", actor_role, memory_id=memory_id, namespace=row["namespace"])
        self.conn.commit()
        return {"id": memory_id, "status": "active", "expires_at": self._iso(expires)}
