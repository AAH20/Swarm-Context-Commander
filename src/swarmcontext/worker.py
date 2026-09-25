"""Provider-neutral computer-use dispatch contract with executable synthetic adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .protocol import computer_use_event
from .registry import ContractError
from .scheduler import Work, placement


@dataclass(frozen=True)
class Job:
    task_id: str
    tenant_id: str
    objective: str
    provider: str
    read_only: bool = True
    estimated_tokens: int = 256


class ComputerAdapter(Protocol):
    provider: str

    def run(self, job: Job, context: dict) -> tuple[str, str]:
        """Return event kind and observation. A real adapter must enforce permissions."""


class FixtureAdapter:
    provider = "fixture"

    def run(self, job: Job, context: dict) -> tuple[str, str]:
        return "complete", f"Synthetic task {job.task_id} viewed {len(context.get('items', []))} context items."


def execute(job: Job, context: dict, adapter: ComputerAdapter) -> dict:
    if not job.task_id or not job.tenant_id or not 1 <= len(job.objective) <= 500:
        raise ContractError("invalid computer-use job")
    if job.provider != adapter.provider:
        raise ContractError("provider and adapter differ")
    if not job.read_only:
        raise ContractError("computer-use writes require an external approval/executor")
    if context.get("tenant_id") != job.tenant_id or context.get("schema_version") != "swarmcontext-bundle/v1":
        raise ContractError("context bundle tenant or schema mismatch")
    work = Work(job.task_id, job.tenant_id, job.estimated_tokens, needs_browser=True)
    kind, observation = adapter.run(job, context)
    event = computer_use_event(provider=job.provider, task_id=job.task_id,
                               kind=kind, observation=observation, side_effect=False)
    return {"schema_version": "swarmcontext-worker-result/v1", "task_id": job.task_id,
            "placement_class": placement(work), "context_sha256": context.get("bundle_sha256"),
            "event": event, "status": "synthetic_completed" if job.provider == "fixture" else "completed",
            "authority": "receipt_only"}
