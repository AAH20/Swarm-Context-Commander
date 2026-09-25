"""Resource-aware placement and bounded deficit-round-robin scheduling."""

from __future__ import annotations

import heapq
import itertools
from collections import deque
from dataclasses import dataclass

from .registry import ContractError


@dataclass(frozen=True)
class Work:
    task_id: str
    tenant_id: str
    estimated_tokens: int
    priority: int = 0
    deadline_ns: int = 0
    needs_browser: bool = False
    runs_code: bool = False
    high_isolation: bool = False
    read_only: bool = True
    estimated_seconds: int = 1


def placement(work: Work) -> str:
    if work.runs_code or work.high_isolation:
        return "microvm"
    if work.needs_browser or not work.read_only or work.estimated_seconds > 10:
        return "container"
    return "serverless"


class FairQueue:
    """O(log n) enqueue/dequeue within a tenant; weighted fairness across tenants.

    Each round grants quantum * weight token credits. Large jobs wait for
    sufficient credits rather than bypassing admission.
    """

    def __init__(self, *, quantum_tokens: int = 512, max_tokens_per_work: int = 16384):
        if quantum_tokens < 1 or max_tokens_per_work < quantum_tokens:
            raise ContractError("invalid queue token bounds")
        self.quantum = quantum_tokens
        self.max_tokens = max_tokens_per_work
        self._queues: dict[str, list[tuple[int, int, int, Work]]] = {}
        self._active: deque[str] = deque()
        self._deficit: dict[str, int] = {}
        self._weights: dict[str, int] = {}
        self._sequence = itertools.count()
        self._ids: set[str] = set()

    def set_weight(self, tenant_id: str, weight: int) -> None:
        if not tenant_id or not 1 <= weight <= 16:
            raise ContractError("tenant weight must be 1-16")
        self._weights[tenant_id] = weight

    def put(self, work: Work) -> None:
        if not work.task_id or not work.tenant_id or work.task_id in self._ids:
            raise ContractError("invalid or duplicate task")
        if not 1 <= work.estimated_tokens <= self.max_tokens or not 0 <= work.priority <= 10:
            raise ContractError("task exceeds token or priority bounds")
        queue = self._queues.setdefault(work.tenant_id, [])
        if not queue:
            self._active.append(work.tenant_id)
            self._deficit.setdefault(work.tenant_id, 0)
        deadline = work.deadline_ns if work.deadline_ns > 0 else 2**63 - 1
        heapq.heappush(queue, (-work.priority, deadline, next(self._sequence), work))
        self._ids.add(work.task_id)

    def pop(self) -> Work | None:
        if not self._active:
            return None
        # Bound the scan even when every head task is near the maximum size.
        rounds = (self.max_tokens // self.quantum + 1) * len(self._active)
        for _ in range(rounds):
            tenant = self._active[0]
            self._deficit[tenant] += self.quantum * self._weights.get(tenant, 1)
            head = self._queues[tenant][0][3]
            if head.estimated_tokens <= self._deficit[tenant]:
                work = heapq.heappop(self._queues[tenant])[3]
                self._deficit[tenant] -= work.estimated_tokens
                self._ids.remove(work.task_id)
                if not self._queues[tenant]:
                    self._active.popleft()
                    del self._deficit[tenant]
                    del self._queues[tenant]
                else:
                    self._active.rotate(-1)
                return work
            self._active.rotate(-1)
        raise ContractError("scheduler failed to find an admissible task")

    def __len__(self) -> int:
        return len(self._ids)
