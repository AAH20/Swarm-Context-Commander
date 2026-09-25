"""Reproducible single-node logical-fleet benchmark, not a cluster claim."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from .registry import Registry
from .scheduler import FairQueue, Work


def benchmark_fleet(agents: int = 150000, active_tasks: int = 10000, tenants: int = 100) -> dict:
    if not 1 <= agents <= 1_000_000 or not 1 <= active_tasks <= agents or not 1 <= tenants <= agents:
        raise ValueError("invalid fleet benchmark dimensions")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fleet.db"
        registry = Registry(path)
        start = time.perf_counter()
        count = registry.register_synthetic(agents, tenants=tenants)
        registration_seconds = time.perf_counter() - start
        queue = FairQueue()
        start = time.perf_counter()
        for index in range(active_tasks):
            queue.put(Work(f"task-{index}", f"tenant-{index % tenants:04d}",
                           128 + (index % 8) * 64, priority=index % 3))
        enqueue_seconds = time.perf_counter() - start
        start = time.perf_counter()
        seen = set()
        while len(queue):
            item = queue.pop()
            if item.task_id in seen:
                raise AssertionError("duplicate task dequeue")
            seen.add(item.task_id)
        drain_seconds = time.perf_counter() - start
        registry.close()
        return {"schema_version": "swarmcontext-fleet-benchmark/v1",
                "scope": "single_process_sqlite_registration_and_in_memory_scheduler_only",
                "logical_agents": count, "active_synthetic_tasks": len(seen), "tenants": tenants,
                "registration_seconds": round(registration_seconds, 4),
                "enqueue_seconds": round(enqueue_seconds, 4),
                "drain_seconds": round(drain_seconds, 4),
                "sqlite_bytes": path.stat().st_size,
                "hypothetical_events_per_second_at_one_event_per_agent_minute": round(agents / 60, 2),
                "not_measured": ["A2A network throughput", "Cognee latency", "vLLM tokens/s",
                                 "browser sessions", "distributed failover", "GPU cost"]}
