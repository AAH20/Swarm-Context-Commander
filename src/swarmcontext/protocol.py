"""Narrow A2A-inspired and computer-use event contracts, not A2A conformance."""

from __future__ import annotations

import hashlib

from .registry import ContractError, canonical


def task_envelope(*, task_id: str, agent_id: str, tenant_id: str,
                  context_sha256: str, objective: str, artifact_ref: str | None = None) -> dict:
    if not all(isinstance(x, str) and x and len(x) <= 128 for x in (task_id, agent_id, tenant_id)):
        raise ContractError("invalid task identity")
    if len(context_sha256) != 64 or any(c not in "0123456789abcdef" for c in context_sha256):
        raise ContractError("invalid context digest")
    if not isinstance(objective, str) or not 1 <= len(objective) <= 500:
        raise ContractError("objective must be 1-500 characters")
    if artifact_ref is not None and (not isinstance(artifact_ref, str) or not artifact_ref.startswith("sha256:")
                                     or len(artifact_ref) != 71):
        raise ContractError("artifact reference must be content addressed")
    return {"schema_version": "swarmcontext-task/v1", "task_id": task_id,
            "agent_id": agent_id, "tenant_id": tenant_id, "objective": objective,
            "context_sha256": context_sha256, "artifact_ref": artifact_ref,
            "limits": "A2A-inspired sidecar; not a conformant A2A Task"}


def computer_use_event(*, provider: str, task_id: str, kind: str,
                       observation: str, side_effect: bool) -> dict:
    if provider not in ("openmanus", "browser-use", "openhands", "skyvern", "fixture"):
        raise ContractError("unsupported computer-use provider")
    if kind not in ("navigate", "observe", "input", "click", "submit", "complete"):
        raise ContractError("unsupported computer-use event")
    if not task_id or not isinstance(observation, str) or len(observation) > 10000 or type(side_effect) is not bool:
        raise ContractError("invalid computer-use observation")
    return {"schema_version": "swarmcontext-computer-event/v1", "provider": provider,
            "task_id": task_id, "kind": kind, "side_effect": side_effect,
            "observation_sha256": hashlib.sha256(observation.encode()).hexdigest(),
            "observation_bytes": len(observation.encode()), "authority": "receipt_only"}


def cognee_chunks(response: list, *, tenant_id: str, query: str) -> list[dict]:
    """Normalize saved Cognee CHUNKS output without trusting it as instruction."""
    if not isinstance(query, str) or not tenant_id or not 1 <= len(query) <= 240 or not isinstance(response, list):
        raise ContractError("invalid Cognee response context")
    normalized = []
    for item in response[:10]:
        if not isinstance(item, dict):
            raise ContractError("Cognee result must be an object")
        text = item.get("text", item.get("content"))
        if not isinstance(text, str) or len(text) > 10000:
            raise ContractError("Cognee result lacks bounded text")
        normalized.append({"tenant_id": tenant_id, "source_id_unverified": str(item.get("id", ""))[:128],
                           "text_untrusted": text[:1000],
                           "source_sha256": hashlib.sha256(text.encode()).hexdigest()})
    return normalized
