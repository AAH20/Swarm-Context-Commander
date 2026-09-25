"""Opt-in loopback Cognee CHUNKS retrieval into tenant-scoped untrusted memory."""

from __future__ import annotations

import hashlib
import json
from urllib import error, request
from urllib.parse import urlsplit

from .context import ContextIndex, Memory
from .registry import ContractError, canonical


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ContractError("Cognee HTTP redirects are not allowed")


def search_local(base_url: str, query: str, *, allow_network: bool = False,
                 top_k: int = 10) -> list:
    parsed = urlsplit(base_url)
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1")
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ContractError("Cognee URL must be a local HTTP origin")
    if not allow_network:
        raise ContractError("explicit local-network opt-in required")
    if not isinstance(query, str) or not 1 <= len(query) <= 240 or not 1 <= top_k <= 10:
        raise ContractError("invalid Cognee query or top_k")
    payload = canonical({"query": query, "search_type": "CHUNKS", "top_k": top_k}).encode()
    req = request.Request(base_url.rstrip("/") + "/api/v1/search", payload,
                          headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.build_opener(_NoRedirect()).open(req, timeout=10) as response:
            raw = response.read(65537)
    except (error.URLError, TimeoutError) as exc:
        raise ContractError(f"local Cognee request failed: {type(exc).__name__}") from exc
    if len(raw) > 65536:
        raise ContractError("Cognee response exceeds 64 KiB")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("Cognee response is not JSON") from exc
    if not isinstance(value, list):
        raise ContractError("Cognee CHUNKS response must be a list")
    return value


def ingest_chunks(index: ContextIndex, response: list, *, tenant_id: str, now: int,
                  max_items: int = 10) -> int:
    """Treat Cognee text as low-trust data; duplicate content is not reinserted."""
    if not tenant_id or not isinstance(response, list) or len(response) > max_items:
        raise ContractError("invalid Cognee response size or tenant")
    pending = []
    for item in response:
        if not isinstance(item, dict):
            raise ContractError("Cognee chunk must be an object")
        text = item.get("text", item.get("content"))
        if not isinstance(text, str) or not 1 <= len(text) <= 10000:
            raise ContractError("Cognee chunk needs bounded text/content")
        digest = hashlib.sha256(text.encode()).hexdigest()
        memory_id = "cognee:" + hashlib.sha256(canonical([tenant_id, digest]).encode()).hexdigest()
        if memory_id not in index.items:
            pending.append(Memory(memory_id, tenant_id, "tenant", text, digest, now,
                                  trust=0, pinned=False))
    if len({item.memory_id for item in pending}) != len(pending):
        raise ContractError("Cognee response contains duplicate content")
    if any((item.tenant_id, item.source_sha256) in index.tombstones for item in pending):
        raise ContractError("Cognee response contains a deleted source")
    for item in pending:
        index.add(item)
    return len(pending)
