"""Deterministic, synthetic graph/context evaluation fixtures.

This is a local contract test, not a GraphRAG or production-scale result.
"""

from __future__ import annotations

import hashlib

from .context import ContextIndex, Memory


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def graph_fixture() -> dict:
    """Exercise retrieval, one-hop links, scope and source deletion on fixed labels."""
    index = ContextIndex()
    records = (
        Memory("refund", "merchant-a", "tenant", "Refund case 42 requires ledger review.", _digest("refund-source"), 1, trust=3),
        Memory("ledger", "merchant-a", "tenant", "Ledger entry 42 records a reversal.", _digest("ledger-source"), 2, trust=3),
        Memory("private", "merchant-b", "tenant", "Refund case 42 private competing ledger.", _digest("private-source"), 3, trust=3),
        Memory("agent", "merchant-a", "agent", "Refund case 42 agent-only note.", _digest("agent-source"), 4, trust=3, owner_agent_id="agent-b"),
    )
    for record in records:
        index.add(record)
    index.link("refund", "ledger")
    query = "refund review"
    before = index.compile(query, tenant="merchant-a", agent="agent-a", now=5)
    found = {item["memory_id"] for item in before["items"]}
    expected = {"refund", "ledger"}
    deleted = index.delete_source(_digest("refund-source"), tenant_id="merchant-a")
    after = index.compile(query, tenant="merchant-a", agent="agent-a", now=6)
    remaining = {item["memory_id"] for item in after["items"]}
    return {
        "schema_version": "swarmcontext-graph-eval/v1",
        "fixture": "synthetic-four-record-one-hop-v1",
        "query": query,
        "expected_ids": sorted(expected),
        "selected_ids": sorted(found),
        "source_recall": len(found & expected) / len(expected),
        "source_precision": len(found & expected) / len(found) if found else 0.0,
        "forbidden_scope_leaks": len(found & {"private", "agent"}),
        "deleted_records": deleted,
        "deleted_source_reappeared": "refund" in remaining,
        "remaining_ids": sorted(remaining),
        "estimated_tokens": before["estimated_tokens"],
        "claim": "local_synthetic_contract_only",
        "not_measured": ["graph_extraction", "semantic_retrieval", "answer_grounding", "distributed_consistency", "live_cognee"],
    }
