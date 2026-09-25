"""Small, inspectable lexical-and-graph context compiler and memory GC.

This intentionally precedes a Cognee integration so the retrieval baseline
can be measured independently of embeddings, graph extraction, or LLMs.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .registry import ContractError, canonical


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]{2,}", text.lower()))


@dataclass(frozen=True)
class Memory:
    memory_id: str
    tenant_id: str
    scope: str
    text: str
    source_sha256: str
    created_at: int
    expires_at: int | None = None
    trust: int = 1
    pinned: bool = False
    owner_agent_id: str | None = None


@dataclass(frozen=True)
class ContextPolicy:
    """Explicit user/tenant context preference; never expands access scope."""

    version: str = "default-v1"
    token_budget: int = 512
    max_items: int = 8
    min_trust: int = 0
    allowed_scopes: tuple[str, ...] = ("agent", "tenant", "public")
    preferred_terms: tuple[str, ...] = ()

    def validate(self) -> None:
        if (not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", self.version)
                or not 1 <= self.token_budget <= 32768 or not 1 <= self.max_items <= 32
                or not 0 <= self.min_trust <= 3 or not self.allowed_scopes
                or any(scope not in ("agent", "tenant", "public") for scope in self.allowed_scopes)
                or len(self.preferred_terms) > 10
                or any(not re.fullmatch(r"[a-z0-9_]{2,32}", term) for term in self.preferred_terms)):
            raise ContractError("invalid context policy")


class ContextIndex:
    def __init__(self):
        self.items: dict[str, Memory] = {}
        self.postings: dict[str, set[str]] = {}
        self.edges: dict[str, set[str]] = {}
        self.tombstones: set[str] = set()

    def add(self, item: Memory) -> None:
        if (not item.memory_id or not item.tenant_id or item.scope not in ("agent", "tenant", "public")
                or not 1 <= len(item.text) <= 10000 or not 0 <= item.trust <= 3
                or not re.fullmatch(r"[0-9a-f]{64}", item.source_sha256)):
            raise ContractError("invalid memory record")
        if item.scope == "agent" and (not item.owner_agent_id or len(item.owner_agent_id) > 128):
            raise ContractError("agent-scoped memory requires explicit owner_agent_id")
        if item.source_sha256 in self.tombstones:
            raise ContractError("deleted source cannot be reingested")
        if item.memory_id in self.items:
            raise ContractError("duplicate memory ID")
        self.items[item.memory_id] = item
        for term in _terms(item.text):
            self.postings.setdefault(term, set()).add(item.memory_id)

    def link(self, left: str, right: str) -> None:
        if left not in self.items or right not in self.items or left == right:
            raise ContractError("graph edge endpoints must exist and differ")
        if self.items[left].tenant_id != self.items[right].tenant_id:
            raise ContractError("cross-tenant memory edges are prohibited")
        self.edges.setdefault(left, set()).add(right)
        self.edges.setdefault(right, set()).add(left)

    def _visible(self, item: Memory, tenant: str, agent: str, now: int) -> bool:
        if item.expires_at is not None and item.expires_at <= now and not item.pinned:
            return False
        if item.scope == "public":
            return True
        if item.tenant_id != tenant:
            return False
        return item.scope == "tenant" or item.owner_agent_id == agent

    def compile(self, query: str, *, tenant: str, agent: str, now: int,
                token_budget: int = 512, max_items: int = 8, policy: ContextPolicy | None = None) -> dict:
        policy = policy or ContextPolicy(token_budget=token_budget, max_items=max_items)
        policy.validate()
        if not query or not tenant or not agent:
            raise ContractError("invalid context request")
        terms = _terms(query)
        ids = set().union(*(self.postings.get(term, set()) for term in terms)) if terms else set()
        neighbors = set().union(*(self.edges.get(item, set()) for item in ids)) if ids else set()
        ids |= neighbors
        ids |= {key for key, item in self.items.items() if item.pinned and self._visible(item, tenant, agent, now)}
        ranked = []
        for key in ids:
            item = self.items[key]
            if (not self._visible(item, tenant, agent, now) or item.scope not in policy.allowed_scopes
                    or item.trust < policy.min_trust):
                continue
            overlap = len(terms & _terms(item.text))
            preference = len(set(policy.preferred_terms) & _terms(item.text))
            rank = overlap * 4 + preference * 2 + item.trust * 2 + int(item.pinned) * 100 + int(key in neighbors)
            ranked.append((-rank, -item.created_at, key, item))
        ranked.sort()
        selected, hashes, used = [], set(), 0
        for _, _, key, item in ranked:
            text_hash = hashlib.sha256(item.text.encode()).hexdigest()
            if text_hash in hashes:
                continue
            estimated = max(1, (len(item.text) + 3) // 4)
            if used + estimated > policy.token_budget:
                continue
            selected.append({"memory_id": key, "text": item.text, "source_sha256": item.source_sha256,
                             "scope": item.scope, "trust": item.trust})
            hashes.add(text_hash)
            used += estimated
            if len(selected) == policy.max_items:
                break
        payload = {"schema_version": "swarmcontext-bundle/v1", "tenant_id": tenant,
                   "agent_id": agent, "items": selected, "estimated_tokens": used,
                   "token_budget": policy.token_budget, "policy_version": policy.version}
        payload["bundle_sha256"] = hashlib.sha256(canonical(payload).encode()).hexdigest()
        return payload

    def _remove(self, key: str) -> None:
        item = self.items.pop(key)
        for term in _terms(item.text):
            posting = self.postings[term]
            posting.discard(key)
            if not posting:
                del self.postings[term]
        for neighbor in self.edges.pop(key, set()):
            self.edges[neighbor].discard(key)

    def delete_source(self, source_sha256: str) -> int:
        if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise ContractError("invalid source digest")
        self.tombstones.add(source_sha256)
        keys = [key for key, item in self.items.items() if item.source_sha256 == source_sha256]
        for key in keys:
            self._remove(key)
        return len(keys)

    def collect_expired(self, now: int) -> int:
        keys = [key for key, item in self.items.items()
                if not item.pinned and item.expires_at is not None and item.expires_at <= now]
        for key in keys:
            self._remove(key)
        return len(keys)
