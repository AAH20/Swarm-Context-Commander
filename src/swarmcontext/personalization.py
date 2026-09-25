"""Inspectable, synthetic policy-selection loop for three personalization scales.

This is a deterministic contextual bandit *baseline*, not a trained model. Only
pre-approved ContextPolicy variants can be selected; feedback never changes
tenant visibility, executes actions, or promotes a candidate to production.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .context import ContextIndex, ContextPolicy, Memory
from .registry import ContractError


TIERS = ("consumer", "smb", "enterprise")


@dataclass(frozen=True)
class Feedback:
    accepted: bool
    cost_usd: float
    latency_ms: float
    reviewer: str = "synthetic_fixture"

    def reward(self) -> float:
        if (not math.isfinite(self.cost_usd) or self.cost_usd < 0
                or not math.isfinite(self.latency_ms) or self.latency_ms < 0
                or not self.reviewer):
            raise ContractError("invalid feedback")
        # Fixed, inspectable proxy. The acceptance label must come from an
        # independent reviewer in a real deployment, not the same agent.
        return max(0.0, float(self.accepted) - min(self.cost_usd, 1.0) * 0.2
                   - min(self.latency_ms, 10_000) / 10_000 * 0.1)


class PolicySelector:
    """UCB1 over an allowlist of policies, partitioned by tier."""

    def __init__(self, arms: dict[str, dict[str, ContextPolicy]]):
        if set(arms) != set(TIERS) or any(not row for row in arms.values()):
            raise ContractError("each tier needs approved policies")
        for row in arms.values():
            for policy in row.values():
                policy.validate()
        self.arms = arms
        self.stats = {tier: {name: [0, 0.0] for name in rows} for tier, rows in arms.items()}

    def choose(self, tier: str) -> tuple[str, ContextPolicy]:
        if tier not in self.arms:
            raise ContractError("unknown tier")
        row = self.stats[tier]
        total = sum(n for n, _ in row.values())
        name = max(sorted(row), key=lambda key: (
            float("inf") if row[key][0] == 0 else
            row[key][1] / row[key][0] + math.sqrt(2 * math.log(total) / row[key][0]),
        ))
        return name, self.arms[tier][name]

    def observe(self, tier: str, name: str, feedback: Feedback) -> None:
        if tier not in self.stats or name not in self.stats[tier]:
            raise ContractError("feedback must refer to an approved arm")
        reward = feedback.reward()
        self.stats[tier][name][0] += 1
        self.stats[tier][name][1] += reward

    def snapshot(self) -> dict:
        return {tier: {name: {"observations": n, "mean_proxy_reward": round(total / n, 4) if n else None}
                       for name, (n, total) in sorted(row.items())}
                for tier, row in self.stats.items()}


def approved_policies() -> dict[str, dict[str, ContextPolicy]]:
    return {
        "consumer": {
            "compact": ContextPolicy("consumer-compact-v1", 24, 2, 1, ("agent", "public"), ("budget",)),
            "rich": ContextPolicy("consumer-rich-v1", 64, 4, 1, ("agent", "public"), ("budget",)),
        },
        "smb": {
            "compact": ContextPolicy("smb-compact-v1", 32, 2, 1, ("agent", "tenant"), ("inventory",)),
            "rich": ContextPolicy("smb-rich-v1", 80, 5, 1, ("agent", "tenant"), ("margin",)),
        },
        "enterprise": {
            "compact": ContextPolicy("enterprise-compact-v1", 40, 2, 2, ("agent", "tenant"), ("incident",)),
            "rich": ContextPolicy("enterprise-rich-v1", 96, 6, 2, ("agent", "tenant"), ("incident",)),
        },
    }


def demonstration() -> dict:
    """One reproducible synthetic evaluation, with an isolation probe per tier."""
    selector = PolicySelector(approved_policies())
    scenarios = {
        "consumer": ("household", "alex", "Which headphones fit my budget?",
                     "My headphones budget is 80 dollars and I prefer repairable products.",
                     "A public headphone buying guide lists fit and battery life."),
        "smb": ("merchant", "buyer", "Can we restock inventory without hurting margin?",
                "Current inventory is low and margin approval is required before restock.",
                "The merchant inventory forecast expects a seasonal spike."),
        "enterprise": ("operations", "responder", "What is the incident handoff context?",
                       "Incident handoff requires a verified runbook and named approver.",
                       "The incident runbook lists escalation and recovery checks."),
    }
    examples = {}
    for tier, (tenant, agent, query, first, second) in scenarios.items():
        index = ContextIndex()
        for i, body in enumerate((first, second)):
            index.add(Memory(f"{tier}-{i}", tenant, "agent" if i == 0 else "tenant",
                             body, hashlib.sha256(body.encode()).hexdigest(), 1 + i,
                             trust=3, owner_agent_id=agent if i == 0 else None))
        forbidden = f"Other tenant confidential {tier} data."
        index.add(Memory(f"other-{tier}", "unrelated", "tenant", forbidden,
                         hashlib.sha256(forbidden.encode()).hexdigest(), 3, trust=3))
        selected_name, policy = selector.choose(tier)
        bundle = index.compile(query, tenant=tenant, agent=agent, now=4, policy=policy)
        for _ in range(12):
            selector.observe(tier, "compact", Feedback(False, 0.01, 80))
            selector.observe(tier, "rich", Feedback(True, 0.03, 160))
        post_name, _ = selector.choose(tier)
        examples[tier] = {"query": query, "initial_policy": selected_name,
                          "selected_memory_ids": [item["memory_id"] for item in bundle["items"]],
                          "estimated_tokens": bundle["estimated_tokens"],
                          "cross_tenant_excluded": all(item["memory_id"] != f"other-{tier}"
                                                       for item in bundle["items"]),
                          "post_feedback_policy": post_name}
    return {"schema_version": "swarmcontext-personalization-demo/v1",
            "claim": "synthetic_deterministic_baseline_not_production_learning",
            "examples": examples, "policy_stats": selector.snapshot()}
