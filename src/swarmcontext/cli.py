"""Reference CLI."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from .benchmark import benchmark_fleet
from .cognee import ingest_chunks, search_local
from .context import ContextIndex, Memory
from .personalization import demonstration as personalization_demonstration
from .registry import ContractError, Registry, canonical
from .scheduler import FairQueue, Work, placement
from .worker import FixtureAdapter, Job, execute


def demo() -> dict:
    index = ContextIndex()
    index.add(Memory("agent-1:note", "tenant-1", "agent", "Refund reconciliation needs review before rollout.",
                     "a" * 64, 1, trust=3, owner_agent_id="agent-1"))
    index.add(Memory("tenant-2:secret", "tenant-2", "tenant", "Private competing tenant fact.",
                     "b" * 64, 1, trust=3))
    ingest_chunks(index, [{"id": "synthetic-graph-note", "text": "Synthetic refund ledger context."}],
                  tenant_id="tenant-1", now=1)
    bundle = index.compile("refund reconciliation", tenant="tenant-1", agent="agent-1", now=2)
    queue = FairQueue()
    work = Work("task-1", "tenant-1", 300, needs_browser=True)
    queue.put(work)
    with tempfile.TemporaryDirectory() as directory:
        registry = Registry(Path(directory) / "demo.db")
        registry.register("agent-1", "tenant-1", "browser")
        registry.submit(task_id="task-1", tenant_id="tenant-1", agent_id="agent-1",
                        idempotency_key="demo-1", request={"context_sha256": bundle["bundle_sha256"]})
        attempt = registry.lease("task-1", "demo-worker")
        registry.finish("task-1", "demo-worker", attempt, success=True)
        state = registry.task_state("task-1")
        registry.close()
    selected = queue.pop()
    worker = execute(Job(selected.task_id, selected.tenant_id, "Review refund evidence", "fixture"),
                     bundle, FixtureAdapter())
    return {"schema_version": "swarmcontext-demo/v1", "claim": "synthetic_local_reference",
            "placement": placement(selected), "task_state": state,
            "context": bundle, "worker": worker, "cross_tenant_material_excluded": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="swarm-context-commander")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("demo", help="run a synthetic local task and context compilation")
    run.add_argument("--output")
    personal = commands.add_parser("personalization-demo", help="run synthetic consumer, SMB and enterprise policy learning")
    personal.add_argument("--output")
    bench = commands.add_parser("bench-fleet", help="benchmark logical registration and in-memory scheduling")
    bench.add_argument("--agents", type=int, default=150000)
    bench.add_argument("--active-tasks", type=int, default=10000)
    bench.add_argument("--tenants", type=int, default=100)
    bench.add_argument("--output")
    context = commands.add_parser("context-cognee", help="compile untrusted Cognee CHUNKS into a local context bundle")
    context.add_argument("--query", required=True)
    context.add_argument("--tenant", required=True)
    context.add_argument("--agent", required=True)
    source = context.add_mutually_exclusive_group(required=True)
    source.add_argument("--response-file")
    source.add_argument("--base-url")
    context.add_argument("--allow-network", action="store_true")
    context.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo()
        elif args.command == "personalization-demo":
            result = personalization_demonstration()
        elif args.command == "bench-fleet":
            result = benchmark_fleet(args.agents, args.active_tasks, args.tenants)
        else:
            if args.response_file:
                file = Path(args.response_file)
                if file.stat().st_size > 65536:
                    raise ContractError("Cognee response file exceeds 64 KiB")
                chunks = json.loads(file.read_text(encoding="utf-8"))
            else:
                chunks = search_local(args.base_url, args.query, allow_network=args.allow_network)
            index = ContextIndex()
            ingest_chunks(index, chunks, tenant_id=args.tenant, now=int(time.time()))
            result = index.compile(args.query, tenant=args.tenant, agent=args.agent, now=int(time.time()))
        output = canonical(result) + "\n"
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8")
            print(path)
        else:
            print(output, end="")
        return 0
    except (ContractError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
