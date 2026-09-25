"""Durable logical-agent registry and idempotent task admission.

SQLite is a reproducible single-node reference backend, not the intended
distributed store for production fleet traffic.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path


class ContractError(ValueError):
    """An input violates the versioned local contract."""


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class Registry:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                capability TEXT NOT NULL, created_ns INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS agents_tenant_idx ON agents(tenant_id);
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
                agent_id TEXT NOT NULL REFERENCES agents(agent_id),
                idempotency_key TEXT NOT NULL, request_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('queued','leased','completed','failed')),
                created_ns INTEGER NOT NULL, lease_owner TEXT, lease_until_ns INTEGER,
                attempts INTEGER NOT NULL DEFAULT 0,
                UNIQUE(tenant_id, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS tasks_state_idx ON tasks(state, created_ns);
        """)

    def close(self) -> None:
        self.db.close()

    def register(self, agent_id: str, tenant_id: str, capability: str = "read") -> None:
        if not agent_id or not tenant_id or capability not in ("read", "browser", "code"):
            raise ContractError("invalid agent registration")
        with self.db:
            self.db.execute("INSERT INTO agents VALUES (?,?,?,?)",
                            (agent_id, tenant_id, capability, time.time_ns()))

    def register_synthetic(self, count: int, *, tenants: int = 100, batch: int = 5000) -> int:
        if not 1 <= count <= 1_000_000 or not 1 <= tenants <= count:
            raise ContractError("invalid synthetic fleet size")
        now = time.time_ns()
        for start in range(0, count, batch):
            rows = ((f"synthetic-agent-{i:07d}", f"tenant-{i % tenants:04d}", "read", now)
                    for i in range(start, min(start + batch, count)))
            with self.db:
                self.db.executemany("INSERT INTO agents VALUES (?,?,?,?)", rows)
        return self.count_agents()

    def count_agents(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]

    def submit(self, *, task_id: str, tenant_id: str, agent_id: str,
               idempotency_key: str, request: dict) -> str:
        if not all(isinstance(x, str) and 1 <= len(x) <= 128 for x in
                   (task_id, tenant_id, agent_id, idempotency_key)):
            raise ContractError("invalid task identifiers")
        payload = canonical(request)
        if len(payload.encode("utf-8")) > 8192:
            raise ContractError("task request exceeds 8 KiB; use artifact references")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        agent = self.db.execute("SELECT tenant_id FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
        if agent is None or agent[0] != tenant_id:
            raise ContractError("agent is absent or belongs to another tenant")
        with self.db:
            try:
                self.db.execute("INSERT INTO tasks(task_id,tenant_id,agent_id,idempotency_key,request_sha256,state,created_ns) "
                                "VALUES (?,?,?,?,?,'queued',?)",
                                (task_id, tenant_id, agent_id, idempotency_key, digest, time.time_ns()))
                return task_id
            except sqlite3.IntegrityError:
                row = self.db.execute("SELECT task_id,agent_id,request_sha256 FROM tasks "
                                      "WHERE tenant_id=? AND idempotency_key=?",
                                      (tenant_id, idempotency_key)).fetchone()
                if row and row[1:] == (agent_id, digest):
                    return row[0]
                raise ContractError("idempotency key reused with a different request") from None

    def lease(self, task_id: str, worker: str, *, ttl_seconds: int = 30) -> int:
        if not worker or not 1 <= ttl_seconds <= 3600:
            raise ContractError("invalid worker or lease TTL")
        now = time.time_ns()
        with self.db:
            cursor = self.db.execute("UPDATE tasks SET state='leased', lease_owner=?, lease_until_ns=?, "
                                     "attempts=attempts+1 WHERE task_id=? AND "
                                     "(state='queued' OR (state='leased' AND lease_until_ns<?))",
                                     (worker, now + ttl_seconds * 1_000_000_000, task_id, now))
            if cursor.rowcount != 1:
                raise ContractError("task is not available for lease")
            return self.db.execute("SELECT attempts FROM tasks WHERE task_id=?", (task_id,)).fetchone()[0]

    def finish(self, task_id: str, worker: str, attempt: int, *, success: bool) -> None:
        now = time.time_ns()
        with self.db:
            cursor = self.db.execute("UPDATE tasks SET state=?, lease_owner=NULL, lease_until_ns=NULL "
                                     "WHERE task_id=? AND state='leased' AND lease_owner=? AND attempts=? "
                                     "AND lease_until_ns>=?",
                                     ("completed" if success else "failed", task_id, worker, attempt, now))
            if cursor.rowcount != 1:
                raise ContractError("stale or expired lease cannot commit")

    def task_state(self, task_id: str) -> str | None:
        row = self.db.execute("SELECT state FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        return row[0] if row else None
